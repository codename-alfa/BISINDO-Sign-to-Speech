package com.signtospeech.pipeline

import android.content.Context
import android.util.Log
import com.google.mediapipe.tasks.components.containers.NormalizedLandmark
import com.signtospeech.mediapipe.DelegateMode
import com.signtospeech.ml.DynamicClassifier
import com.signtospeech.ml.DynamicFeatureBuilder
import com.signtospeech.ml.FeatureExtractor
import com.signtospeech.ml.GestureBuffer
import com.signtospeech.ml.ModelConfig
import com.signtospeech.ml.PredictionResult
import com.signtospeech.ml.PredictionStabilizer
import com.signtospeech.ml.RecognitionMode
import com.signtospeech.ml.StaticClassifier
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Orkestrator pipeline Arah 1 (Tuli -> Dengar) yang berjalan pada single-thread inference executor
 * terpisah dari UI thread:
 * 1. Mengonversi landmark ke koordinat isotropik model space (`FeatureExtractor.toModelSpace`).
 * 2. Menjalankan `StaticClassifier` (Mode Huruf) atau `GestureBuffer` + `DynamicFeatureBuilder` + `DynamicClassifier` (Mode Kata).
 * 3. Menyaring prediksi melalui `PredictionStabilizer` (>= 70%, bebas flicker & bebas trigger `_idle`).
 * 4. Mengirimkan `UiState` dan callback `onCommitted(label)` ke UI/TTS.
 */
class TranslationPipeline(
    context: Context,
    private val onStateUpdated: (UiState) -> Unit,
    private val onCommitted: (String, RecognitionMode) -> Unit
) : AutoCloseable {

    data class UiState(
        val mode: RecognitionMode,
        val handDetected: Boolean,
        val currentResult: PredictionResult?,
        val committedTranscript: List<String>,
        val lastCommittedLabel: String?,
        val mediaPipeMs: Long,
        val classifierMs: Float,
        val activeDelegate: DelegateMode,
        val bufferFrames: Int,
        val dynamicModelReady: Boolean,
        val dynamicStatusNote: String?
    )

    private val inferenceExecutor: ExecutorService = Executors.newSingleThreadExecutor()

    private val staticClassifier = StaticClassifier(context)
    private val dynamicClassifier = DynamicClassifier(context)
    private val dynamicMeta: ModelConfig.DynamicModelMeta = loadMeta(context)

    private val gestureBuffer = GestureBuffer(
        windowMs = dynamicMeta.windowMs,
        maxGapMs = dynamicMeta.maxGapMs
    )
    private val stabilizer = PredictionStabilizer()
    private val transcript = ArrayDeque<String>()

    @Volatile
    var currentMode: RecognitionMode = RecognitionMode.LETTER
        private set

    @Volatile
    private var lastDynamicEvalMs: Long = 0L

    @Volatile
    private var lastDynamicResult: PredictionResult? = null

    val isDynamicAvailable: Boolean
        get() = dynamicClassifier.isAvailable

    val dynamicUnavailableReason: String?
        get() = dynamicClassifier.unavailableReason

    private fun loadMeta(context: Context): ModelConfig.DynamicModelMeta {
        return try {
            val text = context.assets.open(ModelConfig.DYNAMIC_META_ASSET).bufferedReader().use { it.readText() }
            ModelConfig.parseDynamicMeta(text)
        } catch (e: Exception) {
            Log.i(TAG, "Menggunakan default DynamicModelMeta (${e.message})")
            ModelConfig.DynamicModelMeta()
        }
    }

    fun setMode(newMode: RecognitionMode) {
        if (newMode == currentMode) return
        currentMode = newMode
        inferenceExecutor.execute {
            gestureBuffer.clear()
            stabilizer.reset()
            lastDynamicEvalMs = 0L
            lastDynamicResult = null
        }
    }

    fun onContextReset() {
        inferenceExecutor.execute {
            gestureBuffer.clear()
            stabilizer.reset()
            lastDynamicEvalMs = 0L
            lastDynamicResult = null
        }
    }

    fun clearTranscript() {
        inferenceExecutor.execute {
            transcript.clear()
            stabilizer.resetAllIncludingHistory()
        }
    }

    fun processLandmarks(
        landmarks: List<NormalizedLandmark>?,
        imageWidth: Int,
        imageHeight: Int,
        isFrontCamera: Boolean,
        frameTimestampMs: Long,
        mediaPipeMs: Long,
        activeDelegate: DelegateMode
    ) {
        if (inferenceExecutor.isShutdown) return

        inferenceExecutor.execute {
            val mode = currentMode
            val hasHand = landmarks != null && landmarks.size >= FeatureExtractor.NUM_LANDMARKS

            if (!hasHand || landmarks == null) {
                gestureBuffer.onNoHandDetected(frameTimestampMs)
                stabilizer.onNoHand()
                lastDynamicResult = null
                onStateUpdated(
                    UiState(
                        mode = mode,
                        handDetected = false,
                        currentResult = null,
                        committedTranscript = transcript.toList(),
                        lastCommittedLabel = transcript.lastOrNull(),
                        mediaPipeMs = mediaPipeMs,
                        classifierMs = 0f,
                        activeDelegate = activeDelegate,
                        bufferFrames = gestureBuffer.size(),
                        dynamicModelReady = dynamicClassifier.isAvailable,
                        dynamicStatusNote = dynamicClassifier.unavailableReason
                    )
                )
                return@execute
            }

            // Mirror X untuk menyamakan kamera depan dengan selfie view saat training
            val mirrorX = isFrontCamera && ModelConfig.MIRROR_X_FOR_MODEL
            val modelSpacePts = FeatureExtractor.toModelSpace(
                landmarks = landmarks,
                width = imageWidth,
                height = imageHeight,
                mirrorX = mirrorX
            )

            when (mode) {
                RecognitionMode.LETTER -> {
                    val features63 = FeatureExtractor.extract(modelSpacePts)
                    val rawPred = staticClassifier.classify(features63)
                    val stabOut = stabilizer.update(RecognitionMode.LETTER, rawPred, frameTimestampMs)

                    if (stabOut.committedLabel != null) {
                        appendTranscript(stabOut.committedLabel)
                        onCommitted(stabOut.committedLabel, RecognitionMode.LETTER)
                    }

                    onStateUpdated(
                        UiState(
                            mode = mode,
                            handDetected = true,
                            currentResult = rawPred,
                            committedTranscript = transcript.toList(),
                            lastCommittedLabel = transcript.lastOrNull(),
                            mediaPipeMs = mediaPipeMs,
                            classifierMs = rawPred?.inferenceTimeMs ?: 0f,
                            activeDelegate = activeDelegate,
                            bufferFrames = 1,
                            dynamicModelReady = dynamicClassifier.isAvailable,
                            dynamicStatusNote = null
                        )
                    )
                }

                RecognitionMode.WORD -> {
                    if (!dynamicClassifier.isAvailable) {
                        onStateUpdated(
                            UiState(
                                mode = mode,
                                handDetected = true,
                                currentResult = null,
                                committedTranscript = transcript.toList(),
                                lastCommittedLabel = transcript.lastOrNull(),
                                mediaPipeMs = mediaPipeMs,
                                classifierMs = 0f,
                                activeDelegate = activeDelegate,
                                bufferFrames = 0,
                                dynamicModelReady = false,
                                dynamicStatusNote = dynamicClassifier.unavailableReason
                                    ?: "Model kata dinamis belum tersedia"
                            )
                        )
                        return@execute
                    }

                    gestureBuffer.addFrame(frameTimestampMs, modelSpacePts)

                    val dueForEval = (frameTimestampMs - lastDynamicEvalMs) >= dynamicMeta.hopMs
                    var currentPred = lastDynamicResult

                    if (dueForEval) {
                        val seq30x66 = DynamicFeatureBuilder.buildFromBuffer(
                            buffer = gestureBuffer,
                            tEndMs = frameTimestampMs,
                            windowMs = dynamicMeta.windowMs.toInt(),
                            seqLen = dynamicMeta.sequenceLength,
                            maxGapMs = dynamicMeta.maxGapMs.toInt(),
                            minValidFrames = dynamicMeta.minValidFrames
                        )

                        if (seq30x66 != null) {
                            lastDynamicEvalMs = frameTimestampMs
                            currentPred = dynamicClassifier.classify(seq30x66)
                            lastDynamicResult = currentPred

                            val stabOut = stabilizer.update(
                                mode = RecognitionMode.WORD,
                                result = currentPred,
                                timestampMs = frameTimestampMs
                            )

                            if (stabOut.shouldClearBuffer) {
                                gestureBuffer.clear()
                                lastDynamicResult = null
                            }

                            if (stabOut.committedLabel != null) {
                                appendTranscript(stabOut.committedLabel)
                                onCommitted(stabOut.committedLabel, RecognitionMode.WORD)
                            }
                        }
                    }

                    val note = if (gestureBuffer.size() < dynamicMeta.minValidFrames) {
                        "Mengumpulkan sekuens (${gestureBuffer.size()}/${dynamicMeta.minValidFrames}+ frame)..."
                    } else if (dynamicMeta.isBootstrapSynthetic) {
                        "Model Kata Bootstrap Aktif"
                    } else {
                        null
                    }

                    onStateUpdated(
                        UiState(
                            mode = mode,
                            handDetected = true,
                            currentResult = currentPred,
                            committedTranscript = transcript.toList(),
                            lastCommittedLabel = transcript.lastOrNull(),
                            mediaPipeMs = mediaPipeMs,
                            classifierMs = currentPred?.inferenceTimeMs ?: 0f,
                            activeDelegate = activeDelegate,
                            bufferFrames = gestureBuffer.size(),
                            dynamicModelReady = true,
                            dynamicStatusNote = note
                        )
                    )
                }
            }
        }
    }

    private fun appendTranscript(label: String) {
        if (transcript.size >= MAX_TRANSCRIPT_ITEMS) {
            transcript.removeFirst()
        }
        transcript.addLast(label)
    }

    override fun close() {
        inferenceExecutor.shutdownNow()
        staticClassifier.close()
        dynamicClassifier.close()
    }

    companion object {
        private const val TAG = "TranslationPipeline"
        private const val MAX_TRANSCRIPT_ITEMS = 12
    }
}

