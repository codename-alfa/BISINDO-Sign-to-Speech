package com.signtospeech.ml

import android.content.Context

/**
 * Classifier untuk kata dinamis BISINDO (LSTM sekuens).
 * Input: [1, 30, 66] float32 -> Output: [1, 6] probabilitas softmax (5 kata + _idle).
 * Jika model belum di-retrain ke shape [1, 30, 66], `isAvailable` bernilai false tanpa membuat aplikasi crash.
 */
class DynamicClassifier(
    context: Context,
    modelAssetPath: String = ModelConfig.DYNAMIC_MODEL_ASSET,
    labelsAssetPath: String = ModelConfig.DYNAMIC_LABELS_ASSET
) : TfliteClassifier(
    context = context,
    modelAssetPath = modelAssetPath,
    labelsAssetPath = labelsAssetPath,
    expectedInputShape = intArrayOf(
        1,
        ModelConfig.SEQUENCE_LENGTH,
        ModelConfig.DYNAMIC_NUM_FEATURES
    )
) {

    @Synchronized
    fun classify(sequence30x66: Array<FloatArray>): PredictionResult? {
        val interp = interpreter ?: return null
        if (!isAvailable || sequence30x66.size != ModelConfig.SEQUENCE_LENGTH) return null

        val input = arrayOf(sequence30x66)
        val output = Array(1) { FloatArray(labels.size) }

        val inferMs = measureMs {
            interp.run(input, output)
        }
        return buildPredictionResult(output[0], inferMs)
    }
}

