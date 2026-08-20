"""
9_make_map.py
--------------
Konum eklenmiş tespitleri (8_join_gps.py çıktısı) tek bir HTML
dosyasında etkileşimli bir haritaya dönüştürür. Belediye ekibi
Excel'de satır aramak yerine haritayı açar, renkli iğnelere tıklar,
küçük fotoğrafı + bilgiyi görür.

Fotoğraflar dosyanın İÇİNE gömülüdür (base64) -- yani tek bir .html
dosyasını e-postayla/WhatsApp'la gönderebilir, internet olmadan da
tarayıcıda açabilirsin, ekstra klasör taşımana gerek kalmaz.

Kullanım:
    python 9_make_map.py --detections output/detections/tespitler_gps.csv --images output/report/isaretli_kareler --out output/report/harita.html
"""

import os
import base64
import argparse
import pandas as pd
import folium
from folium.plugins import MarkerCluster

# Öncelik/kategoriye göre iğne rengi (folium'un desteklediği isimler)
COLOR_MAP = {
    "yüksek": "red",
    "orta": "orange",
    "düşük": "lightred",
    "bilgi": "blue",
}

ICON_MAP = {
    "yüksek": "exclamation-triangle",
    "orta": "exclamation-circle",
    "düşük": "info-circle",
    "bilgi": "info-circle",
}


def sanitize(name: str) -> str:
    return name.replace(" ", "_").replace("(", "").replace(")", "")


def image_to_base64(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_map(detections_path: str, images_dir: str, out_path: str):
    df = pd.read_csv(detections_path)

    if "enlem" not in df.columns or "boylam" not in df.columns:
        raise RuntimeError(
            "CSV'de enlem/boylam sütunu yok. Önce 8_join_gps.py çalıştırılmalı."
        )

    center_lat = df["enlem"].mean()
    center_lon = df["boylam"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="OpenStreetMap")

    # Rota çizgisi -- tüm tespit noktalarını zamana göre sıraya koyup birleştir
    if "ilk_gorulme_sn" in df.columns:
        route = df.sort_values("ilk_gorulme_sn")[["enlem", "boylam"]].values.tolist()
        folium.PolyLine(route, color="gray", weight=2, opacity=0.5, dash_array="5,10").add_to(m)

    cluster = MarkerCluster(name="Tespitler").add_to(m)

    for idx, row in df.iterrows():
        kategori = row["kategori"]
        oncelik = row.get("oncelik", "bilgi")
        color = COLOR_MAP.get(oncelik, "gray")
        icon_name = ICON_MAP.get(oncelik, "info-circle")

        img_filename = f"nesne_{idx+1:03d}_{sanitize(kategori)}.jpg"
        img_path = os.path.join(images_dir, img_filename)
        img_b64 = image_to_base64(img_path)

        maps_link = row.get("google_maps", f"https://www.google.com/maps?q={row['enlem']},{row['boylam']}")

        popup_html = f"""
        <div style="width:260px; font-family:sans-serif;">
            <b>{kategori}</b><br>
            Öncelik: <b>{oncelik}</b><br>
            Görülme sayısı: {row.get('gorulme_sayisi', '-')}<br>
            Güven: {row.get('en_yuksek_guven', '-')}<br>
        """
        if img_b64:
            popup_html += f'<img src="data:image/jpeg;base64,{img_b64}" style="width:100%; margin-top:6px; border-radius:4px;"><br>'
        popup_html += f'<a href="{maps_link}" target="_blank">Google Maps\'te aç →</a></div>'

        folium.Marker(
            location=[row["enlem"], row["boylam"]],
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{kategori} ({oncelik})",
            icon=folium.Icon(color=color, icon=icon_name, prefix="fa"),
        ).add_to(cluster)

    folium.LayerControl().add_to(m)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    m.save(out_path)
    print(f"Harita -> {out_path}")
    print(f"Toplam {len(df)} tespit haritalandı.")
    print("Bu dosyayı çift tıklayıp tarayıcıda açabilirsin (internet gerekmez, fotoğraflar dosyanın içinde).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--detections", default="output/detections/tespitler_gps.csv")
    parser.add_argument("--images", default="output/report/isaretli_kareler")
    parser.add_argument("--out", default="output/report/harita.html")
    args = parser.parse_args()

    build_map(args.detections, args.images, args.out)
