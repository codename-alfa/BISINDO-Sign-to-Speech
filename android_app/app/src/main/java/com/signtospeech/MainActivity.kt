package com.signtospeech

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.signtospeech.camera.CameraManager
import com.signtospeech.databinding.ActivityMainBinding
import com.signtospeech.mediapipe.HandLandmarkerHelper
import java.util.Locale

/**
 * MainActivity sebagai orchestrator utama:
 * - Meminta izin CAMERA secara runtime.
 * - Menginisialisasi CameraManager dan HandLandmarkerHelper.
 * - Menerima landmark hasil deteksi MediaPipe dan memperbarui OverlayView secara real-time.
 */
class MainActivity : AppCompatActivity(), HandLandmarkerHelper.LandmarkerListener {

    private lateinit var binding: ActivityMainBinding
    private lateinit var cameraManager: CameraManager
    private lateinit var handLandmarkerHelper: HandLandmarkerHelper

    private var frameCount = 0
    private var lastFpsTimestamp = System.currentTimeMillis()
    private var currentFps = 0.0

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            setupCameraAndPipeline()
        } else {
            showPermissionDeniedUI()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnGrantPermission.setOnClickListener {
            requestCameraPermission()
        }

        binding.btnSwitchCamera.setOnClickListener {
            if (::cameraManager.isInitialized) {
                cameraManager.switchCamera()
                binding.overlayView.clear()
            }
        }

        if (hasCameraPermission()) {
            setupCameraAndPipeline()
        } else {
            requestCameraPermission()
        }
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestCameraPermission() {
        requestPermissionLauncher.launch(Manifest.permission.CAMERA)
    }

    private fun showPermissionDeniedUI() {
        binding.permissionContainer.visibility = View.VISIBLE
        binding.previewView.visibility = View.GONE
        binding.overlayView.visibility = View.GONE
        binding.badgeContainer.visibility = View.GONE
        binding.btnSwitchCamera.visibility = View.GONE
    }

    private fun setupCameraAndPipeline() {
        binding.permissionContainer.visibility = View.GONE
        binding.previewView.visibility = View.VISIBLE
        binding.overlayView.visibility = View.VISIBLE
        binding.badgeContainer.visibility = View.VISIBLE
        binding.btnSwitchCamera.visibility = View.VISIBLE

        // 1. Inisialisasi MediaPipe Tasks Vision
        handLandmarkerHelper = HandLandmarkerHelper(
            context = this,
            handLandmarkerHelperListener = this
        )

        // 2. Inisialisasi CameraManager
        cameraManager = CameraManager(
            context = this,
            lifecycleOwner = this,
            previewView = binding.previewView
        ) { imageProxy, isFrontCamera ->
            handLandmarkerHelper.detectLiveStream(imageProxy, isFrontCamera)
        }

        // 3. Mulai CameraX Preview
        binding.previewView.post {
            cameraManager.startCamera(
                onSuccess = {
                    Log.d(TAG, "Kamera berhasil dijalankan")
                },
                onError = { exc ->
                    Toast.makeText(this, "Gagal membuka kamera: ${exc.message}", Toast.LENGTH_LONG).show()
                }
            )
        }
    }

    override fun onResults(resultBundle: HandLandmarkerHelper.ResultBundle) {
        runOnUiThread {
            // Hitung frame rate FPS
            frameCount++
            val currentTime = System.currentTimeMillis()
            val deltaTime = currentTime - lastFpsTimestamp
            if (deltaTime >= 1000) {
                currentFps = (frameCount * 1000.0) / deltaTime
                frameCount = 0
                lastFpsTimestamp = currentTime
                binding.tvFps.text = String.format(Locale.US, "FPS: %.1f", currentFps)
            }

            val firstResult = resultBundle.results.firstOrNull()
            if (firstResult != null && firstResult.landmarks().isNotEmpty()) {
                val handCount = firstResult.landmarks().size
                binding.tvStatus.text = getString(R.string.status_detected, handCount)
                binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.landmark_point))

                // Render 21 landmark di OverlayView
                binding.overlayView.setResults(
                    handLandmarkerResults = firstResult,
                    imageHeight = resultBundle.inputImageHeight,
                    imageWidth = resultBundle.inputImageWidth,
                    isFrontCamera = cameraManager.isFrontCamera()
                )
            } else {
                binding.tvStatus.text = getString(R.string.status_searching)
                binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.landmark_point))
                binding.overlayView.clear()
            }
        }
    }

    override fun onError(error: String) {
        runOnUiThread {
            Log.e(TAG, "MediaPipe Error: $error")
            binding.tvStatus.text = "Error: $error"
            binding.tvStatus.setTextColor(ContextCompat.getColor(this, android.R.color.holo_red_light))
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::cameraManager.isInitialized) {
            cameraManager.shutdown()
        }
        if (::handLandmarkerHelper.isInitialized) {
            handLandmarkerHelper.clearHandLandmarker()
        }
    }

    companion object {
        private const val TAG = "SignToSpeechMainActivity"
    }
}
