"""
scrape_kemendikdasmen_sibi.py — Scraper resmi untuk Kamus SIBI Kemendikdasmen
(https://pkplk.kemendikdasmen.go.id/sibi/).

Mengunduh:
1. 26 Foto Studio Abjad (A..Z): /sibi/SIBI/abjad/{A..Z}.png (+ membuat versi mirrornya)
2. 26 Video HD Peragaan Abjad (A..Z): /sibi/SIBI/katadasar/{A..Z}.webm
3. 40 Video HD Peragaan Angka (1..10, 11..1000, Satuan/Puluhan/Ratusan/Ribuan): /sibi/SIBI/angka/*.webm

Serta mengekstrak:
- Seluruh frame puncak ("Apex Hold Frames" saat tangan stabil memperagakan gestur)
- Menyimpan citra apex hold asli & versi mirror fisiknya (cv2.flip)
- Mengekstrak 21 titik 3D MediaPipe HandLandmarker (orientasi kanonik & mirror)
- Menghasilkan Golden Reference Centroids untuk 36 kelas statis (A-Z + 1-10)
"""

from __future__ import annotations

import json
import os
import re
import ssl
import string
import sys
import urllib.request
from pathlib import Path

import cv2
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
RAW_SIBI_DIR = ROOT / "data" / "raw_sibi" / "kemendikdasmen"
ABJAD_IMG_DIR = RAW_SIBI_DIR / "abjad_img"
ABJAD_MIRROR_IMG_DIR = RAW_SIBI_DIR / "abjad_img_mirror"
ABJAD_VID_DIR = RAW_SIBI_DIR / "abjad_video"
ANGKA_VID_DIR = RAW_SIBI_DIR / "angka_video"
APEX_FRAMES_DIR = RAW_SIBI_DIR / "apex_frames"
APEX_MIRROR_DIR = RAW_SIBI_DIR / "apex_frames_mirror"

GOLDEN_CSV = RAW_SIBI_DIR / "kemendikdasmen_golden_landmarks.csv"
GOLDEN_CENTROIDS_JSON = RAW_SIBI_DIR / "kemendikdasmen_golden_centroids.json"

HAND_LANDMARKER_PATH = ROOT.parent / "android_app" / "app" / "src" / "main" / "assets" / "hand_landmarker.task"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def download_file(url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists() and dest.stat().st_size > 512:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    safe_url = url.replace(" ", "%20")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(safe_url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, context=CTX, timeout=25).read()
            dest.write_bytes(data)
            return True
        except Exception as e:
            if attempt == retries - 1:
                print(f"   [WARN] Gagal mengunduh {url}: {e}")
    return False


def discover_angka_videos() -> list[tuple[str, str]]:
    """Kembalikan list (label_bersih, video_url) dari semua halaman /kosakata/angka."""
    discovered: list[tuple[str, str]] = []
    seen_urls = set()
    for offset in ["", "/12", "/24", "/36"]:
        url = f"https://pkplk.kemendikdasmen.go.id/sibi/kosakata/angka{offset}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            html = urllib.request.urlopen(req, context=CTX, timeout=20).read().decode("utf-8", errors="ignore")
            items = re.findall(
                r'<source src="([^"]+)"[^>]*>.*?<p class="topText"><strong>\s*&nbsp;(.*?)&nbsp;\s*</strong></p>',
                html,
                re.DOTALL,
            )
            for src, lbl in items:
                clean_lbl = lbl.strip().replace(".", "")
                if src not in seen_urls:
                    seen_urls.add(src)
                    discovered.append((clean_lbl, src))
        except Exception as e:
            print(f"   [WARN] Gagal memindai halaman angka {url}: {e}")
    return discovered


def create_detector(min_conf: float = 0.25) -> vision.HandLandmarker:
    base_options = python.BaseOptions(model_asset_path=str(HAND_LANDMARKER_PATH))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=min_conf,
        min_hand_presence_confidence=min_conf,
    )
    return vision.HandLandmarker.create_from_options(options)


def detect_single_hand(detector: vision.HandLandmarker, bgr_img: np.ndarray, try_padding: bool = True):
    """Deteksi 1 tangan utama pada citra BGR. Kembalikan (pts_21x3, handedness, confidence, img_shape)."""
    candidates = [bgr_img]
    if try_padding:
        candidates.append(cv2.copyMakeBorder(bgr_img, 80, 80, 80, 80, cv2.BORDER_CONSTANT, value=[255, 255, 255]))
        candidates.append(cv2.copyMakeBorder(bgr_img, 140, 140, 140, 140, cv2.BORDER_CONSTANT, value=[255, 255, 255]))

    for img in candidates:
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = detector.detect(mp_img)
        if res.hand_landmarks:
            # Jika ada 2 tangan di video peraga (misal tangan kiri diam di bawah), ambil tangan yang posisinya lebih tinggi (y_wrist lebih kecil)
            best_idx = 0
            if len(res.hand_landmarks) > 1:
                y_wrists = [hlm[0].y for hlm in res.hand_landmarks]
                best_idx = int(np.argmin(y_wrists))
            lm = res.hand_landmarks[best_idx]
            pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float64)
            handedness = res.handedness[best_idx][0].category_name
            score = float(res.handedness[best_idx][0].score)
            return pts, handedness, score, (w, h)
    return None


def extract_apex_frames_from_video(
    detector: vision.HandLandmarker,
    video_path: Path,
    top_k: int = 28,
) -> list[tuple[np.ndarray, np.ndarray, str, float, tuple[int, int]]]:
    """
    Ekstrak frame-frame puncak ('Apex Hold') dari video peragaan Kemendikdasmen:
    Peraga mengangkat tangan dari bawah -> menahan pose huruf/angka di posisi atas -> menurunkan tangan.
    Kita memilih frame di mana pergelangan tangan sudah diangkat (y_wrist lebih tinggi dari rata-rata bawah)
    dan kecepatan gerak jari paling stabil.
    """
    cap = cv2.VideoCapture(str(video_path))
    raw_detections = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        det = detect_single_hand(detector, frame, try_padding=False)
        if det is not None:
            pts, handedness, score, wh = det
            hand_size = float(np.linalg.norm(pts[0] - pts[9]))
            if hand_size > 0.02:
                raw_detections.append({
                    "frame_idx": frame_idx,
                    "frame": frame,
                    "pts": pts,
                    "handedness": handedness,
                    "score": score,
                    "wh": wh,
                    "wrist_y": float(pts[0, 1]),
                    "mean_y": float(np.mean(pts[:, 1])),
                })
    cap.release()

    if not raw_detections:
        return []

    # Filter hanya saat tangan sedang diangkat memperagakan isyarat (mean_y di bagian 65% tertinggi dari rentang gerak video)
    all_mean_y = np.array([d["mean_y"] for d in raw_detections])
    y_min, y_max = float(np.min(all_mean_y)), float(np.max(all_mean_y))
    y_thresh = y_min + 0.55 * (y_max - y_min) if (y_max - y_min) > 0.08 else y_max + 1.0

    active = [d for d in raw_detections if d["mean_y"] <= y_thresh]
    if len(active) < 5:
        active = raw_detections

    # Hitung stabilitas bentuk jari (fitur 63D kanonik) terhadap median frame aktif
    feats = []
    for d in active:
        w, h = d["wh"]
        # Canonicalize ke orientasi yang seragam berdasarkan handedness
        pts_c = d["pts"].copy()
        ms = feature_utils.to_model_space(pts_c, w, h, mirror_x=False)
        f63 = feature_utils.normalize_landmarks(ms)
        # Jika handedness Left, balik komponen X agar sebanding
        if d["handedness"].lower() == "left":
            f63 = f63.copy()
            f63[0::3] *= -1.0
        feats.append(f63)

    feats_arr = np.stack(feats, axis=0)
    median_feat = np.median(feats_arr, axis=0)
    dists = np.linalg.norm(feats_arr - median_feat, axis=1)

    order = np.argsort(dists)[:top_k]
    selected = []
    for idx in order:
        d = active[int(idx)]
        selected.append((d["frame"], d["pts"], d["handedness"], d["score"], d["wh"]))
    return selected


def canonical_and_mirror_features(
    pts_21x3: np.ndarray,
    width: int,
    height: int,
    handedness: str,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Kembalikan (feat_canonical_right, feat_mirror_left) dalam ruang 63 fitur.
    Dengan memastikan satu vektor adalah orientasi kanonik (Right) dan pasangannya adalah
    mirror horizontalnya (x -> -x), kita menjamin 100% ketersediaan versi asli + mirror!
    """
    ms = feature_utils.to_model_space(pts_21x3, width, height, mirror_x=False)
    feat = feature_utils.normalize_landmarks(ms)

    # Normalisasi kanonik: pastikan feat_canonical merepresentasikan sisi tangan acuan yang konsisten
    # Pada MediaPipe, jika kita membalik citra secara horizontal (x -> 1 - x), maka komponen X pada
    # 63 fitur (indeks 0, 3, 6, ..., 60) berubah tanda (f[0::3] *= -1).
    feat_mirror = feat.copy()
    feat_mirror[0::3] *= -1.0

    if handedness.lower() == "left":
        return feat_mirror, feat
    return feat, feat_mirror


def main():
    for d in [ABJAD_IMG_DIR, ABJAD_MIRROR_IMG_DIR, ABJAD_VID_DIR, ANGKA_VID_DIR, APEX_FRAMES_DIR, APEX_MIRROR_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    print("🌐 [1/4] Mengunduh 26 Foto Studio & 26 Video HD Abjad SIBI dari Kemendikdasmen...")
    for letter in string.ascii_uppercase:
        img_url = f"https://pkplk.kemendikdasmen.go.id/sibi/SIBI/abjad/{letter}.png"
        vid_url = f"https://pkplk.kemendikdasmen.go.id/sibi/SIBI/katadasar/{letter}.webm"
        img_dst = ABJAD_IMG_DIR / f"{letter}.png"
        vid_dst = ABJAD_VID_DIR / f"{letter}.webm"
        download_file(img_url, img_dst)
        download_file(vid_url, vid_dst)
        # Buat versi mirror fisik dari foto studio
        if img_dst.exists():
            img = cv2.imread(str(img_dst))
            if img is not None:
                cv2.imwrite(str(ABJAD_MIRROR_IMG_DIR / f"{letter}_mirror.png"), cv2.flip(img, 1))

    print("🌐 [2/4] Memindai & mengunduh seluruh 40 Video HD Angka SIBI dari Kemendikdasmen...")
    angka_items = discover_angka_videos()
    print(f"   Ditemukan {len(angka_items)} video angka di Kemendikdasmen.")
    for lbl, url in angka_items:
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", lbl)
        vid_dst = ANGKA_VID_DIR / f"{safe_name}.webm"
        download_file(url, vid_dst)

    print("🤖 [3/4] Mengekstrak 3D Landmarks, Apex Hold Frames & membuat pasangan Mirror...")
    detector = create_detector(min_conf=0.15)

    rows = []
    golden_centroids: dict[str, list[float]] = {}

    # Daftar kelas statis: A..Z (26) + 1..10 (10) = 36 kelas
    target_classes = list(string.ascii_uppercase) + [str(i) for i in range(1, 11)]

    for cls in target_classes:
        cls_canonical_vecs = []

        # 1. Jika huruf A-Z, ekstrak dari foto studio PNG terlebih dahulu
        if cls in string.ascii_uppercase:
            img_path = ABJAD_IMG_DIR / f"{cls}.png"
            if img_path.exists():
                bgr = cv2.imread(str(img_path))
                if bgr is not None:
                    det = detect_single_hand(detector, bgr, try_padding=True)
                    if det is not None:
                        pts, handed, score, (w, h) = det
                        f_canon, f_mir = canonical_and_mirror_features(pts, w, h, handed)
                        # Bobot tinggi untuk foto studio resmi
                        for _ in range(5):
                            cls_canonical_vecs.append(f_canon)
                        rows.append({
                            "label": cls,
                            "provider": "kemendikdasmen_png",
                            "orientation": "canonical",
                            "confidence": score,
                            **{f"f{i}": float(f_canon[i]) for i in range(63)},
                        })
                        rows.append({
                            "label": cls,
                            "provider": "kemendikdasmen_png_mirror",
                            "orientation": "mirror",
                            "confidence": score,
                            **{f"f{i}": float(f_mir[i]) for i in range(63)},
                        })

        # 2. Ekstrak dari Video HD (.webm)
        if cls in string.ascii_uppercase:
            vid_path = ABJAD_VID_DIR / f"{cls}.webm"
        else:
            vid_path = ANGKA_VID_DIR / f"{cls}.webm"

        if vid_path.exists():
            apex_list = extract_apex_frames_from_video(detector, vid_path, top_k=30)
            if apex_list:
                # Simpan 1 citra apex representatif + versi mirror fisiknya untuk dokumentasi & poster panduan
                best_frame = apex_list[0][0]
                cv2.imwrite(str(APEX_FRAMES_DIR / f"{cls}_apex.jpg"), best_frame)
                cv2.imwrite(str(APEX_MIRROR_DIR / f"{cls}_apex_mirror.jpg"), cv2.flip(best_frame, 1))

                for frame_bgr, pts, handed, score, (w, h) in apex_list:
                    f_canon, f_mir = canonical_and_mirror_features(pts, w, h, handed)
                    cls_canonical_vecs.append(f_canon)
                    rows.append({
                        "label": cls,
                        "provider": "kemendikdasmen_video",
                        "orientation": "canonical",
                        "confidence": score,
                        **{f"f{i}": float(f_canon[i]) for i in range(63)},
                    })
                    rows.append({
                        "label": cls,
                        "provider": "kemendikdasmen_video_mirror",
                        "orientation": "mirror",
                        "confidence": score,
                        **{f"f{i}": float(f_mir[i]) for i in range(63)},
                    })

        if cls_canonical_vecs:
            centroid = np.median(np.stack(cls_canonical_vecs, axis=0), axis=0)
            golden_centroids[cls] = [round(float(x), 6) for x in centroid]
            print(f"   [OK] Kelas '{cls}': {len(cls_canonical_vecs)} sampel kanonik (+{len(cls_canonical_vecs)} mirror) diekstrak.")
        else:
            print(f"   [ERR] Kelas '{cls}': Tidak ada landmark terdeteksi!")

    detector.close()

    df = pd.DataFrame(rows)
    df.to_csv(GOLDEN_CSV, index=False)
    GOLDEN_CENTROIDS_JSON.write_text(json.dumps(golden_centroids, indent=2), encoding="utf-8")
    print(f"\n✅ [4/4] Selesai! Total sampel referensi Kemendikdasmen (asli + mirror): {len(df)} baris.")
    print(f"   Golden CSV      : {GOLDEN_CSV}")
    print(f"   Golden Centroids: {GOLDEN_CENTROIDS_JSON} ({len(golden_centroids)}/36 kelas)")


if __name__ == "__main__":
    main()

