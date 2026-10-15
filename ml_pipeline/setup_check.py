"""
setup_check.py — Verifikasi environment ML end-to-end (jalankan sekali setelah setup).

    .venv\\Scripts\\python setup_check.py

Yang dicek:
  1. Versi Python 3.10–3.12 (TensorFlow & MediaPipe belum mendukung 3.13+)
  2. Import & versi library inti
  3. Unduh model `hand_landmarker.task` ke assets/ (jika belum ada)
  4. MediaPipe Tasks API HandLandmarker bisa dibuat & dijalankan
  5. Model Keras LSTM dummy (30, 63) bisa dikonversi ke TFLite dengan BUILTINS saja
     dan outputnya sama dengan Keras
  6. Kontrak normalisasi (feature_utils) valid
"""

from __future__ import annotations

import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
HAND_MODEL_PATH = ASSETS_DIR / "hand_landmarker.task"
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)

results: list[tuple[str, bool, str]] = []


def step(name: str):
    def deco(fn):
        def run():
            try:
                info = fn() or ""
                results.append((name, True, info))
                print(f"[PASS] {name} {info}")
            except Exception as exc:  # noqa: BLE001 - report every failure
                results.append((name, False, repr(exc)))
                print(f"[FAIL] {name}: {exc!r}")
        return run
    return deco


@step("Python version")
def check_python():
    v = sys.version_info
    if not ((3, 10) <= (v.major, v.minor) <= (3, 12)):
        raise RuntimeError(f"Python {v.major}.{v.minor} tidak didukung; pakai 3.10-3.12")
    return f"{v.major}.{v.minor}.{v.micro}"


@step("Library imports")
def check_imports():
    import cv2
    import mediapipe as mp
    import numpy as np
    import sklearn
    import tensorflow as tf
    return (f"tf={tf.__version__} mediapipe={mp.__version__} cv2={cv2.__version__} "
            f"sklearn={sklearn.__version__} numpy={np.__version__}")


@step("Download hand_landmarker.task")
def check_model_download():
    ASSETS_DIR.mkdir(exist_ok=True)
    if not HAND_MODEL_PATH.exists():
        urllib.request.urlretrieve(HAND_MODEL_URL, HAND_MODEL_PATH)
    size_mb = HAND_MODEL_PATH.stat().st_size / 1e6
    if size_mb < 1:
        raise RuntimeError(f"Model terlalu kecil ({size_mb:.2f} MB), unduhan rusak?")
    return f"({size_mb:.1f} MB)"


@step("MediaPipe Tasks HandLandmarker")
def check_hand_landmarker():
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(HAND_MODEL_PATH)),
        running_mode=vision.RunningMode.IMAGE,
        num_hands=1,
    )
    with vision.HandLandmarker.create_from_options(options) as landmarker:
        blank = np.zeros((256, 256, 3), dtype=np.uint8)
        result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=blank))
    return f"(hands on blank image: {len(result.hand_landmarks)})"


@step("Keras LSTM -> TFLite (builtins only)")
def check_lstm_conversion():
    import numpy as np
    import tensorflow as tf

    from feature_utils import NUM_FEATURES, SEQUENCE_LENGTH

    tf.keras.utils.set_random_seed(0)
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(SEQUENCE_LENGTH, NUM_FEATURES), batch_size=1),
        tf.keras.layers.LSTM(64),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(5, activation="softmax"),
    ])

    method = "from_keras_model"
    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
        tflite_bytes = converter.convert()
    except Exception:
        # Fallback untuk Keras 3: export SavedModel lalu konversi
        method = "export+from_saved_model"
        with tempfile.TemporaryDirectory() as tmp:
            model.export(tmp)
            converter = tf.lite.TFLiteConverter.from_saved_model(tmp)
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
            tflite_bytes = converter.convert()

    x = np.random.default_rng(0).normal(size=(1, SEQUENCE_LENGTH, NUM_FEATURES)).astype(np.float32)
    keras_out = model(x).numpy()

    interpreter = tf.lite.Interpreter(model_content=tflite_bytes)
    interpreter.allocate_tensors()
    interpreter.set_tensor(interpreter.get_input_details()[0]["index"], x)
    interpreter.invoke()
    tflite_out = interpreter.get_tensor(interpreter.get_output_details()[0]["index"])

    if not np.allclose(keras_out, tflite_out, atol=1e-4):
        raise RuntimeError("Output TFLite berbeda dari Keras")
    return f"(method={method}, size={len(tflite_bytes) / 1024:.0f} KB, outputs match)"


@step("Normalization contract (feature_utils)")
def check_feature_utils():
    import feature_utils
    if not feature_utils.VECTORS_PATH.exists():
        raise RuntimeError("tests/normalization_vectors.json belum ada; jalankan `python feature_utils.py`")
    feature_utils.validate_vectors()
    feature_utils._self_test_labels()


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    for check in (check_python, check_imports, check_model_download,
                  check_hand_landmarker, check_lstm_conversion, check_feature_utils):
        check()
    failed = [r for r in results if not r[1]]
    print("\n" + ("ALL CHECKS PASSED - environment siap." if not failed
                  else f"{len(failed)} CHECK(S) FAILED - lihat detail di atas."))
    sys.exit(1 if failed else 0)
