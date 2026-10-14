"""
test_webcam_static.py — Pengujian inferensi real-time alfabet statis via webcam laptop.

Fitur:
- Deteksi tangan via MediaPipe Tasks HandLandmarker
- Visualisasi skeleton keypoints & landmark connections
- Inferensi real-time static_model.tflite
- Indikator SLA threshold: Hijau jika confidence >= 70%, Oranye jika < 70%
- Tampilan latensi inferensi on-device (ms)
- Tekan 'q' untuk keluar
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import tensorflow as tf
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import feature_utils

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
MODEL_TFLITE = ROOT / "models" / "static_model.tflite"
HAND_MODEL = ROOT / "assets" / "hand_landmarker.task"
LABELS_PATH = ROOT / "labels" / "static_labels.txt"

# Koneksi tulang tangan MediaPipe
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # Ibu jari
    (0, 5), (5, 6), (6, 7), (7, 8),           # Telunjuk
    (5, 9), (9, 10), (10, 11), (11, 12),      # Jari tengah
    (9, 13), (13, 14), (14, 15), (15, 16),    # Jari manis
    (13, 17), (17, 18), (18, 19), (19, 20),   # Kelingking
    (0, 17)                                   # Telapak bawah
]


def draw_skeleton(frame, landmarks, is_confident=True):
    h, w, _ = frame.shape
    coords = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

    bone_color = (0, 220, 100) if is_confident else (0, 165, 255)
    joint_color = (255, 255, 255) if is_confident else (0, 200, 255)

    # Gambar garis tulang
    for start_idx, end_idx in HAND_CONNECTIONS:
        cv2.line(frame, coords[start_idx], coords[end_idx], bone_color, 2, cv2.LINE_AA)

    # Gambar sendi (joints)
    for i, pt in enumerate(coords):
        radius = 5 if i in [4, 8, 12, 16, 20] else 3
        cv2.circle(frame, pt, radius, joint_color, -1, cv2.LINE_AA)
        cv2.circle(frame, pt, radius, (0, 0, 0), 1, cv2.LINE_AA)


def run_webcam():
    if not MODEL_TFLITE.exists():
        print(f"❌ Model TFLite {MODEL_TFLITE} belum ada. Jalankan train_static_model.py dan convert_to_tflite.py dahulu.")
        return

    labels = feature_utils.load_labels(LABELS_PATH)

    # Setup MediaPipe Tasks
    base_options = mp_python.BaseOptions(model_asset_path=str(HAND_MODEL))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
    )
    landmarker = vision.HandLandmarker.create_from_options(options)

    # Setup TFLite Interpreter
    interpreter = tf.lite.Interpreter(model_path=str(MODEL_TFLITE))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Tidak dapat membuka webcam. Pastikan perangkat kamera tidak sedang digunakan aplikasi lain.")
        return

    print("\n🎥 Webcam aktif! Arahkan tangan Anda ke kamera.")
    print("   Tekan tombol 'q' untuk keluar.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Mirror agar terasa natural seperti cermin
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        # Konversi ke RGB untuk MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        detect_start = time.perf_counter()
        detection_result = landmarker.detect(mp_image)
        detect_time_ms = (time.perf_counter() - detect_start) * 1000

        pred_text = "Menunggu Tangan..."
        conf_percent = 0
        is_confident = False
        infer_time_ms = 0.0

        if detection_result.hand_landmarks:
            landmarks = detection_result.hand_landmarks[0]

            try:
                features = feature_utils.normalize_landmarks(landmarks)
                # TFLite inference
                infer_start = time.perf_counter()
                input_data = np.expand_dims(features, axis=0)
                interpreter.set_tensor(input_details[0]["index"], input_data)
                interpreter.invoke()
                output_data = interpreter.get_tensor(output_details[0]["index"])[0]
                infer_time_ms = (time.perf_counter() - infer_start) * 1000

                best_idx = int(np.argmax(output_data))
                best_prob = float(output_data[best_idx])
                conf_percent = int(best_prob * 100)
                is_confident = (best_prob >= 0.70)

                pred_text = f"Alfabet: {labels[best_idx]}"

                # Gambar skeleton tangan
                draw_skeleton(frame, landmarks, is_confident=is_confident)

            except ValueError:
                pass

        # Visual HUD Overlay
        card_color = (15, 23, 42)  # Dark slate
        border_color = (0, 220, 100) if is_confident else ((0, 165, 255) if conf_percent > 0 else (100, 100, 100))

        # Background Box Info
        cv2.rectangle(frame, (20, 20), (360, 140), card_color, -1)
        cv2.rectangle(frame, (20, 20), (360, 140), border_color, 2)

        # Prediksi Huruf
        text_color = (0, 255, 120) if is_confident else ((0, 200, 255) if conf_percent > 0 else (200, 200, 200))
        cv2.putText(frame, pred_text, (35, 60), cv2.FONT_HERSHEY_DUPLEX, 0.9, text_color, 2, cv2.LINE_AA)

        # Confidence Bar / Text
        if conf_percent > 0:
            status_tag = "STABIL (>=70%)" if is_confident else "RAGU (<70%)"
            cv2.putText(frame, f"Keyakinan: {conf_percent}% ({status_tag})", (35, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.55, text_color, 1, cv2.LINE_AA)
            cv2.putText(frame, f"Latensi: {detect_time_ms + infer_time_ms:.1f} ms (Inference: {infer_time_ms:.1f} ms)", (35, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)
        else:
            cv2.putText(frame, "Posisikan satu tangan di layar", (35, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)
            cv2.putText(frame, "Tekan 'q' untuk keluar", (35, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 120), 1)

        cv2.imshow("BISINDO Sign-to-Speech (Static Tester)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    print("👋 Sesi webcam ditutup.")


if __name__ == "__main__":
    run_webcam()
