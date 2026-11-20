"""
test_dynamic_parity.py — Verifikasi paritas numerik penuh antara dynamic_model.keras dan dynamic_model.tflite
pada seluruh sekuens validasi Leave-One-Signer-Out (held-out signer) maupun seluruh take nyata.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

import feature_utils
import train_dynamic_model

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "dynamic_raw"
MODELS_DIR = ROOT / "models"
MODEL_KERAS = MODELS_DIR / "dynamic_model.keras"
MODEL_TFLITE = MODELS_DIR / "dynamic_model.tflite"
MODEL_META = MODELS_DIR / "dynamic_model_meta.json"
PARITY_JSON = MODELS_DIR / "dynamic_parity_report.json"


def run_parity_test(held_out_signer: str | None = None, all_takes: bool = False) -> dict[str, float | int | str]:
    if not MODEL_KERAS.exists():
        raise FileNotFoundError(f"Model Keras tidak ditemukan: {MODEL_KERAS}")
    if not MODEL_TFLITE.exists():
        raise FileNotFoundError(f"Model TFLite tidak ditemukan: {MODEL_TFLITE}")

    raw_labels = feature_utils.load_labels(feature_utils.DYNAMIC_LABELS_PATH)
    records, _ = train_dynamic_model.load_recordings(
        data_dir=DATA_DIR,
        raw_labels=raw_labels,
        min_samples_per_class=1,
        allow_synthetic=False,
    )

    if not all_takes and held_out_signer is None and MODEL_META.exists():
        meta = json.loads(MODEL_META.read_text(encoding="utf-8"))
        held_out_signer = meta.get("primary_held_out_signer")
        if not held_out_signer:
            val_mode = str(meta.get("validation_mode", ""))
            if "held_out=" in val_mode:
                held_out_signer = val_mode.split("held_out=")[-1].rstrip(")")

    if all_takes or not held_out_signer:
        target_recs = records
        scope_label = "all_takes"
    else:
        target_recs = [r for r in records if r["signer"] == held_out_signer]
        scope_label = f"loso_held_out:{held_out_signer}"

    if not target_recs:
        raise RuntimeError(f"Tidak ada rekaman ditemukan untuk cakupan '{scope_label}'.")

    rng = np.random.default_rng(123)
    X_list, y_list = [], []
    for r in target_recs:
        crops = train_dynamic_model.extract_crops_from_recording(
            r["ts_ms"], r["landmarks"], augment_crops=1, rng=rng
        )
        for c in crops:
            X_list.append(c)
            y_list.append(r["class_idx"])

    X_seq = np.stack(X_list, axis=0).astype(np.float32)
    y_true = np.array(y_list, dtype=np.int32)

    keras_model = tf.keras.models.load_model(str(MODEL_KERAS))
    keras_probs = keras_model.predict(X_seq, verbose=0)

    interpreter = tf.lite.Interpreter(model_path=str(MODEL_TFLITE))
    interpreter.allocate_tensors()
    in_det = interpreter.get_input_details()[0]
    out_det = interpreter.get_output_details()[0]
    in_idx = in_det["index"]
    out_idx = out_det["index"]
    in_dtype = in_det["dtype"]

    tflite_probs = np.empty_like(keras_probs)
    t0 = time.perf_counter()
    for i in range(len(X_seq)):
        interpreter.set_tensor(in_idx, X_seq[i : i + 1].astype(in_dtype))
        interpreter.invoke()
        tflite_probs[i] = interpreter.get_tensor(out_idx)[0]
    avg_ms = (time.perf_counter() - t0) / len(X_seq) * 1000.0

    abs_diff = np.abs(keras_probs - tflite_probs)
    max_abs_diff = float(np.max(abs_diff))
    mean_abs_diff = float(np.mean(abs_diff))

    keras_pred = np.argmax(keras_probs, axis=1)
    tflite_pred = np.argmax(tflite_probs, axis=1)
    mismatches = int(np.sum(keras_pred != tflite_pred))
    keras_acc = float(np.mean(keras_pred == y_true))
    tflite_acc = float(np.mean(tflite_pred == y_true))
    tflite_size_kb = round(MODEL_TFLITE.stat().st_size / 1024.0, 2)

    print(f"Scope tested           : {scope_label}")
    print(f"Sequences tested       : {len(X_seq)}")
    print(f"Input tensor shape     : {list(in_det['shape'])} ({in_dtype.__name__})")
    print(f"TFLite file size       : {tflite_size_kb:.2f} KB")
    print(f"Keras accuracy         : {keras_acc * 100:.2f}%")
    print(f"TFLite accuracy        : {tflite_acc * 100:.2f}%")
    print(f"Max absolute prob diff : {max_abs_diff:.8e} ({max_abs_diff:.6f})")
    print(f"Mean absolute prob diff: {mean_abs_diff:.8e}")
    print(f"Argmax class mismatches: {mismatches} / {len(X_seq)} ({(1 - mismatches / len(X_seq)) * 100:.2f}% agreement)")
    print(f"Mean TFLite host time  : {avg_ms:.4f} ms/sequence")

    assert mismatches == 0, f"Terdapat {mismatches} perbedaan kelas antara Keras dan TFLite!"
    assert max_abs_diff < 1e-4, f"Selisih probabilitas melebihi ambang 1e-4: {max_abs_diff}"

    result = {
        "scope": scope_label,
        "n_sequences": int(len(X_seq)),
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
    parser = argparse.ArgumentParser(description="Verify Keras vs TFLite parity for dynamic BISINDO BiLSTM.")
    parser.add_argument("--signer", type=str, default=None, help="Held-out signer name (defaults to meta).")
    parser.add_argument("--all-takes", action="store_true", help="Evaluate parity across all dynamic takes.")
    args = parser.parse_args()
    run_parity_test(held_out_signer=args.signer, all_takes=args.all_takes)
