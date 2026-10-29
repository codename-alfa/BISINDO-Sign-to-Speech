"""
collect_dynamic_data.py — Skrip perekaman data gestur dinamis BISINDO (Sprint 2, Time-Based Raw NPZ).

Target Kelas (6 Kelas dari labels/dynamic_labels.txt):
1. Halo
2. Terima kasih
3. Tolong
4. Ya
5. Tidak
6. _idle  (tangan diam / gerakan transisi acak tanpa makna isyarat)

Fitur Utama (Kontrak Sprint 2):
- Resolusi kamera dikunci 640x480 (4:3)
- Perekaman berbasis waktu 2.0 detik (RECORD_DURATION_MS = 2000 ms)
- Menyimpan raw landmark dalam model space (NaN jika tangan tidak terdeteksi) beserta timestamps_ms
  ke `data/dynamic_raw/<KELAS>/<signer>_<idx:03d>.npz`
- Argumen CLI:
  * `--signer danish|vanesa|ahmad` (default: danish)
  * `--review` : putar ulang maksimal 3 sampel acak per kelas untuk verifikasi kualitas
- Kontrol Keyboard:
  * 'r' : Mulai hitung mundur 3 detik & rekam 2.0 detik
  * 'u' : Undo (hapus rekaman terakhir pada kelas aktif)
  * 'n' / 'p' : Pindah ke kelas berikutnya / sebelumnya
  * 'q' : Keluar
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
DYNAMIC_RAW_DIR = ROOT / "data" / "dynamic_raw"
MODEL_ASSET = ROOT / "assets" / "hand_landmarker.task"
LABELS_PATH = ROOT / "labels" / "dynamic_labels.txt"

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
RECORD_DURATION_MS = 2000

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def load_classes() -> list[str]:
    raw_labels = feature_utils.load_labels(LABELS_PATH)
    return [lbl.replace(" ", "_") for lbl in raw_labels]


def init_landmarker() -> vision.HandLandmarker:
    if not MODEL_ASSET.exists():
        raise FileNotFoundError(f"Model {MODEL_ASSET} tidak ditemukan.")
    base_options = mp_python.BaseOptions(model_asset_path=str(MODEL_ASSET))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def list_existing_takes(class_name: str, signer: str | None = None) -> list[Path]:
    class_dir = DYNAMIC_RAW_DIR / class_name
    if not class_dir.exists():
        return []
    pattern = f"{signer}_*.npz" if signer else "*.npz"
    return sorted(class_dir.glob(pattern))


def next_take_index(class_name: str, signer: str) -> int:
    takes = list_existing_takes(class_name, signer)
    if not takes:
        return 0
    indices = []
    for p in takes:
        stem_parts = p.stem.split("_")
        if stem_parts and stem_parts[-1].isdigit():
            indices.append(int(stem_parts[-1]))
    return (max(indices) + 1) if indices else len(takes)


def draw_skeleton_norm(frame: np.ndarray, landmarks) -> None:
    h, w, _ = frame.shape
    coords = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for p1, p2 in HAND_CONNECTIONS:
        cv2.line(frame, coords[p1], coords[p2], (0, 255, 255), 2, cv2.LINE_AA)
    for cx, cy in coords:
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1, cv2.LINE_AA)


def compute_max_missing_gap_ms(timestamps_ms: list[float], valid_flags: list[bool]) -> float:
    """Hitung durasi terpanjang tangan hilang berturut-turut dalam rekaman (ms)."""
    if not timestamps_ms:
        return float(RECORD_DURATION_MS)
    valid_ts = [t for t, ok in zip(timestamps_ms, valid_flags) if ok]
    if not valid_ts:
        return float(timestamps_ms[-1] - timestamps_ms[0]) if len(timestamps_ms) > 1 else float(RECORD_DURATION_MS)
    gaps = [
        valid_ts[0] - timestamps_ms[0],
        timestamps_ms[-1] - valid_ts[-1],
    ]
    for i in range(len(valid_ts) - 1):
        gaps.append(valid_ts[i + 1] - valid_ts[i])
    return float(max(gaps))


def review_recordings(specific_file: Path | None = None) -> None:
    """Putar ulang rekaman secara visual untuk cek kualitas tracking/gerakan.
    
    Jika specific_file diberikan, putar file tersebut berulang kali (looping)
    hingga pengguna menekan 'q' atau ESC. Tekan spasi untuk jeda/lanjut.
    """
    classes = load_classes()
    print("=" * 60)
    print("🔍 MODE REVIEW REKAMAN DYNAMIC_RAW (.npz)")
    print("   Kontrol: 'q' / ESC = keluar, Spasi = jeda / lanjut")
    print("=" * 60)

    if specific_file is not None:
        target_files = [specific_file]
        loop_single = True
    else:
        target_files = []
        for cls in classes:
            takes = list_existing_takes(cls)
            if takes:
                target_files.extend(random.sample(takes, k=min(3, len(takes))))
        loop_single = False

    if not target_files:
        print("⚠️ Tidak ada file rekaman untuk di-review.")
        return

    for npz_path in target_files:
        if not npz_path.exists():
            print(f"❌ File tidak ditemukan: {npz_path}")
            continue

        data = np.load(npz_path, allow_pickle=True)
        ts = data["timestamps_ms"]
        lms = data["landmarks"]  # (N, 21, 3) in model space
        w = int(data.get("width", CAMERA_WIDTH))
        h = int(data.get("height", CAMERA_HEIGHT))
        lbl = str(data.get("label", npz_path.parent.name))
        signer = str(data.get("signer", npz_path.stem.split("_")[0]))
        aspect = w / h if h > 0 else 1.0

        print(f"\n▶️ Memutar: {npz_path.name} (Label: '{lbl}', Signer: '{signer}', {len(ts)} frame)")

        paused = False
        while True:
            for idx, (t_ms, pts) in enumerate(zip(ts, lms)):
                canvas = np.zeros((h, w, 3), dtype=np.uint8)
                cv2.rectangle(canvas, (0, 0), (w, 75), (30, 30, 30), -1)
                cv2.putText(
                    canvas,
                    f"REVIEW: {lbl} [{signer}] | {npz_path.name}",
                    (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )
                cv2.putText(
                    canvas,
                    f"Frame {idx + 1}/{len(ts)} ({t_ms:.0f} ms) | Spasi: Pause, 'q': Keluar",
                    (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (200, 200, 200),
                    1,
                )

                if not np.isnan(pts).any():
                    coords = [(int((pt[0] / aspect) * w), int(pt[1] * h)) for pt in pts]
                    for p1, p2 in HAND_CONNECTIONS:
                        cv2.line(canvas, coords[p1], coords[p2], (0, 230, 118), 2, cv2.LINE_AA)
                    for cx, cy in coords:
                        cv2.circle(canvas, (cx, cy), 4, (255, 255, 255), -1, cv2.LINE_AA)
                else:
                    cv2.putText(
                        canvas,
                        "TANGAN TIDAK TERDETEKSI (NaN)",
                        (15, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )

                cv2.imshow("BISINDO Dynamic Review", canvas)

                # Frame timing approx 40-50ms (or responsive pause)
                key = cv2.waitKey(45) & 0xFF
                if key in (ord("q"), 27):
                    cv2.destroyAllWindows()
                    print("✅ Selesai me-review rekaman.")
                    return
                elif key == 32:  # Spasi (pause)
                    paused = True
                    while paused:
                        k2 = cv2.waitKey(100) & 0xFF
                        if k2 in (ord("q"), 27):
                            cv2.destroyAllWindows()
                            return
                        elif k2 == 32:
                            paused = False

            if not loop_single:
                break

    cv2.destroyAllWindows()
    print("✅ Selesai me-review rekaman.")


def run_recorder(signer: str) -> None:
    classes = load_classes()
    current_idx = 0

    print("=" * 65)
    print(f"🎥 BISINDO DYNAMIC GESTURE RECORDER (Signer: {signer})")
    print(f"Target Kelas ({len(classes)}): {classes}")
    print(f"Durasi Rekam per Take: {RECORD_DURATION_MS / 1000:.1f} detik @ {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print("Kontrol Keyboard:")
    print("  'r' : Mulai countdown 3 detik & rekam 2.0 detik")
    print("  'u' : Undo (hapus take terakhir milik signer ini di kelas aktif)")
    print("  'n' : Pindah ke kelas berikutnya")
    print("  'p' : Pindah ke kelas sebelumnya")
    print("  'q' : Keluar")
    print("=" * 65)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Kamera webcam tidak dapat dibuka.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    landmarker = init_landmarker()

    state = "IDLE"  # IDLE, COUNTDOWN, RECORDING
    countdown_start = 0.0
    record_start = 0.0
    rec_timestamps_ms: list[float] = []
    rec_landmarks_ms: list[np.ndarray] = []
    rec_valid_flags: list[bool] = []
    last_warning_msg = ""
    last_warning_until = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Pastikan resolusi 640x480 (4:3)
        if frame.shape[1] != CAMERA_WIDTH or frame.shape[0] != CAMERA_HEIGHT:
            frame = cv2.resize(frame, (CAMERA_WIDTH, CAMERA_HEIGHT))

        # Mirror selfie view: koordinat landmark dari frame ini sudah bercermin di sumbu X
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection = landmarker.detect(mp_img)

        hand_detected = bool(detection.hand_landmarks)
        current_model_pts: np.ndarray | None = None

        if hand_detected:
            raw_lms = detection.hand_landmarks[0]
            draw_skeleton_norm(frame, raw_lms)
            try:
                # mirror_x=False karena frame sudah di-flip secara horizontal di atas
                current_model_pts = feature_utils.to_model_space(raw_lms, w, h, mirror_x=False)
            except Exception:
                current_model_pts = None

        current_class = classes[current_idx]
        signer_takes = list_existing_takes(current_class, signer)
        all_takes = list_existing_takes(current_class, None)

        # UI Overlay Header
        cv2.rectangle(frame, (0, 0), (w, 92), (20, 20, 20), -1)
        cv2.putText(
            frame,
            f"KELAS: {current_class} ({current_idx + 1}/{len(classes)}) | Signer '{signer}': {len(signer_takes)} (Total: {len(all_takes)})",
            (15, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (0, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            "Tekan 'r': Rekam 2.0s | 'u': Undo | 'n'/'p': Ganti Kelas | 'q': Keluar",
            (15, 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (200, 200, 200),
            1,
        )

        # Ringkasan progres semua kelas di baris ke-3 header
        summary_counts = " | ".join(f"{c[:6]}:{len(list_existing_takes(c, signer))}" for c in classes)
        cv2.putText(frame, summary_counts, (15, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (160, 220, 160), 1)

        now = time.perf_counter()

        if now < last_warning_until and last_warning_msg:
            cv2.rectangle(frame, (15, 100), (w - 15, 138), (0, 0, 180), -1)
            cv2.putText(frame, last_warning_msg, (25, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        if state == "IDLE":
            status_text = "STATUS: SIAP (Tekan 'r' untuk rekam)"
            status_color = (0, 255, 0) if hand_detected else (0, 165, 255)
            cv2.putText(frame, status_text, (15, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

        elif state == "COUNTDOWN":
            rem = 3 - int(now - countdown_start)
            if rem > 0:
                cv2.putText(
                    frame,
                    f"BERSIAP: {rem}",
                    (w // 2 - 140, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.8,
                    (0, 0, 255),
                    4,
                )
            else:
                state = "RECORDING"
                record_start = now
                rec_timestamps_ms = []
                rec_landmarks_ms = []
                rec_valid_flags = []
                print(f"🔴 Merekam '{current_class}' (2.0 detik)...")

        elif state == "RECORDING":
            elapsed_ms = (now - record_start) * 1000.0
            rec_timestamps_ms.append(float(elapsed_ms))
            if current_model_pts is not None:
                rec_landmarks_ms.append(current_model_pts)
                rec_valid_flags.append(True)
            else:
                rec_landmarks_ms.append(np.full((feature_utils.NUM_LANDMARKS, feature_utils.NUM_COORDS), np.nan, dtype=np.float32))
                rec_valid_flags.append(False)

            progress_ratio = min(1.0, elapsed_ms / RECORD_DURATION_MS)
            cv2.putText(
                frame,
                f"MEREKAM: {elapsed_ms / 1000.0:.2f}s / {RECORD_DURATION_MS / 1000.0:.1f}s ({len(rec_timestamps_ms)} frames)",
                (15, h - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 255),
                2,
            )
            bar_w = int(progress_ratio * (w - 30))
            cv2.rectangle(frame, (15, h - 20), (15 + bar_w, h - 10), (0, 0, 255), -1)

            if elapsed_ms >= RECORD_DURATION_MS:
                max_gap = compute_max_missing_gap_ms(rec_timestamps_ms, rec_valid_flags)
                is_idle_class = current_class.startswith("_")
                if not is_idle_class and max_gap > feature_utils.MAX_GAP_MS:
                    last_warning_msg = f"PERINGATAN: Tangan hilang {max_gap:.0f} ms (>300ms)! Tekan 'u' untuk ulang."
                    last_warning_until = now + 5.0
                    print(f"⚠️ {last_warning_msg}")

                target_dir = DYNAMIC_RAW_DIR / current_class
                target_dir.mkdir(parents=True, exist_ok=True)
                take_idx = next_take_index(current_class, signer)
                out_path = target_dir / f"{signer}_{take_idx:03d}.npz"

                ts_arr = np.array(rec_timestamps_ms, dtype=np.float32)
                lms_arr = np.stack(rec_landmarks_ms, axis=0).astype(np.float32)
                fps_est = len(ts_arr) / max(0.001, (ts_arr[-1] / 1000.0)) if len(ts_arr) > 1 else 0.0

                np.savez_compressed(
                    out_path,
                    timestamps_ms=ts_arr,
                    landmarks=lms_arr,
                    width=np.int32(w),
                    height=np.int32(h),
                    fps=np.float32(fps_est),
                    signer=signer,
                    label=current_class,
                )
                print(
                    f"✅ Disimpan: {out_path.relative_to(ROOT)} | {len(ts_arr)} frame ({fps_est:.1f} FPS), max_gap={max_gap:.0f} ms"
                )
                state = "IDLE"

        cv2.imshow("BISINDO Dynamic Recorder", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("r") and state == "IDLE":
            state = "COUNTDOWN"
            countdown_start = time.perf_counter()
        elif key == ord("u") and state == "IDLE":
            takes = list_existing_takes(current_class, signer)
            if takes:
                last_file = takes[-1]
                last_file.unlink(missing_ok=True)
                last_warning_msg = f"UNDO: {last_file.name} dihapus."
                last_warning_until = time.perf_counter() + 3.0
                print(f"🗑️ Undo berhasil: {last_file.name} dihapus.")
            else:
                print(f"ℹ️ Belum ada rekaman '{signer}' di kelas '{current_class}' untuk di-undo.")
        elif key == ord("n") and state == "IDLE":
            current_idx = (current_idx + 1) % len(classes)
        elif key == ord("p") and state == "IDLE":
            current_idx = (current_idx - 1) % len(classes)

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("👋 Sesi perekaman selesai.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BISINDO Dynamic Gesture Recorder (Raw NPZ)")
    parser.add_argument(
        "--signer",
        type=str,
        default="danish",
        choices=["danish", "vanesa", "ahmad"],
        help="Nama anggota tim perekam (danish | vanesa | ahmad)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Putar ulang sampel rekaman acak per kelas untuk cek kualitas",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="Path file .npz spesifik untuk diputar ulang secara visual (misal: data/dynamic_raw/Terima_kasih/danish_053.npz)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.file:
        review_recordings(Path(args.file))
    elif args.review:
        review_recordings()
    else:
        run_recorder(args.signer.lower())
