package com.signtospeech

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.android.material.snackbar.Snackbar
import com.signtospeech.camera.CameraManager
import com.signtospeech.databinding.ActivityMainBinding
import com.signtospeech.mediapipe.DelegateGuard
import com.signtospeech.mediapipe.DelegateMode
import com.signtospeech.mediapipe.HandLandmarkerHelper
import com.signtospeech.mediapipe.SharedPreferencesDelegateStore
import com.signtospeech.ml.RecognitionMode
import com.signtospeech.pipeline.AppDirection
import com.signtospeech.pipeline.TranslationPipeline
import com.signtospeech.speech.KeywordMatcher
import com.signtospeech.speech.SpeechToTextManager
import com.signtospeech.speech.TTSManager
import com.signtospeech.ui.PredictionDisplay
import com.signtospeech.ui.TextCardDisplay
import java.util.Locale

/**
 * MainActivity sebagai orchestrator utama untuk Sistem Komunikasi Dua Arah Penuh (Full Bi-Directional):
 * - Arah 1 (Tuli -> Dengar): Kamera CameraX + HandLandmarker + TranslationPipeline (Huruf/Kata) + TTS.
 * - Arah 2 (Dengar -> Tuli): Mikrofon + SpeechToTextManager (id-ID) + KeywordMatcher + TextCardDisplay.
 * - Mode Switcher: Berpindah mulus via Bottom Navigation Bar tanpa konflik resource kamera/audio.
 */
class MainActivity : AppCompatActivity(), HandLandmarkerHelper.LandmarkerListener {

    private lateinit var binding: ActivityMainBinding

    // Arah 1 Components
    private lateinit var cameraManager: CameraManager
    private lateinit var handLandmarkerHelper: HandLandmarkerHelper
    private lateinit var translationPipeline: TranslationPipeline
    private lateinit var predictionDisplay: PredictionDisplay
    private lateinit var ttsManager: TTSManager
    private lateinit var delegateGuard: DelegateGuard

    // Arah 2 Components
    private lateinit var speechToTextManager: SpeechToTextManager
    private lateinit var textCardDisplay: TextCardDisplay

    private var currentDirection: AppDirection = AppDirection.SIGN_TO_SPEECH

    private var frameCount = 0
    private var lastFpsTimestamp = System.currentTimeMillis()
    private var currentFps = 0.0
    private var lastMediaPipeMs = 0L
    private var lastClassifierMs = 0f

    private val requestCameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            setupCameraAndPipeline()
        } else {
            showPermissionDeniedUI()
        }
    }

    private val requestAudioPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            speechToTextManager.toggleListening()
        } else {
            Toast.makeText(
                this,
                getString(R.string.audio_permission_required),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val prefs = getSharedPreferences(DelegateGuard.PREFS_NAME, Context.MODE_PRIVATE)
        delegateGuard = DelegateGuard(
            store = SharedPreferencesDelegateStore(prefs),
            isEmulator = detectIsEmulator()
        )

        ttsManager = TTSManager(context = this) {
            runOnUiThread {
                Toast.makeText(
                    this,
                    "Suara Bahasa Indonesia (id-ID) belum terpasang di perangkat, menggunakan suara default.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }

        predictionDisplay = PredictionDisplay(binding) {
            if (::translationPipeline.isInitialized) {
                translationPipeline.clearTranscript()
            }
        }

        translationPipeline = TranslationPipeline(
            context = this,
            onStateUpdated = { uiState ->
                runOnUiThread {
                    lastMediaPipeMs = uiState.mediaPipeMs
                    lastClassifierMs = uiState.classifierMs
                    predictionDisplay.render(uiState)
                    updateHudText(uiState.activeDelegate)
                }
            },
            onCommitted = { committedLabel, _ ->
                runOnUiThread {
                    if (currentDirection == AppDirection.SIGN_TO_SPEECH) {
                        ttsManager.speak(committedLabel)
                    }
                }
            }
        )

        setupArah2Components()
        setupUiListeners()

        if (hasCameraPermission()) {
            setupCameraAndPipeline()
        } else {
            requestCameraPermission()
        }
    }

    private fun setupArah2Components() {
        textCardDisplay = TextCardDisplay(
            context = this,
            tvSpeechTranscript = binding.tvSpeechTranscript,
            tvSpeechStatus = binding.tvSpeechStatus,
            tvCardsHeader = binding.tvCardsHeader,
            llVisualCards = binding.llVisualCards,
            llQuickPresets = binding.llQuickPresets,
            progressAudioLevel = binding.progressAudioLevel,
            btnToggleMic = binding.btnToggleMic,
            tvMicIcon = binding.tvMicIcon,
            tvMicLabel = binding.tvMicLabel,
            tvArah2ModeBadge = binding.tvArah2ModeBadge,
            btnArah2Manual = binding.btnArah2Manual,
            btnArah2Clear = binding.btnArah2Clear,
            scrollArah2Content = binding.scrollArah2Content,
            onPresetSelected = { presetText ->
                val analysis = KeywordMatcher.match(presetText)
                textCardDisplay.updateAnalysis(analysis)
            },
            onManualInputSubmitted = { inputText ->
                val analysis = KeywordMatcher.match(inputText)
                textCardDisplay.updateAnalysis(analysis)
            },
            onClearClicked = {
                speechToTextManager.cancel()
            },
            onToggleMicClicked = {
                handleMicToggleClick()
            }
        )

        speechToTextManager = SpeechToTextManager(
            context = this,
            onPartialResult = { partialText ->
                runOnUiThread {
                    val analysis = KeywordMatcher.match(partialText)
                    textCardDisplay.updateAnalysis(analysis)
                }
            },
            onFinalResult = { finalText ->
                runOnUiThread {
                    val analysis = KeywordMatcher.match(finalText)
                    textCardDisplay.updateAnalysis(analysis)
                }
            },
            onRmsChanged = { rmsdB ->
                runOnUiThread {
                    textCardDisplay.updateAudioLevel(rmsdB)
                }
            },
            onListeningStateChanged = { isListening ->
                runOnUiThread {
                    textCardDisplay.updateListeningState(isListening)
                }
            },
            onError = { _, errorMessage ->
                runOnUiThread {
                    Toast.makeText(this, errorMessage, Toast.LENGTH_SHORT).show()
                }
            },
            onOfflineModeChanged = { isOffline ->
                runOnUiThread {
                    textCardDisplay.updateOfflineBadge(isOffline)
                }
            }
        )
    }

    private fun handleMicToggleClick() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            speechToTextManager.toggleListening()
        } else {
            requestAudioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun setupUiListeners() {
        // Navigation Switcher Tabs
        binding.tabArah1.setOnClickListener {
            switchDirection(AppDirection.SIGN_TO_SPEECH)
        }

        binding.tabArah2.setOnClickListener {
            switchDirection(AppDirection.SPEECH_TO_TEXT)
        }

        // Arah 1 Controls
        binding.btnGrantPermission.setOnClickListener {
            requestCameraPermission()
        }

        binding.btnSwitchCamera.setOnClickListener {
            if (::cameraManager.isInitialized) {
                cameraManager.switchCamera()
                binding.overlayView.clear()
                translationPipeline.onContextReset()
            }
        }

        binding.btnModeLetter.setOnClickListener {
            selectRecognitionMode(RecognitionMode.LETTER)
        }

        binding.btnModeWord.setOnClickListener {
            selectRecognitionMode(RecognitionMode.WORD)
        }

        binding.btnMuteTts.setOnClickListener {
            val muted = ttsManager.toggleMute()
            binding.btnMuteTts.text = getString(if (muted) R.string.tts_muted else R.string.tts_on)
            binding.btnMuteTts.setBackgroundColor(
                ContextCompat.getColor(
                    this,
                    if (muted) R.color.chip_inactive_bg else R.color.chip_active_bg
                )
            )
        }

        binding.btnDelegateCpu.setOnClickListener {
            requestDelegateSwitch(DelegateMode.CPU)
        }

        binding.btnDelegateGpu.setOnClickListener {
            if (!delegateGuard.isGpuAvailable()) {
                val msg = if (delegateGuard.isEmulator) {
                    "GPU dinonaktifkan otomatis pada Emulator (AVD)"
                } else {
                    "GPU diblokir setelah crash. Tekan lama tombol GPU untuk mereset blokir."
                }
                Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            requestDelegateSwitch(DelegateMode.GPU)
        }

        binding.btnDelegateGpu.setOnLongClickListener {
            if (delegateGuard.isEmulator) {
                Toast.makeText(this, "GPU tetap terkunci pada Emulator (AVD)", Toast.LENGTH_SHORT).show()
                return@setOnLongClickListener true
            }
            delegateGuard.resetBlock()
            updateDelegateButtons(
                if (::handLandmarkerHelper.isInitialized) handLandmarkerHelper.activeDelegate else DelegateMode.CPU
            )
            Toast.makeText(this, "Blokir GPU telah direset. Anda dapat mencoba GPU kembali.", Toast.LENGTH_SHORT).show()
            true
        }
    }

    /**
     * Berpindah mode komunikasi antara Arah 1 (Tuli -> Dengar) dan Arah 2 (Dengar -> Tuli).
     * Memastikan isolasi resource (kamera di-pause dan TTS di-stop pada Arah 2).
     */
    private fun switchDirection(targetDirection: AppDirection) {
        if (currentDirection == targetDirection) return
        currentDirection = targetDirection

        if (targetDirection == AppDirection.SPEECH_TO_TEXT) {
            // 1. Masuk ke Arah 2: Dengar -> Tuli
            if (::cameraManager.isInitialized) {
                cameraManager.pauseCamera()
            }
            if (::ttsManager.isInitialized) {
                ttsManager.stop()
            }

            // Sembunyikan Layer Arah 1
            binding.previewView.visibility = View.GONE
            binding.overlayView.visibility = View.GONE
            binding.badgeContainer.visibility = View.GONE
            binding.btnSwitchCamera.visibility = View.GONE
            binding.predictionPanel.visibility = View.GONE

            // Tampilkan Layer Arah 2
            binding.arah2Container.visibility = View.VISIBLE

            // Perbarui visual tab navigasi
            binding.tvTabArah1Title.setTextColor(ContextCompat.getColor(this, R.color.color_nav_inactive))
            binding.indicatorTabArah1.setBackgroundColor(Color.TRANSPARENT)
            binding.tvTabArah2Title.setTextColor(ContextCompat.getColor(this, R.color.color_nav_active))
            binding.indicatorTabArah2.setBackgroundColor(ContextCompat.getColor(this, R.color.color_nav_active))

            Log.d(TAG, "Beralih ke Subsistem Arah 2 (Dengar -> Tuli)")
        } else {
            // 2. Kembali ke Arah 1: Tuli -> Dengar
            if (::speechToTextManager.isInitialized && speechToTextManager.isListening) {
                speechToTextManager.stopListening()
            }

            // Sembunyikan Layer Arah 2
            binding.arah2Container.visibility = View.GONE

            // Tampilkan Layer Arah 1
            binding.previewView.visibility = View.VISIBLE
            binding.overlayView.visibility = View.VISIBLE
            binding.badgeContainer.visibility = View.VISIBLE
            binding.btnSwitchCamera.visibility = View.VISIBLE
            binding.predictionPanel.visibility = View.VISIBLE

            // Resume kamera
            if (::cameraManager.isInitialized) {
                cameraManager.resumeCamera()
            }

            // Perbarui visual tab navigasi
            binding.tvTabArah1Title.setTextColor(ContextCompat.getColor(this, R.color.color_nav_active))
            binding.indicatorTabArah1.setBackgroundColor(ContextCompat.getColor(this, R.color.color_nav_active))
            binding.tvTabArah2Title.setTextColor(ContextCompat.getColor(this, R.color.color_nav_inactive))
            binding.indicatorTabArah2.setBackgroundColor(Color.TRANSPARENT)

            Log.d(TAG, "Beralih ke Subsistem Arah 1 (Tuli -> Dengar)")
        }
    }

    private fun selectRecognitionMode(mode: RecognitionMode) {
        translationPipeline.setMode(mode)
        val isLetter = mode == RecognitionMode.LETTER
        binding.btnModeLetter.setBackgroundColor(
            ContextCompat.getColor(this, if (isLetter) R.color.chip_active_bg else R.color.chip_inactive_bg)
        )
        binding.btnModeWord.setBackgroundColor(
            ContextCompat.getColor(this, if (!isLetter) R.color.chip_active_bg else R.color.chip_inactive_bg)
        )
    }

    private fun requestDelegateSwitch(targetMode: DelegateMode) {
        if (!::handLandmarkerHelper.isInitialized || !::cameraManager.isInitialized) return
        delegateGuard.savePreferred(targetMode)
        resetFpsCounter()
        translationPipeline.onContextReset()

        if (targetMode == DelegateMode.GPU) {
            Toast.makeText(this, "Memuat Delegate.GPU...", Toast.LENGTH_SHORT).show()
        }

        cameraManager.runOnCameraThread {
            handLandmarkerHelper.switchDelegate(targetMode)
        }
    }

    private fun updateDelegateButtons(activeMode: DelegateMode) {
        val isCpu = activeMode == DelegateMode.CPU
        val gpuAvailable = delegateGuard.isGpuAvailable()

        binding.btnDelegateCpu.setBackgroundColor(
            ContextCompat.getColor(this, if (isCpu) R.color.chip_active_bg else R.color.chip_inactive_bg)
        )

        val gpuBg = when {
            !isCpu -> R.color.chip_active_bg
            !gpuAvailable -> R.color.chip_disabled_bg
            else -> R.color.chip_inactive_bg
        }
        binding.btnDelegateGpu.setBackgroundColor(ContextCompat.getColor(this, gpuBg))
        binding.btnDelegateGpu.setTextColor(
            ContextCompat.getColor(this, if (gpuAvailable || !isCpu) R.color.white else R.color.text_muted)
        )
    }

    private fun resetFpsCounter() {
        frameCount = 0
        currentFps = 0.0
        lastFpsTimestamp = System.currentTimeMillis()
    }

    private fun updateHudText(activeDelegate: DelegateMode) {
        binding.tvFps.text = String.format(
            Locale.US,
            "FPS: %.1f · MP: %d ms · Cls: %.1f ms · %s",
            currentFps,
            lastMediaPipeMs,
            lastClassifierMs,
            activeDelegate.name
        )
    }

    private fun hasCameraPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun requestCameraPermission() {
        requestCameraPermissionLauncher.launch(Manifest.permission.CAMERA)
    }

    private fun showPermissionDeniedUI() {
        binding.permissionContainer.visibility = View.VISIBLE
        binding.previewView.visibility = View.GONE
        binding.overlayView.visibility = View.GONE
        binding.badgeContainer.visibility = View.GONE
        binding.btnSwitchCamera.visibility = View.GONE
        binding.predictionPanel.visibility = View.GONE
        binding.arah2Container.visibility = View.GONE
    }

    private fun setupCameraAndPipeline() {
        binding.permissionContainer.visibility = View.GONE
        binding.previewView.visibility = View.VISIBLE
        binding.overlayView.visibility = View.VISIBLE
        binding.badgeContainer.visibility = View.VISIBLE
        binding.btnSwitchCamera.visibility = View.VISIBLE
        binding.predictionPanel.visibility = View.VISIBLE

        val startupDelegate = delegateGuard.resolveStartupMode()
        if (delegateGuard.wasBlockedByCrash()) {
            Snackbar.make(
                binding.rootContainer,
                "GPU dinonaktifkan otomatis karena crash sebelumnya (tekan lama tombol GPU untuk reset)",
                Snackbar.LENGTH_LONG
            ).show()
        }

        // 1. Inisialisasi MediaPipe Tasks Vision (1 tangan, startupDelegate via DelegateGuard)
        handLandmarkerHelper = HandLandmarkerHelper(
            initialDelegate = startupDelegate,
            delegateGuard = delegateGuard,
            context = this,
            handLandmarkerHelperListener = this
        )
        updateDelegateButtons(handLandmarkerHelper.activeDelegate)

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

    override fun onDelegateChanged(active: DelegateMode, reason: String?) {
        runOnUiThread {
            updateDelegateButtons(active)
            updateHudText(active)
            if (!reason.isNullOrBlank()) {
                Toast.makeText(this, reason, Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onResults(resultBundle: HandLandmarkerHelper.ResultBundle) {
        val firstResult = resultBundle.results.firstOrNull()
        val firstHandLandmarks = firstResult?.landmarks()?.firstOrNull()
        val isFront = if (::cameraManager.isInitialized) cameraManager.isFrontCamera() else false

        // Kirim ke TranslationPipeline (single-thread inference executor)
        translationPipeline.processLandmarks(
            landmarks = firstHandLandmarks,
            imageWidth = resultBundle.inputImageWidth,
            imageHeight = resultBundle.inputImageHeight,
            isFrontCamera = isFront,
            frameTimestampMs = resultBundle.frameTimestampMs,
            mediaPipeMs = resultBundle.inferenceTime,
            activeDelegate = resultBundle.activeDelegate
        )

        runOnUiThread {
            frameCount++
            val currentTime = System.currentTimeMillis()
            val deltaTime = currentTime - lastFpsTimestamp
            if (deltaTime >= 1000) {
                currentFps = (frameCount * 1000.0) / deltaTime
                frameCount = 0
                lastFpsTimestamp = currentTime
                updateHudText(resultBundle.activeDelegate)
            }

            if (firstResult != null && firstResult.landmarks().isNotEmpty()) {
                val handCount = firstResult.landmarks().size
                binding.tvStatus.text = getString(R.string.status_detected, handCount)
                binding.tvStatus.setTextColor(ContextCompat.getColor(this, R.color.landmark_point))

                binding.overlayView.setResults(
                    handLandmarkerResults = firstResult,
                    imageHeight = resultBundle.inputImageHeight,
                    imageWidth = resultBundle.inputImageWidth,
                    isFrontCamera = isFront
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

    override fun onPause() {
        super.onPause()
        if (::speechToTextManager.isInitialized && speechToTextManager.isListening) {
            speechToTextManager.stopListening()
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
        if (::translationPipeline.isInitialized) {
            translationPipeline.close()
        }
        if (::ttsManager.isInitialized) {
            ttsManager.shutdown()
        }
        if (::speechToTextManager.isInitialized) {
            speechToTextManager.destroy()
        }
    }

    private fun detectIsEmulator(): Boolean {
        val fp = Build.FINGERPRINT.lowercase(Locale.US)
        val hw = Build.HARDWARE.lowercase(Locale.US)
        val model = Build.MODEL.lowercase(Locale.US)
        val product = Build.PRODUCT.lowercase(Locale.US)
        return fp.contains("generic") ||
            fp.contains("emulator") ||
            hw == "goldfish" ||
            hw == "ranchu" ||
            model.contains("sdk_gphone") ||
            model.contains("emulator") ||
            product.contains("emulator") ||
            product.contains("sdk_gphone")
    }

    companion object {
        private const val TAG = "SignToSpeechMainActivity"
    }
}
