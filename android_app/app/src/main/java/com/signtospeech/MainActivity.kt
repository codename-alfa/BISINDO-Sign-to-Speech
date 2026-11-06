package com.signtospeech

import android.Manifest
import android.app.AlertDialog
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.ViewGroup
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.core.content.res.ResourcesCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.google.android.material.snackbar.Snackbar
import com.signtospeech.camera.CameraManager
import com.signtospeech.databinding.ActivityMainBinding
import com.signtospeech.debug.AppLogger
import com.signtospeech.debug.CrashHandler
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
import com.signtospeech.ui.HapticFeedbackHelper
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
    private lateinit var hapticFeedbackHelper: HapticFeedbackHelper

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
            handleMicToggleClick()
        } else {
            Toast.makeText(
                this,
                getString(R.string.audio_permission_required),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        AppLogger.init(this)
        CrashHandler.install(this)
        hapticFeedbackHelper = HapticFeedbackHelper(this)

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

        predictionDisplay = PredictionDisplay(
            binding = binding,
            onSuggestionSelected = { correctedLabel ->
                if (::translationPipeline.isInitialized) {
                    translationPipeline.replaceLastCommitted(correctedLabel)
                    Toast.makeText(
                        this,
                        "Dikoreksi menjadi: $correctedLabel",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            },
            onDeleteLastTranscript = {
                if (::translationPipeline.isInitialized) {
                    translationPipeline.deleteLastCommitted()
                }
            },
            onClearTranscript = {
                if (::translationPipeline.isInitialized) {
                    translationPipeline.clearTranscript()
                }
            }
        )

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
                        hapticFeedbackHelper.vibrate(HapticFeedbackHelper.PulseType.GESTURE_COMMITTED)
                    }
                }
            }
        )

        setupArah2Components()
        setupUiListeners()

        ViewCompat.setOnApplyWindowInsetsListener(binding.rootContainer) { _, insets ->
            val navBars = insets.getInsets(WindowInsetsCompat.Type.navigationBars())
            val toggleParams = binding.bottomNavDirection.layoutParams as? ViewGroup.MarginLayoutParams
            toggleParams?.bottomMargin = dpToPx(16) + navBars.bottom
            binding.bottomNavDirection.layoutParams = toggleParams

            binding.predictionPanel.setPadding(
                binding.predictionPanel.paddingLeft,
                binding.predictionPanel.paddingTop,
                binding.predictionPanel.paddingRight,
                dpToPx(56) + navBars.bottom
            )
            binding.arah2Container.setPadding(
                binding.arah2Container.paddingLeft,
                binding.arah2Container.paddingTop,
                binding.arah2Container.paddingRight,
                dpToPx(56) + navBars.bottom
            )
            insets
        }

        if (AppLogger.hasPreviousCrash(this)) {
            checkPreviousCrash()
        }

        if (hasCameraPermission()) {
            setupCameraAndPipeline()
        } else {
            requestCameraPermission()
        }

        handleDebugDemoIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleDebugDemoIntent(intent)
    }

    private fun handleDebugDemoIntent(intent: Intent?) {
        val holdSplash = intent?.getBooleanExtra("debug_hold_splash", false) == true
        val demoLabel = intent?.getStringExtra("debug_commit_label")

        val targetDirection = intent?.getStringExtra("debug_direction")
        val arah2Text = intent?.getStringExtra("debug_arah2_text")

        if (holdSplash) {
            binding.loadingSplashOverlay.alpha = 1f
            binding.loadingSplashOverlay.visibility = View.VISIBLE
        } else if (!demoLabel.isNullOrBlank() || !targetDirection.isNullOrBlank() || !arah2Text.isNullOrBlank()) {
            binding.loadingSplashOverlay.visibility = View.GONE
        } else if (binding.loadingSplashOverlay.visibility == View.VISIBLE) {
            binding.loadingSplashOverlay.postDelayed({
                binding.loadingSplashOverlay.animate()
                    .alpha(0f)
                    .setDuration(250L)
                    .withEndAction {
                        binding.loadingSplashOverlay.visibility = View.GONE
                    }
                    .start()
            }, 1100L)
        }

        if (targetDirection.equals("arah2", ignoreCase = true) || targetDirection.equals("SPEECH_TO_TEXT", ignoreCase = true)) {
            binding.rootContainer.post {
                switchDirection(AppDirection.SPEECH_TO_TEXT)
            }
        } else if (targetDirection.equals("arah1", ignoreCase = true) || targetDirection.equals("SIGN_TO_SPEECH", ignoreCase = true)) {
            binding.rootContainer.post {
                switchDirection(AppDirection.SIGN_TO_SPEECH)
            }
        }

        if (!arah2Text.isNullOrBlank()) {
            binding.rootContainer.post {
                switchDirection(AppDirection.SPEECH_TO_TEXT)
                val analysis = KeywordMatcher.match(arah2Text)
                textCardDisplay.updateAnalysis(analysis)
            }
        }

        if (!demoLabel.isNullOrBlank() && ::translationPipeline.isInitialized) {
            val items = demoLabel.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            binding.rootContainer.postDelayed({
                if (::cameraManager.isInitialized) {
                    cameraManager.pauseCamera()
                }
                translationPipeline.appendCommittedSequence(items)
            }, 900L)
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
            btnArah2DebugLog = binding.btnArah2DebugLog,
            btnArah2Clear = binding.btnArah2Clear,
            scrollArah2Content = binding.scrollArah2Content,
            etArah2KeyboardInput = binding.etArah2KeyboardInput,
            btnSubmitKeyboard = binding.btnSubmitKeyboard,
            btnArah2Edit = binding.btnArah2Edit,
            ivMicIcon = binding.ivMicIcon,
            hudDot = binding.hudArah2Dot,
            hudContainer = binding.hudArah2Status,
            onPresetSelected = { presetText ->
                if (::speechToTextManager.isInitialized && speechToTextManager.isListening) {
                    speechToTextManager.stopListening()
                }
                val analysis = KeywordMatcher.match(presetText)
                textCardDisplay.updateAnalysis(analysis)
            },
            onManualInputSubmitted = { inputText ->
                if (::speechToTextManager.isInitialized && speechToTextManager.isListening) {
                    speechToTextManager.stopListening()
                }
                val analysis = KeywordMatcher.match(inputText)
                textCardDisplay.updateAnalysis(analysis)
            },
            onClearClicked = {
                speechToTextManager.cancel()
            },
            onToggleMicClicked = {
                handleMicToggleClick()
            },
            onToggleModeClicked = {
                handleModeToggle()
            },
            onShowLogClicked = {
                showDebugLogDialog()
            },
            onCardsMatched = { cards ->
                HapticFeedbackHelper.resolvePulseForCards(cards)?.let { pulse ->
                    hapticFeedbackHelper.vibrate(pulse)
                }
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
            onRmsLevelChanged = { rmsdB ->
                runOnUiThread {
                    textCardDisplay.updateAudioLevel(rmsdB)
                }
            },
            onListeningStateChanged = { isListening ->
                runOnUiThread {
                    textCardDisplay.updateListeningState(isListening)
                }
            },
            onErrorOccurred = { _, errorMessage ->
                runOnUiThread {
                    Toast.makeText(this, errorMessage, Toast.LENGTH_SHORT).show()
                }
            },
            onOfflineModeChanged = { isOffline ->
                runOnUiThread {
                    textCardDisplay.updateOfflineBadge(isOffline)
                }
            },
            onServiceUnavailable = {
                runOnUiThread {
                    Toast.makeText(
                        this,
                        "Layanan suara tidak tersedia pada perangkat. Silakan gunakan opsi pengetikan keyboard.",
                        Toast.LENGTH_LONG
                    ).show()
                    textCardDisplay.updateListeningState(false)
                    textCardDisplay.focusKeyboardInput()
                }
            }
        )
    }

    private fun handleModeToggle() {
        val isOffline = speechToTextManager.toggleOfflineMode()
        textCardDisplay.updateOfflineBadge(isOffline)
        val msg = getString(if (isOffline) R.string.mode_offline_toast else R.string.mode_online_toast)
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
        AppLogger.i(TAG, "Mode suara diganti manual: isOffline=$isOffline")
    }

    private fun showDebugLogDialog() {
        val diagnostics = AppLogger.getFormattedDiagnostics()
        val logView = TextView(this).apply {
            text = diagnostics
            typeface = Typeface.MONOSPACE
            textSize = 10f
            setTextColor(Color.WHITE)
            setPadding(dpToPx(16), dpToPx(16), dpToPx(16), dpToPx(16))
            setTextIsSelectable(true)
        }
        val scrollView = ScrollView(this).apply {
            addView(logView)
            setBackgroundColor(Color.parseColor("#0F172A"))
        }

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.dialog_log_title))
            .setView(scrollView)
            .setPositiveButton(getString(R.string.btn_copy_log)) { _, _ ->
                copyLogToClipboard(diagnostics)
            }
            .setNeutralButton(getString(R.string.btn_share_file)) { _, _ ->
                shareLogFile()
            }
            .setNegativeButton(getString(R.string.btn_clear_log)) { _, _ ->
                AppLogger.clearLogs(this)
                Toast.makeText(this, "Log diagnostik telah dibersihkan.", Toast.LENGTH_SHORT).show()
            }
            .show()
    }

    private fun checkPreviousCrash() {
        val crashDump = AppLogger.getLatestCrashDump(this) ?: return
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.previous_crash_title))
            .setMessage(getString(R.string.previous_crash_message))
            .setPositiveButton(getString(R.string.btn_copy_log)) { _, _ ->
                copyLogToClipboard(crashDump)
                AppLogger.clearCrashDump(this)
            }
            .setNeutralButton(getString(R.string.btn_share_file)) { _, _ ->
                shareLogFile()
                AppLogger.clearCrashDump(this)
            }
            .setNegativeButton(getString(R.string.btn_close)) { _, _ ->
                AppLogger.clearCrashDump(this)
            }
            .show()
    }

    private fun copyLogToClipboard(text: String) {
        try {
            val safeText = if (text.length > 50_000) {
                text.take(25_000) + "\n\n... [Log dipotong untuk clipboard, silakan gunakan 'Bagikan Berkas' untuk log lengkap] ...\n\n" + text.takeLast(25_000)
            } else {
                text
            }
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
            val clip = ClipData.newPlainText("SignToSpeech_Diagnostics", safeText)
            clipboard?.setPrimaryClip(clip)
            Toast.makeText(this, getString(R.string.log_copied_toast), Toast.LENGTH_SHORT).show()
            AppLogger.i(TAG, "Log berhasil disalin ke clipboard pengguna")
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Gagal menyalin log ke clipboard: ${t.message}", t)
            Toast.makeText(this, "Ukuran log terlalu besar untuk clipboard. Silakan gunakan opsi Bagikan Berkas.", Toast.LENGTH_LONG).show()
        }
    }

    private fun shareLogFile() {
        try {
            val logFile = AppLogger.getLogFile(this)
            val uri = FileProvider.getUriForFile(
                this,
                "${applicationContext.packageName}.fileprovider",
                logFile
            )
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_STREAM, uri)
                putExtra(Intent.EXTRA_SUBJECT, "SignToSpeech Diagnostic Log")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, "Bagikan Berkas Log"))
            AppLogger.i(TAG, "Membuka Android share sheet untuk file: ${logFile.name}")
        } catch (e: Exception) {
            AppLogger.e(TAG, "Gagal membagikan berkas log: ${e.message}", e)
            Toast.makeText(this, "Gagal membagikan file: ${e.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun dpToPx(dp: Int): Int {
        val density = resources.displayMetrics.density
        return (dp * density).toInt()
    }

    private fun handleMicToggleClick() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            try {
                AppLogger.d(TAG, "Tombol mic diklik (serviceAvailable=${speechToTextManager.isServiceAvailable})")
                if (speechToTextManager.isServiceAvailable) {
                    speechToTextManager.toggleListening()
                } else {
                    AppLogger.w(TAG, "Layanan speech recognizer tidak tersedia. Beralih ke input keyboard.")
                    Toast.makeText(
                        this,
                        "Layanan suara tidak tersedia di perangkat ini. Silakan gunakan pengetikan teks.",
                        Toast.LENGTH_LONG
                    ).show()
                    textCardDisplay.updateListeningState(false)
                    textCardDisplay.focusKeyboardInput()
                }
            } catch (t: Throwable) {
                AppLogger.e(TAG, "Pengecualian saat toggleListening: ${t.message}", t)
                Toast.makeText(
                    this,
                    "Layanan suara tidak tersedia pada perangkat. Silakan gunakan opsi pengetikan keyboard.",
                    Toast.LENGTH_LONG
                ).show()
                textCardDisplay.updateListeningState(false)
                textCardDisplay.focusKeyboardInput()
            }
        } else {
            AppLogger.i(TAG, "Meminta izin RECORD_AUDIO...")
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

        binding.loadingSplashOverlay.setOnClickListener {
            binding.loadingSplashOverlay.visibility = View.GONE
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
            binding.btnMuteTts.setBackgroundResource(
                if (muted) R.drawable.bg_figma_sound_mute else R.drawable.bg_figma_sound_on
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

            // Perbarui visual tab navigasi (Figma Segmented Pill Toggle #23:305)
            binding.tabArah1.setBackgroundResource(0)
            binding.tvTabArah1Title.setTextColor(ContextCompat.getColor(this, R.color.figma_toggle_inactive_text))
            binding.tvTabArah1Title.typeface = ResourcesCompat.getFont(this, R.font.inter_semibold_italic)
            binding.tabArah2.setBackgroundResource(R.drawable.bg_figma_bottom_toggle_active_right)
            binding.tvTabArah2Title.setTextColor(ContextCompat.getColor(this, R.color.figma_toggle_active_text))
            binding.tvTabArah2Title.typeface = ResourcesCompat.getFont(this, R.font.inter_light_italic)

            AppLogger.i(TAG, "Beralih ke Subsistem Arah 2 (Dengar -> Tuli)")
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

            // Perbarui visual tab navigasi (Figma Segmented Pill Toggle #23:305)
            binding.tabArah1.setBackgroundResource(R.drawable.bg_figma_bottom_toggle_active)
            binding.tvTabArah1Title.setTextColor(ContextCompat.getColor(this, R.color.figma_toggle_active_text))
            binding.tvTabArah1Title.typeface = ResourcesCompat.getFont(this, R.font.inter_light_italic)
            binding.tabArah2.setBackgroundResource(0)
            binding.tvTabArah2Title.setTextColor(ContextCompat.getColor(this, R.color.figma_toggle_inactive_text))
            binding.tvTabArah2Title.typeface = ResourcesCompat.getFont(this, R.font.inter_semibold_italic)

            AppLogger.i(TAG, "Beralih ke Subsistem Arah 1 (Tuli -> Dengar)")
        }
    }

    private fun selectRecognitionMode(mode: RecognitionMode) {
        translationPipeline.setMode(mode)
        val isLetter = mode == RecognitionMode.LETTER
        binding.btnModeLetter.setBackgroundResource(
            if (isLetter) R.drawable.bg_figma_pill_active else 0
        )
        binding.btnModeLetter.setTextColor(
            if (isLetter) Color.WHITE else Color.parseColor("#80FFFFFF")
        )
        binding.btnModeWord.setBackgroundResource(
            if (!isLetter) R.drawable.bg_figma_pill_active else 0
        )
        binding.btnModeWord.setTextColor(
            if (!isLetter) Color.WHITE else Color.parseColor("#80FFFFFF")
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

        binding.btnDelegateCpu.setBackgroundResource(
            if (isCpu) R.drawable.bg_figma_pill_active else 0
        )
        binding.btnDelegateCpu.setTextColor(
            if (isCpu) Color.WHITE else Color.parseColor("#80FFFFFF")
        )

        val gpuBg = when {
            !isCpu -> R.drawable.bg_figma_pill_active
            else -> 0
        }
        binding.btnDelegateGpu.setBackgroundResource(gpuBg)
        binding.btnDelegateGpu.setTextColor(
            when {
                !isCpu -> Color.WHITE
                gpuAvailable -> Color.parseColor("#80FFFFFF")
                else -> Color.parseColor("#4DFFFFFF")
            }
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
