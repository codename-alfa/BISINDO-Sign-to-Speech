"""
collect_static_data.py — Ekstraksi 21 koordinat 3D MediaPipe & normalisasi 63-fitur ke CSV.

Menggunakan:
- MediaPipe Tasks API (HandLandmarker)
- Single source of truth normalisasi: feature_utils.normalize_landmarks()
- Output: data/static/static_data.csv
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import feature_utils

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw" / "bisindo_alphabets"
STATIC_DIR = ROOT / "data" / "static"
OUTPUT_CSV = STATIC_DIR / "static_data.csv"
MODEL_ASSET = ROOT / "assets" / "hand_landmarker.task"


def init_landmarker() -> vision.HandLandmarker:
    if not MODEL_ASSET.exists():
        raise FileNotFoundError(f"Model {MODEL_ASSET} tidak ditemukan. Jalankan setup_check.py terlebih dahulu.")

    base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_ASSET))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def process_dataset(raw_dir: Path = RAW_DIR, output_csv: Path = OUTPUT_CSV) -> None:
    print(f"🚀 Memulai ekstraksi landmark statis dari: {raw_dir}")
    if not raw_dir.exists():
        raise FileNotFoundError(f"Direktori dataset mentah tidak ditemukan: {raw_dir}")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    landmarker = init_landmarker()

    expected_labels = feature_utils.load_labels(feature_utils.STATIC_LABELS_PATH)
    header = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)] + ["label"]

    total_images_scanned = 0
    total_hands_detected = 0
    class_stats = {lbl: {"scanned": 0, "detected": 0} for lbl in expected_labels}

    start_time = time.time()

    with open(output_csv, mode="w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)

        for label in expected_labels:
            class_folder = raw_dir / label
            if not class_folder.exists() or not class_folder.is_dir():
                print(f"⚠️ Folder kelas '{label}' tidak ditemukan, dilewati.")
                continue

            image_files = [img for img in class_folder.iterdir() if img.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
            class_stats[label]["scanned"] = len(image_files)

            print(f"📸 Memproses kelas '{label}' ({len(image_files)} gambar)...", end="", flush=True)
            detected_in_class = 0

            for img_path in image_files:
                total_images_scanned += 1
                bgr_img = cv2.imread(str(img_path))
                if bgr_img is None:
                    continue

                rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_img)

                detection_result = landmarker.detect(mp_image)

                if detection_result.hand_landmarks:
                    # Ambil tangan pertama yang terdeteksi
                    raw_landmarks = detection_result.hand_landmarks[0]
                    try:
                        features = feature_utils.normalize_landmarks(raw_landmarks)
                        # Simpan baris: 63 float + string label
                        row = [f"{val:.6f}" for val in features] + [label]
                        writer.writerow(row)
                        detected_in_class += 1
                        total_hands_detected += 1
                    except ValueError:
                        # Degenerate hand size
                        pass

            class_stats[label]["detected"] = detected_in_class
            ratio = (detected_in_class / len(image_files) * 100) if image_files else 0
            print(f" Selesai! (Terdeteksi: {detected_in_class}/{len(image_files)} - {ratio:.1f}%)")

    landmarker.close()
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("📊 REKAPITULASI EKSTRAKSI LANDMARK STATIS")
    print("=" * 60)
    print(f"Total Gambar Dipindai  : {total_images_scanned}")
    print(f"Total Tangan Berhasil  : {total_hands_detected} ({total_hands_detected / max(1, total_images_scanned) * 100:.1f}%)")
    print(f"Waktu Eksekusi         : {elapsed:.2f} detik")
    print(f"File Hasil Ekstraksi   : {output_csv}")
    print("=" * 60)

    if total_hands_detected == 0:
        print("❌ PERINGATAN: Tidak ada satu pun tangan yang terdeteksi dari dataset.")
        sys.exit(1)
    else:
        print("✅ Ekstraksi selesai dan CSV fitur siap untuk proses pelatihan model!")


if __name__ == "__main__":
    process_dataset()
