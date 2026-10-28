package com.signtospeech.mediapipe

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import android.util.Log
import androidx.camera.core.ImageProxy
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.framework.image.MPImage
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarkerResult
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Helper untuk mengelola siklus hidup MediaPipe HandLandmarker Tasks Vision
 * dalam mode LIVE_STREAM (1 tangan, mendukung pergantian delegate CPU | GPU dengan DelegateGuard).
 */
class HandLandmarkerHelper(
    var minHandDetectionConfidence: Float = DEFAULT_HAND_DETECTION_CONFIDENCE,
    var minHandTrackingConfidence: Float = DEFAULT_HAND_TRACKING_CONFIDENCE,
    var minHandPresenceConfidence: Float = DEFAULT_HAND_PRESENCE_CONFIDENCE,
    var maxNumHands: Int = DEFAULT_NUM_HANDS,
    initialDelegate: DelegateMode = DelegateMode.CPU,
    private val delegateGuard: DelegateGuard? = null,
    val context: Context,
    val handLandmarkerHelperListener: LandmarkerListener? = null
) {

    private var handLandmarker: HandLandmarker? = null

    @Volatile
    var activeDelegate: DelegateMode = initialDelegate
        private set

    private val isSwitching = AtomicBoolean(false)
    private val gpuConfirmedThisRun = AtomicBoolean(false)

    init {
        setupHandLandmarker(initialDelegate)
    }

    @Synchronized
    fun clearHandLandmarker() {
        try {
            handLandmarker?.close()
        } catch (e: Exception) {
            Log.w(TAG, "Gagal menutup HandLandmarker: ${e.message}")
        } finally {
            handLandmarker = null
        }
    }

    fun isClose(): Boolean = handLandmarker == null

    /**
     * Inisialisasi HandLandmarker dengan mode delegate yang diminta.
     * Jika GPU gagal di level Kotlin/Java, otomatis fallback ke CPU.
     */
    @Synchronized
    fun setupHandLandmarker(requestedMode: DelegateMode = activeDelegate) {
        clearHandLandmarker()

        val targetMode = if (requestedMode == DelegateMode.GPU && delegateGuard?.isGpuAvailable() == false) {
            DelegateMode.CPU
        } else {
            requestedMode
        }

        if (targetMode == DelegateMode.GPU) {
            gpuConfirmedThisRun.set(false)
            delegateGuard?.markGpuAttempt()
        }

        val initialized = tryCreateLandmarker(targetMode)
        if (initialized) {
            activeDelegate = targetMode
            handLandmarkerHelperListener?.onDelegateChanged(targetMode, null)
            return
        }

        // Jika tadi mencoba GPU dan gagal secara graceful (exception Kotlin tertangkap), fallback ke CPU
        if (targetMode == DelegateMode.GPU) {
            delegateGuard?.markGpuFailedGracefully()
            Log.w(TAG, "Inisialisasi Delegate.GPU gagal, melakukan fallback otomatis ke Delegate.CPU")
            if (tryCreateLandmarker(DelegateMode.CPU)) {
                activeDelegate = DelegateMode.CPU
                handLandmarkerHelperListener?.onDelegateChanged(
                    DelegateMode.CPU,
                    "GPU tidak didukung perangkat ini, beralih ke CPU"
                )
            }
        }
    }

    /**
     * Dipanggil pada cameraExecutor thread untuk mengganti delegate CPU <-> GPU secara aman.
     */
    fun switchDelegate(newMode: DelegateMode) {
        if (newMode == activeDelegate && handLandmarker != null) {
            handLandmarkerHelperListener?.onDelegateChanged(activeDelegate, null)
            return
        }
        if (!isSwitching.compareAndSet(false, true)) return
        try {
            setupHandLandmarker(newMode)
        } finally {
            isSwitching.set(false)
        }
    }

    private fun tryCreateLandmarker(mode: DelegateMode): Boolean {
        return try {
            val mpDelegate = if (mode == DelegateMode.GPU) Delegate.GPU else Delegate.CPU
            val baseOptions = BaseOptions.builder()
                .setModelAssetPath(MP_HAND_LANDMARKER_TASK)
                .setDelegate(mpDelegate)
                .build()

            val options = HandLandmarker.HandLandmarkerOptions.builder()
                .setBaseOptions(baseOptions)
                .setMinHandDetectionConfidence(minHandDetectionConfidence)
                .setMinTrackingConfidence(minHandTrackingConfidence)
                .setMinHandPresenceConfidence(minHandPresenceConfidence)
                .setNumHands(maxNumHands)
                .setRunningMode(RunningMode.LIVE_STREAM)
                .setResultListener(this::returnLivestreamResult)
                .setErrorListener(this::returnLivestreamError)
                .build()

            handLandmarker = HandLandmarker.createFromOptions(context, options)
            Log.d(TAG, "MediaPipe HandLandmarker aktif (delegate=$mode, maxNumHands=$maxNumHands)")
            true
        } catch (t: Throwable) {
            Log.e(TAG, "Gagal inisialisasi HandLandmarker (delegate=$mode): ${t.message}", t)
            if (mode == DelegateMode.CPU) {
                handLandmarkerHelperListener?.onError(
                    "Gagal inisialisasi HandLandmarker (${mode.name}): ${t.message}"
                )
            }
            false
        }
    }

    /**
     * Menerima frame dari CameraX ImageAnalysis, melakukan rotasi sesuai orientasi sensor,
     * dan mengirimkan ke MediaPipe HandLandmarker via detectAsync.
     */
    fun detectLiveStream(imageProxy: ImageProxy, isFrontCamera: Boolean) {
        if (isSwitching.get()) {
            imageProxy.close()
            return
        }

        val frameTime = SystemClock.uptimeMillis()

        try {
            val bitmapBuffer = imageProxy.toBitmap()

            val matrix = Matrix().apply {
                postRotate(imageProxy.imageInfo.rotationDegrees.toFloat())
            }

            val rotatedBitmap = Bitmap.createBitmap(
                bitmapBuffer,
                0,
                0,
                bitmapBuffer.width,
                bitmapBuffer.height,
                matrix,
                true
            )

            if (rotatedBitmap != bitmapBuffer) {
                bitmapBuffer.recycle()
            }

            val mpImage = BitmapImageBuilder(rotatedBitmap).build()
            handLandmarker?.detectAsync(mpImage, frameTime)
        } catch (e: Exception) {
            Log.e(TAG, "Error saat memproses frame kamera untuk MediaPipe", e)
        } finally {
            imageProxy.close()
        }
    }

    private fun returnLivestreamResult(
        result: HandLandmarkerResult,
        input: MPImage
    ) {
        if (activeDelegate == DelegateMode.GPU && gpuConfirmedThisRun.compareAndSet(false, true)) {
            delegateGuard?.markGpuConfirmed()
        }

        val finishTimeMs = SystemClock.uptimeMillis()
        val frameTs = result.timestampMs()
        val inferenceTime = (finishTimeMs - frameTs).coerceAtLeast(0L)

        handLandmarkerHelperListener?.onResults(
            ResultBundle(
                results = listOf(result),
                inferenceTime = inferenceTime,
                frameTimestampMs = frameTs,
                inputImageHeight = input.height,
                inputImageWidth = input.width,
                activeDelegate = activeDelegate
            )
        )
    }

    private fun returnLivestreamError(error: RuntimeException) {
        handLandmarkerHelperListener?.onError(
            error.message ?: "Terjadi kesalahan tidak dikenal pada MediaPipe"
        )
    }

    data class ResultBundle(
        val results: List<HandLandmarkerResult>,
        val inferenceTime: Long,
        val frameTimestampMs: Long,
        val inputImageHeight: Int,
        val inputImageWidth: Int,
        val activeDelegate: DelegateMode = DelegateMode.CPU
    )

    interface LandmarkerListener {
        fun onError(error: String)
        fun onResults(resultBundle: ResultBundle)
        fun onDelegateChanged(active: DelegateMode, reason: String?) {}
    }

    companion object {
        private const val TAG = "HandLandmarkerHelper"
        private const val MP_HAND_LANDMARKER_TASK = "hand_landmarker.task"

        const val DEFAULT_HAND_DETECTION_CONFIDENCE = 0.5f
        const val DEFAULT_HAND_TRACKING_CONFIDENCE = 0.5f
        const val DEFAULT_HAND_PRESENCE_CONFIDENCE = 0.5f
        const val DEFAULT_NUM_HANDS = 1
    }
}
