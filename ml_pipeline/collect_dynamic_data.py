"""
collect_dynamic_data.py — Skrip perekaman data gestur dinamis BISINDO via webcam laptop.

Target Kata (5 Kelas):
1. Halo
2. Terima kasih
3. Tolong
4. Ya
5. Tidak

Fitur:
- Deteksi keypoints tangan real-time via MediaPipe Tasks HandLandmarker
- Countdown 3 detik sebelum perekaman dimulai
- Perekaman tepat 30 frame sekuens (shape: 30, 63)
- Normalisasi on-the-fly memakai feature_utils.normalize_landmarks()
- Penyimpanan otomatis ke data/dynamic/<LABEL>/seq_<idx>.npy
- Tombol:
  * 'r' : Mulai hitung mundur & rekam sekuens
  * 'n' : Ganti ke kelas berikutnya
  * 'p' : Ganti ke kelas sebelumnya
  * 'q' : Keluar
"""

from __future__ import annotations

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
DYNAMIC_DIR = ROOT / "data" / "dynamic"
MODEL_ASSET = ROOT / "assets" / "hand_landmarker.task"
LABELS_PATH = ROOT / "labels" / "dynamic_labels.txt"

def load_classes() -> list[str]:
    raw_labels = feature_utils.load_labels(LABELS_PATH)
    # Gunakan nama folder yang aman (ganti spasi dengan underscore)
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

def count_existing_sequences(class_name: str) -> int:
    class_dir = DYNAMIC_DIR / class_name
    if not class_dir.exists():
        return 0
    return len(list(class_dir.glob("*.npy")))

def draw_skeleton(frame: np.ndarray, landmarks) -> None:
    h, w, _ = frame.shape
    coords = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17)
    ]
    for p1, p2 in connections:
        cv2.line(frame, coords[p1], coords[p2], (0, 255, 255), 2)
    for cx, cy in coords:
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

def run_recorder():
    classes = load_classes()
    current_idx = 0

    print("=" * 60)
    print("🎥 BISINDO DYNAMIC GESTURE RECORDER")
    print(f"Target Kelas ({len(classes)}): {classes}")
    print("Kontrol Keyboard:")
    print("  'r' : Mulai countdown 3 detik & rekam 30 frames")
    print("  'n' : Pindah ke kelas berikutnya")
    print("  'p' : Pindah ke kelas sebelumnya")
    print("  'q' : Keluar")
    print("=" * 60)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Kamera webcam tidak dapat dibuka.")
        return

    landmarker = init_landmarker()

    state = "IDLE" # IDLE, COUNTDOWN, RECORDING
    countdown_start = 0.0
    recorded_frames: list[np.ndarray] = []
    last_valid_features: np.ndarray | None = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1) # Mirror selfie view
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection = landmarker.detect(mp_img)

        hand_detected = bool(detection.hand_landmarks)
        current_features = None

        if hand_detected:
            draw_skeleton(frame, detection.hand_landmarks[0])
            try:
                current_features = feature_utils.normalize_landmarks(detection.hand_landmarks[0])
                last_valid_features = current_features
            except Exception:
                pass

        current_class = classes[current_idx]
        total_saved = count_existing_sequences(current_class)

        # UI Overlay Header
        cv2.rectangle(frame, (0, 0), (w, 80), (20, 20, 20), -1)
        cv2.putText(frame, f"TARGET: {current_class} ({current_idx + 1}/{len(classes)}) | Tersimpan: {total_saved} sekuens", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "Tekan 'r': Rekam | 'n'/'p': Ganti Kelas | 'q': Keluar", (15, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        now = time.time()

        if state == "IDLE":
            status_text = "STATUS: SIAP (Tekan 'r' untuk rekam)"
            status_color = (0, 255, 0) if hand_detected else (0, 165, 255)
            cv2.putText(frame, status_text, (15, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        elif state == "COUNTDOWN":
            rem = 3 - int(now - countdown_start)
            if rem > 0:
                cv2.putText(frame, f"BERSIAP DALAM: {rem}", (w // 2 - 180, h // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 0, 255), 4)
            else:
                state = "RECORDING"
                recorded_frames = []
                print(f"🔴 Merekam kelas '{current_class}'...")

        elif state == "RECORDING":
            # Ambil fitur frame saat ini (atau ulangi frame terakhir jika deteksi sempat putus)
            feat_to_add = current_features if current_features is not None else last_valid_features
            if feat_to_add is None:
                feat_to_add = np.zeros(feature_utils.NUM_FEATURES, dtype=np.float32)

            recorded_frames.append(feat_to_add)
            progress = len(recorded_frames)

            # Progress HUD
            cv2.putText(frame, f"🔴 MEREKAM: {progress}/{feature_utils.SEQUENCE_LENGTH}", (15, h - 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            bar_w = int((progress / feature_utils.SEQUENCE_LENGTH) * (w - 30))
            cv2.rectangle(frame, (15, h - 20), (15 + bar_w, h - 10), (0, 0, 255), -1)

            if progress >= feature_utils.SEQUENCE_LENGTH:
                # Selesai rekam sekuens
                target_dir = DYNAMIC_DIR / current_class
                target_dir.mkdir(parents=True, exist_ok=True)
                seq_arr = np.stack(recorded_frames, axis=0).astype(np.float32)
                seq_idx = count_existing_sequences(current_class)
                out_path = target_dir / f"seq_{seq_idx:03d}.npy"
                np.save(out_path, seq_arr)
                print(f"✅ Sekuens #{seq_idx:03d} berhasil disimpan ke: {out_path.name}")
                state = "IDLE"

        cv2.imshow("BISINDO Dynamic Recorder", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('r') and state == "IDLE":
            state = "COUNTDOWN"
            countdown_start = time.time()
        elif key == ord('n') and state == "IDLE":
            current_idx = (current_idx + 1) % len(classes)
        elif key == ord('p') and state == "IDLE":
            current_idx = (current_idx - 1) % len(classes)

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("👋 Sesi perekaman selesai.")

if __name__ == "__main__":
    run_recorder()
