"""
test_static_parity.py — Verifikasi paritas numerik penuh antara static_model.keras dan static_model.tflite
pada seluruh sampel uji nyata (`split == 'test'`) di static_data.csv.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

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
MODEL_KERAS = MODELS_DIR / "static_model.keras"
MODEL_TFLITE = MODELS_DIR / "static_model.tflite"
PARITY_JSON = MODELS_DIR / "static_parity_report.json"


def run_parity_test() -> dict[str, float | int]:
    if not MODEL_KERAS.exists():
        raise FileNotFoundError(f"Model Keras tidak ditemukan: {MODEL_KERAS}")
    if not MODEL_TFLITE.exists():
        raise FileNotFoundError(f"Model TFLite tidak ditemukan: {MODEL_TFLITE}")
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset statis tidak ditemukan: {CSV_PATH}")

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
    y_test = np.array([label_to_idx[lbl] for lbl in test_df["label"].values], dtype=np.int32)

    keras_model = tf.keras.models.load_model(str(MODEL_KERAS))
    keras_probs = keras_model.predict(X_test, verbose=0)

    interpreter = tf.lite.Interpreter(model_path=str(MODEL_TFLITE))
    interpreter.allocate_tensors()
    in_idx = interpreter.get_input_details()[0]["index"]
    out_idx = interpreter.get_output_details()[0]["index"]
    in_dtype = interpreter.get_input_details()[0]["dtype"]

    tflite_probs = np.empty_like(keras_probs)
    t0 = time.perf_counter()
    for i in range(len(X_test)):
        interpreter.set_tensor(in_idx, X_test[i : i + 1].astype(in_dtype))
        interpreter.invoke()
        tflite_probs[i] = interpreter.get_tensor(out_idx)[0]
    avg_ms = (time.perf_counter() - t0) / len(X_test) * 1000.0

    abs_diff = np.abs(keras_probs - tflite_probs)
    max_abs_diff = float(np.max(abs_diff))
    mean_abs_diff = float(np.mean(abs_diff))

    keras_pred = np.argmax(keras_probs, axis=1)
    tflite_pred = np.argmax(tflite_probs, axis=1)
    mismatches = int(np.sum(keras_pred != tflite_pred))
    keras_acc = float(np.mean(keras_pred == y_test))
    tflite_acc = float(np.mean(tflite_pred == y_test))
    tflite_size_kb = round(MODEL_TFLITE.stat().st_size / 1024.0, 2)

    print(f"Samples tested         : {len(X_test)}")
    print(f"Input tensor dtype     : {in_dtype.__name__}")
    print(f"TFLite file size       : {tflite_size_kb:.2f} KB")
    print(f"Keras test accuracy    : {keras_acc * 100:.2f}%")
    print(f"TFLite test accuracy   : {tflite_acc * 100:.2f}%")
    print(f"Max absolute prob diff : {max_abs_diff:.8e} ({max_abs_diff:.6f})")
    print(f"Mean absolute prob diff: {mean_abs_diff:.8e}")
    print(f"Argmax class mismatches: {mismatches} / {len(X_test)} ({(1 - mismatches / len(X_test)) * 100:.2f}% agreement)")
    print(f"Mean TFLite host time  : {avg_ms:.4f} ms/frame")

    assert mismatches == 0, f"Terdapat {mismatches} perbedaan kelas antara Keras dan TFLite!"
    assert max_abs_diff < 1e-4, f"Selisih probabilitas melebihi ambang 1e-4: {max_abs_diff}"

    result = {
        "n_samples": int(len(X_test)),
        "tflite_size_kb": tflite_size_kb,
        "max_abs_diff": max_abs_diff,
        "mean_abs_diff": mean_abs_diff,
        "mismatches": mismatches,
        "keras_acc": keras_acc,
        "tflite_acc": tflite_acc,
        "avg_ms": avg_ms,
    }
    PARITY_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    run_parity_test()
