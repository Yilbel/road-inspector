"""
0_setup_models.py
------------------
Hazır, açık kaynak, eğitilmiş modelleri indirir. Kendi modelimizi
eğitmiyoruz -- topluluğun eğittiği modelleri kullanıyoruz.

  - yolov8n.pt          : Ultralytics kütüphanesi ilk kullanımda otomatik indirir.
  - road_damage.pt       : oracl4/RoadDamageDetection (GitHub) -> çukur + çatlak
  - traffic_sign.pt      : nezahatkorkmaz/traffic-sign-detection (Hugging Face) -> genel tabela

Kullanım:
    pip install -r requirements.txt huggingface_hub
    python 0_setup_models.py
"""

import os
import shutil
import subprocess
import sys

MODELS_DIR = "models"


def download_road_damage_model():
    target = os.path.join(MODELS_DIR, "road_damage.pt")
    if os.path.exists(target):
        print(f"[ok] {target} zaten var, atlanıyor.")
        return

    print("Road damage modeli indiriliyor (oracl4/RoadDamageDetection)...")
    tmp_dir = "_tmp_road_damage_repo"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/oracl4/RoadDamageDetection.git", tmp_dir],
        check=True,
    )

    models_subdir = os.path.join(tmp_dir, "models")
    pt_files = [f for f in os.listdir(models_subdir) if f.endswith(".pt")]
    if not pt_files:
        raise RuntimeError(f"{models_subdir} içinde .pt dosyası bulunamadı. Repoyu elle kontrol et.")

    # En büyük .pt dosyasını al (genelde en güncel/eğitilmiş model odur)
    chosen = max(pt_files, key=lambda f: os.path.getsize(os.path.join(models_subdir, f)))
    shutil.copy(os.path.join(models_subdir, chosen), target)
    shutil.rmtree(tmp_dir)
    print(f"[ok] {chosen} -> {target}")


def download_traffic_sign_model():
    target = os.path.join(MODELS_DIR, "traffic_sign.pt")
    if os.path.exists(target):
        print(f"[ok] {target} zaten var, atlanıyor.")
        return

    print("Trafik tabelası modeli indiriliyor (Hugging Face: nezahatkorkmaz/traffic-sign-detection)...")
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("huggingface_hub kurulu değil. Kur: pip install huggingface_hub")
        sys.exit(1)

    downloaded_path = hf_hub_download(
        repo_id="nezahatkorkmaz/traffic-sign-detection",
        filename="best.pt",
        local_dir=MODELS_DIR,
    )
    shutil.copy(downloaded_path, target)
    print(f"[ok] {target}")


if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    download_road_damage_model()
    download_traffic_sign_model()
    print("\nTüm modeller hazır. yolov8n.pt ise 2_detect.py çalıştırıldığında otomatik inecek.")
