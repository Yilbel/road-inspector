"""
2_detect.py
-----------
Çıkarılan kareler üzerinde nesne tespiti yapar.

Kendi modelimizi eğitmiyoruz -- üç HAZIR açık kaynak model kullanıyoruz:

  1) yolov8n.pt (Ultralytics, COCO)
     -> "traffic light", "stop sign" gibi hazır sınıflar.
     İlk çalıştırmada otomatik indirilir, hiçbir şey yapmana gerek yok.

  2) Road damage modeli (çukur + çatlaklar)
     Kaynak: https://github.com/oracl4/RoadDamageDetection
     O repoyu klonlayıp models/ klasöründeki .pt dosyasını
     buraya (models/road_damage.pt) kopyala:
         git clone https://github.com/oracl4/RoadDamageDetection.git
         cp RoadDamageDetection/models/*.pt models/road_damage.pt

  3) Genel trafik tabelası modeli
     Kaynak: https://huggingface.co/nezahatkorkmaz/traffic-sign-detection
     Hugging Face'ten indirip models/traffic_sign.pt olarak kaydet:
         pip install huggingface_hub
         python -c "from huggingface_hub import hf_hub_download; \
             print(hf_hub_download('nezahatkorkmaz/traffic-sign-detection', 'best.pt', local_dir='models'))"
         # inen dosyayı models/traffic_sign.pt olarak yeniden adlandır

İkinci ve üçüncü modeller olmadan da script çalışır (sadece COCO
sınıflarını -- trafik ışığı, dur tabelası -- tespit eder), ama tam
performans için ikisini de indirmen önerilir.

Kullanım:
    python 2_detect.py --frames output/frames --out output/detections \
        --road-damage-model models/road_damage.pt \
        --sign-model models/traffic_sign.pt
"""

import os
import glob
import argparse
import pandas as pd
from ultralytics import YOLO

# COCO'nun genel modelinde işimize yarayan sınıflar
RELEVANT_COCO_CLASSES = {
    "traffic light": "trafik ışığı",
    "stop sign": "dur tabelası",
}

# Güven eşikleri (0-1 arası), modele göre ayrı ayrı ayarlanmış.
# Road damage modeli bizim video koşullarında daha çok yanlış alarm
# verdiği için onun eşiğini daha yüksek tuttuk.
CONF_THRESHOLD_GENERAL = 0.35      # trafik ışığı, dur tabelası (COCO)
CONF_THRESHOLD_ROAD_DAMAGE = 0.45  # çukur, çatlak
CONF_THRESHOLD_SIGN = 0.35         # genel tabelalar


def run_detection(frames_dir: str, out_dir: str, road_damage_model_path: str | None, sign_model_path: str | None):
    os.makedirs(out_dir, exist_ok=True)
    crops_dir = os.path.join(out_dir, "crops")
    os.makedirs(crops_dir, exist_ok=True)

    general_model = YOLO("yolov8n.pt")  # ilk çalıştırmada otomatik indirilir
    road_damage_model = YOLO(road_damage_model_path) if road_damage_model_path and os.path.exists(road_damage_model_path) else None
    sign_model = YOLO(sign_model_path) if sign_model_path and os.path.exists(sign_model_path) else None

    if road_damage_model is None:
        print("UYARI: road-damage modeli bulunamadı, çukur/çatlak tespiti YAPILMAYACAK.")
    if sign_model is None:
        print("UYARI: sign modeli bulunamadı, genel tabela tespiti YAPILMAYACAK (sadece 'dur' tabelası COCO'dan gelecek).")

    frame_paths = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
    if not frame_paths:
        raise RuntimeError(f"{frames_dir} içinde .jpg bulunamadı. Önce 1_extract_frames.py çalıştır.")

    rows = []
    detection_id = 0

    for frame_path in frame_paths:
        filename = os.path.basename(frame_path)
        # frame_00001_t000012.50s.jpg -> zaman damgasını çek
        try:
            timestamp = filename.split("_t")[1].replace("s.jpg", "")
        except IndexError:
            timestamp = "bilinmiyor"

        results_list = []

        # 1) Genel model (trafik ışığı, tabela vb.)
        results = general_model(frame_path, conf=CONF_THRESHOLD_GENERAL, verbose=False)[0]
        for box in results.boxes:
            cls_name = general_model.names[int(box.cls[0])]
            if cls_name in RELEVANT_COCO_CLASSES:
                results_list.append({
                    "category": RELEVANT_COCO_CLASSES[cls_name],
                    "confidence": float(box.conf[0]),
                    "bbox": box.xyxy[0].tolist(),
                })

        # 2) Road damage modeli (çukur, çatlaklar)
        if road_damage_model is not None:
            rd_results = road_damage_model(frame_path, conf=CONF_THRESHOLD_ROAD_DAMAGE, verbose=False)[0]
            for box in rd_results.boxes:
                cls_name = road_damage_model.names[int(box.cls[0])]
                results_list.append({
                    "category": f"yol hasarı ({cls_name})",
                    "confidence": float(box.conf[0]),
                    "bbox": box.xyxy[0].tolist(),
                })

        # 3) Genel trafik tabelası modeli
        if sign_model is not None:
            sign_results = sign_model(frame_path, conf=CONF_THRESHOLD_SIGN, verbose=False)[0]
            for box in sign_results.boxes:
                cls_name = sign_model.names[int(box.cls[0])]
                results_list.append({
                    "category": f"tabela ({cls_name})",
                    "confidence": float(box.conf[0]),
                    "bbox": box.xyxy[0].tolist(),
                })

        for det in results_list:
            detection_id += 1
            rows.append({
                "id": detection_id,
                "kaynak_kare": filename,
                "zaman_sn": timestamp,
                "kategori": det["category"],
                "guven": round(det["confidence"], 3),
                "bbox_x1y1x2y2": det["bbox"],
            })

        if results_list:
            print(f"{filename}: {len(results_list)} tespit")

    df = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, "tespitler.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nToplam {len(df)} tespit -> {csv_path}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", default="output/frames", help="Kare klasörü")
    parser.add_argument("--out", default="output/detections", help="Çıktı klasörü")
    parser.add_argument("--road-damage-model", default="models/road_damage.pt", help="Çukur/çatlak modeli .pt yolu")
    parser.add_argument("--sign-model", default="models/traffic_sign.pt", help="Trafik tabelası modeli .pt yolu")
    args = parser.parse_args()

    run_detection(args.frames, args.out, args.road_damage_model, args.sign_model)
