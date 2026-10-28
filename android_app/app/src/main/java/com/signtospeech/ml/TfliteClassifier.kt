package com.signtospeech.ml

import android.content.Context
import android.os.SystemClock
import android.util.Log
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.support.common.FileUtil

/**
 * Base class Strategy Pattern untuk TFLite Classifier (Static MLP & Dynamic LSTM).
 * Selalu berjalan pada CPU (numThreads = 2) karena ukuran model mikro (<150 KB),
 * memetakan file model via mmap, dan memvalidasi dimensi tensor saat inisialisasi.
 */
abstract class TfliteClassifier(
    context: Context,
    val modelAssetPath: String,
    val labelsAssetPath: String,
    expectedInputShape: IntArray,
    numThreads: Int = 2
) : AutoCloseable {

    protected var interpreter: Interpreter? = null
    val labels: List<String>

    var isAvailable: Boolean = false
        protected set

    var unavailableReason: String? = null
        protected set

    init {
        val loadedLabels = try {
            context.assets.open(labelsAssetPath).bufferedReader().useLines { lines ->
                lines.map { it.trim() }.filter { it.isNotEmpty() }.toList()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Gagal memuat label dari $labelsAssetPath: ${e.message}", e)
            emptyList()
        }
        labels = loadedLabels

        try {
            if (labels.isEmpty()) {
                throw IllegalStateException("Daftar label kosong pada $labelsAssetPath")
            }

            val mappedBuffer = FileUtil.loadMappedFile(context, modelAssetPath)
            val options = Interpreter.Options().apply {
                setNumThreads(numThreads)
            }
            val interp = Interpreter(mappedBuffer, options)
            interp.allocateTensors()

            val inShape = interp.getInputTensor(0).shape()
            val outShape = interp.getOutputTensor(0).shape()

            if (!inShape.contentEquals(expectedInputShape)) {
                interp.close()
                unavailableReason =
                    "Shape input $modelAssetPath ${inShape.contentToString()} != ekspektasi ${expectedInputShape.contentToString()}"
                Log.w(TAG, unavailableReason ?: "")
            } else if (outShape.size != 2 || outShape[0] != 1 || outShape[1] != labels.size) {
                interp.close()
                unavailableReason =
                    "Shape output $modelAssetPath ${outShape.contentToString()} != [1, ${labels.size}]"
                Log.w(TAG, unavailableReason ?: "")
            } else {
                interpreter = interp
                isAvailable = true
                Log.d(
                    TAG,
                    "Berhasil memuat $modelAssetPath (in=${inShape.contentToString()}, out=${outShape.contentToString()})"
                )
            }
        } catch (e: Exception) {
            unavailableReason = "Gagal memuat $modelAssetPath: ${e.message}"
            Log.e(TAG, unavailableReason ?: "", e)
        }
    }

    protected fun buildPredictionResult(
        probabilities: FloatArray,
        inferenceTimeMs: Float
    ): PredictionResult {
        val indexed = probabilities.mapIndexed { idx, prob ->
            val label = labels.getOrElse(idx) { "?$idx" }
            ScoredLabel(label, prob)
        }.sortedByDescending { it.confidence }

        val top1 = indexed.firstOrNull() ?: ScoredLabel("-", 0f)
        val top3 = indexed.filter { !it.label.startsWith("_") }.take(3)

        return PredictionResult(
            label = top1.label,
            confidence = top1.confidence,
            top3 = top3,
            inferenceTimeMs = inferenceTimeMs
        )
    }

    protected inline fun measureMs(block: () -> Unit): Float {
        val t0 = SystemClock.elapsedRealtimeNanos()
        block()
        val elapsedNs = (SystemClock.elapsedRealtimeNanos() - t0).coerceAtLeast(0L)
        return elapsedNs / 1_000_000f
    }

    @Synchronized
    override fun close() {
        try {
            interpreter?.close()
        } catch (e: Exception) {
            Log.w(TAG, "Error saat menutup interpreter $modelAssetPath: ${e.message}")
        } finally {
            interpreter = null
            isAvailable = false
        }
    }

    companion object {
        private const val TAG = "TfliteClassifier"
    }
}

