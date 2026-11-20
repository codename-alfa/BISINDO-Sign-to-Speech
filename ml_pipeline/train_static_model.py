"""
train_static_model.py — Pelatihan model Keras MLP untuk klasifikasi 36 kelas statis SIBI (A-Z + 1-10).
Menggunakan split bebas kebocoran (`split == 'train'` dan `split == 'val'`) dari `static_data.csv`;
split `test` TIDAK PERNAH disentuh selama training maupun ModelCheckpoint.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "static" / "static_data.csv"
MODELS_DIR = ROOT / "models"
MODEL_OUTPUT = MODELS_DIR / "static_model.keras"
CURVES_OUTPUT = MODELS_DIR / "training_curves_static.png"
META_OUTPUT = MODELS_DIR / "static_model_meta.json"


def load_dataset(csv_path: Path = CSV_PATH):
    if not csv_path.exists():
        raise FileNotFoundError(f"File {csv_path} tidak ditemukan. Jalankan clean_and_align_sibi.py terlebih dahulu.")

    df = pd.read_csv(csv_path, dtype={"label": str})
    if "label" not in df.columns or "split" not in df.columns:
        raise ValueError("Kolom 'label' dan 'split' wajib ada di static_data.csv. Jalankan ulang clean_and_align_sibi.py.")
    df["label"] = df["label"].astype(str).str.strip()

    expected_labels = feature_utils.load_labels(feature_utils.STATIC_LABELS_PATH)
    label_to_idx = {label: i for i, label in enumerate(expected_labels)}
    df = df[df["label"].isin(label_to_idx)].copy()

    feature_cols = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)]

    def to_xy(sub: pd.DataFrame):
        X = sub[feature_cols].values.astype(np.float32)
        y_idx = np.array([label_to_idx[lbl] for lbl in sub["label"].values], dtype=np.int32)
        y = tf.keras.utils.to_categorical(y_idx, num_classes=len(expected_labels))
        return X, y

    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "val"]
    test_df = df[df["split"] == "test"]
    if train_df.empty or val_df.empty or test_df.empty:
        raise ValueError("Split train/val/test tidak lengkap di static_data.csv.")

    X_train, y_train = to_xy(train_df)
    X_val, y_val = to_xy(val_df)
    print(f"📊 Dataset dimuat: Train={len(X_train)}, Val={len(X_val)} (real held-out), Test={len(test_df)} (reserved unseen).")
    return X_train, y_train, X_val, y_val, expected_labels


def build_mlp_model(num_classes: int = 36) -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(feature_utils.NUM_FEATURES,), name="landmark_features"),
        tf.keras.layers.Dense(128, activation="relu", name="dense_1"),
        tf.keras.layers.BatchNormalization(name="batchnorm_1"),
        tf.keras.layers.Dropout(0.3, name="dropout_1"),
        tf.keras.layers.Dense(64, activation="relu", name="dense_2"),
        tf.keras.layers.Dropout(0.3, name="dropout_2"),
        tf.keras.layers.Dense(num_classes, activation="softmax", name="prediction_probabilities"),
    ], name="sibi_static_mlp")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model(epochs: int = 80, batch_size: int = 32):
    tf.keras.utils.set_random_seed(42)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    X_train, y_train, X_val, y_val, labels = load_dataset()

    model = build_mlp_model(num_classes=len(labels))
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=15,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-5,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(MODEL_OUTPUT),
            monitor="val_accuracy",
            save_best_only=True,
            verbose=1,
        ),
    ]

    print("\n🏋️ Memulai pelatihan model MLP SIBI (36 kelas)...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        shuffle=True,
        callbacks=callbacks,
        verbose=1,
    )

    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
    print("\n" + "=" * 55)
    print(f"🎯 Evaluasi Validation Split (Real Unseen): Akurasi = {val_acc * 100:.2f}% | Loss = {val_loss:.4f}")
    print("=" * 55)

    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Training Accuracy", color="#2563EB", lw=2)
    plt.plot(history.history["val_accuracy"], label="Validation Accuracy", color="#10B981", lw=2)
    plt.title("Static SIBI MLP (36 Classes) - Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Training Loss", color="#DC2626", lw=2)
    plt.plot(history.history["val_loss"], label="Validation Loss", color="#F59E0B", lw=2)
    plt.title("Static SIBI MLP (36 Classes) - Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(CURVES_OUTPUT), dpi=180)
    plt.close()

    meta = {
        "architecture": "Feedforward MLP (128 -> BN -> Drop0.3 -> 64 -> Drop0.3 -> 36)",
        "trainable_params": int(model.count_params()),
        "num_classes": len(labels),
        "train_samples": int(len(X_train)),
        "val_samples_real_bilateral": int(len(X_val)),
        "val_accuracy": round(float(val_acc), 4),
        "val_loss": round(float(val_loss), 4),
        "epochs_trained": int(len(history.history["accuracy"])),
    }
    META_OUTPUT.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"📈 Grafik kurva pelatihan disimpan ke: {CURVES_OUTPUT}")
    print(f"💾 Model Keras terbaik disimpan ke: {MODEL_OUTPUT}")


if __name__ == "__main__":
    train_model()
