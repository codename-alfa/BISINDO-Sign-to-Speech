package com.signtospeech.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import androidx.core.content.ContextCompat
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarkerResult
import com.signtospeech.R
import kotlin.math.max

/**
 * OverlayView menggambar 21 landmark tangan dan garis rangka (skeleton)
 * di atas CameraX PreviewView dengan transformasi koordinat presisi.
 */
class OverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private var results: HandLandmarkerResult? = null
    private var imageHeight: Int = 1
    private var imageWidth: Int = 1
    private var isFrontCamera: Boolean = false

    private val density = context.resources.displayMetrics.density

    private val pointPaint = Paint().apply {
        color = ContextCompat.getColor(context, R.color.landmark_point)
        style = Paint.Style.FILL
        isAntiAlias = true
    }

    private val wristPaint = Paint().apply {
        color = ContextCompat.getColor(context, R.color.landmark_wrist)
        style = Paint.Style.FILL
        isAntiAlias = true
    }

    private val linePaint = Paint().apply {
        color = ContextCompat.getColor(context, R.color.landmark_connection)
        strokeWidth = 3f * density
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
        isAntiAlias = true
    }

    fun clear() {
        results = null
        invalidate()
    }

    fun setResults(
        handLandmarkerResults: HandLandmarkerResult,
        imageHeight: Int,
        imageWidth: Int,
        isFrontCamera: Boolean = false
    ) {
        this.results = handLandmarkerResults
        this.imageHeight = imageHeight
        this.imageWidth = imageWidth
        this.isFrontCamera = isFrontCamera
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        val currentResults = results ?: return
        if (currentResults.landmarks().isEmpty()) return

        // Hitung faktor skala untuk mode fillCenter
        val scaleFactor = max(width * 1f / imageWidth, height * 1f / imageHeight)
        val offsetX = (width - imageWidth * scaleFactor) / 2f
        val offsetY = (height - imageHeight * scaleFactor) / 2f

        for (landmarkList in currentResults.landmarks()) {
            // 1. Gambar koneksi antar sendi (Bones)
            for (connection in HandLandmarker.HAND_CONNECTIONS) {
                val startIdx = connection.start()
                val endIdx = connection.end()

                if (startIdx < landmarkList.size && endIdx < landmarkList.size) {
                    val p1 = landmarkList[startIdx]
                    val p2 = landmarkList[endIdx]

                    val p1NormX = if (isFrontCamera) (1f - p1.x()) else p1.x()
                    val p2NormX = if (isFrontCamera) (1f - p2.x()) else p2.x()

                    val startX = p1NormX * imageWidth * scaleFactor + offsetX
                    val startY = p1.y() * imageHeight * scaleFactor + offsetY

                    val endX = p2NormX * imageWidth * scaleFactor + offsetX
                    val endY = p2.y() * imageHeight * scaleFactor + offsetY

                    canvas.drawLine(startX, startY, endX, endY, linePaint)
                }
            }

            // 2. Gambar 21 titik sendi (Landmarks)
            for ((index, landmark) in landmarkList.withIndex()) {
                val normX = if (isFrontCamera) (1f - landmark.x()) else landmark.x()
                val pointX = normX * imageWidth * scaleFactor + offsetX
                val pointY = landmark.y() * imageHeight * scaleFactor + offsetY

                // Wrist (index 0) ditonjolkan dengan warna kuning terang sebagai titik acuan normalisasi
                if (index == 0) {
                    canvas.drawCircle(pointX, pointY, 9f * density, wristPaint)
                } else {
                    canvas.drawCircle(pointX, pointY, 6f * density, pointPaint)
                }
            }
        }
    }
}
