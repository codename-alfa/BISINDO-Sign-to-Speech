package com.signtospeech.speech

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

/**
 * SpeechToTextManager mengelola pengenalan ucapan Bahasa Indonesia (id-ID)
 * menggunakan Android native SpeechRecognizer dengan arsitektur tangguh:
 * - Thread-safety: Seluruh interaksi SpeechRecognizer dieksekusi di Main/UI thread.
 * - OEM Shield (HyperOS / Xiaomi / Redmi): Mendeteksi layanan Google TTS / GMS secara eksplisit
 *   guna menghindari SecurityException / binder crash pada com.miui.voiceassist.
 * - Smart Offline-First: Mencoba mode offline terlebih dahulu; jika paket bahasa offline
 *   belum diunduh (error 12/13), otomatis fallback ke mode standar tanpa crash.
 * - Fallback Intent Handler: Jika in-app recognizer tidak diizinkan atau crash oleh sistem OS,
 *   otomatis mengalihkan ke dialog suara sistem (ACTION_RECOGNIZE_SPEECH).
 * - Toggle Tap-to-Start / Tap-to-Stop: Sesuai preferensi kontrol pengguna.
 * - Streaming Partial Results: Teks langsung tampil ke layar saat pembicara bersuara.
 * - RMS Level Callback: Menampilkan bar visualisasi level input suara mikrofon.
 */
class SpeechToTextManager(
    private val context: Context,
    private val onPartialResult: (String) -> Unit,
    private val onFinalResult: (String) -> Unit,
    private val onRmsChanged: (Float) -> Unit,
    private val onListeningStateChanged: (Boolean) -> Unit,
    private val onError: (Int, String) -> Unit,
    private val onOfflineModeChanged: (Boolean) -> Unit,
    private val onFallbackToIntentRequested: (() -> Unit)? = null
) {

    private val mainHandler = Handler(Looper.getMainLooper())
    private var speechRecognizer: SpeechRecognizer? = null

    var isListening: Boolean = false
        private set

    var isOfflinePreferred: Boolean = true
        private set

    var isServiceAvailable: Boolean = false
        private set

    private var retryWithoutOffline: Boolean = false

    init {
        mainHandler.post {
            initRecognizer()
        }
    }

    /**
     * Menginisialisasi SpeechRecognizer dengan penanganan multi-layer untuk mencegah
     * SecurityException / crash pada MIUI / HyperOS (Xiaomi / Redmi).
     */
    fun initRecognizer() {
        try {
            speechRecognizer?.destroy()
        } catch (t: Throwable) {
            Log.w(TAG, "Pengecualian saat membersihkan recognizer lama", t)
        }
        speechRecognizer = null
        isServiceAvailable = false

        // 1. Cek layanan RecognitionService yang terdaftar di perangkat
        val serviceIntent = Intent("android.speech.RecognitionService")
        val availableServices = try {
            context.packageManager.queryIntentServices(serviceIntent, 0)
        } catch (t: Throwable) {
            emptyList()
        }

        Log.d(TAG, "Layanan speech recognition terdeteksi: ${availableServices.map { it.serviceInfo.packageName }}")

        // 2. Prioritas 1: Google Speech Services (paling stabil & bebas SecurityException di HyperOS)
        val googleServices = listOf(
            ComponentName("com.google.android.tts", "com.google.android.apps.speech.tts.googletts.service.GoogleTTSRecognitionService"),
            ComponentName("com.google.android.googlequicksearchbox", "com.google.android.voicesearch.service.RecognitionService")
        )

        for (googleComp in googleServices) {
            try {
                val recognizer = SpeechRecognizer.createSpeechRecognizer(context, googleComp)
                recognizer.setRecognitionListener(createListener())
                speechRecognizer = recognizer
                isServiceAvailable = true
                Log.d(TAG, "SpeechRecognizer berhasil dibuat via Google service: $googleComp")
                return
            } catch (t: Throwable) {
                Log.w(TAG, "Gagal mengikat ke $googleComp: ${t.message}")
            }
        }

        // 3. Prioritas 2: Coba layanan pihak ketiga non-MIUI yang terdaftar
        for (resolveInfo in availableServices) {
            val pkg = resolveInfo.serviceInfo.packageName
            // Hindari com.miui.voiceassist yang sering melempar SecurityException pada aplikasi pihak ketiga
            if (pkg.contains("miui") || pkg.contains("xiaomi")) {
                continue
            }
            try {
                val comp = ComponentName(pkg, resolveInfo.serviceInfo.name)
                val recognizer = SpeechRecognizer.createSpeechRecognizer(context, comp)
                recognizer.setRecognitionListener(createListener())
                speechRecognizer = recognizer
                isServiceAvailable = true
                Log.d(TAG, "SpeechRecognizer berhasil dibuat via service: $comp")
                return
            } catch (t: Throwable) {
                Log.w(TAG, "Gagal mengikat ke service $pkg: ${t.message}")
            }
        }

        // 4. Prioritas 3: Default createSpeechRecognizer(context) dengan perlindungan Throwable
        try {
            if (SpeechRecognizer.isRecognitionAvailable(context)) {
                val recognizer = SpeechRecognizer.createSpeechRecognizer(context)
                recognizer.setRecognitionListener(createListener())
                speechRecognizer = recognizer
                isServiceAvailable = true
                Log.d(TAG, "SpeechRecognizer berhasil dibuat via default createSpeechRecognizer")
                return
            }
        } catch (t: Throwable) {
            Log.e(TAG, "SecurityException/Throwable saat createSpeechRecognizer default: ${t.message}", t)
            speechRecognizer = null
            isServiceAvailable = false
        }

        Log.w(TAG, "In-app SpeechRecognizer tidak dapat diaktifkan. Akan menggunakan Fallback System Voice Dialog.")
    }

    private fun createListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                Log.d(TAG, "onReadyForSpeech: Mikrofon aktif dan siap menerima suara")
                isListening = true
                onListeningStateChanged(true)
            }

            override fun onBeginningOfSpeech() {
                Log.d(TAG, "onBeginningOfSpeech: Pengguna mulai berbicara")
            }

            override fun onRmsChanged(rmsdB: Float) {
                onRmsChanged(rmsdB)
            }

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {
                Log.d(TAG, "onEndOfSpeech: Suara berhenti terdeteksi")
                isListening = false
                onListeningStateChanged(false)
            }

            override fun onError(error: Int) {
                Log.w(TAG, "onError: kode error = $error")
                isListening = false
                onListeningStateChanged(false)

                // Cek apakah error karena paket bahasa offline tidak tersedia (12 atau 13)
                if ((error == 12 || error == 13) && isOfflinePreferred) {
                    Log.i(TAG, "Bahasa offline id-ID tidak tersedia. Beralih otomatis ke mode standar/online...")
                    isOfflinePreferred = false
                    onOfflineModeChanged(false)
                    retryWithoutOffline = true
                    mainHandler.postDelayed({
                        startListeningInternal(preferOffline = false)
                    }, 200)
                    return
                }

                // Jika terjadi ERROR_CLIENT (5) atau ERROR_INSUFFICIENT_PERMISSIONS pada OEM ROM,
                // alihkan otomatis ke fallback dialog suara sistem yang 100% aman
                if (error == SpeechRecognizer.ERROR_CLIENT || error == SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS) {
                    Log.w(TAG, "Error client/binding pada SpeechRecognizer. Mengaktifkan fallback dialog suara sistem...")
                    onFallbackToIntentRequested?.invoke()
                    return
                }

                val message = mapErrorCodeToMessage(error)
                onError(error, message)
            }

            override fun onResults(results: Bundle?) {
                isListening = false
                onListeningStateChanged(false)

                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val recognizedText = matches?.firstOrNull()?.trim()
                if (!recognizedText.isNullOrEmpty()) {
                    Log.d(TAG, "onResults (Final): $recognizedText")
                    onFinalResult(recognizedText)
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull()?.trim()
                if (!text.isNullOrEmpty()) {
                    Log.d(TAG, "onPartialResults: $text")
                    onPartialResult(text)
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    /**
     * Memulai atau menghentikan listening secara toggle (Tap-to-Start / Tap-to-Stop).
     */
    fun toggleListening() {
        if (isListening) {
            stopListening()
        } else {
            startListening()
        }
    }

    /**
     * Memulai mendengarkan mikrofon.
     */
    fun startListening() {
        startListeningInternal(preferOffline = isOfflinePreferred)
    }

    private fun startListeningInternal(preferOffline: Boolean) {
        mainHandler.post {
            if (speechRecognizer == null || !isServiceAvailable) {
                initRecognizer()
            }

            // Jika in-app SpeechRecognizer tetap tidak tersedia di perangkat ini (misal Redmi Pad 2 tanpa GMS),
            // langsung panggil dialog suara sistem bawaan OS tanpa crash!
            if (speechRecognizer == null || !isServiceAvailable) {
                Log.w(TAG, "SpeechRecognizer tidak tersedia, mengalihkan ke system voice dialog...")
                onFallbackToIntentRequested?.invoke()
                return@post
            }

            try {
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "id-ID")
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "id-ID")
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)

                    // Hanya sertakan flag offline jika mode offline aktif
                    if (preferOffline) {
                        putExtra(EXTRA_PREFER_OFFLINE, true)
                    }
                }

                speechRecognizer?.startListening(intent)
                isListening = true
                onListeningStateChanged(true)
                onOfflineModeChanged(preferOffline)
                Log.d(TAG, "Mulai mendengarkan (preferOffline: $preferOffline)")
            } catch (t: Throwable) {
                Log.e(TAG, "Pengecualian saat speechRecognizer.startListening: ${t.message}", t)
                isListening = false
                onListeningStateChanged(false)
                // Fallback instan ke dialog suara sistem
                onFallbackToIntentRequested?.invoke()
            }
        }
    }

    /**
     * Menghentikan perekaman dan menunggu hasil pengenalan akhir.
     */
    fun stopListening() {
        mainHandler.post {
            try {
                speechRecognizer?.stopListening()
            } catch (t: Throwable) {
                Log.w(TAG, "Pengecualian saat stopListening", t)
            } finally {
                isListening = false
                onListeningStateChanged(false)
                Log.d(TAG, "Perekaman suara dihentikan oleh pengguna")
            }
        }
    }

    /**
     * Membatalkan proses pengenalan suara tanpa memproses hasil.
     */
    fun cancel() {
        mainHandler.post {
            try {
                speechRecognizer?.cancel()
            } catch (t: Throwable) {
                Log.w(TAG, "Pengecualian saat cancel", t)
            } finally {
                isListening = false
                onListeningStateChanged(false)
            }
        }
    }

    /**
     * Membersihkan alokasi native SpeechRecognizer saat activity di-destroy.
     */
    fun destroy() {
        mainHandler.post {
            try {
                speechRecognizer?.destroy()
            } catch (t: Throwable) {
                Log.w(TAG, "Pengecualian saat destroy SpeechRecognizer", t)
            } finally {
                speechRecognizer = null
                isListening = false
                isServiceAvailable = false
                Log.d(TAG, "SpeechRecognizer berhasil di-destroy")
            }
        }
    }

    companion object {
        private const val TAG = "SpeechToTextManager"
        private const val EXTRA_PREFER_OFFLINE = "android.speech.extra.PREFER_OFFLINE"

        /**
         * Pemetaan kode error native Android ke pesan ramah pengguna berbahasa Indonesia.
         */
        fun mapErrorCodeToMessage(errorCode: Int): String {
            return when (errorCode) {
                SpeechRecognizer.ERROR_AUDIO -> "Kesalahan perekaman mikrofon audio."
                SpeechRecognizer.ERROR_CLIENT -> "Kesalahan aplikasi klien suara."
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Izin mikrofon (RECORD_AUDIO) belum diberikan."
                SpeechRecognizer.ERROR_NETWORK -> "Koneksi internet bermasalah."
                SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Waktu koneksi jaringan habis."
                SpeechRecognizer.ERROR_NO_MATCH -> "Tidak ada ucapan yang terdeteksi. Silakan coba lagi."
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Layanan pengenalan suara sedang sibuk."
                SpeechRecognizer.ERROR_SERVER -> "Terjadi kesalahan pada server pengenalan suara."
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Tidak ada suara yang terdengar."
                12 -> "Paket bahasa offline belum diunduh di sistem."
                13 -> "Bahasa offline tidak didukung oleh perangkat."
                else -> "Gagal mengenali suara (Kode error: $errorCode)."
            }
        }
    }
}
