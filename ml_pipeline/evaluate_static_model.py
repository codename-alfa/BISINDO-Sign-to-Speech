"""
evaluate_static_model.py — Evaluasi akurasi, confusion matrix, dan per-class metrics model statis.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
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
MODEL_PATH = MODELS_DIR / "static_model.keras"
CONF_MATRIX_IMG = MODELS_DIR / "confusion_matrix_static.png"
REPORT_TXT = MODELS_DIR / "classification_report_static.txt"


def evaluate():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model {MODEL_PATH} belum ada. Jalankan train_static_model.py terlebih dahulu.")

    expected_labels = feature_utils.load_labels(feature_utils.STATIC_LABELS_PATH)
    label_to_idx = {label: i for i, label in enumerate(expected_labels)}

    df = pd.read_csv(CSV_PATH)
    df = df[df["label"].isin(label_to_idx)].copy()

    feature_cols = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)]
    X = df[feature_cols].values.astype(np.float32)
    y_true_indices = np.array([label_to_idx[lbl] for lbl in df["label"].values], dtype=np.int32)

    # Evaluasi pada validation split yang sama (random_state=42)
    _, X_test, _, y_test_indices = train_test_split(
        X, y_true_indices, test_size=0.20, random_state=42, stratify=y_true_indices
    )

    print(f"🔍 Mengevaluasi model pada {len(X_test)} sampel uji...")
    model = tf.keras.models.load_model(str(MODEL_PATH))

    # Prediksi
    y_pred_probs = model.predict(X_test, verbose=0)
    y_pred_indices = np.argmax(y_pred_probs, axis=1)

    # Classification Report
    report = classification_report(
        y_test_indices, y_pred_indices, target_names=expected_labels, digits=4
    )
    print("\n--- 📋 CLASSIFICATION REPORT (A-Z) ---")
    print(report)

    # Simpan teks report
    REPORT_TXT.write_text(report, encoding="utf-8")
    print(f"📝 Laporan teks disimpan ke: {REPORT_TXT}")

    # Confusion Matrix
    cm = confusion_matrix(y_test_indices, y_pred_indices)

    plt.figure(figsize=(14, 12))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=expected_labels, yticklabels=expected_labels,
        cbar=True, square=True
    )
    plt.title("Confusion Matrix — BISINDO Static Alphabet Model (MLP)", fontsize=14, pad=15)
    plt.xlabel("Predicted Label", fontsize=12)
    plt.ylabel("True Label", fontsize=12)
    plt.tight_layout()
    plt.savefig(str(CONF_MATRIX_IMG), dpi=150)
    plt.close()
    print(f"🖼️ Confusion matrix plot disimpan ke: {CONF_MATRIX_IMG}")


if __name__ == "__main__":
    evaluate()
