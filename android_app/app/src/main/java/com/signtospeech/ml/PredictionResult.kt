package com.signtospeech.ml

/**
 * Mode pengenalan aktif pada pipeline Arah 1 (Tuli -> Dengar).
 */
enum class RecognitionMode {
    LETTER, // Alfabet Statis A-Z (MLP 63 fitur)
    WORD    // Kata Dinamis (LSTM 30x66 fitur)
}

/**
 * Pasangan label dan probabilitas untuk tampilan utama maupun top-3 fallback suggestions.
 */
data class ScoredLabel(
    val label: String,
    val confidence: Float
)

/**
 * Hasil inferensi dari StaticClassifier atau DynamicClassifier.
 */
data class PredictionResult(
    val label: String,
    val confidence: Float,
    val top3: List<ScoredLabel>,
    val inferenceTimeMs: Float,
    val isConfident: Boolean = confidence >= ModelConfig.CONFIDENCE_THRESHOLD
) {
    val isIdleClass: Boolean
        get() = label.startsWith("_")
}

