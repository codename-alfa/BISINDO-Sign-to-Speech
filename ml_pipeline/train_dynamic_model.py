"""
train_dynamic_model.py — Pelatihan model LSTM sekuens gestur dinamis BISINDO (66 fitur, 6 kelas) & ekspor TFLite.

Target Kelas (6 kelas dari labels/dynamic_labels.txt):
1. Halo
2. Terima kasih
3. Tolong
4. Ya
5. Tidak
6. _idle

Fitur Utama (Sprint 2):
- Memuat rekaman mentah `.npz` dari `data/dynamic_raw/<Kelas>/<signer>_<idx>.npz`
- Augmentasi time-shift crop x4 (jendela 1.5s dari rekaman 2.0s) HANYA pada data train
  (pemisahan train/val dilakukan pada level take/rekaman agar bebas data leakage)
- Ekstraksi fitur via `feature_utils.resample_window` -> `feature_utils.dynamic_features` -> (30, 66)
- Menolak berjalan jika ada kelas < 30 rekaman nyata kecuali diberi flag `--allow-synthetic`
- Strategi validasi:
  * Leave-One-Signer-Out (LOSO) jika jumlah signer unik >= 3
  * Stratified 80/20 pada level take jika jumlah signer < 3
- Output:
  * `models/dynamic_model.tflite` (Builtins Only, input [1, 30, 66], output [1, 6])
  * `models/dynamic_model_meta.json`
  * `models/confusion_matrix_dynamic.png`
  * `models/classification_report_dynamic.txt`
  * `models/training_curves_dynamic.png`
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

import feature_utils

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = ROOT / "data" / "dynamic_raw"
MODELS_DIR = ROOT / "models"
MODEL_KERAS = MODELS_DIR / "dynamic_model.keras"
MODEL_TFLITE = MODELS_DIR / "dynamic_model.tflite"
MODEL_META = MODELS_DIR / "dynamic_model_meta.json"
CURVES_PLOT = MODELS_DIR / "training_curves_dynamic.png"
CM_PLOT = MODELS_DIR / "confusion_matrix_dynamic.png"
REPORT_TXT = MODELS_DIR / "classification_report_dynamic.txt"
LABELS_PATH = ROOT / "labels" / "dynamic_labels.txt"

SEQUENCE_LENGTH = feature_utils.SEQUENCE_LENGTH
DYNAMIC_NUM_FEATURES = feature_utils.DYNAMIC_NUM_FEATURES
WINDOW_MS = feature_utils.DYNAMIC_WINDOW_MS
HOP_MS = feature_utils.DYNAMIC_HOP_MS


def make_synthetic_raw_recording(
    motion_type: str,
    rng: np.random.Generator,
    duration_ms: float = 2000.0,
    fps: float = 25.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Hasilkan rekaman mentah (ts_ms, landmarks_model_space) berdurasi 2.0 detik."""
    base_hand = feature_utils._canonical_hand().astype(np.float32)
    num_frames = int(round((duration_ms / 1000.0) * fps))
    ts_ms = np.linspace(0.0, duration_ms, num_frames, dtype=np.float32)

    scale_mod = float(rng.uniform(0.85, 1.15))
    rot_angle = float(rng.uniform(-0.12, 0.12))
    c, s = np.cos(rot_angle), np.sin(rot_angle)
    rot_mat = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32)

    # Variasi bentuk jari per kata agar shape + trajectory sama-sama informatif
    shape_template = base_hand.copy()
    if motion_type == "nod":  # Ya: kepalan / anggukan
        shape_template[5:, 1] = shape_template[0, 1] - 0.08
    elif motion_type == "shake":  # Tidak: jari telunjuk & tengah terbuka bergoyang
        shape_template[13:, 1] = shape_template[0, 1] - 0.06
    elif motion_type == "pray_help":  # Tolong: tangan tegak naik-turun
        shape_template[:, 0] *= 0.90

    frames = []
    for t_val in ts_ms:
        progress = float(t_val / max(1.0, duration_ms))
        pts = ((shape_template - shape_template[0]) @ rot_mat) * scale_mod + shape_template[0]

        if motion_type == "wave":  # Halo: lambaian kiri-kanan besar
            dx = 0.16 * np.sin(progress * 3.0 * np.pi)
            dy = 0.02 * np.cos(progress * 2.0 * np.pi)
            ds = 1.0
        elif motion_type == "chest_to_front":  # Terima kasih: gerak maju dari dagu/dada (skala membesar + turun)
            dx = 0.02 * np.sin(progress * np.pi)
            dy = 0.12 * progress
            ds = 1.0 + 0.28 * progress
        elif motion_type == "pray_help":  # Tolong: gerak naik-turun memohon
            dx = 0.02 * np.cos(progress * 2.0 * np.pi)
            dy = -0.14 * np.sin(progress * 2.0 * np.pi)
            ds = 1.0 + 0.08 * np.sin(progress * np.pi)
        elif motion_type == "nod":  # Ya: anggukan vertikal cepat
            dx = 0.0
            dy = 0.15 * np.sin(progress * 4.0 * np.pi)
            ds = 1.0
        elif motion_type == "shake":  # Tidak: goyangan horizontal cepat
            dx = 0.18 * np.sin(progress * 4.0 * np.pi)
            dy = 0.0
            ds = 1.0
        else:  # _idle: hampir diam / drift sangat kecil
            dx = float(rng.normal(0.0, 0.008))
            dy = float(rng.normal(0.0, 0.008))
            ds = 1.0 + float(rng.normal(0.0, 0.01))

        pts = (pts - pts[0]) * ds + pts[0]
        pts[:, 0] += dx
        pts[:, 1] += dy
        pts += rng.normal(0.0, 0.004, size=pts.shape).astype(np.float32)
        frames.append(pts)

    return ts_ms, np.stack(frames, axis=0).astype(np.float32)


def extract_crops_from_recording(
    ts_ms: np.ndarray,
    landmarks: np.ndarray,
    augment_crops: int,
    rng: np.random.Generator,
) -> list[np.ndarray]:
    """Ekstrak 1 (jika augment_crops=1) atau beberapa crop 1.5s dari rekaman 2.0s."""
    if len(ts_ms) == 0:
        return []
    t_min = float(ts_ms[0])
    t_max = float(ts_ms[-1])
    total_span = t_max - t_min

    if total_span < WINDOW_MS:
        # Jika durasi rekaman sedikit di bawah 1500 ms, geser t_end ke t_min + WINDOW_MS jika cukup dekat
        candidate_ends = [t_max]
    elif augment_crops <= 1:
        # Evaluasi / validasi: 1 crop deterministik di tengah rekaman
        mid_end = t_min + WINDOW_MS + 0.5 * (total_span - WINDOW_MS)
        candidate_ends = [mid_end]
    else:
        # Training: pilih titik akhir terdistribusi merata + sedikit jitter
        slack = max(0.0, total_span - WINDOW_MS)
        base_ends = np.linspace(t_min + WINDOW_MS, t_min + WINDOW_MS + slack, augment_crops)
        candidate_ends = []
        for be in base_ends:
            jitter = float(rng.uniform(-25.0, 25.0)) if slack > 60.0 else 0.0
            t_end = float(np.clip(be + jitter, t_min + WINDOW_MS, t_max))
            candidate_ends.append(t_end)

    feats_list: list[np.ndarray] = []
    for t_end in candidate_ends:
        res = feature_utils.resample_window(ts_ms, landmarks, t_end_ms=t_end)
        if res is not None:
            feats_list.append(feature_utils.dynamic_features(res))
    return feats_list


def load_recordings(
    data_dir: Path,
    raw_labels: list[str],
    min_samples_per_class: int = 30,
    allow_synthetic: bool = False,
) -> tuple[list[dict], bool]:
    """Muat daftar rekaman (level take) beserta metadata signer dan label."""
    classes = [lbl.replace(" ", "_") for lbl in raw_labels]
    motion_map = {
        "Halo": "wave",
        "Terima_kasih": "chest_to_front",
        "Tolong": "pray_help",
        "Ya": "nod",
        "Tidak": "shake",
        "_idle": "idle",
    }

    records: list[dict] = []
    used_synthetic = False
    rng = np.random.default_rng(42)
    synthetic_signers = ["danish", "vanesa", "ahmad"]

    print(f"📦 Memuat rekaman mentah (.npz) dari: {data_dir}")
    deficit_classes: list[tuple[str, int]] = []

    for class_idx, cls_folder in enumerate(classes):
        cls_dir = data_dir / cls_folder
        npz_files = sorted(cls_dir.glob("*.npz")) if cls_dir.exists() else []
        valid_class_records: list[dict] = []

        for f in npz_files:
            try:
                dat = np.load(f, allow_pickle=True)
                ts_ms = np.asarray(dat["timestamps_ms"], dtype=np.float32)
                lms = np.asarray(dat["landmarks"], dtype=np.float32)
                signer = str(dat["signer"]) if "signer" in dat else f.stem.split("_")[0].lower()
                # Uji apakah minimal 1 jendela tengah valid (atau untuk _idle jika ada landmark)
                test_crops = extract_crops_from_recording(ts_ms, lms, augment_crops=1, rng=rng)
                if test_crops:
                    valid_class_records.append({
                        "ts_ms": ts_ms,
                        "landmarks": lms,
                        "class_idx": class_idx,
                        "class_name": raw_labels[class_idx],
                        "signer": signer,
                        "is_synthetic": False,
                    })
            except Exception as exc:
                print(f"   ⚠️ Gagal membaca {f.name}: {exc}")

        print(f"   Kelas '{raw_labels[class_idx]}' ({cls_folder}): {len(valid_class_records)} rekaman nyata valid.")

        if len(valid_class_records) < min_samples_per_class:
            if not allow_synthetic:
                deficit_classes.append((raw_labels[class_idx], len(valid_class_records)))
            else:
                used_synthetic = True
                needed = min_samples_per_class - len(valid_class_records)
                print(f"   ℹ️ [--allow-synthetic] Menambahkan {needed} rekaman sintetis untuk '{cls_folder}'...")
                m_type = motion_map.get(cls_folder, "idle")
                for k in range(needed):
                    ts_s, lms_s = make_synthetic_raw_recording(m_type, rng)
                    valid_class_records.append({
                        "ts_ms": ts_s,
                        "landmarks": lms_s,
                        "class_idx": class_idx,
                        "class_name": raw_labels[class_idx],
                        "signer": synthetic_signers[k % len(synthetic_signers)],
                        "is_synthetic": True,
                    })

        records.extend(valid_class_records)

    if deficit_classes and not allow_synthetic:
        msg_lines = [
            f"❌ Jumlah rekaman nyata belum memenuhi syarat minimum ({min_samples_per_class} take/kelas):",
        ]
        for c_name, cnt in deficit_classes:
            msg_lines.append(f"   - {c_name}: {cnt}/{min_samples_per_class} rekaman")
        msg_lines.append(
            "Jalankan `python collect_dynamic_data.py --signer <nama>` sesuai RECORDING_GUIDE.md, "
            "atau gunakan `--allow-synthetic` hanya untuk smoke-test/bootstrap."
        )
        raise RuntimeError("\n".join(msg_lines))

    return records, used_synthetic


def build_datasets(
    records: list[dict],
    augment_factor: int = 4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """Pisahkan train/val pada level take (LOSO jika >=3 signer, selain itu stratified 80/20),
    lalu terapkan augmentasi time-shift crop hanya pada train."""
    rng = np.random.default_rng(123)
    signers = sorted({r["signer"] for r in records})

    if len(signers) >= 3:
        # Leave-One-Signer-Out: gunakan signer terakhir secara alfabetis sebagai held-out signer
        held_out_signer = signers[-1]
        train_recs = [r for r in records if r["signer"] != held_out_signer]
        val_recs = [r for r in records if r["signer"] == held_out_signer]
        val_mode = f"leave_one_signer_out (held_out={held_out_signer})"
    else:
        labels_arr = np.array([r["class_idx"] for r in records])
        indices = np.arange(len(records))
        tr_idx, va_idx = train_test_split(
            indices,
            test_size=0.2,
            random_state=42,
            stratify=labels_arr,
        )
        train_recs = [records[i] for i in tr_idx]
        val_recs = [records[i] for i in va_idx]
        val_mode = "stratified_80_20_take_level"

    X_train_list, y_train_list = [], []
    for r in train_recs:
        crops = extract_crops_from_recording(r["ts_ms"], r["landmarks"], augment_crops=augment_factor, rng=rng)
        for c in crops:
            X_train_list.append(c)
            y_train_list.append(r["class_idx"])

    X_val_list, y_val_list = [], []
    for r in val_recs:
        crops = extract_crops_from_recording(r["ts_ms"], r["landmarks"], augment_crops=1, rng=rng)
        for c in crops:
            X_val_list.append(c)
            y_val_list.append(r["class_idx"])

    X_train = np.stack(X_train_list, axis=0).astype(np.float32)
    y_train = np.array(y_train_list, dtype=np.int32)
    X_val = np.stack(X_val_list, axis=0).astype(np.float32)
    y_val = np.array(y_val_list, dtype=np.int32)

    print(
        f"✅ Split ({val_mode}): Train={len(X_train)} sampel (dari {len(train_recs)} take), "
        f"Val={len(X_val)} sampel (dari {len(val_recs)} take), Shape={X_train.shape[1:]}"
    )
    return X_train, y_train, X_val, y_val, val_mode


def build_model(num_classes: int, batch_size: int | None = None) -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.Input(
            shape=(SEQUENCE_LENGTH, DYNAMIC_NUM_FEATURES),
            batch_size=batch_size,
            name="sequence_features",
        ),
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


def convert_model_to_tflite(trained_model: tf.keras.Model, num_classes: int, out_tflite: Path) -> float:
    print("\n⚙️ Mengonversi model LSTM (30x66) ke TFLite (Builtins Only)...")
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

    out_tflite.parent.mkdir(parents=True, exist_ok=True)
    out_tflite.write_bytes(tflite_bytes)
    size_kb = len(tflite_bytes) / 1024.0
    print(f"✅ Model TFLite disimpan: {out_tflite} ({size_kb:.1f} KB)")

    # Parity Test
    rng = np.random.default_rng(7)
    test_seq = rng.normal(size=(1, SEQUENCE_LENGTH, DYNAMIC_NUM_FEATURES)).astype(np.float32)
    keras_out = infer_model.predict(test_seq, verbose=0)[0]

    interpreter = tf.lite.Interpreter(model_content=tflite_bytes)
    interpreter.allocate_tensors()
    in_det = interpreter.get_input_details()[0]
    out_det = interpreter.get_output_details()[0]

    assert list(in_det["shape"]) == [1, SEQUENCE_LENGTH, DYNAMIC_NUM_FEATURES], (
        f"Unexpected input shape: {in_det['shape']}"
    )
    assert list(out_det["shape"]) == [1, num_classes], f"Unexpected output shape: {out_det['shape']}"

    interpreter.set_tensor(in_det["index"], test_seq)
    interpreter.invoke()
    tflite_out = interpreter.get_tensor(out_det["index"])[0]

    max_diff = float(np.max(np.abs(keras_out - tflite_out)))
    print(f"🧪 Parity Check TFLite vs Keras (LSTM 30x66): Max Diff = {max_diff:.6f}")
    if max_diff >= 1e-4:
        raise AssertionError(f"Parity diff terlalu besar: {max_diff}")
    print("🎉 PARITY CHECK PASSED: Model LSTM TFLite 100% konsisten dengan Keras!")
    return max_diff


def save_evaluation_artifacts(
    model: tf.keras.Model,
    X_val: np.ndarray,
    y_val: np.ndarray,
    raw_labels: list[str],
    cm_path: Path,
    report_path: Path,
) -> None:
    preds = model.predict(X_val, verbose=0)
    y_pred = np.argmax(preds, axis=1)

    report = classification_report(
        y_val,
        y_pred,
        target_names=raw_labels,
        digits=4,
        zero_division=0,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"📄 Classification report disimpan ke: {report_path}")

    cm = confusion_matrix(y_val, y_pred, labels=list(range(len(raw_labels))))
    plt.figure(figsize=(7, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=raw_labels,
        yticklabels=raw_labels,
    )
    plt.title("Confusion Matrix Model Dinamis (LSTM 30x66)")
    plt.xlabel("Prediksi")
    plt.ylabel("Aktual")
    plt.tight_layout()
    plt.savefig(str(cm_path), dpi=150)
    plt.close()
    print(f"📊 Confusion matrix disimpan ke: {cm_path}")


def run_training(
    data_dir: Path = DEFAULT_DATA_DIR,
    out_dir: Path = MODELS_DIR,
    min_samples: int = 30,
    allow_synthetic: bool = False,
    epochs: int = 60,
    augment_factor: int = 4,
) -> dict:
    raw_labels = feature_utils.load_labels(LABELS_PATH)
    out_dir.mkdir(parents=True, exist_ok=True)

    records, used_synthetic = load_recordings(
        data_dir=data_dir,
        raw_labels=raw_labels,
        min_samples_per_class=min_samples,
        allow_synthetic=allow_synthetic,
    )
    X_train, y_train, X_val, y_val, val_mode = build_datasets(records, augment_factor=augment_factor)

    model = build_model(len(raw_labels))
    keras_path = out_dir / "dynamic_model.keras"
    tflite_path = out_dir / "dynamic_model.tflite"
    meta_path = out_dir / "dynamic_model_meta.json"
    curves_path = out_dir / "training_curves_dynamic.png"
    cm_path = out_dir / "confusion_matrix_dynamic.png"
    report_path = out_dir / "classification_report_dynamic.txt"

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=15, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-5),
        tf.keras.callbacks.ModelCheckpoint(str(keras_path), monitor="val_accuracy", save_best_only=True),
    ]

    print(f"\n🚀 Memulai training LSTM ({epochs} epochs max)...")
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=16,
        callbacks=callbacks,
        verbose=1,
    )

    val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)
    print("\n" + "=" * 55)
    print(f"🎯 Evaluasi Set Validasi LSTM: Akurasi = {val_acc * 100:.2f}% | Loss = {val_loss:.4f}")
    print("=" * 55)

    # Plot kurva pelatihan
    plt.figure(figsize=(10, 4))
    plt.subplot(1, 2, 1)
    plt.plot(history.history["accuracy"], label="Train Acc")
    plt.plot(history.history["val_accuracy"], label="Val Acc")
    plt.title("Akurasi Model Dinamis (LSTM 30x66)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(history.history["loss"], label="Train Loss")
    plt.plot(history.history["val_loss"], label="Val Loss")
    plt.title("Loss Model Dinamis (LSTM 30x66)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(curves_path), dpi=150)
    plt.close()

    save_evaluation_artifacts(model, X_val, y_val, raw_labels, cm_path=cm_path, report_path=report_path)
    max_diff = convert_model_to_tflite(model, len(raw_labels), out_tflite=tflite_path)

    meta = {
        "schema_version": 2,
        "window_ms": WINDOW_MS,
        "hop_ms": HOP_MS,
        "sequence_length": SEQUENCE_LENGTH,
        "num_features": DYNAMIC_NUM_FEATURES,
        "max_gap_ms": feature_utils.MAX_GAP_MS,
        "min_valid_frames": feature_utils.MIN_VALID_FRAMES,
        "labels": raw_labels,
        "val_accuracy": round(float(val_acc), 4),
        "val_loss": round(float(val_loss), 4),
        "validation_mode": val_mode,
        "is_bootstrap_synthetic": bool(used_synthetic),
        "tflite_parity_max_diff": round(float(max_diff), 8),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"🗂️ Metadata model disimpan ke: {meta_path}")
    return meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train BISINDO Dynamic LSTM Model (30x66)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Folder data/dynamic_raw")
    parser.add_argument("--out-dir", type=Path, default=MODELS_DIR, help="Folder output models/")
    parser.add_argument("--min-samples", type=int, default=30, help="Minimum rekaman nyata per kelas")
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Izinkan pelengkap sintetis jika rekaman nyata kurang dari --min-samples (untuk bootstrap/smoke test)",
    )
    parser.add_argument("--epochs", type=int, default=60, help="Jumlah maksimum epoch training")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_training(
        data_dir=args.data_dir,
        out_dir=args.out_dir,
        min_samples=args.min_samples,
        allow_synthetic=args.allow_synthetic,
        epochs=args.epochs,
    )
