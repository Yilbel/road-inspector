"""
7_extract_gps.py
-----------------
Videonun içine gömülü GoPro GPMF telemetrisinden GPS verisini çıkarır.
İki çıktı üretir:
  - output/gps/gps_track.gpx   -> standart GPX formatı (Google Earth,
                                   GPX görüntüleyicilerde açılabilir)
  - output/gps/gps_track.csv   -> zaman_sn, enlem, boylam sütunlu basit
                                   tablo, videonun BAŞINDAN itibaren geçen
                                   saniyeyi baz alır (tespitler.csv'deki
                                   "zaman_sn" ile aynı referans noktası)

Kullanım:
    python 7_extract_gps.py --video input/video.mp4 --out output/gps
"""

import os
import argparse
import gpmf
import gpxpy


def extract(video_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    print("GPMF akışı okunuyor (ffmpeg ile)...")
    stream = gpmf.io.extract_gpmf_stream(video_path)

    print("GPS blokları çıkarılıyor...")
    gps_blocks = gpmf.gps.extract_gps_blocks(stream)
    if not gps_blocks:
        raise RuntimeError(
            "Videoda GPS bloğu bulunamadı. Video GoPro GPMF formatında "
            "GPS içermiyor olabilir (ayarlarda GPS kapalıysa da böyle olur)."
        )

    gps_data = list(map(gpmf.gps.parse_gps_block, gps_blocks))
    print(f"{len(gps_data)} GPS bloğu ayrıştırıldı.")

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_track.segments.append(gpmf.gps.make_pgx_segment(gps_data))

    gpx_path = os.path.join(out_dir, "gps_track.gpx")
    with open(gpx_path, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
    print(f"GPX -> {gpx_path}")

    points = gpx.tracks[0].segments[0].points
    if not points:
        raise RuntimeError("GPX içinde nokta bulunamadı.")

    first_time = points[0].time
    csv_path = os.path.join(out_dir, "gps_track.csv")
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("zaman_sn,enlem,boylam,irtifa\n")
        for p in points:
            elapsed = (p.time - first_time).total_seconds()
            f.write(f"{elapsed:.3f},{p.latitude},{p.longitude},{p.elevation or ''}\n")

    print(f"CSV -> {csv_path}")
    print(f"\nToplam {len(points)} GPS noktası, video süresine yayılmış.")
    print(f"İlk nokta: {points[0].latitude:.6f}, {points[0].longitude:.6f}")
    print(f"Son nokta: {points[-1].latitude:.6f}, {points[-1].longitude:.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Girdi video yolu")
    parser.add_argument("--out", default="output/gps", help="GPS çıktı klasörü")
    args = parser.parse_args()

    extract(args.video, args.out)
