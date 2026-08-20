"""
6_final_report.py
------------------
5_dedupe_and_prioritize.py'nin ürettiği tekilleştirilmiş, öncelik
puanlı listeden BELEDİYEYE SUNULACAK final raporu üretir:
  - Her benzersiz nesne için tek bir işaretli görsel (temsili kare)
  - Öncelik sütunu içeren, kategoriye göre gruplu Excel raporu

Kullanım:
    python 6_final_report.py --frames output/frames --detections output/detections/tespitler_tekil.csv --out output/report
"""

import os
import ast
import argparse
import cv2
import pandas as pd


def parse_bbox(value):
    if isinstance(value, str):
        return ast.literal_eval(value)
    return value


PRIORITY_COLOR = {
    "yüksek": (0, 0, 255),   # kırmızı
    "orta": (0, 140, 255),   # turuncu
    "düşük": (0, 255, 255),  # sarı
    "bilgi": (255, 0, 0),    # mavi
}


def draw_and_save(frames_dir: str, df: pd.DataFrame, out_dir: str):
    annotated_dir = os.path.join(out_dir, "isaretli_kareler")
    os.makedirs(annotated_dir, exist_ok=True)

    for idx, row in df.iterrows():
        frame_name = row["temsili_kare"]
        frame_path = os.path.join(frames_dir, frame_name)
        img = cv2.imread(frame_path)
        if img is None:
            continue

        bbox = parse_bbox(row["bbox_x1y1x2y2"])
        x1, y1, x2, y2 = map(int, bbox)
        color = PRIORITY_COLOR.get(row["oncelik"], (0, 255, 0))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        label = f"{row['kategori']} | {row['oncelik']} | {row['gorulme_sayisi']}x gorulmus"
        cv2.putText(img, label, (x1, max(y1 - 12, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Dosya adını nesne no'suyla benzersiz yapalım (aynı kare birden fazla nesne için temsili olabilir)
        out_name = f"nesne_{idx+1:03d}_{row['kategori'].replace(' ', '_').replace('(', '').replace(')', '')}.jpg"
        cv2.imwrite(os.path.join(annotated_dir, out_name), img)

    print(f"İşaretli kareler -> {annotated_dir}")


def build_excel(df: pd.DataFrame, out_dir: str):
    excel_path = os.path.join(out_dir, "belediye_raporu_final.xlsx")

    summary = df.groupby("kategori").size().reset_index(name="adet").sort_values("adet", ascending=False)

    road_damage = df[df["kategori"].str.startswith("yol hasarı")].copy()
    road_damage_priority = (
        road_damage.groupby("oncelik").size().reset_index(name="adet")
        if len(road_damage) > 0 else pd.DataFrame(columns=["oncelik", "adet"])
    )

    display_df = df[[
        "kategori", "oncelik", "gorulme_sayisi", "en_yuksek_guven",
        "ilk_gorulme_sn", "son_gorulme_sn", "temsili_kare"
    ]].sort_values(["kategori", "oncelik"])

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Özet", index=False)
        road_damage_priority.to_excel(writer, sheet_name="Yol Hasarı Önceliği", index=False)
        display_df.to_excel(writer, sheet_name="Tüm Nesneler", index=False)

    print(f"Excel raporu -> {excel_path}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", default="output/frames")
    parser.add_argument("--detections", default="output/detections/tespitler_tekil.csv")
    parser.add_argument("--out", default="output/report")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    df = pd.read_csv(args.detections)

    summary = build_excel(df, args.out)
    draw_and_save(args.frames, df, args.out)

    print(f"\nToplam {len(df)} benzersiz nesne.")
    print(summary.to_string(index=False))
