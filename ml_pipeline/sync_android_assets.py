"""
sync_android_assets.py — Menyalin model TFLite, metadata JSON, dan berkas label ke folder assets Android
serta memverifikasi kesesuaian dimensi tensor input/output terhadap daftar label.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import tensorflow as tf

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
LABELS_DIR = ROOT / "labels"
ANDROID_ASSETS_DIR = ROOT.parent / "android_app" / "app" / "src" / "main" / "assets"


def verify_tflite_asset(tflite_path: Path, expected_input_shape: list[int], expected_num_classes: int) -> None:
    interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
    interpreter.allocate_tensors()
    in_shape = [int(x) for x in interpreter.get_input_details()[0]["shape"]]
    out_shape = [int(x) for x in interpreter.get_output_details()[0]["shape"]]

    if in_shape != expected_input_shape:
        raise AssertionError(
            f"{tflite_path.name}: input shape {in_shape} != expected {expected_input_shape}"
        )
    if out_shape != [1, expected_num_classes]:
        raise AssertionError(
            f"{tflite_path.name}: output shape {out_shape} != expected [1, {expected_num_classes}]"
        )
    print(f"   [OK] {tflite_path.name}: input={in_shape}, output={out_shape} ({tflite_path.stat().st_size / 1024:.1f} KB)")


def sync_assets() -> None:
    if not ANDROID_ASSETS_DIR.exists():
        raise FileNotFoundError(f"Folder assets Android tidak ditemukan: {ANDROID_ASSETS_DIR}")

    files_to_copy = [
        (MODELS_DIR / "static_model.tflite", ANDROID_ASSETS_DIR / "static_model.tflite", True),
        (MODELS_DIR / "dynamic_model.tflite", ANDROID_ASSETS_DIR / "dynamic_model.tflite", True),
        (MODELS_DIR / "dynamic_model_meta.json", ANDROID_ASSETS_DIR / "dynamic_model_meta.json", False),
        (LABELS_DIR / "static_labels.txt", ANDROID_ASSETS_DIR / "static_labels.txt", True),
        (LABELS_DIR / "dynamic_labels.txt", ANDROID_ASSETS_DIR / "dynamic_labels.txt", True),
    ]

    print(f"🔄 Menyinkronkan model & label ke: {ANDROID_ASSETS_DIR}")
    for src, dst, required in files_to_copy:
        if not src.exists():
            if required:
                raise FileNotFoundError(f"File wajib tidak ditemukan: {src}")
            continue
        shutil.copy2(src, dst)
        print(f"   Copied: {src.name} -> assets/{dst.name}")

    static_labels = feature_utils.load_labels(ANDROID_ASSETS_DIR / "static_labels.txt")
    dynamic_labels = feature_utils.load_labels(ANDROID_ASSETS_DIR / "dynamic_labels.txt")

    verify_tflite_asset(
        ANDROID_ASSETS_DIR / "static_model.tflite",
        expected_input_shape=[1, feature_utils.NUM_FEATURES],
        expected_num_classes=len(static_labels),
    )
    verify_tflite_asset(
        ANDROID_ASSETS_DIR / "dynamic_model.tflite",
        expected_input_shape=[1, feature_utils.SEQUENCE_LENGTH, feature_utils.DYNAMIC_NUM_FEATURES],
        expected_num_classes=len(dynamic_labels),
    )

    meta_dst = ANDROID_ASSETS_DIR / "dynamic_model_meta.json"
    if meta_dst.exists():
        meta = json.loads(meta_dst.read_text(encoding="utf-8"))
        assert meta["num_features"] == feature_utils.DYNAMIC_NUM_FEATURES
        assert meta["sequence_length"] == feature_utils.SEQUENCE_LENGTH
        assert meta["labels"] == dynamic_labels
        print(f"   [OK] dynamic_model_meta.json: schema_v{meta.get('schema_version')}, val_acc={meta.get('val_accuracy')}")

    print("✅ Sinkronisasi & verifikasi assets Android selesai!")


if __name__ == "__main__":
    sync_assets()

