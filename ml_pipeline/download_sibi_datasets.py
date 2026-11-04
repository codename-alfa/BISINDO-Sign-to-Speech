"""
download_sibi_datasets.py — Mengunduh berbagai dataset SIBI (Abjad & Angka) dari Kaggle
menggunakan kagglehub dan mengekstrak 21 titik 3D MediaPipe HandLandmarker beserta
orientasi kanonik dan versi mirror-nya.

Daftar penyedia dataset SIBI yang dijelajahi:
1. alvinbintang/sibi-dataset
2. alfarizy29/combined-sibi-dataset
3. renitriyaningsihhh/sibi-sign-language-dataset
4. andresaputraginting/gesturesibi
5. ardamavi/sign-language-digits-dataset (1-hand digits 0-9 / 1-9 untuk kandidat angka yang akan diverifikasi terhadap Kemendikdasmen)
6. Cache lokal Kagglehub yang sudah terunduh sebelumnya (dievaluasi ketat per kelas terhadap Golden Centroid SIBI Kemendikdasmen)
"""

from __future__ import annotations

import os
import re
import string
import sys
from pathlib import Path

import cv2
import kagglehub
import mediapipe as mp
import numpy as np
import pandas as pd
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
RAW_SIBI_DIR = ROOT / "data" / "raw_sibi"
KAGGLE_EXTRACTED_CSV = RAW_SIBI_DIR / "kaggle_sibi_raw_landmarks.csv"
HAND_LANDMARKER_PATH = ROOT.parent / "android_app" / "app" / "src" / "main" / "assets" / "hand_landmarker.task"

KAGGLE_SIBI_DATASETS = [
    ("alvinbintang_sibi", "alvinbintang/sibi-dataset"),
    ("alfarizy29_combined_sibi", "alfarizy29/combined-sibi-dataset"),
    ("renitriyaningsih_sibi", "renitriyaningsihhh/sibi-sign-language-dataset"),
    ("andresaputraginting_sibi", "andresaputraginting/gesturesibi"),
    ("ardamavi_digits", "ardamavi/sign-language-digits-dataset"),
]

VALID_CLASSES = set(string.ascii_uppercase) | {str(i) for i in range(1, 11)}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def create_detector(min_conf: float = 0.40) -> vision.HandLandmarker:
    base_options = python.BaseOptions(model_asset_path=str(HAND_LANDMARKER_PATH))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=min_conf,
        min_hand_presence_confidence=min_conf,
    )
    return vision.HandLandmarker.create_from_options(options)


def infer_class_from_path(img_path: Path) -> str | None:
    """Tentukan label kelas (A..Z atau 1..10) dari nama folder induknya."""
    for part in reversed(img_path.parent.parts):
        clean = part.strip().upper()
        if clean in VALID_CLASSES:
            return clean
        # Cek pola seperti "01", "02", ..., "09"
        if clean.isdigit():
            val = str(int(clean))
            if val in VALID_CLASSES:
                return val
    return None


def extract_from_directory(
    detector: vision.HandLandmarker,
    provider_name: str,
    root_dir: Path,
    max_per_class: int = 180,
) -> list[dict]:
    """Pindai semua gambar di root_dir, ambil hingga max_per_class per kelas, ekstrak landmark 1-tangan."""
    class_files: dict[str, list[Path]] = {c: [] for c in VALID_CLASSES}

    for dirpath, _, filenames in os.walk(root_dir):
        p_dir = Path(dirpath)
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in IMAGE_EXTS:
                continue
            full_path = p_dir / fn
            lbl = infer_class_from_path(full_path)
            if lbl is not None:
                class_files[lbl].append(full_path)

    rows = []
    rng = np.random.default_rng(42)

    total_found_classes = sum(1 for v in class_files.values() if len(v) > 0)
    print(f"   📂 [{provider_name}] Menemukan {total_found_classes} kelas di {root_dir}")

    for cls in sorted(VALID_CLASSES):
        files = class_files[cls]
        if not files:
            continue
        if len(files) > max_per_class:
            indices = rng.choice(len(files), size=max_per_class, replace=False)
            sampled_files = [files[int(i)] for i in indices]
        else:
            sampled_files = files

        detected_count = 0
        for img_path in sampled_files:
            bgr = cv2.imread(str(img_path))
            if bgr is None:
                continue
            h, w = bgr.shape[:2]
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = detector.detect(mp_img)

            # Filter ketat: HANYA terima jika terdeteksi tepat 1 tangan (atau jika >1, abaikan agar tidak tercampur gestur 2-tangan!)
            if not res.hand_landmarks or len(res.hand_landmarks) != 1:
                continue

            lm = res.hand_landmarks[0]
            pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float64)
            handedness = res.handedness[0][0].category_name
            score = float(res.handedness[0][0].score)

            if score < 0.50:
                continue

            try:
                ms = feature_utils.to_model_space(pts, w, h, mirror_x=False)
                feat = feature_utils.normalize_landmarks(ms)
            except ValueError:
                continue

            # Canonicalize ke orientasi acuan (Right)
            if handedness.lower() == "left":
                feat_canon = feat.copy()
                feat_canon[0::3] *= -1.0
            else:
                feat_canon = feat

            rows.append({
                "label": cls,
                "provider": provider_name,
                "orig_handedness": handedness,
                "confidence": round(score, 4),
                **{f"f{i}": float(feat_canon[i]) for i in range(63)},
            })
            detected_count += 1

        if detected_count > 0:
            print(f"      - Kelas '{cls}': {detected_count}/{len(sampled_files)} sampel 1-tangan valid diekstrak.")

    return rows


def main():
    RAW_SIBI_DIR.mkdir(parents=True, exist_ok=True)
    detector = create_detector(min_conf=0.40)

    all_rows = []

    print("🚀 Mengunduh & mengekstrak dataset SIBI dari Kaggle...")
    for provider_name, slug in KAGGLE_SIBI_DATASETS:
        print(f"\n⬇️ Mengunduh '{slug}' ({provider_name})...")
        try:
            dl_path = Path(kagglehub.dataset_download(slug))
            print(f"   Path: {dl_path}")
            rows = extract_from_directory(detector, provider_name, dl_path, max_per_class=160)
            all_rows.extend(rows)
        except Exception as e:
            print(f"   [WARN] Gagal memproses {slug}: {e}")

    # Periksa juga cache kagglehub lokal yang sudah ada sebelumnya (sebagai kandidat tambahan yang nanti disaring ketat terhadap Golden Centroid SIBI)
    cache_root = Path.home() / ".cache" / "kagglehub" / "datasets"
    if cache_root.exists():
        for existing_slug in ["achmadnoer/alfabet-bisindo", "yunitayupratiwi/bisindo-alphabets"]:
            author, ds_name = existing_slug.split("/")
            local_ds_dir = cache_root / author / ds_name
            if local_ds_dir.exists():
                provider_name = f"cached_{author}"
                print(f"\n📂 Mengekstrak kandidat 1-tangan dari cache lokal '{existing_slug}'...")
                rows = extract_from_directory(detector, provider_name, local_ds_dir, max_per_class=120)
                all_rows.extend(rows)

    detector.close()

    df = pd.DataFrame(all_rows)
    df.to_csv(KAGGLE_EXTRACTED_CSV, index=False)
    print(f"\n✅ Ekstraksi selesai! Total kandidat sampel 1-tangan Kaggle: {len(df)} baris.")
    print(f"   Disimpan ke: {KAGGLE_EXTRACTED_CSV}")


if __name__ == "__main__":
    main()

