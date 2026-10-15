"""
enrich_static_dataset.py — Ekstrak landmark dari dataset citra manusia nyata (Meisyavira, Yunitayupratiwi, Achmadnoer)
dan gabungkan dengan data kanonikal untuk menghasilkan static_data.csv yang tangguh.
"""

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
STATIC_DIR = ROOT / "data" / "static"
OUTPUT_CSV = STATIC_DIR / "static_data.csv"
MODEL_ASSET = ROOT / "assets" / "hand_landmarker.task"

KAGGLE_CACHE = Path(r"C:\Users\CodenameAlfa\.cache\kagglehub\datasets")

DATASETS = [
    {
        "name": "meisyavira",
        "path": KAGGLE_CACHE / r"meisyavira\abjad-bahasa-isyarat-indonesia-bisindo\versions\1\dataset_merged",
        "type": "folder_per_class",
    },
    {
        "name": "yunitayupratiwi",
        "path": KAGGLE_CACHE / r"yunitayupratiwi\bisindo-dataset\versions\1\BISINDO - Dataset",
        "type": "prefix_per_class",
    },
    {
        "name": "achmadnoer",
        "path": KAGGLE_CACHE / r"achmadnoer\alfabet-bisindo\versions\2\Citra BISINDO",
        "type": "folder_per_class",
    },
]

def init_landmarker() -> vision.HandLandmarker:
    base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_ASSET))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)

def extract_features(landmarker: vision.HandLandmarker, img_path: Path):
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        return None
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = landmarker.detect(mp_img)
    if res.hand_landmarks:
        try:
            return feature_utils.normalize_landmarks(res.hand_landmarks[0])
        except Exception:
            return None
    return None

def main():
    print("🚀 Memulai pengayaan dataset statis dari citra manusia nyata...")
    start_time = time.time()
    landmarker = init_landmarker()

    existing_rows = []
    if OUTPUT_CSV.exists():
        with open(OUTPUT_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            existing_rows = list(reader)
        print(f"📦 Data kanonikal yang sudah ada: {len(existing_rows)} sampel")
    else:
        header = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)] + ["label"]

    real_extracted_rows = []
    stats_per_dataset = {}

    for ds in DATASETS:
        name = ds["name"]
        root = ds["path"]
        print(f"\n📂 Memproses dataset: {name} ({root})...")
        if not root.exists():
            print(f"⚠️ Direktori tidak ditemukan: {root}, dilewati.")
            continue

        scanned = 0
        extracted = 0

        if ds["type"] == "folder_per_class":
            class_dirs = [d for d in root.iterdir() if d.is_dir() and len(d.name) == 1 and d.name.isalpha()]
            for cd in class_dirs:
                cls = cd.name.upper()
                for img in cd.glob("*.jpg"):
                    scanned += 1
                    feats = extract_features(landmarker, img)
                    if feats is not None:
                        row = [f"{val:.6f}" for val in feats] + [cls]
                        real_extracted_rows.append(row)
                        extracted += 1

        elif ds["type"] == "prefix_per_class":
            imgs = list(root.rglob("*.jpg"))
            for img in imgs:
                # Format: A.uuid.jpg
                prefix = img.name.split(".")[0].upper()
                if len(prefix) == 1 and prefix.isalpha():
                    scanned += 1
                    feats = extract_features(landmarker, img)
                    if feats is not None:
                        row = [f"{val:.6f}" for val in feats] + [prefix]
                        real_extracted_rows.append(row)
                        extracted += 1

        rate = (extracted / scanned * 100) if scanned > 0 else 0
        print(f"   -> Berhasil mengekstrak: {extracted}/{scanned} sampel ({rate:.1f}%)")
        stats_per_dataset[name] = {"scanned": scanned, "extracted": extracted}

    landmarker.close()

    # Gabungkan data kanonikal + data nyata
    total_combined = existing_rows + real_extracted_rows
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(total_combined)

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("🎉 PENGAYAAN DATASET STATIS SELESAI")
    print("=" * 60)
    print(f"Total Sampel Nyata Diekstrak  : {len(real_extracted_rows)}")
    print(f"Total Sampel Akhir Digabung   : {len(total_combined)} baris")
    print(f"Waktu Eksekusi                : {elapsed:.2f} detik")
    print(f"Tersimpan di                  : {OUTPUT_CSV}")
    print("=" * 60)

if __name__ == "__main__":
    main()
