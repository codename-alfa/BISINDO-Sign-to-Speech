"""
train_static_model.py — Pelatihan model Keras MLP untuk klasifikasi alfabet statis BISINDO A-Z.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split

import feature_utils

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "static" / "static_data.csv"
MODELS_DIR = ROOT / "models"
MODEL_OUTPUT = MODELS_DIR / "static_model.keras"
CURVES_OUTPUT = MODELS_DIR / "training_curves_static.png"


def load_dataset(csv_path: Path = CSV_PATH):
    if not csv_path.exists():
        raise FileNotFoundError(f"File {csv_path} tidak ditemukan. Jalankan collect_static_data.py terlebih dahulu.")

    df = pd.read_csv(csv_path)
    if "label" not in df.columns:
        raise ValueError("Kolom 'label' tidak ditemukan di dataset CSV.")

    expected_labels = feature_utils.load_labels(feature_utils.STATIC_LABELS_PATH)
    label_to_idx = {label: i for i, label in enumerate(expected_labels)}

    # Filter hanya label yang valid
    df = df[df["label"].isin(label_to_idx)].copy()
    if df.empty:
        raise ValueError("Tidak ada data valid yang cocok dengan static_labels.txt.")

    feature_cols = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)]
    X = df[feature_cols].values.astype(np.float32)
    y_labels = df["label"].values

    y_indices = np.array([label_to_idx[lbl] for lbl in y_labels], dtype=np.int32)
    y = tf.keras.utils.to_categorical(y_indices, num_classes=len(expected_labels))

    print(f"📊 Dataset dimuat: {len(X)} sampel dari {len(expected_labels)} kelas.")
    return X, y, expected_labels


def build_mlp_model(num_classes: int = 26) -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(feature_utils.NUM_FEATURES,), name="landmark_features"),
        tf.keras.layers.Dense(128, activation="relu", name="dense_1"),
        tf.keras.layers.BatchNormalization(name="batchnorm_1"),
        tf.keras.layers.Dropout(0.3, name="dropout_1"),
        tf.keras.layers.Dense(64, activation="relu", name="dense_2"),
        tf.keras.layers.Dropout(0.3, name="dropout_2"),
        tf.keras.layers.Dense(num_classes, activation="softmax", name="prediction_probabilities"),
    ], name="bisindo_static_mlp")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def train_model(epochs: int = 80, batch_size: int = 32):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    X, y, labels = load_dataset()

    # Stratified split 80% train, 20% validation
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=np.argmax(y, axis=1)
    )

    print(f"🔹 Split data: {len(X_train)} training, {len(X_val)} validation.")

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

    print("\n🏋️ Memulai pelatihan model MLP...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    # Evaluasi final pada set validasi
    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
    print("\n" + "=" * 50)
    print(f"🎯 Evaluasi Set Validasi: Akurasi = {val_acc * 100:.2f}% | Loss = {val_loss:.4f}")
    print("=" * 50)

    # Plot & simpan kurva pelatihan
    plt.figure(figsize=(12, 5))

    # Subplot 1: Akurasi
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Training Accuracy", color="#2563EB", lw=2)
    plt.plot(history.history["val_accuracy"], label="Validation Accuracy", color="#10B981", lw=2)
    plt.title("Model Accuracy Progression")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Subplot 2: Loss
    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Training Loss", color="#DC2626", lw=2)
    plt.plot(history.history["val_loss"], label="Validation Loss", color="#F59E0B", lw=2)
    plt.title("Model Loss Progression")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(CURVES_OUTPUT), dpi=150)
    plt.close()
    print(f"📈 Grafik kurva pelatihan disimpan ke: {CURVES_OUTPUT}")
    print(f"💾 Model Keras terbaik disimpan ke: {MODEL_OUTPUT}")


if __name__ == "__main__":
    train_model()
