"""
feature_utils.py — Single source of truth untuk feature engineering landmark.

KONTRAK: Implementasi ini HARUS identik dengan `FeatureExtractor.kt` di Android.
Setiap perubahan formula di sini wajib diikuti perubahan di Kotlin, lalu
regenerate `tests/normalization_vectors.json` dan jalankan unit test Kotlin.

Formula (3D, relatif terhadap wrist, diskalakan ukuran tangan):
    P_norm = (P - P_wrist) / || P_wrist - P_middle_mcp ||

Output: float32[63] dengan urutan [x0, y0, z0, x1, y1, z1, ..., x20, y20, z20].

Jalankan langsung untuk generate + validasi test vector:
    python feature_utils.py            # validasi terhadap JSON yang ada
    python feature_utils.py --regen    # tulis ulang JSON (hanya jika formula berubah)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Konstanta kontrak (harus sama dengan Kotlin)
# ---------------------------------------------------------------------------
WRIST = 0
MIDDLE_MCP = 9
NUM_LANDMARKS = 21
NUM_COORDS = 3
NUM_FEATURES = NUM_LANDMARKS * NUM_COORDS  # 63
SEQUENCE_LENGTH = 30  # frame per sequence untuk model dinamis
MIN_HAND_SIZE = 1e-6

ROOT = Path(__file__).resolve().parent
LABELS_DIR = ROOT / "labels"
STATIC_LABELS_PATH = LABELS_DIR / "static_labels.txt"
DYNAMIC_LABELS_PATH = LABELS_DIR / "dynamic_labels.txt"
VECTORS_PATH = ROOT / "tests" / "normalization_vectors.json"


def _to_array(landmarks) -> np.ndarray:
    """Terima ndarray (21,3), list of [x,y,z], atau list objek ber-atribut .x/.y/.z
    (mis. `NormalizedLandmark` dari MediaPipe Tasks). Return float64 (21,3)."""
    if isinstance(landmarks, np.ndarray):
        pts = landmarks.astype(np.float64)
    else:
        items = list(landmarks)
        if items and hasattr(items[0], "x"):
            pts = np.array([[lm.x, lm.y, lm.z] for lm in items], dtype=np.float64)
        else:
            pts = np.asarray(items, dtype=np.float64)
    if pts.shape != (NUM_LANDMARKS, NUM_COORDS):
        raise ValueError(f"Expected shape ({NUM_LANDMARKS}, {NUM_COORDS}), got {pts.shape}")
    return pts


def normalize_landmarks(landmarks) -> np.ndarray:
    """21 landmark tangan -> vektor fitur float32[63] (lihat docstring modul)."""
    pts = _to_array(landmarks)
    hand_size = float(np.linalg.norm(pts[WRIST] - pts[MIDDLE_MCP]))
    if hand_size < MIN_HAND_SIZE:
        raise ValueError("Degenerate hand: jarak wrist-middle_mcp ~ 0")
    return ((pts - pts[WRIST]) / hand_size).astype(np.float32).reshape(-1)


def build_sequence(frames: Sequence[np.ndarray]) -> np.ndarray:
    """Gabungkan SEQUENCE_LENGTH vektor fitur menjadi float32 (30, 63) untuk LSTM."""
    if len(frames) != SEQUENCE_LENGTH:
        raise ValueError(f"Expected {SEQUENCE_LENGTH} frames, got {len(frames)}")
    seq = np.stack([np.asarray(f, dtype=np.float32) for f in frames])
    if seq.shape != (SEQUENCE_LENGTH, NUM_FEATURES):
        raise ValueError(f"Bad sequence shape {seq.shape}")
    return seq


def load_labels(path: Path | str) -> list[str]:
    """Baca file label; urutan baris = indeks output softmax."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip()]


# ---------------------------------------------------------------------------
# Test vectors (dipakai juga oleh unit test Kotlin FeatureExtractorTest)
# ---------------------------------------------------------------------------
def _sample_inputs() -> list[dict]:
    """3 sampel deterministik: tangan sintetis kanonik, tangan diskalakan+digeser,
    dan landmark acak dengan seed tetap."""
    canonical = np.array([
        [0.50, 0.80, 0.00],
        [0.42, 0.74, -0.02], [0.36, 0.66, -0.03], [0.32, 0.58, -0.04], [0.29, 0.51, -0.05],
        [0.44, 0.56, -0.01], [0.43, 0.46, -0.02], [0.43, 0.39, -0.03], [0.42, 0.33, -0.03],
        [0.50, 0.55, -0.01], [0.50, 0.44, -0.02], [0.50, 0.36, -0.03], [0.50, 0.30, -0.03],
        [0.56, 0.57, -0.01], [0.57, 0.47, -0.02], [0.58, 0.40, -0.03], [0.58, 0.34, -0.03],
        [0.62, 0.61, -0.01], [0.64, 0.54, -0.02], [0.65, 0.49, -0.03], [0.66, 0.44, -0.03],
    ])
    shifted = canonical * 0.6 + np.array([0.15, -0.10, 0.02])
    rng = np.random.default_rng(42)
    random = rng.uniform(0.0, 1.0, size=(NUM_LANDMARKS, NUM_COORDS))
    return [
        {"name": "canonical_open_hand", "landmarks": canonical},
        {"name": "scaled_and_shifted", "landmarks": shifted},
        {"name": "random_seed_42", "landmarks": random},
    ]


def generate_vectors() -> dict:
    cases = []
    for s in _sample_inputs():
        out = normalize_landmarks(s["landmarks"])
        cases.append({
            "name": s["name"],
            "input": np.round(s["landmarks"], 6).tolist(),
            "expected": [round(float(v), 6) for v in out],
        })
    return {
        "description": "Test vectors for landmark normalization parity (Python feature_utils <-> Kotlin FeatureExtractor).",
        "formula": "P_norm = (P - P_wrist) / ||P_wrist - P_middle_mcp||",
        "tolerance": 1e-5,
        "cases": cases,
    }


def validate_vectors(path: Path = VECTORS_PATH) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    tol = data["tolerance"]
    for case in data["cases"]:
        got = normalize_landmarks(np.array(case["input"]))
        exp = np.array(case["expected"], dtype=np.float32)
        if got.shape != (NUM_FEATURES,) or not np.allclose(got, exp, atol=tol):
            raise AssertionError(f"Mismatch on case '{case['name']}'")
    # Invariant: skala & translasi tidak boleh mengubah fitur
    c = data["cases"]
    if not np.allclose(c[0]["expected"], c[1]["expected"], atol=tol):
        raise AssertionError("Normalization is not scale/translation invariant")
    print(f"[OK] {len(c)} normalization vectors valid (tol={tol}).")


def _self_test_labels() -> None:
    static = load_labels(STATIC_LABELS_PATH)
    dynamic = load_labels(DYNAMIC_LABELS_PATH)
    assert static == [chr(c) for c in range(ord("A"), ord("Z") + 1)], "static labels must be A..Z"
    assert len(dynamic) >= 5, "dynamic labels must contain the 5 MVP words"
    print(f"[OK] labels: static={len(static)} dynamic={len(dynamic)} {dynamic}")


if __name__ == "__main__":
    if "--regen" in sys.argv or not VECTORS_PATH.exists():
        VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
        VECTORS_PATH.write_text(json.dumps(generate_vectors(), indent=2), encoding="utf-8")
        print(f"[GEN] wrote {VECTORS_PATH.relative_to(ROOT)}")
    validate_vectors()
    _self_test_labels()
