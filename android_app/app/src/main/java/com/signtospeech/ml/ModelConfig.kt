package com.signtospeech.ml

/**
 * Konfigurasi konstanta kontrak model ML & parser metadata JSON model dinamis.
 */
object ModelConfig {
    const val CONFIDENCE_THRESHOLD = 0.70f
    const val MIRROR_X_FOR_MODEL = true

    const val STATIC_NUM_FEATURES = 63
    const val DYNAMIC_NUM_FEATURES = 66
    const val SEQUENCE_LENGTH = 30

    const val DYNAMIC_WINDOW_MS = 1500L
    const val DYNAMIC_HOP_MS = 200L
    const val MAX_GAP_MS = 300L
    const val MIN_VALID_FRAMES = 5

    // Stabilizer parameters
    const val STATIC_MIN_CONSISTENT_FRAMES = 3
    const val STATIC_MIN_HOLD_MS = 400L
    const val DYNAMIC_MIN_CONSISTENT_EVALS = 2
    const val DYNAMIC_COOLDOWN_MS = 1000L
    const val SAME_LABEL_RECOMMIT_COOLDOWN_MS = 2000L

    const val STATIC_MODEL_ASSET = "static_model.tflite"
    const val STATIC_LABELS_ASSET = "static_labels.txt"
    const val DYNAMIC_MODEL_ASSET = "dynamic_model.tflite"
    const val DYNAMIC_LABELS_ASSET = "dynamic_labels.txt"
    const val DYNAMIC_META_ASSET = "dynamic_model_meta.json"

    /**
     * Peta pasangan Huruf <-> Angka SIBI (dan huruf mirip) yang memiliki bentuk jari sangat berdekatan.
     * Digunakan oleh fitur Interactive Quick Suggestion agar user Tuli dapat mengoreksi mandiri
     * dengan 1 ketukan jika terjadi ketertukaran antara huruf dan angka.
     */
    val SIBI_CONFUSABLE_ALTERNATIVES: Map<String, List<String>> = mapOf(
        "D" to listOf("1", "Z"),
        "1" to listOf("D", "I"),
        "V" to listOf("2", "K", "U"),
        "2" to listOf("V", "K", "U"),
        "W" to listOf("6", "3"),
        "6" to listOf("W", "3"),
        "3" to listOf("W", "6"),
        "B" to listOf("4", "5"),
        "4" to listOf("B", "5"),
        "5" to listOf("B", "4"),
        "F" to listOf("9", "O"),
        "9" to listOf("F", "O"),
        "I" to listOf("J", "1", "10"),
        "J" to listOf("I", "10"),
        "A" to listOf("S", "10", "T"),
        "10" to listOf("A", "I", "S"),
        "7" to listOf("8", "W"),
        "8" to listOf("7", "W"),
        "M" to listOf("N", "T"),
        "N" to listOf("M", "T"),
        "U" to listOf("R", "V", "2"),
        "R" to listOf("U", "V"),
        "K" to listOf("P", "V", "2"),
        "G" to listOf("Q", "H"),
        "H" to listOf("G", "U")
    )

    /**
     * Menghasilkan daftar kandidat Quick Suggestion (maksimal 3 alternatif unik di luar label utama)
     * yang menggabungkan prediksi Top-3 model dan pasangan identik Huruf <-> Angka SIBI.
     */
    fun resolveQuickSuggestions(primaryLabel: String, top3: List<ScoredLabel>): List<String> {
        val suggestions = LinkedHashSet<String>()
        for (item in top3) {
            if (item.label != primaryLabel && !item.label.startsWith("_") && item.confidence >= 0.05f) {
                suggestions.add(item.label)
            }
        }
        SIBI_CONFUSABLE_ALTERNATIVES[primaryLabel]?.forEach { alt ->
            if (alt != primaryLabel) {
                suggestions.add(alt)
            }
        }
        return suggestions.take(3)
    }

    data class DynamicModelMeta(
        val schemaVersion: Int = 2,
        val windowMs: Long = DYNAMIC_WINDOW_MS,
        val hopMs: Long = DYNAMIC_HOP_MS,
        val sequenceLength: Int = SEQUENCE_LENGTH,
        val numFeatures: Int = DYNAMIC_NUM_FEATURES,
        val maxGapMs: Long = MAX_GAP_MS,
        val minValidFrames: Int = MIN_VALID_FRAMES,
        val valAccuracy: Float = 0f,
        val isBootstrapSynthetic: Boolean = false
    )

    /**
     * Parser ringan tanpa ketergantungan Android SDK agar dapat dipanggil di JVM unit test maupun runtime.
     */
    fun parseDynamicMeta(jsonText: String): DynamicModelMeta {
        fun extractInt(key: String, default: Int): Int {
            val regex = Regex(""""$key"\s*:\s*(-?\d+)""")
            return regex.find(jsonText)?.groupValues?.get(1)?.toIntOrNull() ?: default
        }
        fun extractFloat(key: String, default: Float): Float {
            val regex = Regex(""""$key"\s*:\s*(-?\d+(?:\.\d+)?)""")
            return regex.find(jsonText)?.groupValues?.get(1)?.toFloatOrNull() ?: default
        }
        fun extractBool(key: String, default: Boolean): Boolean {
            val regex = Regex(""""$key"\s*:\s*(true|false)""")
            return regex.find(jsonText)?.groupValues?.get(1)?.toBooleanStrictOrNull() ?: default
        }

        return DynamicModelMeta(
            schemaVersion = extractInt("schema_version", 2),
            windowMs = extractInt("window_ms", DYNAMIC_WINDOW_MS.toInt()).toLong(),
            hopMs = extractInt("hop_ms", DYNAMIC_HOP_MS.toInt()).toLong(),
            sequenceLength = extractInt("sequence_length", SEQUENCE_LENGTH),
            numFeatures = extractInt("num_features", DYNAMIC_NUM_FEATURES),
            maxGapMs = extractInt("max_gap_ms", MAX_GAP_MS.toInt()).toLong(),
            minValidFrames = extractInt("min_valid_frames", MIN_VALID_FRAMES),
            valAccuracy = extractFloat("val_accuracy", 0f),
            isBootstrapSynthetic = extractBool("is_bootstrap_synthetic", false)
        )
    }
}

