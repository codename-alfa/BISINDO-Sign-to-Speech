"""
generate_canonical_landmarks.py — Generator dataset landmark kanonik 26 alfabet BISINDO A-Z.

Menghasilkan variasi data numerik 63-fitur ternormalisasi berdasarkan pose tangan kanonik
MediaPipe Hands (21 titik 3D) untuk tiap alfabet BISINDO, dengan augmentasi rotasi, skala,
dan jitter anatomis.

Output digabung ke: data/static/static_data.csv
"""

from __future__ import annotations

import csv
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
STATIC_DIR = ROOT / "data" / "static"
OUTPUT_CSV = STATIC_DIR / "static_data.csv"

# 21 Keypoints dasar (Wrist=0, Thumb=1..4, Index=5..8, Middle=9..12, Ring=13..16, Pinky=17..20)
BASE_HAND_2D = np.array([
    [0.0, 0.45],                            # 0: Wrist
    [-0.15, 0.35], [-0.28, 0.22], [-0.35, 0.08], [-0.40, -0.05],  # 1-4: Thumb
    [-0.12, 0.05], [-0.15, -0.15], [-0.16, -0.32], [-0.17, -0.45],# 5-8: Index
    [0.0, 0.0], [0.0, -0.22], [0.0, -0.38], [0.0, -0.52],        # 9-12: Middle
    [0.12, 0.05], [0.15, -0.18], [0.16, -0.33], [0.17, -0.46],    # 13-16: Ring
    [0.24, 0.12], [0.28, -0.05], [0.30, -0.18], [0.32, -0.30]     # 17-20: Pinky
], dtype=np.float64)


def get_alphabet_pose_config(char_idx: int) -> dict:
    """Konfigurasi tekukan jari & posisi jempol yang unik untuk masing-masing alfabet (0=A s/d 25=Z)."""
    # 5 jari: [Thumb, Index, Middle, Ring, Pinky]
    # Nilai 1.0 = terbuka lurus, 0.2 = mengepal/menekuk
    configs = [
        # A: Kepalan dengan ibu jari di samping telunjuk
        [0.8, 0.2, 0.2, 0.2, 0.2],
        # B: 4 jari lurus ke atas, ibu jari menekuk di telapak
        [0.2, 1.0, 1.0, 1.0, 1.0],
        # C: Tangan melengkung seperti huruf C
        [0.6, 0.6, 0.6, 0.6, 0.6],
        # D: Telunjuk tegak lurus, jari lain melingkar menyentuh jempol
        [0.4, 1.0, 0.3, 0.3, 0.3],
        # E: Semua jari menekuk ke bawah seperti cakar
        [0.3, 0.3, 0.3, 0.3, 0.3],
        # F: Telunjuk & jempol membentuk lingkaran, 3 jari lain tegak
        [0.4, 0.4, 1.0, 1.0, 1.0],
        # G: Telunjuk & jempol mengarah horizontal
        [0.9, 0.9, 0.2, 0.2, 0.2],
        # H: Telunjuk & jari tengah mengarah horizontal
        [0.2, 0.9, 0.9, 0.2, 0.2],
        # I: Kelingking tegak lurus, jari lain mengepal
        [0.2, 0.2, 0.2, 0.2, 1.0],
        # J: Kelingking dengan orientasi memutar
        [0.3, 0.2, 0.2, 0.2, 0.9],
        # K: Telunjuk & jari tengah membentuk huruf V dengan jempol di tengah
        [0.7, 1.0, 0.9, 0.2, 0.2],
        # L: Telunjuk & jempol membentuk sudut 90 derajat (L shape)
        [1.0, 1.0, 0.2, 0.2, 0.2],
        # M: Tiga jari menutup di atas ibu jari
        [0.2, 0.4, 0.4, 0.4, 0.2],
        # N: Dua jari menutup di atas ibu jari
        [0.2, 0.4, 0.4, 0.2, 0.2],
        # O: Semua jari melingkar membentuk huruf O
        [0.5, 0.5, 0.5, 0.5, 0.5],
        # P: Bentuk K yang mengarah ke bawah
        [0.6, 0.8, 0.7, 0.2, 0.2],
        # Q: Bentuk G yang mengarah ke bawah
        [0.8, 0.8, 0.2, 0.2, 0.2],
        # R: Telunjuk dan jari tengah menyilang
        [0.2, 0.95, 0.95, 0.2, 0.2],
        # S: Kepalan tangan dengan ibu jari di depan jari-jari
        [0.25, 0.15, 0.15, 0.15, 0.15],
        # T: Ibu jari menyembul di antara telunjuk dan jari tengah
        [0.5, 0.3, 0.2, 0.2, 0.2],
        # U: Telunjuk dan jari tengah rapat tegak lurus
        [0.2, 1.0, 1.0, 0.2, 0.2],
        # V: Telunjuk dan jari tengah terbuka membentuk huruf V
        [0.2, 1.0, 1.0, 0.2, 0.2],
        # W: Tiga jari tengah tegak terbuka membentuk huruf W
        [0.2, 1.0, 1.0, 1.0, 0.2],
        # X: Telunjuk menekuk seperti kait
        [0.2, 0.55, 0.2, 0.2, 0.2],
        # Y: Ibu jari dan kelingking terbuka (shaka sign)
        [1.0, 0.2, 0.2, 0.2, 1.0],
        # Z: Telunjuk bergerak membentuk huruf Z
        [0.3, 0.9, 0.2, 0.2, 0.2]
    ]

    cfg = configs[char_idx % len(configs)]
    # Tambahkan z-depth offset untuk membedakan kelas yang mirip di 2D (seperti U vs V)
    z_spread = 0.05 if char_idx == 21 else 0.0  # V lebih spread
    return {"finger_scales": cfg, "z_spread": z_spread}


def generate_pose_landmarks(char_idx: int, rng: np.random.Generator) -> np.ndarray:
    """Menghasilkan koordinat 21 titik 3D (x, y, z) untuk 1 alfabet dengan augmentasi realistis."""
    pts = BASE_HAND_2D.copy()
    cfg = get_alphabet_pose_config(char_idx)
    scales = cfg["finger_scales"]

    # 3D coordinates: tambah z default
    z_coords = np.zeros((21, 1), dtype=np.float64)
    landmarks_3d = np.hstack([pts, z_coords])

    # Modifikasi panjang segmen jari berdasarkan skala tekukan
    finger_ranges = [
        (1, 5),   # Thumb
        (5, 9),   # Index
        (9, 13),  # Middle
        (13, 17), # Ring
        (17, 21), # Pinky
    ]

    for f_idx, (start, end) in enumerate(finger_ranges):
        scale = scales[f_idx]
        base_pt = landmarks_3d[start]
        for tip_idx in range(start + 1, end):
            vec = landmarks_3d[tip_idx] - base_pt
            landmarks_3d[tip_idx] = base_pt + vec * scale
            # Jika menekuk, tambahkan offset kedalaman z ke dalam telapak
            if scale < 0.5:
                landmarks_3d[tip_idx, 2] += (0.5 - scale) * 0.15

    # Tambahkan variasi z-spread (misal untuk V)
    if cfg["z_spread"] > 0:
        landmarks_3d[8, 0] -= 0.04
        landmarks_3d[12, 0] += 0.04

    # --- Augmentasi Realistis ---
    # 1. Rotasi 3D kecil (-15 sampai +15 derajat)
    angle_z = np.radians(rng.uniform(-15, 15))
    cos_z, sin_z = np.cos(angle_z), np.sin(angle_z)
    rot_matrix = np.array([
        [cos_z, -sin_z, 0],
        [sin_z, cos_z, 0],
        [0, 0, 1]
    ])
    landmarks_3d = landmarks_3d @ rot_matrix.T

    # 2. Skala ukuran tangan keseluruhan (0.85 - 1.15)
    hand_scale = rng.uniform(0.85, 1.15)
    landmarks_3d *= hand_scale

    # 3. Translasi posisi di layar
    shift = rng.uniform(-0.15, 0.15, size=(1, 3))
    landmarks_3d += shift

    # 4. Jitter noise anatomi kecil pada tiap sendi
    jitter = rng.normal(0, 0.008, size=landmarks_3d.shape)
    landmarks_3d += jitter

    return landmarks_3d


def generate_dataset(samples_per_class: int = 100, output_csv: Path = OUTPUT_CSV) -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    expected_labels = feature_utils.load_labels(feature_utils.STATIC_LABELS_PATH)
    header = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)] + ["label"]

    rng = np.random.default_rng(42)
    total_generated = 0

    print(f"🧬 Menghasilkan dataset kanonik MediaPipe: {len(expected_labels)} kelas, {samples_per_class} sampel/kelas...")

    with open(output_csv, mode="w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)

        for char_idx, label in enumerate(expected_labels):
            for _ in range(samples_per_class):
                raw_landmarks = generate_pose_landmarks(char_idx, rng)
                features = feature_utils.normalize_landmarks(raw_landmarks)
                row = [f"{val:.6f}" for val in features] + [label]
                writer.writerow(row)
                total_generated += 1

    print(f"✅ Selesai! {total_generated} sampel fitur telah disimpan ke: {output_csv}")


if __name__ == "__main__":
    generate_dataset(samples_per_class=100)
