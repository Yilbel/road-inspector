# Yol Denetim Pipeline'ı (Çukur / Tabela / Trafik Işığı Tespiti)

Kendi model eğitmiyoruz -- açık kaynak, hazır eğitilmiş YOLOv8
modellerini kullanıyoruz:

| Model | Kaynak | Ne tespit ediyor |
|---|---|---|
| `yolov8n.pt` | [Ultralytics](https://github.com/ultralytics/ultralytics) (COCO) | trafik ışığı, dur tabelası |
| `road_damage.pt` | [oracl4/RoadDamageDetection](https://github.com/oracl4/RoadDamageDetection) | çukur, boyuna/enine/timsah sırtı çatlak |
| `traffic_sign.pt` | [nezahatkorkmaz/traffic-sign-detection](https://huggingface.co/nezahatkorkmaz/traffic-sign-detection) | genel trafik tabelaları |

## Kurulum

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Hazır modelleri indir (ilk seferde birkaç dakika sürebilir)
python 0_setup_models.py
```

> `0_setup_models.py` GitHub reposunu klonlayıp `models/road_damage.pt`
> olarak, Hugging Face'ten de `models/traffic_sign.pt` olarak kopyalar.
> `huggingface_hub`'daki dosya adı `best.pt` değilse (repo güncellenmiş
> olabilir), hatayı görüp dosya adını scriptte düzeltmen gerekebilir --
> https://huggingface.co/nezahatkorkmaz/traffic-sign-detection/tree/main
> adresinden gerçek dosya adını kontrol edebilirsin.

## Çalıştırma

```bash
# 1) Videodan kare çıkar (saniyede 2 kare, ihtiyaca göre ayarla)
python 1_extract_frames.py --video input/tur.mp4 --fps 2

# 2) Tespit yap
python 2_detect.py

# 3) Rapor üret (Excel + işaretli görseller)
python 3_report.py
```

Çıktılar:
- `output/detections/tespitler.csv` — ham tespit listesi
- `output/report/belediye_raporu.xlsx` — özet + tüm tespitler (Excel)
- `output/report/isaretli_kareler/` — kutucuklu, üzerine yazılı tespit görselleri

## Notlar / ayarlanabilir şeyler

- **`CONF_THRESHOLD`** (`2_detect.py` içinde, varsayılan 0.4) — güven eşiği.
  Yanlış pozitif çoksa yükselt, tespit kaçırıyorsa düşür.
- **`--fps`** (`1_extract_frames.py`) — saniyede kaç kare alınacak.
  Araç hızlı gidiyorsa artır, video uzunsa/işlem yavaşsa azalt.
- **Konum bilgisi yok** — bu pipeline şu an sadece görüntü + zaman
  damgası veriyor. Videonun GPS logu varsa (çoğu araç kamerasında
  `.gpx` veya video metadata'sında olur), zaman damgasıyla eşleştirip
  her tespide enlem/boylam eklemek mümkün — istersen onu da ekleriz.
- **GPU yoksa** çalışır ama yavaş olur (CPU'da kare başına ~0.5-2 sn).
  GPU varsa `ultralytics` otomatik kullanır.
