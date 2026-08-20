"""
1_extract_frames.py
--------------------
Videodan belirli saniye aralıklarıyla kare (frame) çıkarır.
Yol taraması gibi işlerde her kareyi analiz etmeye gerek yok;
saniyede 1-2 kare genelde yeterli ve çok daha hızlıdır.

Kullanım:
    python 1_extract_frames.py --video input/tur.mp4 --fps 2
"""

import cv2
import os
import argparse


def extract_frames(video_path: str, out_dir: str, target_fps: float = 2.0):
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Video açılamadı: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / src_fps if src_fps else 0

    # Kaç kare atlayarak ilerleyeceğimizi hesapla
    frame_interval = max(1, round(src_fps / target_fps))

    print(f"Video FPS: {src_fps:.1f} | Toplam kare: {total_frames} | Süre: {duration_sec:.1f} sn")
    print(f"Hedef: saniyede {target_fps} kare -> her {frame_interval} karede bir alınacak")

    frame_idx = 0
    saved_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp_sec = frame_idx / src_fps
            filename = f"frame_{saved_idx:05d}_t{timestamp_sec:07.2f}s.jpg"
            out_path = os.path.join(out_dir, filename)
            cv2.imwrite(out_path, frame)
            saved_idx += 1

        frame_idx += 1

    cap.release()
    print(f"Toplam {saved_idx} kare çıkarıldı -> {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Girdi video yolu")
    parser.add_argument("--out", default="output/frames", help="Karelerin kaydedileceği klasör")
    parser.add_argument("--fps", type=float, default=2.0, help="Saniyede kaç kare alınacak")
    args = parser.parse_args()

    extract_frames(args.video, args.out, args.fps)
