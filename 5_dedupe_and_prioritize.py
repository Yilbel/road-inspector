"""
5_dedupe_and_prioritize.py
---------------------------
2_detect.py'nin ürettiği ham tespit listesini (tespitler.csv) işler:

  1) TEKİLLEŞTİRME: Aynı kategoriden, zaman ve konum olarak birbirine
     yakın tespitleri (araç yaklaşırken/geçerken aynı çukur/tabela
     birden çok karede görünür) tek bir fiziksel nesne olarak birleştirir.
     Kaç farklı karede görüldüğü "gorulme_sayisi" sütununda saklanır --
     bu dolaylı bir güven göstergesidir (çok karede görülen bir tespit,
     tek seferlik bir yanlış alarmdan çok daha güvenilirdir).

  2) ÖNCELİK PUANLAMASI: Basit kurallarla her tespide düşük/orta/yüksek
     öncelik etiketi verir:
       - yol hasarı: kutucuk büyüklüğü (yakın/büyük çukur = daha acil)
                      + kaç karede görüldüğü
       - trafik ışığı/tabela: şimdilik hep "bilgi" (aciliyet çukur kadar
         kritik değil, ama liste tam olsun diye tutuluyor)

Kullanım:
    python 5_dedupe_and_prioritize.py --detections output/detections/tespitler.csv --out output/detections/tespitler_tekil.csv
"""

import argparse
import ast
import pandas as pd


# Aynı nesne sayılması için zaman ve konum yakınlık eşikleri
TIME_GAP_SECONDS = 2.0      # bu kadar saniye içinde tekrar görülürse "aynı nesne" say
CENTER_DIST_RATIO = 0.15    # kutucuk merkezleri, kare genişliğinin bu oranından yakınsa "aynı nesne" say


def bbox_center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def bbox_area(bbox):
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def parse_bbox(value):
    if isinstance(value, str):
        return ast.literal_eval(value)
    return value


def dedupe(df: pd.DataFrame, frame_width: int = 1920) -> pd.DataFrame:
    df = df.copy()
    df["bbox_x1y1x2y2"] = df["bbox_x1y1x2y2"].apply(parse_bbox)
    df["zaman_sn"] = pd.to_numeric(df["zaman_sn"], errors="coerce")
    df = df.dropna(subset=["zaman_sn"]).sort_values(["kategori", "zaman_sn"]).reset_index(drop=True)

    dist_threshold = frame_width * CENTER_DIST_RATIO

    clusters = []  # her biri: {"rows": [...], "last_time": t, "last_center": (x,y)}

    for _, row in df.iterrows():
        bbox = row["bbox_x1y1x2y2"]
        center = bbox_center(bbox)
        t = row["zaman_sn"]
        kategori = row["kategori"]

        matched = None
        for cluster in clusters:
            if cluster["kategori"] != kategori:
                continue
            if t - cluster["last_time"] > TIME_GAP_SECONDS:
                continue
            cx, cy = cluster["last_center"]
            dist = ((center[0] - cx) ** 2 + (center[1] - cy) ** 2) ** 0.5
            if dist <= dist_threshold:
                matched = cluster
                break

        if matched is not None:
            matched["rows"].append(row)
            matched["last_time"] = t
            matched["last_center"] = center
        else:
            clusters.append({
                "kategori": kategori,
                "rows": [row],
                "last_time": t,
                "last_center": center,
            })

    result_rows = []
    for cluster in clusters:
        rows = cluster["rows"]
        best = max(rows, key=lambda r: r["guven"])
        areas = [bbox_area(r["bbox_x1y1x2y2"]) for r in rows]
        max_area = max(areas)

        result_rows.append({
            "kategori": cluster["kategori"],
            "ilk_gorulme_sn": rows[0]["zaman_sn"],
            "son_gorulme_sn": rows[-1]["zaman_sn"],
            "gorulme_sayisi": len(rows),
            "en_yuksek_guven": round(best["guven"], 3),
            "en_buyuk_kutucuk_alani": round(max_area, 0),
            "temsili_kare": best["kaynak_kare"],
            "bbox_x1y1x2y2": best["bbox_x1y1x2y2"],
        })

    return pd.DataFrame(result_rows).sort_values(["kategori", "ilk_gorulme_sn"]).reset_index(drop=True)


def assign_priority(df: pd.DataFrame, frame_width: int = 1920, frame_height: int = 1080) -> pd.DataFrame:
    df = df.copy()
    frame_area = frame_width * frame_height

    def priority_for_row(row):
        kategori = row["kategori"]
        if not kategori.startswith("yol hasarı"):
            return "bilgi"

        area_ratio = row["en_buyuk_kutucuk_alani"] / frame_area
        gorulme = row["gorulme_sayisi"]

        # Basit kural seti: büyük + sık görülen = yüksek öncelik
        if area_ratio > 0.03 and gorulme >= 3:
            return "yüksek"
        elif area_ratio > 0.01 or gorulme >= 2:
            return "orta"
        else:
            return "düşük"

    df["oncelik"] = df.apply(priority_for_row, axis=1)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", default="output/detections/tespitler.csv")
    parser.add_argument("--out", default="output/detections/tespitler_tekil.csv")
    parser.add_argument("--frame-width", type=int, default=1920, help="Video genişliği (piksel)")
    parser.add_argument("--frame-height", type=int, default=1080, help="Video yüksekliği (piksel)")
    args = parser.parse_args()

    df = pd.read_csv(args.detections)
    print(f"Ham tespit sayısı: {len(df)}")

    deduped = dedupe(df, frame_width=args.frame_width)
    prioritized = assign_priority(deduped, frame_width=args.frame_width, frame_height=args.frame_height)

    prioritized.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Tekilleştirilmiş nesne sayısı: {len(prioritized)}")
    print(f"Çıktı -> {args.out}")

    print("\nKategoriye göre özet:")
    print(prioritized.groupby("kategori").size().sort_values(ascending=False).to_string())

    print("\nYol hasarı önceliklerine göre dağılım:")
    road_damage = prioritized[prioritized["kategori"].str.startswith("yol hasarı")]
    if len(road_damage) > 0:
        print(road_damage.groupby("oncelik").size().to_string())
    else:
        print("(yol hasarı tespiti yok)")
