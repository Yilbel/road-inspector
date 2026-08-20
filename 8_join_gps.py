"""
8_join_gps.py
--------------
gopro2gpx'in ürettiği gps_track.csv (mutlak zaman damgalı enlem/boylam)
ile 5_dedupe_and_prioritize.py'nin ürettiği tespitler_tekil.csv'yi
(videonun başından itibaren geçen saniye) zaman bazında eşleştirir.

Mantık: GPS CSV'sindeki ilk satır "t=0" (videonun başlangıcı) kabul
edilir, sonraki her GPS noktası için o ana kadar geçen saniye hesaplanır.
Her tespit için, kendi "ilk_gorulme_sn" değerine en yakın GPS noktası
bulunup enlem/boylam eklenir.

Kullanım:
    python 8_join_gps.py --detections output/detections/tespitler_tekil.csv --gps output/gps/gps_track.csv --out output/detections/tespitler_gps.csv
"""

import argparse
import pandas as pd


def join(detections_path: str, gps_path: str, out_path: str):
    det = pd.read_csv(detections_path)
    gps = pd.read_csv(gps_path)

    gps["time"] = pd.to_datetime(gps["time"])
    gps = gps.sort_values("time").reset_index(drop=True)
    first_time = gps["time"].iloc[0]
    gps["zaman_sn"] = (gps["time"] - first_time).dt.total_seconds()

    # Her tespit için en yakın GPS zamanını bul (basit "nearest" eşleştirme)
    gps_times = gps["zaman_sn"].values

    def find_nearest_gps(t):
        idx = (abs(gps_times - t)).argmin()
        return gps.iloc[idx]

    enlemler = []
    boylamlar = []
    harita_linkleri = []

    for _, row in det.iterrows():
        t = row["ilk_gorulme_sn"]
        nearest = find_nearest_gps(t)
        lat, lon = nearest["latitude"], nearest["longitude"]
        enlemler.append(lat)
        boylamlar.append(lon)
        harita_linkleri.append(f"https://www.google.com/maps?q={lat},{lon}")

    det["enlem"] = enlemler
    det["boylam"] = boylamlar
    det["google_maps"] = harita_linkleri

    det.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"{len(det)} tespide konum eklendi -> {out_path}")
    print(f"\nÖrnek (ilk 3 satır):")
    print(det[["kategori", "ilk_gorulme_sn", "enlem", "boylam"]].head(3).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", default="output/detections/tespitler_tekil.csv")
    parser.add_argument("--gps", default="output/gps/gps_track.csv")
    parser.add_argument("--out", default="output/detections/tespitler_gps.csv")
    args = parser.parse_args()

    join(args.detections, args.gps, args.out)
