package com.signtospeech.ml

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class ModelSpaceTest {

    private fun readResourceText(resourceName: String): String {
        val stream = javaClass.classLoader?.getResourceAsStream(resourceName)
        assertNotNull("Resource $resourceName tidak ditemukan di classpath test", stream)
        return stream!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
    }

    @Test
    fun testModelSpaceParityAgainstPythonVectors() {
        val json = JSONObject(readResourceText("model_space_vectors.json"))
        val tolerance = json.getDouble("tolerance").toFloat()
        val cases = json.getJSONArray("cases")

        for (cIdx in 0 until cases.length()) {
            val caseObj = cases.getJSONObject(cIdx)
            val name = caseObj.getString("name")
            val width = caseObj.getInt("width")
            val height = caseObj.getInt("height")
            val mirrorX = caseObj.getBoolean("mirror_x")

            val inputArr = caseObj.getJSONArray("input")
            val rawPoints = FloatArray(63)
            for (i in 0 until 21) {
                val pt = inputArr.getJSONArray(i)
                rawPoints[i * 3 + 0] = pt.getDouble(0).toFloat()
                rawPoints[i * 3 + 1] = pt.getDouble(1).toFloat()
                rawPoints[i * 3 + 2] = pt.getDouble(2).toFloat()
            }

            val actualModelSpace = FeatureExtractor.toModelSpace(rawPoints, width, height, mirrorX)
            val actualNormalized = FeatureExtractor.extract(actualModelSpace)

            val expMs = caseObj.getJSONArray("expected_model_space")
            val expNorm = caseObj.getJSONArray("expected_normalized")

            for (j in 0 until 63) {
                assertEquals(
                    "ModelSpace mismatch pada '$name' indeks $j",
                    expMs.getDouble(j).toFloat(),
                    actualModelSpace[j],
                    tolerance
                )
                assertEquals(
                    "Normalized ModelSpace mismatch pada '$name' indeks $j",
                    expNorm.getDouble(j).toFloat(),
                    actualNormalized[j],
                    tolerance
                )
            }
        }
    }
}

