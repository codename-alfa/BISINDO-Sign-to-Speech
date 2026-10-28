package com.signtospeech.ml

import com.google.mediapipe.tasks.components.containers.NormalizedLandmark
import kotlin.math.sqrt

/**
 * FeatureExtractor mengimplementasikan:
 * 1. Transformasi `toModelSpace`: koreksi rasio aspek isotropik (width / height) & pencerminan sumbu X.
 * 2. Formula normalisasi koordinat 21 landmark MediaPipe (identik dengan `feature_utils.py`):
 *    - Titik acuan origin (0, 0, 0): Landmark 0 (Wrist)
 *    - Skala normalisasi: Jarak Landmark 0 (Wrist) ke Landmark 9 (Middle Finger MCP)
 *    - Formula: P_norm = (P_landmark - P_wrist) / Distance(P_wrist, P_middle_mcp)
 *    - Menghasilkan vektor FloatArray berukuran 63 fitur (21 landmarks x 3 koordinat).
 */
object FeatureExtractor {

    const val WRIST = 0
    const val MIDDLE_MCP = 9
    const val NUM_LANDMARKS = 21
    const val NUM_COORDS = 3
    const val NUM_FEATURES = NUM_LANDMARKS * NUM_COORDS // 63
    const val MIN_HAND_SIZE = 1e-6

    /**
     * Overload kompatibel untuk list NormalizedLandmark langsung dari MediaPipe.
     */
    fun extract(landmarks: List<NormalizedLandmark>): FloatArray {
        if (landmarks.size < NUM_LANDMARKS) return FloatArray(NUM_FEATURES)
        val raw = FloatArray(NUM_FEATURES)
        for (i in 0 until NUM_LANDMARKS) {
            val lm = landmarks[i]
            raw[i * 3 + 0] = lm.x()
            raw[i * 3 + 1] = lm.y()
            raw[i * 3 + 2] = lm.z()
        }
        return extract(raw)
    }

    /**
     * Normalisasi dari array float berukuran 63 (21 landmark x 3 koordinat [x, y, z]).
     * Menggunakan presisi Double secara internal agar 100% identik dengan numpy float64 di Python.
     */
    fun extract(points: FloatArray): FloatArray {
        if (points.size < NUM_FEATURES) return FloatArray(NUM_FEATURES)

        val wx = points[WRIST * 3 + 0].toDouble()
        val wy = points[WRIST * 3 + 1].toDouble()
        val wz = points[WRIST * 3 + 2].toDouble()

        val mx = points[MIDDLE_MCP * 3 + 0].toDouble()
        val my = points[MIDDLE_MCP * 3 + 1].toDouble()
        val mz = points[MIDDLE_MCP * 3 + 2].toDouble()

        val handSize = distance3d(wx, wy, wz, mx, my, mz)
        val safeScale = if (handSize < MIN_HAND_SIZE) 1.0 else handSize

        val features = FloatArray(NUM_FEATURES)
        for (i in 0 until NUM_LANDMARKS) {
            val px = points[i * 3 + 0].toDouble()
            val py = points[i * 3 + 1].toDouble()
            val pz = points[i * 3 + 2].toDouble()
            features[i * 3 + 0] = ((px - wx) / safeScale).toFloat()
            features[i * 3 + 1] = ((py - wy) / safeScale).toFloat()
            features[i * 3 + 2] = ((pz - wz) / safeScale).toFloat()
        }
        return features
    }

    /**
     * Konversi list NormalizedLandmark MediaPipe ke koordinat isotropik model space (FloatArray 63).
     */
    fun toModelSpace(
        landmarks: List<NormalizedLandmark>,
        width: Int,
        height: Int,
        mirrorX: Boolean = true
    ): FloatArray {
        if (landmarks.size < NUM_LANDMARKS) return FloatArray(NUM_FEATURES)
        val raw = FloatArray(NUM_FEATURES)
        for (i in 0 until NUM_LANDMARKS) {
            val lm = landmarks[i]
            raw[i * 3 + 0] = lm.x()
            raw[i * 3 + 1] = lm.y()
            raw[i * 3 + 2] = lm.z()
        }
        return toModelSpace(raw, width, height, mirrorX)
    }

    /**
     * Konversi koordinat ternormalisasi [x, y, z] x 21 ke koordinat isotropik model space:
     * - Jika mirrorX=true, x dicerminkan menjadi (1.0 - x) terlebih dahulu.
     * - Sumbu x dan z dikalikan rasio (width / height) agar proporsi tangan invarian terhadap aspek rasio frame.
     */
    fun toModelSpace(
        points: FloatArray,
        width: Int,
        height: Int,
        mirrorX: Boolean = true
    ): FloatArray {
        if (points.size < NUM_FEATURES) return FloatArray(NUM_FEATURES)
        val h = if (height > 0) height.toDouble() else 1.0
        val aspect = if (width > 0) width.toDouble() / h else 1.0

        val out = FloatArray(NUM_FEATURES)
        for (i in 0 until NUM_LANDMARKS) {
            val rawX = points[i * 3 + 0].toDouble()
            val rawY = points[i * 3 + 1].toDouble()
            val rawZ = points[i * 3 + 2].toDouble()

            val mirroredX = if (mirrorX) (1.0 - rawX) else rawX
            out[i * 3 + 0] = (mirroredX * aspect).toFloat()
            out[i * 3 + 1] = rawY.toFloat()
            out[i * 3 + 2] = (rawZ * aspect).toFloat()
        }
        return out
    }

    internal fun handSizeOf(points: FloatArray): Double {
        if (points.size < NUM_FEATURES) return 0.0
        return distance3d(
            points[WRIST * 3 + 0].toDouble(),
            points[WRIST * 3 + 1].toDouble(),
            points[WRIST * 3 + 2].toDouble(),
            points[MIDDLE_MCP * 3 + 0].toDouble(),
            points[MIDDLE_MCP * 3 + 1].toDouble(),
            points[MIDDLE_MCP * 3 + 2].toDouble()
        )
    }

    private fun distance3d(
        x1: Double, y1: Double, z1: Double,
        x2: Double, y2: Double, z2: Double
    ): Double {
        val dx = x1 - x2
        val dy = y1 - y2
        val dz = z1 - z2
        return sqrt(dx * dx + dy * dy + dz * dz)
    }
}
