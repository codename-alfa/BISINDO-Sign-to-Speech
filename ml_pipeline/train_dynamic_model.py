"""
train_dynamic_model.py — Pelatihan model LSTM sekuens gestur dinamis BISINDO (5 kelas) & ekspor TFLite.

Target Kelas (5 kata):
1. Halo
2. Terima kasih
3. Tolong
4. Ya
5. Tidak

Arsitektur:
Input (30, 63) -> LSTM(64, return_sequences=True) -> Dropout(0.2) -> LSTM(64) -> Dropout(0.2) -> Dense(32, relu) -> Dense(5, softmax)
Builtins Only -> Export dynamic_model.tflite
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

import feature_utils

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
DYNAMIC_DIR = ROOT / "data" / "dynamic"
MODELS_DIR = ROOT / "models"
MODEL_KERAS = MODELS_DIR / "dynamic_model.keras"
MODEL_TFLITE = MODELS_DIR / "dynamic_model.tflite"
CURVES_PLOT = MODELS_DIR / "training_curves_dynamic.png"
LABELS_PATH = ROOT / "labels" / "dynamic_labels.txt"

NUM_CLASSES = 5
SEQUENCE_LENGTH = feature_utils.SEQUENCE_LENGTH
NUM_FEATURES = feature_utils.NUM_FEATURES


def generate_synthetic_trajectory(base_shape: np.ndarray, motion_type: str, num_seqs: int = 60) -> list[np.ndarray]:
    """Menghasilkan sekuens sintetis realistis (30, 63) dengan dinamika temporal."""
    seqs = []
    rng = np.random.default_rng(42)

    for _ in range(num_seqs):
        # Noise per sekuens
        scale_mod = rng.uniform(0.85, 1.15)
        rot_angle = rng.uniform(-0.15, 0.15)
        c, s = np.cos(rot_angle), np.sin(rot_angle)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float32)

        frames = []
        for t in range(SEQUENCE_LENGTH):
            progress = t / (SEQUENCE_LENGTH - 1)
            # Gerakan spesifik kata
            if motion_type == "nod": # Ya (mengangguk/turun-naik)
                offset_y = np.sin(progress * 2 * np.pi) * 0.12
                offset_x = 0.0
            elif motion_type == "shake": # Tidak (geleng kiri-kanan)
                offset_x = np.sin(progress * 2 * np.pi) * 0.15
                offset_y = 0.0
            elif motion_type == "chest_to_front": # Terima kasih / Tolong (maju ke depan)
                offset_x = np.sin(progress * np.pi) * 0.08
                offset_y = -progress * 0.15
            else:
                offset_x = rng.normal(0, 0.02)
                offset_y = rng.normal(0, 0.02)

            pts = base_shape.copy() @ R * scale_mod
            pts[:, 0] += offset_x
            pts[:, 1] += offset_y
            pts += rng.normal(0, 0.008, pts.shape).astype(np.float32)

            # Re-normalize
            wrist = pts[0].copy()
            rel = pts - wrist
            scale = np.linalg.norm(pts[9] - wrist)
            if scale < 1e-6:
                scale = 1.0
            norm = (rel / scale).flatten()
            frames.append(norm)

        seqs.append(np.stack(frames, axis=0).astype(np.float32))
    return seqs


def load_or_bootstrap_dataset() -> tuple[np.ndarray, np.ndarray, list[str]]:
    raw_labels = feature_utils.load_labels(LABELS_PATH)
    classes = [lbl.replace(" ", "_") for lbl in raw_labels]
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X_list = []
    y_list = []

    # Bentuk tangan dasar untuk sintetis
    open_hand = np.zeros((21, 3), dtype=np.float32)
    open_hand[9] = [0.0, 0.18, 0.0]

    motion_map = {
        "Halo": "wave",
        "Terima_kasih": "chest_to_front",
        "Tolong": "chest_to_front",
        "Ya": "nod",
        "Tidak": "shake",
    }

    print(f"📦 Memuat sekuens dinamis dari: {DYNAMIC_DIR}")
    for idx, cls in enumerate(classes):
        cls_dir = DYNAMIC_DIR / cls
        existing_files = list(cls_dir.glob("*.npy")) if cls_dir.exists() else []

        cls_seqs = []
        for f in existing_files:
            try:
                arr = np.load(f)
                if arr.shape == (SEQUENCE_LENGTH, NUM_FEATURES):
                    cls_seqs.append(arr)
            except Exception:
                pass

        print(f"   Kelas '{cls}': {len(cls_seqs)} sekuens nyata ditemukan.")

        if len(cls_seqs) < 60:
            needed = 60 - len(cls_seqs)
            print(f"   ℹ️ Melengkapi kelas '{cls}' dengan {needed} sekuens sintetis gerak dinamis...")
            synth = generate_synthetic_trajectory(open_hand, motion_map.get(cls, "none"), num_seqs=needed)
            cls_seqs.extend(synth)

        for seq in cls_seqs:
            X_list.append(seq)
            y_list.append(idx)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    print(f"\n✅ Total Dataset Dinamis: {len(X)} sekuens (Shape: {X.shape})")
    return X, y, classes


def build_model(num_classes: int = NUM_CLASSES, batch_size: int | None = None) -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(SEQUENCE_LENGTH, NUM_FEATURES), batch_size=batch_size, name="sequence_features"),
        tf.keras.layers.LSTM(64),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(num_classes, activation="softmax", name="output_probabilities"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def convert_model_to_tflite(trained_model: tf.keras.Model, num_classes: int) -> None:
    print("\n⚙️ Mengonversi model LSTM ke TFLite (Builtins Only)...")
    # Buat model inference dengan batch_size=1 untuk memastikan TFLite shape inference statis
    infer_model = build_model(num_classes, batch_size=1)
    infer_model.set_weights(trained_model.get_weights())

    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(infer_model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
        tflite_bytes = converter.convert()
    except Exception as exc:
        print(f"ℹ️ Fallback export SavedModel: {exc}")
        with tempfile.TemporaryDirectory() as tmp:
            infer_model.export(tmp)
            converter = tf.lite.TFLiteConverter.from_saved_model(tmp)
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
            tflite_bytes = converter.convert()

    MODEL_TFLITE.write_bytes(tflite_bytes)
    size_kb = len(tflite_bytes) / 1024
    print(f"✅ Model TFLite disimpan: {MODEL_TFLITE} ({size_kb:.1f} KB)")

    # Parity Test
    test_seq = np.random.normal(size=(1, SEQUENCE_LENGTH, NUM_FEATURES)).astype(np.float32)
    keras_out = infer_model.predict(test_seq, verbose=0)[0]

    interpreter = tf.lite.Interpreter(model_content=tflite_bytes)
    interpreter.allocate_tensors()
    in_idx = interpreter.get_input_details()[0]["index"]
    out_idx = interpreter.get_output_details()[0]["index"]
    interpreter.set_tensor(in_idx, test_seq)
    interpreter.invoke()
    tflite_out = interpreter.get_tensor(out_idx)[0]

    max_diff = np.max(np.abs(keras_out - tflite_out))
    print(f"🧪 Parity Check TFLite vs Keras (LSTM): Max Diff = {max_diff:.6f}")
    if max_diff < 1e-4:
        print("🎉 PARITY CHECK PASSED: Model LSTM TFLite 100% konsisten dengan Keras!")
    else:
        print("⚠️ Catatan perbedaan numerik kecil.")


def train():
    X, y, classes = load_or_bootstrap_dataset()
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = build_model(len(classes))
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=15, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-5),
        tf.keras.callbacks.ModelCheckpoint(str(MODEL_KERAS), monitor="val_accuracy", save_best_only=True),
    ]

    print("\n🚀 Memulai training LSTM...")
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=60,
        batch_size=16,
        callbacks=callbacks,
        verbose=1,
    )

    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
    print("\n" + "=" * 50)
    print(f"🎯 Evaluasi Set Validasi LSTM: Akurasi = {val_acc * 100:.2f}% | Loss = {val_loss:.4f}")
    print("=" * 50)

    # Plot kurva
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Train Acc")
    plt.plot(history.history["val_accuracy"], label="Val Acc")
    plt.title("Akurasi Model Dinamis (LSTM)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Val Loss")
    plt.title("Loss Model Dinamis (LSTM)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(CURVES_PLOT), dpi=150)
    plt.close()
    print(f"📈 Grafik kurva pelatihan disimpan ke: {CURVES_PLOT}")

    # Konversi ke TFLite
    convert_model_to_tflite(model, len(classes))


if __name__ == "__main__":
    train()
