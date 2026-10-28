package com.signtospeech.ml

import kotlin.math.max
import kotlin.math.min

/**
 * DynamicFeatureBuilder adalah port 1:1 dari `resample_window` + `dynamic_features` di `feature_utils.py`.
 * Menghasilkan matriks fitur berukuran [30][66] (63 bentuk tangan + dx, dy lintasan wrist + ds perubahan skala)
 * atau `null` jika jendela waktu tidak memenuhi syarat validitas.
 */
object DynamicFeatureBuilder {

    /**
     * Resample rekaman ber-timestamp pada jendela [tEndMs - windowMs, tEndMs]
     * menjadi 30 frame koordinat model space (masing-masing 63 float), atau null jika invalid.
     */
    fun resampleWindow(
        timestampsMs: DoubleArray,
        frames: Array<FloatArray>,
        tEndMs: Double,
        windowMs: Int = ModelConfig.DYNAMIC_WINDOW_MS.toInt(),
        seqLen: Int = ModelConfig.SEQUENCE_LENGTH,
        maxGapMs: Int = ModelConfig.MAX_GAP_MS.toInt(),
        minValidFrames: Int = ModelConfig.MIN_VALID_FRAMES
    ): Array<FloatArray>? {
        if (timestampsMs.isEmpty() || timestampsMs.size != frames.size) return null

        val tStart = tEndMs - windowMs.toDouble()
        val eps = 1e-6

        val validPairs = ArrayList<Pair<Double, FloatArray>>(timestampsMs.size)
        for (i in timestampsMs.indices) {
            val tVal = timestampsMs[i]
            if (tVal < tStart - eps || tVal > tEndMs + eps) continue

            val pts = frames[i]
            if (pts.size < FeatureExtractor.NUM_FEATURES) continue
            var hasNaN = false
            for (v in pts) {
                if (v.isNaN()) {
                    hasNaN = true
                    break
                }
            }
            if (hasNaN) continue
            if (FeatureExtractor.handSizeOf(pts) < FeatureExtractor.MIN_HAND_SIZE) continue

            validPairs.add(Pair(tVal, pts))
        }

        if (validPairs.size < minValidFrames) return null

        validPairs.sortBy { it.first }
        val m = validPairs.size
        val vTs = DoubleArray(m) { validPairs[it].first }
        val vPts = Array(m) { validPairs[it].second }

        // Cek gap di awal jendela, akhir jendela, dan antar-frame berurutan
        if ((vTs[0] - tStart) > maxGapMs + eps) return null
        if ((tEndMs - vTs[m - 1]) > maxGapMs + eps) return null
        for (i in 0 until m - 1) {
            if ((vTs[i + 1] - vTs[i]) > maxGapMs + eps) return null
        }

        val out = Array(seqLen) { FloatArray(FeatureExtractor.NUM_FEATURES) }
        val step = if (seqLen > 1) windowMs.toDouble() / (seqLen - 1).toDouble() else 0.0

        for (k in 0 until seqLen) {
            val tk = tStart + k * step
            when {
                tk <= vTs[0] -> {
                    vPts[0].copyInto(out[k], 0, 0, FeatureExtractor.NUM_FEATURES)
                }
                tk >= vTs[m - 1] -> {
                    vPts[m - 1].copyInto(out[k], 0, 0, FeatureExtractor.NUM_FEATURES)
                }
                else -> {
                    // Cari indeks i terbesar sehingga vTs[i] <= tk
                    var idx = 0
                    for (i in 0 until m - 1) {
                        if (vTs[i] <= tk) {
                            idx = i
                        } else {
                            break
                        }
                    }
                    idx = max(0, min(idx, m - 2))
                    val t0 = vTs[idx]
                    val t1 = vTs[idx + 1]
                    val dt = t1 - t0
                    val alpha = if (dt < 1e-9) 0.0 else (tk - t0) / dt
                    val oneMinusAlpha = 1.0 - alpha
                    val p0 = vPts[idx]
                    val p1 = vPts[idx + 1]
                    val target = out[k]
                    for (j in 0 until FeatureExtractor.NUM_FEATURES) {
                        target[j] = (oneMinusAlpha * p0[j].toDouble() + alpha * p1[j].toDouble()).toFloat()
                    }
                }
            }
        }
        return out
    }

    /**
     * Ekstrak fitur (30, 66) dari jendela ter-resample (30, 63).
     */
    fun computeDynamicFeatures(resampledWindow: Array<FloatArray>): Array<FloatArray> {
        val seqLen = resampledWindow.size
        require(seqLen == ModelConfig.SEQUENCE_LENGTH) {
            "Expected ${ModelConfig.SEQUENCE_LENGTH} frames, got $seqLen"
        }

        val shapes = Array(seqLen) { FloatArray(FeatureExtractor.NUM_FEATURES) }
        val sizes = DoubleArray(seqLen)

        for (t in 0 until seqLen) {
            val pts = resampledWindow[t]
            val sz = FeatureExtractor.handSizeOf(pts)
            val safeSz = if (sz >= FeatureExtractor.MIN_HAND_SIZE) sz else 1.0
            sizes[t] = safeSz
            shapes[t] = FeatureExtractor.extract(pts)
        }

        var sumSize = 0.0
        for (sz in sizes) sumSize += sz
        var meanSize = sumSize / seqLen.toDouble()
        if (meanSize < FeatureExtractor.MIN_HAND_SIZE) meanSize = 1.0

        val firstSize = if (sizes[0] >= FeatureExtractor.MIN_HAND_SIZE) sizes[0] else 1.0
        val w0x = resampledWindow[0][FeatureExtractor.WRIST * 3 + 0].toDouble()
        val w0y = resampledWindow[0][FeatureExtractor.WRIST * 3 + 1].toDouble()

        val result = Array(seqLen) { FloatArray(ModelConfig.DYNAMIC_NUM_FEATURES) }
        for (t in 0 until seqLen) {
            val row = result[t]
            shapes[t].copyInto(row, 0, 0, FeatureExtractor.NUM_FEATURES)

            val wtx = resampledWindow[t][FeatureExtractor.WRIST * 3 + 0].toDouble()
            val wty = resampledWindow[t][FeatureExtractor.WRIST * 3 + 1].toDouble()

            val dx = (wtx - w0x) / meanSize
            val dy = (wty - w0y) / meanSize
            val ds = (sizes[t] / firstSize) - 1.0

            row[63] = dx.toFloat()
            row[64] = dy.toFloat()
            row[65] = ds.toFloat()
        }
        return result
    }

    /**
     * Helper langsung dari GestureBuffer pada timestamp evaluasi `tEndMs`.
     */
    fun buildFromBuffer(
        buffer: GestureBuffer,
        tEndMs: Long,
        windowMs: Int = buffer.windowMs.toInt(),
        seqLen: Int = ModelConfig.SEQUENCE_LENGTH,
        maxGapMs: Int = buffer.maxGapMs.toInt(),
        minValidFrames: Int = ModelConfig.MIN_VALID_FRAMES
    ): Array<FloatArray>? {
        val entries = buffer.snapshot()
        if (entries.size < minValidFrames) return null

        val ts = DoubleArray(entries.size) { entries[it].timestampMs.toDouble() }
        val frames = Array(entries.size) { entries[it].modelSpacePoints }

        val resampled = resampleWindow(
            timestampsMs = ts,
            frames = frames,
            tEndMs = tEndMs.toDouble(),
            windowMs = windowMs,
            seqLen = seqLen,
            maxGapMs = maxGapMs,
            minValidFrames = minValidFrames
        ) ?: return null

        return computeDynamicFeatures(resampled)
    }
}

