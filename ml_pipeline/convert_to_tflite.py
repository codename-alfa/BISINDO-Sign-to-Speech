"""
convert_to_tflite.py — Konversi model Keras MLP ke TFLite & verifikasi parity inferensi.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

import feature_utils

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
MODEL_KERAS = MODELS_DIR / "static_model.keras"
MODEL_TFLITE = MODELS_DIR / "static_model.tflite"
CSV_PATH = ROOT / "data" / "static" / "static_data.csv"


def convert():
    if not MODEL_KERAS.exists():
        raise FileNotFoundError(f"Model {MODEL_KERAS} tidak ditemukan. Jalankan train_static_model.py terlebih dahulu.")

    print(f"🔄 Memuat model Keras dari: {MODEL_KERAS}")
    model = tf.keras.models.load_model(str(MODEL_KERAS))

    print("⚙️ Mengonfigurasi TFLite Converter (Builtins Only)...")
    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
        tflite_model = converter.convert()
    except Exception as exc:
        print(f"ℹ️ from_keras_model fallback ke export SavedModel: {exc}")
        with tempfile.TemporaryDirectory() as tmpdir:
            model.export(tmpdir)
            converter = tf.lite.TFLiteConverter.from_saved_model(tmpdir)
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
            tflite_model = converter.convert()

    # Simpan file .tflite
    MODEL_TFLITE.write_bytes(tflite_model)
    file_size_kb = len(tflite_model) / 1024
    print(f"✅ Model TFLite berhasil dibuat: {MODEL_TFLITE} ({file_size_kb:.1f} KB)")

    # Parity Verification
    verify_parity(model, tflite_model)


def verify_parity(keras_model: tf.keras.Model, tflite_bytes: bytes, num_samples: int = 100):
    print(f"\n🧪 Menjalankan Sanity Parity Check ({num_samples} sampel)...")

    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH)
        feature_cols = [f"f{i}" for i in range(feature_utils.NUM_FEATURES)]
        X_all = df[feature_cols].values.astype(np.float32)
        n = min(num_samples, len(X_all))
        indices = np.random.choice(len(X_all), n, replace=False)
        test_samples = X_all[indices]
    else:
        test_samples = np.random.uniform(-2.0, 2.0, (num_samples, feature_utils.NUM_FEATURES)).astype(np.float32)

    interpreter = tf.lite.Interpreter(model_content=tflite_bytes)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    keras_preds = keras_model.predict(test_samples, verbose=0)
    tflite_preds = []

    start_infer = time.perf_counter()
    for i in range(len(test_samples)):
        sample = np.expand_dims(test_samples[i], axis=0)
        interpreter.set_tensor(input_details[0]["index"], sample)
        interpreter.invoke()
        out = interpreter.get_tensor(output_details[0]["index"])
        tflite_preds.append(out[0])

    tflite_preds = np.array(tflite_preds)
    elapsed_infer_ms = (time.perf_counter() - start_infer) / len(test_samples) * 1000

    keras_classes = np.argmax(keras_preds, axis=1)
    tflite_classes = np.argmax(tflite_preds, axis=1)

    max_prob_diff = np.max(np.abs(keras_preds - tflite_preds))
    mismatches = np.sum(keras_classes != tflite_classes)

    print("-" * 50)
    print(f"Maksimum Perbedaan Probabilitas : {max_prob_diff:.6f}")
    print(f"Ketidakcocokan Prediksi Kelas   : {mismatches} / {len(test_samples)} ({mismatches / len(test_samples) * 100:.1f}%)")
    print(f"Rata-rata Latensi TFLite di PC  : {elapsed_infer_ms:.2f} ms per frame (SLA < 100 ms)")
    print("-" * 50)

    if mismatches == 0 and max_prob_diff < 1e-3:
        print("🎉 PARITY CHECK PASSED: Model TFLite 100% konsisten dengan Keras asli!")
    else:
        print("⚠️ PERINGATAN: Terdapat perbedaan signifikan antara output Keras dan TFLite.")


if __name__ == "__main__":
    convert()
