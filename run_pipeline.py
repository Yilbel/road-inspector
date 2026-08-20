"""
run_pipeline.py
----------------
Tüm yol denetim pipeline'ını TEK KOMUTLA çalıştırır:
  1_extract_frames -> 2_detect -> 5_dedupe_and_prioritize
  -> (varsa) 7_extract_gps -> 8_join_gps -> 6_final_report -> 9_make_map

Kullanım:
    python run_pipeline.py --video input\video.mp4
    python run_pipeline.py --video input\video.mp4 --fps 2 --no-gps
    python run_pipeline.py --video input\video.mp4 --no-map

Notlar:
- Video çözünürlüğü otomatik tespit edilir (--frame-width/--frame-height
  elle vermene gerek yok).
- GPS çıkarma adımı varsayılan olarak denenir; video GoPro/dashcam GPS
  telemetrisi içermiyorsa (ör. GPMF bulunamazsa) otomatik atlanır ve
  pipeline konum bilgisi olmadan devam eder. --no-gps ile baştan
  kapatılabilir.
- Her adım kendi alt sürecinde (subprocess) çalışır; biri hata verirse
  pipeline orada net bir mesajla durur, sonraki adımlara geçmez.
"""
import argparse
import os
import subprocess
import sys
import cv2


def run_step(description: str, cmd: list, allow_fail: bool = False) -> bool:
    """Bir pipeline adımını çalıştırır. Başarılıysa True, başarısızsa
    (allow_fail=True ise) False döner; allow_fail=False iken hata olursa
    programı net bir mesajla sonlandırır."""
    print(f"\n{'=' * 60}")
    print(f"ADIM: {description}")
    print(f"Komut: {' '.join(cmd)}")
    print("=" * 60)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        if allow_fail:
            print(f"\n[UYARI] '{description}' adımı başarısız oldu (çıkış kodu {result.returncode}), "
                  f"bu adım atlanıyor ve pipeline'a devam ediliyor.")
            return False
        else:
            print(f"\n[HATA] '{description}' adımı başarısız oldu (çıkış kodu {result.returncode}).")
            print("Pipeline burada durduruldu. Yukarıdaki hata mesajına bakıp sorunu giderdikten "
                  "sonra tekrar çalıştırabilirsin.")
            sys.exit(1)
    return True


def get_video_resolution(video_path: str):
    if not os.path.isfile(video_path):
        print(f"\n[HATA] Video bulunamadı: {video_path}")
        print("Videonun doğru yolda olduğundan emin ol (ör. input\\video.mp4) ve --video ile belirt.")
        sys.exit(1)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"\n[HATA] Video açılamadı: {video_path}")
        print("Dosyanın bozuk olmadığından ve desteklenen bir formatta (mp4, mov vb.) olduğundan emin ol.")
        sys.exit(1)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if width == 0 or height == 0:
        print(f"\n[HATA] Video çözünürlüğü okunamadı: {video_path}")
        sys.exit(1)
    return width, height


def main():
    parser = argparse.ArgumentParser(
        description="Yol denetim pipeline'ını tek komutla baştan sona çalıştırır."
    )
    parser.add_argument("--video", required=True, help="Girdi videosunun yolu (ör. input\\video.mp4)")
    parser.add_argument("--fps", type=float, default=2.0, help="Saniyede kaç kare örneklenecek (varsayılan: 2)")
    parser.add_argument("--frames", default="output/frames", help="Kare çıktı klasörü")
    parser.add_argument("--out", default="output/report", help="Rapor çıktı klasörü")
    parser.add_argument("--no-gps", action="store_true", help="GPS çıkarma/eşleştirme adımlarını tamamen atla")
    parser.add_argument("--no-map", action="store_true", help="HTML harita üretimini atla")
    args = parser.parse_args()

    python_exe = sys.executable  # aktif venv'in python.exe'si

    print("Yol Denetim Pipeline'ı başlıyor")
    print(f"Video: {args.video}")

    # Çözünürlüğü otomatik tespit et
    width, height = get_video_resolution(args.video)
    print(f"Tespit edilen çözünürlük: {width}x{height}")

    # 1) Kare çıkarma
    run_step(
        "Videodan kare çıkarma",
        [python_exe, "1_extract_frames.py", "--video", args.video, "--fps", str(args.fps), "--out", args.frames],
    )

    # 2) Tespit
    run_step(
        "Modellerle tespit (trafik ışığı / dur tabelası / yol hasarı / tabela)",
        [python_exe, "2_detect.py", "--frames", args.frames],
    )

    # 3) Tekilleştirme + öncelik
    run_step(
        "Tekilleştirme ve öncelik puanlaması",
        [python_exe, "5_dedupe_and_prioritize.py", "--frame-width", str(width), "--frame-height", str(height)],
    )

    # 4) GPS (opsiyonel, hata verirse pipeline durmaz, sadece o adım atlanır)
    gps_ok = False
    detections_file = "output/detections/tespitler_tekil.csv"
    if not args.no_gps:
        gps_extract_ok = run_step(
            "GPS verisini videodan çıkarma (varsa)",
            [python_exe, "7_extract_gps.py", "--video", args.video],
            allow_fail=True,
        )
        if gps_extract_ok:
            gps_ok = run_step(
                "Tespitleri GPS konumuyla eşleştirme",
                [python_exe, "8_join_gps.py"],
                allow_fail=True,
            )
            if gps_ok:
                detections_file = "output/detections/tespitler_gps.csv"
        if not gps_ok:
            print("\n[BİLGİ] GPS verisi bulunamadı ya da eşleştirilemedi. "
                  "Pipeline konum bilgisi olmadan devam ediyor.")
    else:
        print("\n[BİLGİ] --no-gps verildi, GPS adımları atlanıyor.")

    # 5) Final Excel raporu
    run_step(
        "Final Excel raporu ve işaretli görseller",
        [python_exe, "6_final_report.py", "--frames", args.frames, "--detections", detections_file, "--out", args.out],
    )

    # 6) HTML harita (opsiyonel)
    if not args.no_map:
        run_step(
            "Etkileşimli HTML harita",
            [python_exe, "9_make_map.py"],
            allow_fail=True,
        )
    else:
        print("\n[BİLGİ] --no-map verildi, harita adımı atlanıyor.")

    print("\n" + "=" * 60)
    print("PIPELINE TAMAMLANDI")
    print("=" * 60)
    print(f"Excel raporu: {args.out}/belediye_raporu_final.xlsx")
    print(f"İşaretli görseller: {args.out}/isaretli_kareler/")
    if not args.no_map:
        print(f"HTML harita: {args.out}/harita.html")


if __name__ == "__main__":
    main()
