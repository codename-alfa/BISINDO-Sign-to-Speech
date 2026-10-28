"""
smoke_test_dynamic_pipeline.py — Pengujian asap (smoke test) end-to-end untuk pipeline dinamis 66 fitur.

Tahapan yang diuji:
1. Penolakan training jika jumlah rekaman nyata < min_samples dan tanpa `--allow-synthetic`.
2. Pembuatan rekaman `.npz` palsu untuk 3 signer (danish, vanesa, ahmad) x 6 kelas di folder sementara.
3. Pelatihan 2 epoch dengan validasi Leave-One-Signer-Out, ekspor TFLite Builtins Only, & verifikasi shape [1, 30, 66] -> [1, 6].
4. Opsional (`--bootstrap-models`): melatih model bootstrap [1, 30, 66] -> [1, 6] ke `models/` dan menyinkronkan ke `android_app/app/src/main/assets/` agar aplikasi Android dapat langsung diuji sebelum sesi rekam tim selesai.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import tensorflow as tf

import feature_utils
import sync_android_assets
import train_dynamic_model

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def populate_dummy_npz(data_dir: Path, raw_labels: list[str], takes_per_signer: int = 2) -> None:
    rng = np.random.default_rng(99)
    signers = ["danish", "vanesa", "ahmad"]
    motion_map = {
        "Halo": "wave",
        "Terima_kasih": "chest_to_front",
        "Tolong": "pray_help",
        "Ya": "nod",
        "Tidak": "shake",
        "_idle": "idle",
    }

    for lbl in raw_labels:
        cls_folder = lbl.replace(" ", "_")
        cls_dir = data_dir / cls_folder
        cls_dir.mkdir(parents=True, exist_ok=True)
        m_type = motion_map.get(cls_folder, "idle")

        for signer in signers:
            for idx in range(takes_per_signer):
                ts_ms, lms = train_dynamic_model.make_synthetic_raw_recording(m_type, rng)
                out_path = cls_dir / f"{signer}_{idx:03d}.npz"
                np.savez_compressed(
                    out_path,
                    timestamps_ms=ts_ms,
                    landmarks=lms,
                    width=np.int32(640),
                    height=np.int32(480),
                    fps=np.float32(25.0),
                    signer=signer,
                    label=cls_folder,
                )


def run_smoke_test(bootstrap_models: bool = False) -> None:
    raw_labels = feature_utils.load_labels(feature_utils.DYNAMIC_LABELS_PATH)
    assert len(raw_labels) == 6, f"Expected 6 dynamic labels, got {raw_labels}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        empty_data = tmp_path / "empty_raw"
        out_dir = tmp_path / "out_models"

        # 1. Pastikan gagal jika rekaman nyata kurang & allow_synthetic=False
        print("🧪 [1/3] Menguji guard penolakan jika data nyata < min_samples...")
        try:
            train_dynamic_model.run_training(
                data_dir=empty_data,
                out_dir=out_dir,
                min_samples=30,
                allow_synthetic=False,
                epochs=1,
            )
            raise AssertionError("Seharusnya melempar RuntimeError saat data nyata kosong!")
        except RuntimeError:
            print("   [OK] Guard bekerja: menolak training saat rekaman nyata kurang dari batas minimum.")

        # 2. Buat dummy .npz untuk 3 signer x 6 kelas -> jalankan LOSO training 2 epoch
        print("🧪 [2/3] Menguji pipeline .npz -> LOSO split -> resample -> 66 fitur -> LSTM -> TFLite...")
        dummy_data = tmp_path / "dummy_raw"
        populate_dummy_npz(dummy_data, raw_labels, takes_per_signer=2)  # 3 signer x 2 = 6 take/kelas

        meta = train_dynamic_model.run_training(
            data_dir=dummy_data,
            out_dir=out_dir,
            min_samples=6,
            allow_synthetic=False,
            epochs=2,
            augment_factor=2,
        )

        tflite_path = out_dir / "dynamic_model.tflite"
        assert tflite_path.exists(), "dynamic_model.tflite tidak terbentuk!"
        assert meta["validation_mode"].startswith("leave_one_signer_out"), (
            f"Expected LOSO validation mode, got {meta['validation_mode']}"
        )

        interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
        interpreter.allocate_tensors()
        in_shape = [int(x) for x in interpreter.get_input_details()[0]["shape"]]
        out_shape = [int(x) for x in interpreter.get_output_details()[0]["shape"]]
        assert in_shape == [1, 30, 66], f"Input shape salah: {in_shape}"
        assert out_shape == [1, 6], f"Output shape salah: {out_shape}"
        print(f"   [OK] Smoke test TFLite valid: input={in_shape}, output={out_shape}")

    if bootstrap_models:
        print("🧪 [3/3] Melatih bootstrap dynamic_model.tflite (30x66 -> 6 kelas) & sync ke Android assets...")
        train_dynamic_model.run_training(
            min_samples=30,
            allow_synthetic=True,
            epochs=25,
            augment_factor=2,
        )
        sync_android_assets.sync_assets()
    else:
        print("🧪 [3/3] Smoke test selesai (gunakan --bootstrap-models untuk memperbarui models/ & assets/).")


if __name__ == "__main__":
    run_smoke_test(bootstrap_models="--bootstrap-models" in sys.argv)

