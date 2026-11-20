"""
train_dynamic_model.py — Pelatihan model BiLSTM sekuens gestur dinamis BISINDO (30x66 fitur, 6 kelas)
& ekspor TFLite (100% TFLITE_BUILTINS via unroll=True).

Target Kelas (6 kelas dari labels/dynamic_labels.txt):
1. Halo
2. Terima kasih
3. Tolong
4. Ya
5. Tidak
6. _idle

Fitur Utama (v0.6.0):
- Arsitektur true Bidirectional LSTM: SpatialDropout1D + Bidirectional(LSTM(32, unroll=True)) + L2 + Dropout
- Full 3-Fold Leave-One-Signer-Out (LOSO) pada seluruh signer nyata (`ahmad`, `danish`, `vanesa`)
- EarlyStopping & ReduceLROnPlateau memakai validation split internal dari training signers saja (zero test leakage)
- Augmentasi train-only (time-shift crops, mild amplitude/speed scaling, rotasi 3D ringan, dan Gaussian jitter)
- Class-weighted loss dengan penguatan bobot `_idle` untuk menekan false-positive
- Ekspor 100% `TFLITE_BUILTINS` (tanpa Flex delegate `SELECT_TF_OPS`)
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
from sklearn.utils.class_weight import compute_class_weight

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

    shape_template = base_hand.copy()
    if motion_type == "nod":
        shape_template[5:, 1] = shape_template[0, 1] - 0.08
    elif motion_type == "shake":
        shape_template[13:, 1] = shape_template[0, 1] - 0.06
    elif motion_type == "pray_help":
        shape_template[:, 0] *= 0.90

    frames = []
    for t_val in ts_ms:
        progress = float(t_val / max(1.0, duration_ms))
        pts = ((shape_template - shape_template[0]) @ rot_mat) * scale_mod + shape_template[0]

        if motion_type == "wave":
            dx = 0.16 * np.sin(progress * 3.0 * np.pi)
            dy = 0.02 * np.cos(progress * 2.0 * np.pi)
            ds = 1.0
        elif motion_type == "chest_to_front":
            dx = 0.02 * np.sin(progress * np.pi)
            dy = 0.12 * progress
            ds = 1.0 + 0.28 * progress
        elif motion_type == "pray_help":
            dx = 0.02 * np.cos(progress * 2.0 * np.pi)
            dy = -0.14 * np.sin(progress * 2.0 * np.pi)
            ds = 1.0 + 0.08 * np.sin(progress * np.pi)
        elif motion_type == "nod":
            dx = 0.0
            dy = 0.15 * np.sin(progress * 4.0 * np.pi)
            ds = 1.0
        elif motion_type == "shake":
            dx = 0.18 * np.sin(progress * 4.0 * np.pi)
            dy = 0.0
            ds = 1.0
        else:
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
        candidate_ends = [t_max]
    elif augment_crops <= 1:
        mid_end = t_min + WINDOW_MS + 0.5 * (total_span - WINDOW_MS)
        candidate_ends = [mid_end]
    else:
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


def augment_training_sequence(
    seq30x66: np.ndarray,
    rng: np.random.Generator,
    is_idle: bool = False,
) -> np.ndarray:
    """Augmentasi khusus split train untuk generalisasi lintas-signer:
    rotasi Z kecil pada bentuk tangan dan skala kecepatan wrist yang sadar kelas (_idle vs aktif)."""
    aug = seq30x66.copy()
    theta = np.deg2rad(float(rng.uniform(-9.0, 9.0)))
    c, s = float(np.cos(theta)), float(np.sin(theta))

    shapes = aug[:, :63].reshape(SEQUENCE_LENGTH, 21, 3)
    x_old = shapes[:, :, 0].copy()
    y_old = shapes[:, :, 1].copy()
    shapes[:, :, 0] = c * x_old - s * y_old
    shapes[:, :, 1] = s * x_old + c * y_old
    shape_noise = 0.006 if is_idle else 0.009
    shapes += rng.normal(0.0, shape_noise, size=shapes.shape).astype(np.float32)
    aug[:, :63] = shapes.reshape(SEQUENCE_LENGTH, 63)

    # Skala amplitudo gerakan wrist: _idle diredam agar tidak meniru gestur aktif,
    # sedangkan gestur aktif mencakup penandatangan lambat hingga cepat.
    traj_scale = float(rng.uniform(0.25, 0.90)) if is_idle else float(rng.uniform(0.45, 1.35))
    aug[:, 63:65] *= traj_scale
    aug[:, 65] *= float(rng.uniform(0.65, 1.05)) if is_idle else float(rng.uniform(0.70, 1.30))
    aug[:, 63:66] += rng.normal(0.0, 0.003 if is_idle else 0.005, size=(SEQUENCE_LENGTH, 3)).astype(np.float32)
    return aug.astype(np.float32)


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
        raise RuntimeError("\n".join(msg_lines))

    return records, used_synthetic


def _records_to_xy(
    recs: list[dict],
    augment_crops: int,
    rng: np.random.Generator,
    apply_seq_aug: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    X_list, y_list = [], []
    for r in recs:
        crops = extract_crops_from_recording(
            r["ts_ms"], r["landmarks"], augment_crops=augment_crops, rng=rng
        )
        is_idle = r.get("class_name") == "_idle"
        n_aug_copies = 2 if is_idle else 1
        for c in crops:
            X_list.append(c)
            y_list.append(r["class_idx"])
            if apply_seq_aug:
                for _ in range(n_aug_copies):
                    X_list.append(augment_training_sequence(c, rng, is_idle=is_idle))
                    y_list.append(r["class_idx"])
    return np.stack(X_list, axis=0).astype(np.float32), np.array(y_list, dtype=np.int32)


def build_datasets(
    records: list[dict],
    augment_factor: int = 4,
    held_out_signer: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """Bangun dataset split pada level take."""
    rng = np.random.default_rng(123)
    signers = sorted({r["signer"] for r in records})

    if len(signers) >= 3:
        target_held_out = held_out_signer if held_out_signer in signers else signers[-1]
        train_recs = [r for r in records if r["signer"] != target_held_out]
        val_recs = [r for r in records if r["signer"] == target_held_out]
        val_mode = f"leave_one_signer_out (held_out={target_held_out})"
    else:
        labels_arr = np.array([r["class_idx"] for r in records])
        indices = np.arange(len(records))
        tr_idx, va_idx = train_test_split(
            indices, test_size=0.2, random_state=42, stratify=labels_arr
        )
        train_recs = [records[i] for i in tr_idx]
        val_recs = [records[i] for i in va_idx]
        val_mode = "stratified_80_20_take_level"

    X_train, y_train = _records_to_xy(train_recs, augment_crops=augment_factor, rng=rng, apply_seq_aug=(augment_factor >= 4))
    X_val, y_val = _records_to_xy(val_recs, augment_crops=1, rng=rng, apply_seq_aug=False)

    print(
        f"✅ Split ({val_mode}): Train={len(X_train)} sampel (dari {len(train_recs)} take), "
        f"Val/Test={len(X_val)} sampel (dari {len(val_recs)} take), Shape={X_train.shape[1:]}"
    )
    return X_train, y_train, X_val, y_val, val_mode


def build_model(num_classes: int, batch_size: int | None = None, lstm_units: int = 32) -> tf.keras.Model:
    """True Bidirectional LSTM yang unrolled (30 langkah) agar 100% kompatibel TFLITE_BUILTINS."""
    reg = tf.keras.regularizers.l2(1e-4)
    model = tf.keras.Sequential([
        tf.keras.Input(
            shape=(SEQUENCE_LENGTH, DYNAMIC_NUM_FEATURES),
            batch_size=batch_size,
            name="sequence_features",
        ),
        tf.keras.layers.SpatialDropout1D(0.10, name="seq_spatial_dropout"),
        tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(
                lstm_units,
                unroll=True,
                kernel_regularizer=reg,
                recurrent_regularizer=reg,
            ),
            name="bilstm_encoder",
        ),
        tf.keras.layers.Dropout(0.25, name="bilstm_dropout"),
        tf.keras.layers.Dense(32, activation="relu", kernel_regularizer=reg, name="dense_hidden"),
        tf.keras.layers.Dropout(0.15, name="dense_dropout"),
        tf.keras.layers.Dense(num_classes, activation="softmax", name="output_probabilities"),
    ], name="bisindo_dynamic_bilstm")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def convert_model_to_tflite(
    trained_model: tf.keras.Model,
    num_classes: int,
    out_tflite: Path,
    lstm_units: int = 32,
) -> float:
    print("\n⚙️ Mengonversi model BiLSTM (30x66) ke TFLite (TFLITE_BUILTINS Only)...")
    infer_model = build_model(num_classes, batch_size=1, lstm_units=lstm_units)
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
    print(f"🧪 Sanity Parity Check BiLSTM TFLite vs Keras: Max Diff = {max_diff:.6e}")
    if max_diff >= 1e-4:
        raise AssertionError(f"Parity diff terlalu besar: {max_diff}")
    return max_diff


def _compute_class_weights(y_train: np.ndarray, idle_idx: int, idle_boost: float = 1.75) -> dict[int, float]:
    classes = np.unique(y_train)
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    cw = {int(c): float(w) for c, w in zip(classes, weights)}
    if idle_idx in cw:
        cw[idle_idx] *= idle_boost
    return cw


def _train_single_fold(
    train_recs: list[dict],
    test_recs: list[dict],
    raw_labels: list[str],
    epochs: int,
    augment_factor: int,
    lstm_units: int,
    idle_boost: float,
    seed: int = 42,
):
    tf.keras.utils.set_random_seed(seed)
    rng = np.random.default_rng(seed + 100)
    idle_idx = raw_labels.index("_idle") if "_idle" in raw_labels else -1

    # Internal take-level validation split dari training signers agar EarlyStopping bebas kebocoran test signer
    if epochs >= 5 and len(train_recs) >= 40:
        labels_arr = np.array([r["class_idx"] for r in train_recs])
        idx_arr = np.arange(len(train_recs))
        tr_idx, es_idx = train_test_split(idx_arr, test_size=0.14, random_state=seed, stratify=labels_arr)
        fit_recs = [train_recs[i] for i in tr_idx]
        es_recs = [train_recs[i] for i in es_idx]
        X_fit, y_fit = _records_to_xy(fit_recs, augment_crops=augment_factor, rng=rng, apply_seq_aug=True)
        X_es, y_es = _records_to_xy(es_recs, augment_crops=1, rng=rng, apply_seq_aug=False)
    else:
        X_fit, y_fit = _records_to_xy(train_recs, augment_crops=augment_factor, rng=rng, apply_seq_aug=False)
        X_es, y_es = _records_to_xy(test_recs, augment_crops=1, rng=rng, apply_seq_aug=False)

    X_test, y_test = _records_to_xy(test_recs, augment_crops=1, rng=rng, apply_seq_aug=False)
    cw = _compute_class_weights(y_fit, idle_idx=idle_idx, idle_boost=idle_boost)

    model = build_model(len(raw_labels), lstm_units=lstm_units)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss", patience=12, restore_best_weights=True, verbose=0
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=5, min_lr=1e-5, verbose=0
        ),
    ]

    history = model.fit(
        X_fit,
        y_fit,
        validation_data=(X_es, y_es),
        epochs=epochs,
        batch_size=16,
        class_weight=cw,
        callbacks=callbacks,
        verbose=1 if epochs <= 2 else 2,
    )

    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    probs = model.predict(X_test, verbose=0)
    y_pred = np.argmax(probs, axis=1)
    rep_dict = classification_report(
        y_test, y_pred, labels=list(range(len(raw_labels))), target_names=raw_labels, output_dict=True, zero_division=0
    )
    return {
        "model": model,
        "history": history.history,
        "X_test": X_test,
        "y_test": y_test,
        "y_pred": y_pred,
        "test_acc": float(test_acc),
        "test_loss": float(test_loss),
        "macro_f1": float(rep_dict["macro avg"]["f1-score"]),
        "macro_precision": float(rep_dict["macro avg"]["precision"]),
        "idle_recall": float(rep_dict.get("_idle", {}).get("recall", 0.0)),
        "report_dict": rep_dict,
    }


def save_evaluation_artifacts(
    y_val: np.ndarray,
    y_pred: np.ndarray,
    raw_labels: list[str],
    cm_path: Path,
    report_path: Path,
    fold_label: str,
    loso_summary_text: str = "",
) -> None:
    report = classification_report(
        y_val,
        y_pred,
        labels=list(range(len(raw_labels))),
        target_names=raw_labels,
        digits=4,
        zero_division=0,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    full_text = f"=== PRIMARY HELD-OUT FOLD ({fold_label}) ===\n{report}\n{loso_summary_text}"
    report_path.write_text(full_text, encoding="utf-8")
    print(f"📄 Classification report disimpan ke: {report_path}")

    acc = float(np.mean(y_val == y_pred))
    cm = confusion_matrix(y_val, y_pred, labels=list(range(len(raw_labels))))
    plt.figure(figsize=(7.6, 6.2))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=raw_labels,
        yticklabels=raw_labels,
    )
    plt.title(f"Dynamic BISINDO Confusion Matrix (BiLSTM 30x66)\n{fold_label} | Acc={acc*100:.2f}%", fontsize=11)
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.tight_layout()
    plt.savefig(str(cm_path), dpi=200)
    plt.close()
    print(f"📊 Confusion matrix disimpan ke: {cm_path}")


def run_training(
    data_dir: Path = DEFAULT_DATA_DIR,
    out_dir: Path = MODELS_DIR,
    min_samples: int = 30,
    allow_synthetic: bool = False,
    epochs: int = 60,
    augment_factor: int = 4,
    lstm_units: int = 32,
    idle_boost: float = 1.75,
) -> dict:
    raw_labels = feature_utils.load_labels(LABELS_PATH)
    out_dir.mkdir(parents=True, exist_ok=True)

    records, used_synthetic = load_recordings(
        data_dir=data_dir,
        raw_labels=raw_labels,
        min_samples_per_class=min_samples,
        allow_synthetic=allow_synthetic,
    )
    signers = sorted({r["signer"] for r in records})

    keras_path = out_dir / "dynamic_model.keras"
    tflite_path = out_dir / "dynamic_model.tflite"
    meta_path = out_dir / "dynamic_model_meta.json"
    curves_path = out_dir / "training_curves_dynamic.png"
    cm_path = out_dir / "confusion_matrix_dynamic.png"
    report_path = out_dir / "classification_report_dynamic.txt"

    fold_summaries: list[dict] = []
    primary_fold_res = None
    primary_signer = signers[-1]

    if len(signers) >= 3:
        all_y_true, all_y_pred = [], []
        for idx, held_out in enumerate(signers):
            print(f"\n🔁 [LOSO Fold {idx + 1}/{len(signers)}] held_out={held_out}")
            tr_recs = [r for r in records if r["signer"] != held_out]
            te_recs = [r for r in records if r["signer"] == held_out]
            res = _train_single_fold(
                tr_recs, te_recs, raw_labels, epochs=epochs, augment_factor=augment_factor,
                lstm_units=lstm_units, idle_boost=idle_boost, seed=42 + idx
            )
            print(
                f"   -> Fold '{held_out}' (N={len(res['y_test'])}): Acc={res['test_acc']*100:.2f}%, "
                f"MacroF1={res['macro_f1']:.4f}, _idle Recall={res['idle_recall']:.4f}, Loss={res['test_loss']:.4f}"
            )
            fold_summaries.append({
                "held_out_signer": held_out,
                "n_sequences": int(len(res["y_test"])),
                "accuracy": round(res["test_acc"], 4),
                "loss": round(res["test_loss"], 4),
                "macro_precision": round(res["macro_precision"], 4),
                "macro_f1": round(res["macro_f1"], 4),
                "idle_recall": round(res["idle_recall"], 4),
            })
            all_y_true.append(res["y_test"])
            all_y_pred.append(res["y_pred"])
            if held_out == primary_signer:
                primary_fold_res = res

        y_oof_true = np.concatenate(all_y_true)
        y_oof_pred = np.concatenate(all_y_pred)
        mean_acc = float(np.mean([f["accuracy"] for f in fold_summaries]))
        mean_f1 = float(np.mean([f["macro_f1"] for f in fold_summaries]))
        mean_idle = float(np.mean([f["idle_recall"] for f in fold_summaries]))
        oof_acc = float(np.mean(y_oof_true == y_oof_pred))
        oof_rep = classification_report(
            y_oof_true, y_oof_pred, labels=list(range(len(raw_labels))), target_names=raw_labels, digits=4, zero_division=0
        )
        loso_summary_text = (
            f"\n=== 3-FOLD LOSO AGGREGATE (N={len(y_oof_true)}) ===\n"
            f"Mean Fold Accuracy: {mean_acc*100:.2f}% | Overall OOF Accuracy: {oof_acc*100:.2f}%\n"
            f"Mean Macro F1: {mean_f1:.4f} | Mean _idle Recall: {mean_idle:.4f}\n\n"
            + oof_rep
        )
        print(loso_summary_text)
        val_mode = f"leave_one_signer_out (3-fold CV; primary held_out={primary_signer})"
    else:
        labels_arr = np.array([r["class_idx"] for r in records])
        indices = np.arange(len(records))
        tr_idx, va_idx = train_test_split(indices, test_size=0.2, random_state=42, stratify=labels_arr)
        tr_recs = [records[i] for i in tr_idx]
        te_recs = [records[i] for i in va_idx]
        primary_fold_res = _train_single_fold(
            tr_recs, te_recs, raw_labels, epochs=epochs, augment_factor=augment_factor,
            lstm_units=lstm_units, idle_boost=idle_boost, seed=42
        )
        mean_acc = primary_fold_res["test_acc"]
        mean_f1 = primary_fold_res["macro_f1"]
        mean_idle = primary_fold_res["idle_recall"]
        oof_acc = mean_acc
        loso_summary_text = ""
        val_mode = "stratified_80_20_take_level"

    primary_model = primary_fold_res["model"]
    primary_model.save(str(keras_path))
    trainable_params = int(primary_model.count_params())
    print(f"💾 Model BiLSTM Keras disimpan ke: {keras_path} ({trainable_params} params)")

    hist = primary_fold_res["history"]
    fig = plt.figure(figsize=(10.6, 4.4))
    plt.subplot(1, 2, 1)
    plt.plot(hist["accuracy"], label="Train Acc", color="#2563EB", lw=2)
    plt.plot(hist["val_accuracy"], label="Internal Val Acc", color="#10B981", lw=2)
    plt.title(f"Dynamic BiLSTM ({primary_signer} Fold) - Accuracy", fontsize=11)
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(hist["loss"], label="Train Loss", color="#DC2626", lw=2)
    plt.plot(hist["val_loss"], label="Internal Val Loss", color="#F59E0B", lw=2)
    plt.title(f"Dynamic BiLSTM ({primary_signer} Fold) - Loss", fontsize=11)
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(curves_path), dpi=180)
    plt.close(fig)

    save_evaluation_artifacts(
        primary_fold_res["y_test"],
        primary_fold_res["y_pred"],
        raw_labels,
        cm_path=cm_path,
        report_path=report_path,
        fold_label=f"held_out={primary_signer}",
        loso_summary_text=loso_summary_text,
    )
    max_diff = convert_model_to_tflite(primary_model, len(raw_labels), out_tflite=tflite_path, lstm_units=lstm_units)

    meta = {
        "schema_version": 2,
        "architecture": f"Bidirectional(LSTM({lstm_units}, unroll=True)) -> Dropout(0.25) -> Dense(32) -> Dense(6)",
        "trainable_params": trainable_params,
        "tflite_builtins_only": True,
        "window_ms": WINDOW_MS,
        "hop_ms": HOP_MS,
        "sequence_length": SEQUENCE_LENGTH,
        "num_features": DYNAMIC_NUM_FEATURES,
        "max_gap_ms": feature_utils.MAX_GAP_MS,
        "min_valid_frames": feature_utils.MIN_VALID_FRAMES,
        "labels": raw_labels,
        "primary_held_out_signer": primary_signer,
        "val_accuracy": round(float(primary_fold_res["test_acc"]), 4),
        "val_loss": round(float(primary_fold_res["test_loss"]), 4),
        "macro_precision": round(float(primary_fold_res["macro_precision"]), 4),
        "macro_f1": round(float(primary_fold_res["macro_f1"]), 4),
        "idle_recall": round(float(primary_fold_res["idle_recall"]), 4),
        "loso_3fold_mean_accuracy": round(mean_acc, 4),
        "loso_3fold_overall_oof_accuracy": round(oof_acc, 4),
        "loso_3fold_mean_macro_f1": round(mean_f1, 4),
        "loso_3fold_mean_idle_recall": round(mean_idle, 4),
        "loso_folds": fold_summaries,
        "validation_mode": val_mode,
        "is_bootstrap_synthetic": bool(used_synthetic),
        "tflite_parity_max_diff": round(float(max_diff), 8),
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"🗂️ Metadata model disimpan ke: {meta_path}")
    return meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train BISINDO Dynamic BiLSTM Model (30x66)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Folder data/dynamic_raw")
    parser.add_argument("--out-dir", type=Path, default=MODELS_DIR, help="Folder output models/")
    parser.add_argument("--min-samples", type=int, default=30, help="Minimum rekaman nyata per kelas")
    parser.add_argument("--allow-synthetic", action="store_true", help="Izinkan pelengkap sintetis")
    parser.add_argument("--epochs", type=int, default=60, help="Jumlah maksimum epoch training")
    parser.add_argument("--lstm-units", type=int, default=32, help="Jumlah unit LSTM per arah")
    parser.add_argument("--idle-boost", type=float, default=1.75, help="Pengali class weight untuk _idle")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_training(
        data_dir=args.data_dir,
        out_dir=args.out_dir,
        min_samples=args.min_samples,
        allow_synthetic=args.allow_synthetic,
        epochs=args.epochs,
        lstm_units=args.lstm_units,
        idle_boost=args.idle_boost,
    )
