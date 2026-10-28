"""
feature_utils.py — Single source of truth untuk feature engineering landmark (Static & Dynamic).

KONTRAK: Implementasi ini HARUS identik dengan `FeatureExtractor.kt` dan
`DynamicFeatureBuilder.kt` di Android. Setiap perubahan formula di sini wajib
diikuti perubahan di Kotlin, lalu regenerate JSON test vectors dan jalankan
unit test Kotlin (`./gradlew testDebugUnitTest`).

1. Kontrak Model Space (koreksi aspek rasio & mirror kamera depan):
       x' = (1 - x) * (width / height)   jika mirror_x=True, selain itu x * (width / height)
       y' = y
       z' = z * (width / height)

2. Kontrak Fitur Statis (3D, relatif terhadap wrist, diskalakan ukuran tangan):
       P_norm = (P - P_wrist) / || P_wrist - P_middle_mcp ||
   Output: float32[63] dengan urutan [x0, y0, z0, x1, y1, z1, ..., x20, y20, z20].

3. Kontrak Fitur Dinamis (Time-based window 1500 ms -> Resample 30 frame -> 66 fitur/frame):
   - Filter frame valid dalam [t_end - window_ms, t_end] (tanpa NaN, ukuran tangan >= MIN_HAND_SIZE).
   - Valid jika: jumlah frame valid >= MIN_VALID_FRAMES (5), gap awal (valid_ts[0] - t_start) <= MAX_GAP_MS,
     gap akhir (t_end - valid_ts[-1]) <= MAX_GAP_MS, dan gap antar-frame berurutan <= MAX_GAP_MS (300 ms).
   - Interpolasi linear pada 30 titik waktu seragam t_k = t_start + k * window_ms / 29.
   - Fitur per frame (66 float32):
       * [0..62]  : shape_t = normalize_landmarks(win[t])  (63 fitur bentuk tangan)
       * [63..64] : dxy_t   = (wrist_xy[t] - wrist_xy[0]) / mean_hand_size  (2 fitur lintasan wrist)
       * [65]     : ds_t    = (hand_size[t] / hand_size[0]) - 1.0           (1 fitur perubahan skala z-proxy)

Jalankan langsung untuk generate + validasi test vector:
    python feature_utils.py            # validasi terhadap JSON yang ada
    python feature_utils.py --regen    # tulis ulang JSON test vectors
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

import numpy as np

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Konstanta kontrak (harus sama dengan Kotlin ModelConfig / FeatureExtractor)
# ---------------------------------------------------------------------------
WRIST = 0
MIDDLE_MCP = 9
NUM_LANDMARKS = 21
NUM_COORDS = 3
NUM_FEATURES = NUM_LANDMARKS * NUM_COORDS  # 63 (static)
SEQUENCE_LENGTH = 30  # titik sampel hasil resampling dalam jendela waktu
MIN_HAND_SIZE = 1e-6

# Kontrak dinamis (Sprint 2)
DYNAMIC_WINDOW_MS = 1500
DYNAMIC_HOP_MS = 200
DYNAMIC_NUM_FEATURES = NUM_FEATURES + 3  # 66 (63 shape + dx, dy + ds)
MAX_GAP_MS = 300
MIN_VALID_FRAMES = 5

ROOT = Path(__file__).resolve().parent
LABELS_DIR = ROOT / "labels"
STATIC_LABELS_PATH = LABELS_DIR / "static_labels.txt"
DYNAMIC_LABELS_PATH = LABELS_DIR / "dynamic_labels.txt"
TESTS_DIR = ROOT / "tests"
VECTORS_PATH = TESTS_DIR / "normalization_vectors.json"
MODEL_SPACE_VECTORS_PATH = TESTS_DIR / "model_space_vectors.json"
DYNAMIC_VECTORS_PATH = TESTS_DIR / "dynamic_feature_vectors.json"


def _to_array(landmarks) -> np.ndarray:
    """Terima ndarray (21,3) atau (63,), list of [x,y,z], atau list objek ber-atribut .x/.y/.z
    (mis. `NormalizedLandmark` dari MediaPipe Tasks). Return float64 (21,3)."""
    if isinstance(landmarks, np.ndarray):
        pts = landmarks.astype(np.float64)
        if pts.shape == (NUM_FEATURES,):
            pts = pts.reshape(NUM_LANDMARKS, NUM_COORDS)
    else:
        items = list(landmarks)
        if items and hasattr(items[0], "x"):
            pts = np.array([[lm.x, lm.y, lm.z] for lm in items], dtype=np.float64)
        else:
            pts = np.asarray(items, dtype=np.float64)
            if pts.shape == (NUM_FEATURES,):
                pts = pts.reshape(NUM_LANDMARKS, NUM_COORDS)
    if pts.shape != (NUM_LANDMARKS, NUM_COORDS):
        raise ValueError(f"Expected shape ({NUM_LANDMARKS}, {NUM_COORDS}), got {pts.shape}")
    return pts


def to_model_space(
    raw,
    width: int | float,
    height: int | float,
    mirror_x: bool = True,
) -> np.ndarray:
    """Konversi koordinat ternormalisasi MediaPipe (21, 3) ke koordinat isotropik model space.

    - Jika `mirror_x=True`, sumbu X dicerminkan (`1.0 - x`) sebelum dikalikan rasio aspek.
    - Sumbu X dan Z dikalikan `width / height` agar proporsi geometri tangan konsisten
      terhadap gambar persegi (1:1) tanpa distorsi aspek portrait (3:4) vs landscape (4:3).
    """
    pts = _to_array(raw).copy()
    h = float(height) if float(height) > 0 else 1.0
    aspect = float(width) / h if float(width) > 0 else 1.0
    if mirror_x:
        pts[:, 0] = 1.0 - pts[:, 0]
    pts[:, 0] *= aspect
    pts[:, 2] *= aspect
    return pts.astype(np.float32)


def normalize_landmarks(landmarks) -> np.ndarray:
    """21 landmark tangan -> vektor fitur float32[63] (lihat docstring modul)."""
    pts = _to_array(landmarks)
    hand_size = float(np.linalg.norm(pts[WRIST] - pts[MIDDLE_MCP]))
    if hand_size < MIN_HAND_SIZE:
        raise ValueError("Degenerate hand: jarak wrist-middle_mcp ~ 0")
    return ((pts - pts[WRIST]) / hand_size).astype(np.float32).reshape(-1)


def resample_window(
    ts_ms: Sequence[float | int] | np.ndarray,
    raw_seq: Sequence[np.ndarray] | np.ndarray,
    t_end_ms: float | int,
    window_ms: int = DYNAMIC_WINDOW_MS,
    seq_len: int = SEQUENCE_LENGTH,
    max_gap_ms: int = MAX_GAP_MS,
    min_valid_frames: int = MIN_VALID_FRAMES,
) -> np.ndarray | None:
    """Resample rekaman ber-timestamp pada jendela [t_end_ms - window_ms, t_end_ms]
    menjadi array (seq_len, 21, 3) float32 via interpolasi linear, atau None jika jendela invalid."""
    ts_arr = np.asarray(ts_ms, dtype=np.float64)
    seq_arr = np.asarray(raw_seq, dtype=np.float64)
    if seq_arr.ndim == 2 and seq_arr.shape[1] == NUM_FEATURES:
        seq_arr = seq_arr.reshape(-1, NUM_LANDMARKS, NUM_COORDS)
    if len(ts_arr) == 0 or seq_arr.shape != (len(ts_arr), NUM_LANDMARKS, NUM_COORDS):
        return None

    t_end = float(t_end_ms)
    t_start = t_end - float(window_ms)

    # Filter frame yang berada di dalam jendela [t_start, t_end] dan valid (bukan NaN & ukuran tangan layak)
    valid_ts: list[float] = []
    valid_pts: list[np.ndarray] = []
    for t_val, pts in zip(ts_arr, seq_arr):
        if t_val < t_start - 1e-6 or t_val > t_end + 1e-6:
            continue
        if np.isnan(pts).any():
            continue
        hand_size = float(np.linalg.norm(pts[WRIST] - pts[MIDDLE_MCP]))
        if hand_size < MIN_HAND_SIZE:
            continue
        valid_ts.append(float(t_val))
        valid_pts.append(pts)

    if len(valid_ts) < min_valid_frames:
        return None

    # Pastikan terurut berdasarkan timestamp
    order = np.argsort(valid_ts)
    v_ts = np.array([valid_ts[i] for i in order], dtype=np.float64)
    v_pts = np.stack([valid_pts[i] for i in order], axis=0)  # (M, 21, 3)

    # Cek gap di awal jendela, akhir jendela, dan antar-frame berurutan
    if (v_ts[0] - t_start) > max_gap_ms + 1e-6:
        return None
    if (t_end - v_ts[-1]) > max_gap_ms + 1e-6:
        return None
    if len(v_ts) > 1 and float(np.max(np.diff(v_ts))) > max_gap_ms + 1e-6:
        return None

    # Interpolasi linear pada seq_len titik waktu seragam
    target_ts = np.linspace(t_start, t_end, seq_len, dtype=np.float64)
    out = np.zeros((seq_len, NUM_LANDMARKS, NUM_COORDS), dtype=np.float64)

    for k, tk in enumerate(target_ts):
        if tk <= v_ts[0]:
            out[k] = v_pts[0]
        elif tk >= v_ts[-1]:
            out[k] = v_pts[-1]
        else:
            idx = int(np.searchsorted(v_ts, tk, side="right")) - 1
            idx = max(0, min(idx, len(v_ts) - 2))
            t0, t1 = v_ts[idx], v_ts[idx + 1]
            dt = t1 - t0
            alpha = 0.0 if dt < 1e-9 else (tk - t0) / dt
            out[k] = (1.0 - alpha) * v_pts[idx] + alpha * v_pts[idx + 1]

    return out.astype(np.float32)


def dynamic_features(win: np.ndarray) -> np.ndarray:
    """Konversi jendela ter-resample (30, 21, 3) dalam model space menjadi fitur (30, 66) float32."""
    arr = np.asarray(win, dtype=np.float64)
    if arr.ndim == 2 and arr.shape == (SEQUENCE_LENGTH, NUM_FEATURES):
        arr = arr.reshape(SEQUENCE_LENGTH, NUM_LANDMARKS, NUM_COORDS)
    if arr.shape != (SEQUENCE_LENGTH, NUM_LANDMARKS, NUM_COORDS):
        raise ValueError(f"Expected shape ({SEQUENCE_LENGTH}, {NUM_LANDMARKS}, {NUM_COORDS}), got {arr.shape}")

    shapes = np.zeros((SEQUENCE_LENGTH, NUM_FEATURES), dtype=np.float64)
    sizes = np.zeros(SEQUENCE_LENGTH, dtype=np.float64)

    for t in range(SEQUENCE_LENGTH):
        pts = arr[t]
        sz = float(np.linalg.norm(pts[WRIST] - pts[MIDDLE_MCP]))
        safe_sz = sz if sz >= MIN_HAND_SIZE else 1.0
        sizes[t] = safe_sz
        shapes[t] = ((pts - pts[WRIST]) / safe_sz).reshape(-1)

    mean_size = float(np.mean(sizes))
    if mean_size < MIN_HAND_SIZE:
        mean_size = 1.0
    first_size = sizes[0] if sizes[0] >= MIN_HAND_SIZE else 1.0

    wrist_xy = arr[:, WRIST, :2]  # (30, 2)
    dxy = (wrist_xy - wrist_xy[0:1, :]) / mean_size  # (30, 2)
    ds = (sizes / first_size) - 1.0  # (30,)

    feat_66 = np.concatenate([shapes, dxy, ds[:, None]], axis=1)
    return feat_66.astype(np.float32)


def build_sequence(frames: Sequence[np.ndarray]) -> np.ndarray:
    """Gabungkan SEQUENCE_LENGTH vektor fitur menjadi float32 (30, F) untuk LSTM."""
    if len(frames) != SEQUENCE_LENGTH:
        raise ValueError(f"Expected {SEQUENCE_LENGTH} frames, got {len(frames)}")
    seq = np.stack([np.asarray(f, dtype=np.float32) for f in frames])
    if seq.ndim != 2 or seq.shape[0] != SEQUENCE_LENGTH or seq.shape[1] not in (NUM_FEATURES, DYNAMIC_NUM_FEATURES):
        raise ValueError(f"Bad sequence shape {seq.shape}")
    return seq


def load_labels(path: Path | str) -> list[str]:
    """Baca file label; urutan baris = indeks output softmax."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip()]


# ---------------------------------------------------------------------------
# Test vectors (dipakai langsung oleh unit test Kotlin)
# ---------------------------------------------------------------------------
def _canonical_hand() -> np.ndarray:
    return np.array([
        [0.50, 0.80, 0.00],
        [0.42, 0.74, -0.02], [0.36, 0.66, -0.03], [0.32, 0.58, -0.04], [0.29, 0.51, -0.05],
        [0.44, 0.56, -0.01], [0.43, 0.46, -0.02], [0.43, 0.39, -0.03], [0.42, 0.33, -0.03],
        [0.50, 0.55, -0.01], [0.50, 0.44, -0.02], [0.50, 0.36, -0.03], [0.50, 0.30, -0.03],
        [0.56, 0.57, -0.01], [0.57, 0.47, -0.02], [0.58, 0.40, -0.03], [0.58, 0.34, -0.03],
        [0.62, 0.61, -0.01], [0.64, 0.54, -0.02], [0.65, 0.49, -0.03], [0.66, 0.44, -0.03],
    ], dtype=np.float64)


def _sample_inputs() -> list[dict]:
    """3 sampel deterministik: tangan sintetis kanonik, tangan diskalakan+digeser,
    dan landmark acak dengan seed tetap."""
    canonical = _canonical_hand()
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


def generate_model_space_vectors() -> dict:
    base = np.round(_canonical_hand(), 6)
    configs = [
        {"name": "portrait_480x640_mirrored", "width": 480, "height": 640, "mirror_x": True},
        {"name": "landscape_640x480_unmirrored", "width": 640, "height": 480, "mirror_x": False},
        {"name": "square_512x512_mirrored", "width": 512, "height": 512, "mirror_x": True},
    ]
    cases = []
    for cfg in configs:
        ms = to_model_space(base, cfg["width"], cfg["height"], mirror_x=cfg["mirror_x"])
        norm = normalize_landmarks(ms)
        cases.append({
            "name": cfg["name"],
            "width": cfg["width"],
            "height": cfg["height"],
            "mirror_x": cfg["mirror_x"],
            "input": base.tolist(),
            "expected_model_space": [round(float(v), 6) for v in ms.reshape(-1)],
            "expected_normalized": [round(float(v), 6) for v in norm],
        })
    return {
        "description": "Test vectors for to_model_space parity (Python <-> Kotlin).",
        "tolerance": 1e-5,
        "cases": cases,
    }


def generate_dynamic_vectors() -> dict:
    base = _canonical_hand()
    # 1. Horizontal wave (16 sampel @ 100 ms interval dalam [0, 1500])
    ts_16 = [float(i * 100) for i in range(16)]
    seq_wave = []
    for i, t in enumerate(ts_16):
        pts = base.copy()
        pts[:, 0] += 0.12 * np.sin(2.0 * np.pi * (t / 1500.0))
        pts[:, 1] += 0.02 * (i / 15.0)
        seq_wave.append(np.round(pts, 6))
    seq_wave_arr = np.stack(seq_wave, axis=0)
    res_wave = resample_window(ts_16, seq_wave_arr, t_end_ms=1500.0)
    feat_wave = dynamic_features(res_wave)

    # 2. Vertical nod + scale change (11 sampel @ 150 ms interval dalam [0, 1500])
    ts_11 = [float(i * 150) for i in range(11)]
    seq_nod = []
    for i, t in enumerate(ts_11):
        scale = 1.0 + 0.15 * (t / 1500.0)
        pts = (base - base[0]) * scale + base[0]
        pts[:, 1] += 0.10 * np.cos(np.pi * (t / 1500.0))
        seq_nod.append(np.round(pts, 6))
    seq_nod_arr = np.stack(seq_nod, axis=0)
    res_nod = resample_window(ts_11, seq_nod_arr, t_end_ms=1500.0)
    feat_nod = dynamic_features(res_nod)

    # 3. Valid window dengan gap 200 ms (<= 300 ms max_gap_ms)
    # Hapus t=500 dari ts_16 sehingga jarak 400 -> 600 adalah 200 ms (masih valid)
    ts_gap200 = [t for t in ts_16 if int(t) != 500]
    seq_gap200 = np.stack([seq_wave[i] for i, t in enumerate(ts_16) if int(t) != 500], axis=0)
    res_gap200 = resample_window(ts_gap200, seq_gap200, t_end_ms=1500.0)
    feat_gap200 = dynamic_features(res_gap200)

    # 4. Invalid window dengan gap 400 ms (> 300 ms max_gap_ms)
    # Hapus t=500, 600, 700 sehingga jarak 400 -> 800 adalah 400 ms (invalid -> None)
    ts_gap400 = [t for t in ts_16 if int(t) not in (500, 600, 700)]
    seq_gap400 = np.stack([seq_wave[i] for i, t in enumerate(ts_16) if int(t) not in (500, 600, 700)], axis=0)
    res_gap400 = resample_window(ts_gap400, seq_gap400, t_end_ms=1500.0)
    assert res_gap400 is None, "Expected 400ms gap to be rejected"

    cases = [
        {
            "name": "horizontal_wave_16frames",
            "t_end_ms": 1500.0,
            "timestamps_ms": ts_16,
            "frames": seq_wave_arr.tolist(),
            "valid": True,
            "expected_features": [[round(float(x), 6) for x in row] for row in feat_wave],
        },
        {
            "name": "vertical_nod_with_scale_11frames",
            "t_end_ms": 1500.0,
            "timestamps_ms": ts_11,
            "frames": seq_nod_arr.tolist(),
            "valid": True,
            "expected_features": [[round(float(x), 6) for x in row] for row in feat_nod],
        },
        {
            "name": "valid_with_200ms_gap",
            "t_end_ms": 1500.0,
            "timestamps_ms": ts_gap200,
            "frames": seq_gap200.tolist(),
            "valid": True,
            "expected_features": [[round(float(x), 6) for x in row] for row in feat_gap200],
        },
        {
            "name": "invalid_with_400ms_gap",
            "t_end_ms": 1500.0,
            "timestamps_ms": ts_gap400,
            "frames": seq_gap400.tolist(),
            "valid": False,
            "expected_features": None,
        },
    ]
    return {
        "description": "Test vectors for time-based dynamic window resampling & 66D feature extraction (Python <-> Kotlin).",
        "window_ms": DYNAMIC_WINDOW_MS,
        "sequence_length": SEQUENCE_LENGTH,
        "num_features": DYNAMIC_NUM_FEATURES,
        "max_gap_ms": MAX_GAP_MS,
        "min_valid_frames": MIN_VALID_FRAMES,
        "tolerance": 1e-4,
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
    c = data["cases"]
    if not np.allclose(c[0]["expected"], c[1]["expected"], atol=tol):
        raise AssertionError("Normalization is not scale/translation invariant")
    print(f"[OK] {len(c)} static normalization vectors valid (tol={tol}).")


def validate_model_space_vectors(path: Path = MODEL_SPACE_VECTORS_PATH) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} belum ada, jalankan dengan --regen")
    data = json.loads(path.read_text(encoding="utf-8"))
    tol = data["tolerance"]
    for case in data["cases"]:
        ms = to_model_space(case["input"], case["width"], case["height"], mirror_x=case["mirror_x"])
        norm = normalize_landmarks(ms)
        exp_ms = np.array(case["expected_model_space"], dtype=np.float32)
        exp_norm = np.array(case["expected_normalized"], dtype=np.float32)
        if not np.allclose(ms.reshape(-1), exp_ms, atol=tol):
            raise AssertionError(f"Model space mismatch on '{case['name']}'")
        if not np.allclose(norm, exp_norm, atol=tol):
            raise AssertionError(f"Model space normalized mismatch on '{case['name']}'")
    print(f"[OK] {len(data['cases'])} model_space vectors valid (tol={tol}).")


def validate_dynamic_vectors(path: Path = DYNAMIC_VECTORS_PATH) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{path} belum ada, jalankan dengan --regen")
    data = json.loads(path.read_text(encoding="utf-8"))
    tol = data["tolerance"]
    for case in data["cases"]:
        res = resample_window(case["timestamps_ms"], case["frames"], case["t_end_ms"])
        if not case["valid"]:
            if res is not None:
                raise AssertionError(f"Expected invalid window (None) for '{case['name']}'")
        else:
            if res is None:
                raise AssertionError(f"Expected valid window for '{case['name']}', got None")
            feat = dynamic_features(res)
            exp = np.array(case["expected_features"], dtype=np.float32)
            if feat.shape != (SEQUENCE_LENGTH, DYNAMIC_NUM_FEATURES) or not np.allclose(feat, exp, atol=tol):
                max_diff = float(np.max(np.abs(feat - exp)))
                raise AssertionError(f"Dynamic feature mismatch on '{case['name']}' (max_diff={max_diff})")
    print(f"[OK] {len(data['cases'])} dynamic feature vectors valid (tol={tol}).")


def _self_test_labels() -> None:
    static = load_labels(STATIC_LABELS_PATH)
    dynamic = load_labels(DYNAMIC_LABELS_PATH)
    assert static == [chr(c) for c in range(ord("A"), ord("Z") + 1)], "static labels must be A..Z"
    assert len(dynamic) >= 5, "dynamic labels must contain the 5 MVP words (+ optional _idle)"
    print(f"[OK] labels: static={len(static)} dynamic={len(dynamic)} {dynamic}")


if __name__ == "__main__":
    regen = "--regen" in sys.argv
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    if regen or not VECTORS_PATH.exists():
        VECTORS_PATH.write_text(json.dumps(generate_vectors(), indent=2), encoding="utf-8")
        print(f"[GEN] wrote {VECTORS_PATH.relative_to(ROOT)}")
    if regen or not MODEL_SPACE_VECTORS_PATH.exists():
        MODEL_SPACE_VECTORS_PATH.write_text(json.dumps(generate_model_space_vectors(), indent=2), encoding="utf-8")
        print(f"[GEN] wrote {MODEL_SPACE_VECTORS_PATH.relative_to(ROOT)}")
    if regen or not DYNAMIC_VECTORS_PATH.exists():
        DYNAMIC_VECTORS_PATH.write_text(json.dumps(generate_dynamic_vectors(), indent=2), encoding="utf-8")
        print(f"[GEN] wrote {DYNAMIC_VECTORS_PATH.relative_to(ROOT)}")
    validate_vectors()
    validate_model_space_vectors()
    validate_dynamic_vectors()
    _self_test_labels()
