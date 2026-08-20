# Yol Denetim Pipeline'ı

Araç videosundan otomatik olarak **çukur/çatlak, trafik ışığı, trafik
tabelası** tespiti yapar; GPS verisi varsa (GoPro/aksiyon kamerası
videolarında sıkça bulunur) her tespidi haritada işaretlenebilir bir
konuma bağlar. Belediyeye sunulabilecek Excel raporu + işaretli
fotoğraflar üretir.

Kendi model eğitmiyoruz -- açık kaynak, hazır eğitilmiş YOLOv8
modellerini kullanıyoruz:

| Model | Kaynak | Ne tespit ediyor |
|---|---|---|
| `yolov8n.pt` | [Ultralytics](https://github.com/ultralytics/ultralytics) (COCO) | trafik ışığı, dur tabelası |
| `road_damage.pt` | [oracl4/RoadDamageDetection](https://github.com/oracl4/RoadDamageDetection) | çukur, çatlak |
| `traffic_sign.pt` | [nezahatkorkmaz/traffic-sign-detection](https://huggingface.co/nezahatkorkmaz/traffic-sign-detection) | genel trafik tabelaları |

---

## 1) Kurulum

### 1.1 Python

**GPU'nuz (NVIDIA) varsa** en iyi performans için **Python 3.12**
önerilir (PyTorch'un CUDA desteği en sağlam bu sürümde). Python 3.12
kurulu değilse: https://www.python.org/downloads/release/python-3120/
adresinden "Windows installer (64-bit)" indirin, kurulumda **"Add
python.exe to PATH"** kutucuğunu işaretleyin.

GPU'nuz yoksa/önemsemiyorsanız mevcut Python sürümünüzle devam
edebilirsiniz, aşağıdaki `py -3.12` yerine `python` kullanın.

### 1.2 Sanal ortam

```powershell
py -3.12 -m venv venv
venv\Scripts\activate
```

### 1.3 PyTorch (GPU'nuz varsa önce bunu kurun)

NVIDIA ekran kartınız varsa, sürücünüzün desteklediği CUDA sürümünü
görmek için:
```powershell
nvidia-smi
```
Çıktıda "CUDA Version: XX.X" yazan satıra bakın, sonra ona uygun
build'i kurun (örnek, CUDA 12.8 için):
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```
Doğrulama:
```powershell
python -c "import torch; print(torch.cuda.is_available())"
```
`True` dönmeli. GPU'nuz yoksa bu adımı atlayın, bir sonraki adım
otomatik CPU sürümünü kuracaktır.

### 1.4 Diğer kütüphaneler

```powershell
pip install -r requirements.txt
```

### 1.5 Hazır modelleri indir

```powershell
python 0_setup_models.py
```

Bu, `road_damage.pt` (GitHub) ve `traffic_sign.pt` (Hugging Face)
dosyalarını `models/` klasörüne indirir. `yolov8n.pt` ise
`2_detect.py` ilk çalıştırıldığında otomatik iner.

### 1.6 (Opsiyonel) GPS için ffmpeg + gopro2gpx

Videonuzda GPS verisi varsa (GoPro/aksiyon kamerası vb.), konum
eşleştirme özelliğini kullanmak için:

```powershell
winget install ffmpeg
```
(Zaten kuruluysa "No available upgrade found" der, sorun değil.)
Yeni bir terminal açıp doğrulayın: `ffmpeg -version`

```powershell
pip install git+https://github.com/juanmcasillas/gopro2gpx
```

---

## 2) Çalıştırma

Videonuzu `input\` klasörüne koyun (klasör yoksa oluşturun), sonra
sırayla:

```powershell
# 1) Videodan kare çıkar
python 1_extract_frames.py --video input\video.mp4

# 2) Üç modelle tespit yap
python 2_detect.py

# 3) Aynı nesnenin tekrar tekrar sayılmasını önle + öncelik ata
python 5_dedupe_and_prioritize.py --frame-width <GENISLIK> --frame-height <YUKSEKLIK>

# 4) (Opsiyonel) GPS varsa çıkar ve eşleştir
python 7_extract_gps.py --video input\video.mp4
python 8_join_gps.py

# 5) Final Excel raporu + işaretli görseller
python 6_final_report.py

# 6) (Opsiyonel, GPS varsa) Etkileşimli HTML harita
python 9_make_map.py
```

Video çözünürlüğünü bilmiyorsanız:
```powershell
python -c "import cv2; cap = cv2.VideoCapture('input/video.mp4'); print(int(cap.get(3)), 'x', int(cap.get(4)))"
```

GPS adımlarını (4. adım) atlarsanız `6_final_report.py` otomatik
olarak GPS'siz veriyle devam eder; bu durumda `9_make_map.py`
çalışmaz (konum verisi gerektirir).

**Çıktılar:**
- `output/report/belediye_raporu_final.xlsx` — Özet / Yol Hasarı
  Önceliği / Tüm Nesneler (varsa Google Maps linkleriyle) sekmeleri
- `output/report/isaretli_kareler/` — her benzersiz nesne için
  kutucuklu, öncelik renkli bir fotoğraf
- `output/report/harita.html` — tek dosyalık, çift tıklayınca
  tarayıcıda açılan etkileşimli harita (fotoğraflar dosyanın içinde
  gömülü, internet gerekmez). Belediyeye göndermek için Excel'den
  daha kullanışlı: renkli iğneler (kırmızı=yüksek öncelik,
  turuncu=orta, açık kırmızı=düşük, mavi=bilgi), tıklayınca fotoğraf
  + detay açılır.

---

## 3) Ayarlanabilir şeyler

- **Güven eşikleri** (`2_detect.py` içinde `CONF_THRESHOLD_*`) —
  yanlış pozitif çoksa yükseltin, tespit kaçırıyorsa düşürün. Road
  damage modeli genelde daha çok yanlış alarm verdiği için daha
  yüksek tutulur.
- **`--fps`** (`1_extract_frames.py`) — saniyede kaç kare
  analiz edileceği. Varsayılan 2.
- **Tekilleştirme hassasiyeti** (`5_dedupe_and_prioritize.py` içinde
  `TIME_GAP_SECONDS`, `CENTER_DIST_RATIO`).

---

## 4) Bilinen sorunlar / notlar

- **`0_setup_models.py` git clone hatası verirse** ("invalid path...
  Zone.Identifier"): Bu Windows'a özgü bir NTFS sorunu, script içinde
  zaten düzeltilmiş durumda (`core.protectNTFS=false`). Eski bir
  sürümü kullanıyorsanız güncelleyin.
- **"Author identity unknown" git hatası**: `git config --global
  user.email "..."` ve `user.name "..."` ile kimliğinizi tanımlayın.
- **GPU'da `half` deprecation uyarısı**: Zararsız, script durmaz.
- GTX 1650 Ti gibi giriş seviyesi GPU'larda bile CPU'ya göre kayda
  değer hızlanma sağlanır; tam video (30fps, her kareyi analiz)
  yerine örneklenmiş kare akışı (`1_extract_frames.py` ile 2fps)
  kullanmak pratikte yeterli ve çok daha hızlıdır.
