"""
clean_and_align_sibi.py — Pipeline Standarisasi, Cross-Source Consistency Audit,
Outlier Rejection, dan Automatic Mirror Dataset Generation berbasis Golden Standard
Kamus SIBI Kemendikdasmen.

Alur Eksekusi:
1. Memuat Golden Reference Centroids (A..Z + 1..10 = 36 kelas) dari Kemendikdasmen.
2. Memuat seluruh sampel kandidat dari berbagai penyedia di Kaggle (`kaggle_sibi_raw_landmarks.csv`).
3. Provider-Level Alignment Audit:
   - Menghitung rata-rata Cosine Similarity antara centroid tiap penyedia data per kelas
     terhadap Golden Centroid Kemendikdasmen.
   - Jika suatu penyedia data menggunakan kaidah gestur yang menyimpang dari SIBI Kemendikdasmen
     (Cosine Similarity < 0.78), seluruh sub-folder kelas pada penyedia tersebut otomatis DI-DROP.
4. Sample-Level Outlier Rejection:
   - Menyaring sampel individual yang memiliki Cosine Similarity < 0.82 terhadap Golden Centroid
     atau jarak Euclidean di luar batas Q3 + 1.5 * IQR.
5. Class Balancing & Automatic Mirror Generation (50:50 Canonical vs Mirror):
   - Menyeimbangkan jumlah sampel per kelas (augmentasi rotasi/skala 3D ringan untuk kelas yang
     jarang ada di Kaggle seperti J, Z, atau angka).
   - Untuk SETIAP sampel kanonik (Right), otomatis dibuatkan pasangan MIRROR-nya (Left: f[0::3] *= -1)
     sehingga dataset akhir dijamin 100% simetris 50:50 antara tangan kanan dan tangan kiri!
6. Menghasilkan:
   - `data/static/static_data.csv` & `data/static/landmarks.csv`
   - `labels/static_labels.txt` (36 kelas: A..Z + 1..10)
   - `data/static/sibi_cleaning_report.json` (dan menyalin ke `artifacts/`)
   - Poster Panduan Visual Abjad & Angka SIBI 1 Tangan (`artifacts/panduan_sibi_abjad_angka_1_tangan.png`)
"""

from __future__ import annotations

import json
import shutil
import string
import sys
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
RAW_SIBI_DIR = ROOT / "data" / "raw_sibi"
KEMENDIKDASMEN_DIR = RAW_SIBI_DIR / "kemendikdasmen"
GOLDEN_CSV = KEMENDIKDASMEN_DIR / "kemendikdasmen_golden_landmarks.csv"
GOLDEN_CENTROIDS_JSON = KEMENDIKDASMEN_DIR / "kemendikdasmen_golden_centroids.json"
KAGGLE_CSV = RAW_SIBI_DIR / "kaggle_sibi_raw_landmarks.csv"

STATIC_DIR = ROOT / "data" / "static"
STATIC_DATA_CSV = STATIC_DIR / "static_data.csv"
LANDMARKS_CSV = STATIC_DIR / "landmarks.csv"
CLEANING_REPORT_JSON = STATIC_DIR / "sibi_cleaning_report.json"

ARTIFACTS_DIR = ROOT.parent.parent / "artifacts"
BRAIN_DIR = Path(r"C:\Users\CodenameAlfa\.gemini\antigravity\brain\5cdeef75-b9e8-4bec-bb31-17aeb9f751b9")

TARGET_CLASSES = list(string.ascii_uppercase) + [str(i) for i in range(1, 11)]
FEATURE_COLS = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)]

PROVIDER_COS_THRESHOLD = 0.78
SAMPLE_COS_THRESHOLD = 0.82
TARGET_CANONICAL_PER_CLASS = 250  # 250 canonical + 250 mirror = 500 sampel per kelas (total 18.000 sampel untuk 36 kelas)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-8 or nb < 1e-8:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def cosine_sim_matrix(X: np.ndarray, v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1)
    nv = float(np.linalg.norm(v))
    denom = np.maximum(norms * nv, 1e-8)
    return (X @ v) / denom


def augment_3d_landmark_vector(vec63: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Augmentasi geometris ringan pada ruang 3D (rotasi kecil in-plane [-10°, +10°],
    tilt kedalaman z, dan jitter jari mikro) lalu dinormalisasi ulang sesuai kontrak feature_utils.
    """
    pts = vec63.reshape(21, 3).copy()

    # 1. Rotasi in-plane (bidang XY) sekitar wrist (0,0,0)
    angle_deg = rng.uniform(-11.0, 11.0)
    theta = np.deg2rad(angle_deg)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    R_z = np.array([
        [cos_t, -sin_t, 0.0],
        [sin_t,  cos_t, 0.0],
        [0.0,    0.0,   1.0],
    ], dtype=np.float64)

    # 2. Rotasi pitch/yaw 3D ringan [-7°, +7°]
    pitch = np.deg2rad(rng.uniform(-7.0, 7.0))
    yaw = np.deg2rad(rng.uniform(-7.0, 7.0))
    R_x = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(pitch), -np.sin(pitch)],
        [0.0, np.sin(pitch),  np.cos(pitch)],
    ], dtype=np.float64)
    R_y = np.array([
        [ np.cos(yaw), 0.0, np.sin(yaw)],
        [ 0.0,         1.0, 0.0],
        [-np.sin(yaw), 0.0, np.cos(yaw)],
    ], dtype=np.float64)

    pts = pts @ (R_z @ R_x @ R_y).T

    # 3. Jitter mikro proporsional pada sendi jari (kecuali wrist=0)
    noise = rng.normal(0.0, 0.018, size=(21, 3))
    noise[0] = 0.0
    pts += noise

    return feature_utils.normalize_landmarks(pts)


def generate_visual_guide_poster(golden_centroids: dict[str, np.ndarray], out_paths: list[Path]) -> None:
    """Buat Poster Panduan Visual Abjad (A-Z) & Angka (1-10) SIBI 1 Tangan dari Kemendikdasmen."""
    cols = 6
    rows = 6  # 6x6 = 36 kelas (A-Z + 1-10)
    fig, axes = plt.subplots(rows, cols, figsize=(18, 18), facecolor="#0F172A")
    fig.suptitle(
        "PANDUAN RESMI ISYARAT SIBI 1 TANGAN — ABJAD (A–Z) & ANGKA (1–10)\n"
        "(Sumber Acuan: Kamus SIBI Kemendikdasmen RI · Mendukung Tangan Kanan & Kiri / Mirror)",
        fontsize=18,
        fontweight="bold",
        color="#F8FAFC",
        y=0.97,
    )

    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17),
    ]

    for idx, cls in enumerate(TARGET_CLASSES):
        r, c = divmod(idx, cols)
        ax = axes[r, c]
        ax.set_facecolor("#1E293B")

        # Cek apakah ada foto studio PNG atau frame apex untuk ditampilkan di background
        bg_shown = False
        png_path = KEMENDIKDASMEN_DIR / "abjad_img" / f"{cls}.png"
        apex_path = KEMENDIKDASMEN_DIR / "apex_frames" / f"{cls}_apex.jpg"

        if png_path.exists():
            img = cv2.imread(str(png_path))
            if img is not None:
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                ax.imshow(rgb)
                bg_shown = True
        elif apex_path.exists():
            img = cv2.imread(str(apex_path))
            if img is not None:
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                ax.imshow(rgb)
                bg_shown = True

        if not bg_shown and cls in golden_centroids:
            pts = golden_centroids[cls].reshape(21, 3)
            xs, ys = pts[:, 0], -pts[:, 1]
            for i, j in connections:
                ax.plot([xs[i], xs[j]], [ys[i], ys[j]], color="#38BDF8", lw=2.2)
            ax.scatter(xs, ys, color="#F43F5E", s=28, zorder=3)
            ax.set_xlim(np.min(xs) - 0.3, np.max(xs) + 0.3)
            ax.set_ylim(np.min(ys) - 0.3, np.max(ys) + 0.3)

        badge_color = "#10B981" if cls in string.ascii_uppercase else "#F59E0B"
        kind_lbl = "Huruf" if cls in string.ascii_uppercase else "Angka"
        ax.set_title(f"{kind_lbl}: {cls}", fontsize=13, fontweight="bold", color=badge_color, pad=6)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_edgecolor(badge_color)
            spine.set_linewidth(1.5)

    plt.tight_layout(rect=[0.01, 0.01, 0.99, 0.94])
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(str(p), dpi=150, facecolor=fig.get_facecolor())
    plt.close()


def main():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if not GOLDEN_CSV.exists() or not GOLDEN_CENTROIDS_JSON.exists():
        raise FileNotFoundError("Jalankan scrape_kemendikdasmen_sibi.py terlebih dahulu!")

    print("📏 [1/5] Memuat Golden Reference Centroids dari Kamus SIBI Kemendikdasmen...")
    raw_centroids = json.loads(GOLDEN_CENTROIDS_JSON.read_text(encoding="utf-8"))
    golden_centroids: dict[str, np.ndarray] = {
        k: np.array(v, dtype=np.float32) for k, v in raw_centroids.items()
    }
    golden_df = pd.read_csv(GOLDEN_CSV)
    golden_canon_df = golden_df[golden_df["orientation"] == "canonical"].copy()

    # Muat data Kaggle jika ada
    if KAGGLE_CSV.exists():
        kaggle_df = pd.read_csv(KAGGLE_CSV)
        kaggle_df["label"] = kaggle_df["label"].astype(str)
    else:
        kaggle_df = pd.DataFrame(columns=["label", "provider"] + FEATURE_COLS)

    print(f"   Golden Kemendikdasmen (canonical): {len(golden_canon_df)} sampel")
    print(f"   Kandidat Kaggle (canonical)      : {len(kaggle_df)} sampel")

    print("\n🔍 [2/5] Menjalankan Cross-Provider Consistency Audit & Sample-Level Outlier Cleaning...")
    report = {
        "golden_reference_source": "https://pkplk.kemendikdasmen.go.id/sibi/",
        "total_classes": len(TARGET_CLASSES),
        "classes": TARGET_CLASSES,
        "provider_cosine_threshold": PROVIDER_COS_THRESHOLD,
        "sample_cosine_threshold": SAMPLE_COS_THRESHOLD,
        "provider_alignment_audit": {},
        "per_class_summary": {},
        "visually_similar_pairs": {},
    }

    rng = np.random.default_rng(42)
    final_rows = []

    for cls in TARGET_CLASSES:
        gold_vec = golden_centroids[cls]
        cls_gold_samples = golden_canon_df[golden_canon_df["label"].astype(str) == cls][FEATURE_COLS].values.astype(np.float32)

        accepted_kaggle_vecs = []
        rejected_providers = []
        accepted_providers = []
        total_kaggle_raw = 0
        total_kaggle_kept = 0

        if not kaggle_df.empty:
            cls_kag = kaggle_df[kaggle_df["label"] == cls]
            total_kaggle_raw = len(cls_kag)

            for prov, grp in cls_kag.groupby("provider"):
                X_prov = grp[FEATURE_COLS].values.astype(np.float32)
                if len(X_prov) == 0:
                    continue
                prov_centroid = np.median(X_prov, axis=0)
                prov_sim = cosine_sim(prov_centroid, gold_vec)

                audit_key = f"{prov}:{cls}"
                if prov_sim < PROVIDER_COS_THRESHOLD:
                    rejected_providers.append({"provider": prov, "cosine_sim": round(prov_sim, 4), "raw_count": len(X_prov)})
                    report["provider_alignment_audit"][audit_key] = {
                        "status": "REJECTED_RULE_MISMATCH",
                        "cosine_sim_to_kemendikdasmen": round(prov_sim, 4),
                        "samples_dropped": int(len(X_prov)),
                    }
                    continue

                # Sample-level filtering
                sims = cosine_sim_matrix(X_prov, gold_vec)
                dists = np.linalg.norm(X_prov - gold_vec, axis=1)
                q25, q75 = np.percentile(dists, [25, 75])
                iqr = q75 - q25
                max_dist = q75 + 1.5 * iqr

                keep_mask = (sims >= SAMPLE_COS_THRESHOLD) & (dists <= max_dist)
                kept_X = X_prov[keep_mask]
                if len(kept_X) > 0:
                    accepted_kaggle_vecs.append(kept_X)
                    total_kaggle_kept += len(kept_X)
                    accepted_providers.append({"provider": prov, "cosine_sim": round(prov_sim, 4), "kept": int(len(kept_X)), "raw": int(len(X_prov))})
                    report["provider_alignment_audit"][audit_key] = {
                        "status": "ACCEPTED",
                        "cosine_sim_to_kemendikdasmen": round(prov_sim, 4),
                        "samples_kept": int(len(kept_X)),
                        "samples_dropped_as_outliers": int(len(X_prov) - len(kept_X)),
                    }

        # Gabungkan sampel Golden Kemendikdasmen + Kaggle yang lolos verifikasi
        pool_list = [cls_gold_samples]
        if accepted_kaggle_vecs:
            pool_list.extend(accepted_kaggle_vecs)
        clean_pool = np.concatenate(pool_list, axis=0)

        # Seimbangkan ke TARGET_CANONICAL_PER_CLASS sampel kanonik
        if len(clean_pool) >= TARGET_CANONICAL_PER_CLASS:
            # Pastikan seluruh sampel asli Kemendikdasmen masuk, sisanya disampel dari Kaggle bersih
            n_gold = min(len(cls_gold_samples), 60)
            n_rest = TARGET_CANONICAL_PER_CLASS - n_gold
            rest_idx = rng.choice(len(clean_pool), size=n_rest, replace=False)
            canonical_final = np.concatenate([cls_gold_samples[:n_gold], clean_pool[rest_idx]], axis=0)
        else:
            # Augmentasi geometris 3D berbasis sampel Kemendikdasmen & Kaggle bersih
            needed = TARGET_CANONICAL_PER_CLASS - len(clean_pool)
            aug_vecs = []
            for _ in range(needed):
                base_vec = clean_pool[int(rng.integers(0, len(clean_pool)))]
                aug_vecs.append(augment_3d_landmark_vector(base_vec, rng))
            canonical_final = np.concatenate([clean_pool, np.stack(aug_vecs, axis=0)], axis=0)

        # TAHAP KRUSIAL: Pembuatan Otomatis Pasangan Mirror 1:1 (Tangan Kanan <-> Tangan Kiri)
        # Setiap vektor kanonik (f0..f62) dibuatkan versi mirror eksaknya dengan membalik komponen X (indeks 0, 3, 6, ..., 60)
        mirror_final = canonical_final.copy()
        mirror_final[:, 0::3] *= -1.0

        for vec in canonical_final:
            final_rows.append({"label": cls, **{f"f{i}": round(float(vec[i]), 6) for i in range(63)}})
        for vec in mirror_final:
            final_rows.append({"label": cls, **{f"f{i}": round(float(vec[i]), 6) for i in range(63)}})

        report["per_class_summary"][cls] = {
            "kemendikdasmen_canonical_samples": int(len(cls_gold_samples)),
            "kaggle_raw_candidates": int(total_kaggle_raw),
            "kaggle_clean_kept": int(total_kaggle_kept),
            "accepted_providers": accepted_providers,
            "rejected_providers": rejected_providers,
            "final_canonical_samples": int(len(canonical_final)),
            "final_mirror_samples": int(len(mirror_final)),
            "final_total_samples": int(len(canonical_final) + len(mirror_final)),
        }
        print(
            f"   [Kelas {cls:>2}] Gold={len(cls_gold_samples):>2} | Kaggle Keep={total_kaggle_kept:>3}/{total_kaggle_raw:<3} "
            f"| DropProv={len(rejected_providers)} -> Final={len(canonical_final)} Canon + {len(mirror_final)} Mirror = {len(canonical_final)*2}"
        )

    # Hitung matriks kemiripan antar-kelas (khususnya antara Huruf A-Z dan Angka 1-10) untuk fitur Quick Suggestion di Android
    print("\n🔗 [3/5] Menganalisis pasangan Huruf & Angka yang memiliki kemiripan bentuk jari tinggi...")
    for c1 in TARGET_CLASSES:
        sims_other = []
        for c2 in TARGET_CLASSES:
            if c1 == c2:
                continue
            s = cosine_sim(golden_centroids[c1], golden_centroids[c2])
            sims_other.append((c2, round(s, 4)))
        sims_other.sort(key=lambda x: x[1], reverse=True)
        report["visually_similar_pairs"][c1] = sims_other[:3]
        if sims_other[0][1] >= 0.88:
            print(f"   💡 '{c1}' sangat mirip dengan: {sims_other[0][0]} (cos={sims_other[0][1]}), {sims_other[1][0]} (cos={sims_other[1][1]})")

    # Simpan static_labels.txt (36 kelas: A..Z + 1..10)
    print("\n💾 [4/5] Menyimpan static_labels.txt, static_data.csv, landmarks.csv & laporan audit...")
    feature_utils.STATIC_LABELS_PATH.write_text("\n".join(TARGET_CLASSES) + "\n", encoding="utf-8")

    out_df = pd.DataFrame(final_rows)
    out_df.to_csv(STATIC_DATA_CSV, index=False)
    out_df.to_csv(LANDMARKS_CSV, index=False)

    CLEANING_REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    shutil.copy2(CLEANING_REPORT_JSON, ARTIFACTS_DIR / "sibi_cleaning_report.json")
    if BRAIN_DIR.exists():
        shutil.copy2(CLEANING_REPORT_JSON, BRAIN_DIR / "sibi_cleaning_report.json")

    print("🖼️ [5/5] Membuat Poster Panduan Visual Abjad (A-Z) & Angka (1-10) SIBI 1 Tangan...")
    poster_paths = [
        ARTIFACTS_DIR / "panduan_sibi_abjad_angka_1_tangan.png",
        STATIC_DIR / "panduan_sibi_abjad_angka_1_tangan.png",
    ]
    if BRAIN_DIR.exists():
        poster_paths.append(BRAIN_DIR / "panduan_sibi_abjad_angka_1_tangan.png")
    generate_visual_guide_poster(golden_centroids, poster_paths)

    print(f"\n✅ Pipeline Cleaning & Mirroring Selesai!")
    print(f"   Total sampel siap training : {len(out_df)} baris ({len(TARGET_CLASSES)} kelas @ 50% kanan / 50% kiri)")
    print(f"   Dataset CSV                : {STATIC_DATA_CSV}")
    print(f"   Cleaning Audit Report      : {CLEANING_REPORT_JSON}")


if __name__ == "__main__":
    main()

