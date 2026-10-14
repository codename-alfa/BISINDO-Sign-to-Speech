"""
validate_dataset.py — Verifikasi integritas & statistik raw image dataset BISINDO A-Z.
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw" / "bisindo_alphabets"
STATIC_LABELS_PATH = ROOT / "labels" / "static_labels.txt"


def validate_raw_dataset(raw_dir: Path = RAW_DIR) -> bool:
    print(f"🔍 Memvalidasi dataset pada: {raw_dir}")
    if not raw_dir.exists():
        print(f"❌ Direktori raw dataset tidak ditemukan: {raw_dir}")
        print("   Jalankan: python download_dataset.py --generate-starter (atau gunakan --zip)")
        return False

    if STATIC_LABELS_PATH.exists():
        expected_classes = [ln.strip() for ln in STATIC_LABELS_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    else:
        expected_classes = [chr(c) for c in range(ord("A"), ord("Z") + 1)]

    stats = {}
    missing_classes = []
    total_images = 0

    for label in expected_classes:
        class_path = raw_dir / label
        if not class_path.exists() or not class_path.is_dir():
            missing_classes.append(label)
            stats[label] = 0
            continue

        images = [f for f in class_path.iterdir() if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
        count = len(images)
        stats[label] = count
        total_images += count

    print("\n--- 📊 Ringkasan Dataset Alfabet BISINDO ---")
    print(f"Total Kelas Terdefinisi : {len(expected_classes)}")
    print(f"Kelas Ditemukan         : {len(expected_classes) - len(missing_classes)}")
    print(f"Total Gambar Valid      : {total_images}")

    if missing_classes:
        print(f"❌ Kelas yang Hilang / Kosong ({len(missing_classes)}): {', '.join(missing_classes)}")
        return False

    min_class = min(stats, key=stats.get)
    max_class = max(stats, key=stats.get)
    avg_count = total_images / len(expected_classes)

    print(f"Rata-rata Sampel/Kelas  : {avg_count:.1f}")
    print(f"Sampel Terendah         : Kelas '{min_class}' ({stats[min_class]} gambar)")
    print(f"Sampel Tertinggi        : Kelas '{max_class}' ({stats[max_class]} gambar)")

    if total_images < len(expected_classes) * 5:
        print("⚠️ Jumlah gambar terlalu sedikit untuk melatih model (< 5 gambar per kelas).")
        return False

    print("\n✅ Validasi berhasil: Seluruh 26 kelas alfabet A-Z siap untuk diekstraksi!")
    return True


if __name__ == "__main__":
    is_valid = validate_raw_dataset()
    sys.exit(0 if is_valid else 1)
