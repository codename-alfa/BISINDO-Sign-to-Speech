"""
bootstrap_dynamic_data.py — Ekstrak 100 sekuens kata 'Halo' dari dataset Talkee Kaggle
dan simpan ke data/dynamic/Halo/ sebagai sekuens (30, 63) ternormalisasi.
"""

import sys
from pathlib import Path
import numpy as np

import feature_utils

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
DYNAMIC_DIR = ROOT / "data" / "dynamic"
TALKEE_HALO_DIR = Path(r"C:\Users\CodenameAlfa\.cache\kagglehub\datasets\niputukarismadewi\talkee-bisindo-sign-language-dataset\versions\2\dt-final-100seq\Halo")

def normalize_hand_coords(coords: np.ndarray) -> np.ndarray:
    """
    Normalisasi koordinat (21, 3) relatif terhadap wrist dan skala tangan.
    Sama persis dengan kontrak feature_utils.normalize_landmarks.
    """
    wrist = coords[0].copy()
    rel = coords - wrist
    scale = np.linalg.norm(coords[9] - wrist) # keypoint 9 = middle finger mcp
    if scale < 1e-6 or np.isnan(scale):
        scale = 1.0
    norm = rel / scale
    return norm.flatten().astype(np.float32)

def main():
    print("🚀 Memulai bootstrap data dinamis kata 'Halo' dari Talkee...")
    if not TALKEE_HALO_DIR.exists():
        raise FileNotFoundError(f"Folder Talkee Halo tidak ditemukan di: {TALKEE_HALO_DIR}")

    target_halo_dir = DYNAMIC_DIR / "Halo"
    target_halo_dir.mkdir(parents=True, exist_ok=True)

    seq_folders = [d for d in TALKEE_HALO_DIR.iterdir() if d.is_dir()]
    seq_folders.sort(key=lambda x: int(x.name) if x.name.isdigit() else 999)

    valid_seq_count = 0

    for i, seq_folder in enumerate(seq_folders):
        frame_files = [seq_folder / f"{frame_idx}.npy" for frame_idx in range(feature_utils.SEQUENCE_LENGTH)]
        if not all(f.exists() for f in frame_files):
            continue

        seq_frames = []
        for f in frame_files:
            raw_126 = np.load(f)
            # Tangan aktif pada Halo di Talkee adalah tangan kanan [63:126]
            hand_active = raw_126[63:] if (raw_126[63:] != 0).any() else raw_126[:63]
            coords = hand_active.reshape(21, 3)
            feats = normalize_hand_coords(coords)
            seq_frames.append(feats)

        seq_arr = np.stack(seq_frames, axis=0).astype(np.float32) # Shape: (30, 63)
        out_file = target_halo_dir / f"seq_{i:03d}.npy"
        np.save(out_file, seq_arr)
        valid_seq_count += 1

    print(f"✅ Berhasil mengekstrak {valid_seq_count} sekuens 'Halo' (shape: {seq_arr.shape}) ke: {target_halo_dir}")

if __name__ == "__main__":
    main()
