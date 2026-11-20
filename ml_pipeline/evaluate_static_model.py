"""
evaluate_static_model.py — Evaluasi akurasi, confusion matrix, dan per-class metrics model statis SIBI
secara ketat pada split `test` (sampel nyata terpisah bebas leakage).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "static" / "static_data.csv"
MODELS_DIR = ROOT / "models"
MODEL_PATH = MODELS_DIR / "static_model.keras"
CONF_MATRIX_IMG = MODELS_DIR / "confusion_matrix_static.png"
REPORT_TXT = MODELS_DIR / "classification_report_static.txt"
EVAL_JSON = MODELS_DIR / "static_eval_summary.json"


def evaluate():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model {MODEL_PATH} belum ada. Jalankan train_static_model.py terlebih dahulu.")

    expected_labels = feature_utils.load_labels(feature_utils.STATIC_LABELS_PATH)
    label_to_idx = {label: i for i, label in enumerate(expected_labels)}

    df = pd.read_csv(CSV_PATH, dtype={"label": str})
    df["label"] = df["label"].astype(str).str.strip()
    df = df[df["label"].isin(label_to_idx)].copy()
    if "split" not in df.columns:
        raise ValueError("Kolom 'split' wajib ada di static_data.csv.")

    test_df = df[df["split"] == "test"].copy()
    feature_cols = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)]
    X_test = test_df[feature_cols].values.astype(np.float32)
    y_true_indices = np.array([label_to_idx[lbl] for lbl in test_df["label"].values], dtype=np.int32)

    print(f"🔍 Mengevaluasi model pada {len(X_test)} sampel uji NYATA (unseen bilateral test set)...")
    model = tf.keras.models.load_model(str(MODEL_PATH))

    y_pred_probs = model.predict(X_test, verbose=0)
    y_pred_indices = np.argmax(y_pred_probs, axis=1)

    report = classification_report(
        y_true_indices,
        y_pred_indices,
        labels=list(range(len(expected_labels))),
        target_names=expected_labels,
        digits=4,
        zero_division=0,
    )
    report_dict = classification_report(
        y_true_indices,
        y_pred_indices,
        labels=list(range(len(expected_labels))),
        target_names=expected_labels,
        output_dict=True,
        zero_division=0,
    )

    # Evaluasi terpisah untuk orientasi kanonik saja vs mirror saja
    canon_mask = (test_df["orientation"] == "canonical").to_numpy()
    mirror_mask = (test_df["orientation"] == "mirror").to_numpy()
    canon_acc = float(np.mean(y_pred_indices[canon_mask] == y_true_indices[canon_mask]))
    mirror_acc = float(np.mean(y_pred_indices[mirror_mask] == y_true_indices[mirror_mask]))
    bilateral_acc = float(np.mean(y_pred_indices == y_true_indices))

    header_note = (
        f"=== STATIC SIBI TEST EVALUATION (LEAK-FREE HELD-OUT REAL TEST SPLIT) ===\n"
        f"Bilateral Real Test Samples : {len(X_test)} (Canonical={int(canon_mask.sum())}, Mirror={int(mirror_mask.sum())})\n"
        f"Bilateral Real Test Accuracy: {bilateral_acc * 100:.2f}%\n"
        f"Canonical-Only Real Test Acc: {canon_acc * 100:.2f}%\n"
        f"Mirror-Only Real Test Acc   : {mirror_acc * 100:.2f}%\n\n"
    )
    print("\n" + header_note + report)

    REPORT_TXT.write_text(header_note + report, encoding="utf-8")

    # Find lowest per-class recalls
    per_cls = {
        lbl: report_dict[lbl]
        for lbl in expected_labels
    }
    lowest = sorted(per_cls.items(), key=lambda kv: (kv[1]["recall"], kv[1]["f1-score"]))[:5]

    summary = {
        "test_samples_bilateral": int(len(X_test)),
        "test_samples_canonical": int(canon_mask.sum()),
        "test_samples_mirror": int(mirror_mask.sum()),
        "bilateral_accuracy": round(bilateral_acc, 4),
        "canonical_accuracy": round(canon_acc, 4),
        "mirror_accuracy": round(mirror_acc, 4),
        "macro_precision": round(float(report_dict["macro avg"]["precision"]), 4),
        "macro_recall": round(float(report_dict["macro avg"]["recall"]), 4),
        "macro_f1": round(float(report_dict["macro avg"]["f1-score"]), 4),
        "lowest_recall_classes": [
            {"class": k, "recall": round(float(v["recall"]), 4), "precision": round(float(v["precision"]), 4), "support": int(v["support"])}
            for k, v in lowest
        ],
    }
    EVAL_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    cm = confusion_matrix(y_true_indices, y_pred_indices, labels=list(range(len(expected_labels))))
    plt.figure(figsize=(15, 13))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=expected_labels,
        yticklabels=expected_labels,
        cbar=True,
        square=True,
    )
    plt.title(f"Confusion Matrix - Static SIBI Model (MLP 63D, 36 Classes, N={len(X_test)}, Acc={bilateral_acc*100:.2f}%)", fontsize=14, pad=14)
    plt.xlabel("Predicted Label", fontsize=12)
    plt.ylabel("True Label", fontsize=12)
    plt.tight_layout()
    plt.savefig(str(CONF_MATRIX_IMG), dpi=200)
    plt.close()
    print(f"🖼️ Confusion matrix plot disimpan ke: {CONF_MATRIX_IMG}")


if __name__ == "__main__":
    evaluate()
