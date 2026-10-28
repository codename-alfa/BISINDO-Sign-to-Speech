package com.signtospeech.ml

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class DynamicFeatureBuilderTest {

    private fun readResourceText(resourceName: String): String {
        val stream = javaClass.classLoader?.getResourceAsStream(resourceName)
        assertNotNull("Resource $resourceName tidak ditemukan di classpath test", stream)
        return stream!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
    }

    @Test
    fun testDynamicFeaturesParityAgainstPythonVectors() {
        val json = JSONObject(readResourceText("dynamic_feature_vectors.json"))
        val tolerance = json.getDouble("tolerance").toFloat()
        val windowMs = json.getInt("window_ms")
        val seqLen = json.getInt("sequence_length")
        val numFeatures = json.getInt("num_features")
        val maxGapMs = json.getInt("max_gap_ms")
        val minValidFrames = json.getInt("min_valid_frames")

        val cases = json.getJSONArray("cases")
        assertEquals(4, cases.length())

        for (cIdx in 0 until cases.length()) {
            val caseObj = cases.getJSONObject(cIdx)
            val name = caseObj.getString("name")
            val tEndMs = caseObj.getDouble("t_end_ms")
            val isValid = caseObj.getBoolean("valid")

            val tsJson = caseObj.getJSONArray("timestamps_ms")
            val framesJson = caseObj.getJSONArray("frames")

            val timestampsMs = DoubleArray(tsJson.length()) { tsJson.getDouble(it) }
            val frames = Array(framesJson.length()) { fIdx ->
                val ptsJson = framesJson.getJSONArray(fIdx)
                val flat = FloatArray(63)
                for (lmIdx in 0 until 21) {
                    val coord = ptsJson.getJSONArray(lmIdx)
                    flat[lmIdx * 3 + 0] = coord.getDouble(0).toFloat()
                    flat[lmIdx * 3 + 1] = coord.getDouble(1).toFloat()
                    flat[lmIdx * 3 + 2] = coord.getDouble(2).toFloat()
                }
                flat
            }

            val resampled = DynamicFeatureBuilder.resampleWindow(
                timestampsMs = timestampsMs,
                frames = frames,
                tEndMs = tEndMs,
                windowMs = windowMs,
                seqLen = seqLen,
                maxGapMs = maxGapMs,
                minValidFrames = minValidFrames
            )

            if (!isValid) {
                assertNull("Kasus '$name' seharusnya ditolak (null)", resampled)
            } else {
                assertNotNull("Kasus '$name' seharusnya valid (bukan null)", resampled)
                val features = DynamicFeatureBuilder.computeDynamicFeatures(resampled!!)
                assertEquals(seqLen, features.size)
                assertEquals(numFeatures, features[0].size)

                val expMatrix = caseObj.getJSONArray("expected_features")
                for (t in 0 until seqLen) {
                    val expRow = expMatrix.getJSONArray(t)
                    for (f in 0 until numFeatures) {
                        val expectedVal = expRow.getDouble(f).toFloat()
                        assertEquals(
                            "Mismatch fitur dinamis pada '$name' [t=$t, f=$f]",
                            expectedVal,
                            features[t][f],
                            tolerance
                        )
                    }
                }
            }
        }
    }
}

