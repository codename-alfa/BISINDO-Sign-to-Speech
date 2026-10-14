"""
inspect_kaggle_datasets.py — Skrip utilitas untuk memeriksa dataset Kaggle BISINDO lokal.
"""

from pathlib import Path

KAGGLE_DATASETS = {
    "achmadnoer/alfabet-bisindo": {
        "desc": "Citra Statis Huruf A-Z (12 sampel/kelas)",
        "path": Path(r"C:\Users\CodenameAlfa\.cache\kagglehub\datasets\achmadnoer\alfabet-bisindo\versions\2"),
        "total_files": 312,
        "format": ".jpg",
        "mediapipe_rate": "90.1%",
        "status": "Cocok (Statis A-Z)",
    },
    "agungmrf/indonesian-sign-language-bisindo": {
        "desc": "Citra Statis Ter-augmentasi (YOLO format)",
        "path": Path(r"C:\Users\CodenameAlfa\.cache\kagglehub\datasets\agungmrf\indonesian-sign-language-bisindo\versions\1"),
        "total_files": 11470,
        "format": ".jpg + .txt",
        "mediapipe_rate": "65.4%",
        "status": "Cocok Bersyarat (Perlu Filter Landmark)",
    },
    "rizkyyangpalsu/bisindo-video-dataset": {
        "desc": "Video Rekaman Huruf A-Z",
        "path": Path(r"C:\Users\CodenameAlfa\.cache\kagglehub\datasets\rizkyyangpalsu\bisindo-video-dataset\versions\1"),
        "total_files": 78,
        "format": ".mp4",
        "mediapipe_rate": "N/A (Video)",
        "status": "Tidak Cocok (Hanya Alfabet, Bukan 5 Kata Dinamis)",
    },
    "yunitayupratiwi/bisindo-dataset": {
        "desc": "Citra Statis Bersih + XML Pascal-VOC (15 sampel/kelas)",
        "path": Path(r"C:\Users\CodenameAlfa\.cache\kagglehub\datasets\yunitayupratiwi\bisindo-dataset\versions\1"),
        "total_files": 780,
        "format": ".jpg + .xml",
        "mediapipe_rate": "100.0%",
        "status": "Sangat Cocok & Direkomendasikan",
    },
}

def display_status():
    print("=" * 70)
    print("STATUS DATASET KAGGLE BISINDO DI MESIN LOKAL")
    print("=" * 70)
    for handle, info in KAGGLE_DATASETS.items():
        exists = info["path"].exists()
        symbol = "✅" if exists else "❌"
        print(f"{symbol} {handle}")
        print(f"   Deskripsi    : {info['desc']}")
        print(f"   Lokasi Cache : {info['path']}")
        print(f"   Total Berkas : {info['total_files']} berkas ({info['format']})")
        print(f"   Ekstraksi MP : {info['mediapipe_rate']}")
        print(f"   Kelayakan    : {info['status']}")
        print("-" * 70)

if __name__ == "__main__":
    display_status()
