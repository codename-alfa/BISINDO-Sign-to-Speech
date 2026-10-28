package com.signtospeech.ml

import android.content.Context

/**
 * Classifier untuk alfabet statis BISINDO A-Z.
 * Input: [1, 63] float32 -> Output: [1, 26] probabilitas softmax.
 */
class StaticClassifier(
    context: Context,
    modelAssetPath: String = ModelConfig.STATIC_MODEL_ASSET,
    labelsAssetPath: String = ModelConfig.STATIC_LABELS_ASSET
) : TfliteClassifier(
    context = context,
    modelAssetPath = modelAssetPath,
    labelsAssetPath = labelsAssetPath,
    expectedInputShape = intArrayOf(1, ModelConfig.STATIC_NUM_FEATURES)
) {

    @Synchronized
    fun classify(features63: FloatArray): PredictionResult? {
        val interp = interpreter ?: return null
        if (!isAvailable || features63.size < ModelConfig.STATIC_NUM_FEATURES) return null

        val input = arrayOf(features63.copyOf(ModelConfig.STATIC_NUM_FEATURES))
        val output = Array(1) { FloatArray(labels.size) }

        val inferMs = measureMs {
            interp.run(input, output)
        }
        return buildPredictionResult(output[0], inferMs)
    }
}

