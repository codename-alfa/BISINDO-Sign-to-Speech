package com.signtospeech.ml

import com.google.mediapipe.tasks.components.containers.NormalizedLandmark
import kotlin.math.sqrt

/**
 * FeatureExtractor mengimplementasikan formula normalisasi koordinat 21 landmark MediaPipe:
 * - Titik acuan origin (0, 0, 0): Landmark 0 (Wrist)
 * - Skala normalisasi: Jarak Landmark 0 (Wrist) ke Landmark 9 (Middle Finger MCP)
 * Formula: P_norm = (P_landmark - P_wrist) / Distance(P_wrist, P_middle_mcp)
 * Menghasilkan vektor FloatArray berukuran 63 fitur (21 landmarks x 3 koordinat).
 */
object FeatureExtractor {

    fun extract(landmarks: List<NormalizedLandmark>): FloatArray {
        if (landmarks.size < 21) return FloatArray(63)

        val wrist = landmarks[0]
        val handSize = distance(landmarks[0], landmarks[9])
        val safeScale = if (handSize < 1e-4f) 1.0f else handSize

        val features = FloatArray(63)
        for (i in landmarks.indices) {
            val lm = landmarks[i]
            features[i * 3 + 0] = (lm.x() - wrist.x()) / safeScale
            features[i * 3 + 1] = (lm.y() - wrist.y()) / safeScale
            features[i * 3 + 2] = (lm.z() - wrist.z()) / safeScale
        }
        return features
    }

    private fun distance(p1: NormalizedLandmark, p2: NormalizedLandmark): Float {
        val dx = p1.x() - p2.x()
        val dy = p1.y() - p2.y()
        val dz = p1.z() - p2.z()
        return sqrt(dx * dx + dy * dy + dz * dz)
    }
}
