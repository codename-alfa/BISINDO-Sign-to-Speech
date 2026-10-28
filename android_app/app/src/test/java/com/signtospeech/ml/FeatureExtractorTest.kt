package com.signtospeech.ml

import com.google.mediapipe.tasks.components.containers.NormalizedLandmark
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class FeatureExtractorTest {

    private fun readResourceText(resourceName: String): String {
        val stream = javaClass.classLoader?.getResourceAsStream(resourceName)
        assertNotNull("Resource $resourceName tidak ditemukan di classpath test", stream)
        return stream!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
    }

    @Test
    fun testParityAgainstPythonNormalizationVectorsJson() {
        val json = JSONObject(readResourceText("normalization_vectors.json"))
        val tolerance = json.getDouble("tolerance").toFloat()
        val cases = json.getJSONArray("cases")

        assertEquals(3, cases.length())

        for (cIdx in 0 until cases.length()) {
            val caseObj = cases.getJSONObject(cIdx)
            val name = caseObj.getString("name")
            val inputArr = caseObj.getJSONArray("input")
            val expectedArr = caseObj.getJSONArray("expected")

            val landmarks = (0 until inputArr.length()).map { i ->
                val pt = inputArr.getJSONArray(i)
                NormalizedLandmark.create(
                    pt.getDouble(0).toFloat(),
                    pt.getDouble(1).toFloat(),
                    pt.getDouble(2).toFloat()
                )
            }

            val actual = FeatureExtractor.extract(landmarks)
            assertEquals("Ukuran fitur salah pada '$name'", 63, actual.size)

            for (j in 0 until expectedArr.length()) {
                val exp = expectedArr.getDouble(j).toFloat()
                assertEquals(
                    "Mismatch pada kasus '$name' indeks $j",
                    exp,
                    actual[j],
                    tolerance
                )
            }
        }
    }

    @Test
    fun testExtractionShapeAndWristOrigin() {
        val dummyLandmarks = (0 until 21).map { i ->
            NormalizedLandmark.create(0.5f + i * 0.01f, 0.8f - i * 0.02f, i * 0.005f)
        }

        val features = FeatureExtractor.extract(dummyLandmarks)
        assertEquals(63, features.size)
        assertEquals(0.0f, features[0], 1e-5f)
        assertEquals(0.0f, features[1], 1e-5f)
        assertEquals(0.0f, features[2], 1e-5f)
    }

    @Test
    fun testZeroDivisionGuardAndShortInput() {
        // Input kurang dari 21 landmark -> aman mengembalikan vektor nol 63 elemen
        val emptyFeatures = FeatureExtractor.extract(emptyList())
        assertEquals(63, emptyFeatures.size)
        for (v in emptyFeatures) {
            assertEquals(0.0f, v, 1e-6f)
        }

        // Semua titik bertumpuk di (0.5, 0.5, 0.0) -> jarak wrist ke middle_mcp = 0 -> tidak NaN / Infinity
        val degenerate = (0 until 21).map {
            NormalizedLandmark.create(0.5f, 0.5f, 0.0f)
        }
        val degFeatures = FeatureExtractor.extract(degenerate)
        assertEquals(63, degFeatures.size)
        for (v in degFeatures) {
            assertEquals(0.0f, v, 1e-6f)
        }
    }
}
