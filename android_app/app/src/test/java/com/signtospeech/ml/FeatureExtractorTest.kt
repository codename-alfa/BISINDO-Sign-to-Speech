package com.signtospeech.ml

import com.google.mediapipe.tasks.components.containers.NormalizedLandmark
import org.junit.Assert.assertEquals
import org.junit.Test

class FeatureExtractorTest {

    @Test
    fun testExtractionShapeAndWristOrigin() {
        // Buat dummy 21 landmarks
        val dummyLandmarks = (0 until 21).map { i ->
            NormalizedLandmark.create(0.5f + i * 0.01f, 0.8f - i * 0.02f, i * 0.005f)
        }

        val features = FeatureExtractor.extract(dummyLandmarks)

        // 1. Ukuran harus tepat 63
        assertEquals(63, features.size)

        // 2. Koordinat wrist (index 0, 1, 2) harus bernilai 0.0f karena sebagai titik origin
        assertEquals(0.0f, features[0], 1e-5f)
        assertEquals(0.0f, features[1], 1e-5f)
        assertEquals(0.0f, features[2], 1e-5f)
    }
}
