package com.signtospeech.ml

/**
 * Ring buffer ber-timestamp untuk menyimpan sekuens koordinat tangan dalam model space (63 float/frame).
 * - Membuang entri yang lebih tua dari `windowMs + maxGapMs`.
 * - Me-reset otomatis jika terjadi jeda deteksi tangan > `maxGapMs`.
 */
class GestureBuffer(
    val windowMs: Long = ModelConfig.DYNAMIC_WINDOW_MS,
    val maxGapMs: Long = ModelConfig.MAX_GAP_MS
) {

    data class FrameEntry(
        val timestampMs: Long,
        val modelSpacePoints: FloatArray
    )

    private val entries = ArrayDeque<FrameEntry>()

    @Synchronized
    fun addFrame(timestampMs: Long, modelSpacePoints: FloatArray) {
        if (modelSpacePoints.size < FeatureExtractor.NUM_FEATURES) return

        // Validasi ukuran tangan tidak degeneratif dan bebas NaN
        for (v in modelSpacePoints) {
            if (v.isNaN()) {
                onNoHandDetected(timestampMs)
                return
            }
        }
        if (FeatureExtractor.handSizeOf(modelSpacePoints) < FeatureExtractor.MIN_HAND_SIZE) {
            onNoHandDetected(timestampMs)
            return
        }

        val lastTs = entries.lastOrNull()?.timestampMs
        if (lastTs != null && (timestampMs - lastTs > maxGapMs || timestampMs < lastTs)) {
            entries.clear()
        }

        entries.addLast(FrameEntry(timestampMs, modelSpacePoints.copyOf()))
        evictOldEntries(timestampMs)
    }

    @Synchronized
    fun onNoHandDetected(timestampMs: Long) {
        val lastTs = entries.lastOrNull()?.timestampMs ?: return
        if (timestampMs - lastTs > maxGapMs) {
            entries.clear()
        }
    }

    @Synchronized
    private fun evictOldEntries(currentTimestampMs: Long) {
        val minKeepTimestamp = currentTimestampMs - (windowMs + maxGapMs)
        while (entries.isNotEmpty() && entries.first().timestampMs < minKeepTimestamp) {
            entries.removeFirst()
        }
    }

    @Synchronized
    fun snapshot(): List<FrameEntry> = entries.toList()

    @Synchronized
    fun size(): Int = entries.size

    @Synchronized
    fun isEmpty(): Boolean = entries.isEmpty()

    @Synchronized
    fun clear() {
        entries.clear()
    }
}

