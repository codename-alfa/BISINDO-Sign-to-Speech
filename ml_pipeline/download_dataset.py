"""
download_dataset.py — Helper untuk pengadaan & ekstraksi dataset alfabet BISINDO.

Penggunaan:
1. Ekstrak dari file ZIP yang sudah didownload manual dari Kaggle:
   python download_dataset.py --zip "C:\\path\\to\\bisindo_alphabets.zip"

2. Ekstrak dari folder direktori yang sudah ada:
   python download_dataset.py --source-dir "C:\\path\\to\\extracted_folder"

3. Buat starter sample dataset (26 kelas A-Z, data sintetis berbasis landmark) untuk testing pipeline:
   python download_dataset.py --generate-starter
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw" / "bisindo_alphabets"
STATIC_LABELS_PATH = ROOT / "labels" / "static_labels.txt"


def get_expected_labels() -> list[str]:
    if STATIC_LABELS_PATH.exists():
        lines = [ln.strip() for ln in STATIC_LABELS_PATH.read_text(encoding="utf-8").splitlines()]
        return [l for l in lines if l]
    return [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def extract_zip(zip_path: Path, target_dir: Path = RAW_DIR) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"File zip tidak ditemukan: {zip_path}")

    print(f"📦 Mengekstrak ZIP: {zip_path} -> {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        # Cek apakah zip memiliki subfolder A..Z langsung atau di dalam root folder
        z.extractall(target_dir)

    # Reorganize jika zip memiliki 1 parent folder pembungkus
    reorganize_subfolders(target_dir)
    print("✅ Ekstraksi ZIP selesai.")


def copy_from_dir(source_dir: Path, target_dir: Path = RAW_DIR) -> None:
    if not source_dir.exists():
        raise FileNotFoundError(f"Folder sumber tidak ditemukan: {source_dir}")

    print(f"📂 Menyalin dataset dari: {source_dir} -> {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)

    expected = get_expected_labels()
    # Cari folder yang memiliki subfolder A..Z
    found_any = False
    for label in expected:
        # Cari case-insensitive
        matches = [p for p in source_dir.rglob("*") if p.is_dir() and p.name.upper() == label]
        if matches:
            found_any = True
            dest_class_dir = target_dir / label
            dest_class_dir.mkdir(parents=True, exist_ok=True)
            for img in matches[0].glob("*.*"):
                if img.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    shutil.copy2(img, dest_class_dir / img.name)

    if not found_any:
        print("⚠️ Tidak ditemukan subfolder A-Z di folder sumber. Menyalin semua isi...")
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        reorganize_subfolders(target_dir)

    print("✅ Penyalinan dataset selesai.")


def reorganize_subfolders(base_dir: Path) -> None:
    """Jika data berada di subfolder bersarang (misal base_dir/dataset/A/..), angkat ke base_dir/A/."""
    expected = set(get_expected_labels())
    current_dirs = {d.name.upper(): d for d in base_dir.iterdir() if d.is_dir()}

    if expected.issubset(set(current_dirs.keys())):
        return  # Struktur sudah tepat

    # Cari subfolder yang berisi kelas A..Z
    for sub in list(base_dir.rglob("*")):
        if sub.is_dir() and sub.name.upper() in expected:
            dest = base_dir / sub.name.upper()
            if dest != sub:
                dest.mkdir(parents=True, exist_ok=True)
                for f in sub.glob("*.*"):
                    if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                        shutil.move(str(f), str(dest / f.name))


def generate_starter_dataset(target_dir: Path = RAW_DIR, samples_per_class: int = 30) -> None:
    """Membuat starter image dataset sintetis dengan gambar tangan kanonik + variasi visual.
    Ini memastikan pipeline training dapat langsung dijalankan & diverifikasi end-to-end
    bahkan sebelum user mendownload full dataset Kaggle."""
    print(f"🎨 Membuat starter dataset sintetis: 26 kelas A-Z, {samples_per_class} sampel per kelas...")
    target_dir.mkdir(parents=True, exist_ok=True)
    expected = get_expected_labels()

    # Template koordinat 2D dasar telapak tangan (normalisasi 0-1)
    base_wrist = (0.5, 0.8)

    for idx, label in enumerate(expected):
        class_dir = target_dir / label
        class_dir.mkdir(parents=True, exist_ok=True)

        for i in range(samples_per_class):
            img = np.full((320, 320, 3), 40, dtype=np.uint8)  # Background gelap
            # Berikan noise background
            noise = np.random.randint(0, 30, (320, 320, 3), dtype=np.uint8)
            img = cv2.add(img, noise)

            # Gambar bentuk tangan representatif berbeda tiap huruf
            cx = int(base_wrist[0] * 320 + np.random.randint(-15, 15))
            cy = int(base_wrist[1] * 320 + np.random.randint(-15, 15))

            # Sketsa telapak tangan
            palm_color = (180, 200, 230)
            cv2.circle(img, (cx, cy - 60), 45, palm_color, -1)

            # 5 Jari dengan variasi konfigurasi berdasarkan indeks huruf
            finger_angles = [-50, -25, 0, 25, 50]
            for f_idx, angle in enumerate(finger_angles):
                # Variasi menekuk atau meluruskan jari berdasarkan pola bit huruf
                is_extended = bool((idx + f_idx + i) % 2 == 0 or (idx % 3 == 0))
                length = 70 if is_extended else 25

                rad = np.radians(angle - 90 + np.random.uniform(-5, 5))
                tip_x = int(cx + length * np.cos(rad))
                tip_y = int((cy - 60) + length * np.sin(rad))

                cv2.line(img, (cx + (f_idx - 2) * 12, cy - 60), (tip_x, tip_y), palm_color, 14)
                cv2.circle(img, (tip_x, tip_y), 7, (200, 220, 250), -1)

            # Tambahkan label teks kecil di pojok sebagai watermark validasi
            cv2.putText(img, f"BISINDO-{label}-{i+1}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 1)

            filename = class_dir / f"sample_{label}_{i+1:03d}.png"
            cv2.imwrite(str(filename), img)

    print(f"✅ Starter dataset berhasil dibuat di: {target_dir}")


def main():
    parser = argparse.ArgumentParser(description="Ingest atau generate dataset alfabet BISINDO")
    parser.add_argument("--zip", type=str, help="Path ke file zip dataset Kaggle")
    parser.add_argument("--source-dir", type=str, help="Path ke direktori dataset yang sudah diekstrak")
    parser.add_argument("--generate-starter", action="store_true", help="Buat starter dataset gambar sintetis")
    parser.add_argument("--samples", type=int, default=35, help="Jumlah sampel per kelas untuk starter dataset")
    args = parser.parse_args()

    if args.zip:
        extract_zip(Path(args.zip))
    elif args.source_dir:
        copy_from_dir(Path(args.source_dir))
    elif args.generate_starter:
        generate_starter_dataset(samples_per_class=args.samples)
    else:
        # Cek apakah folder raw sudah memiliki data
        expected = get_expected_labels()
        found_dirs = [d.name for d in RAW_DIR.iterdir() if d.is_dir() and d.name in expected] if RAW_DIR.exists() else []
        if len(found_dirs) == 26:
            print(f"ℹ️ Dataset sudah tersedia di {RAW_DIR} ({len(found_dirs)} kelas lengkap).")
        else:
            print("ℹ️ Belum ada argumen yang diberikan. Menjalankan --generate-starter untuk bootstrap pipeline...")
            generate_starter_dataset(samples_per_class=35)


if __name__ == "__main__":
    main()
