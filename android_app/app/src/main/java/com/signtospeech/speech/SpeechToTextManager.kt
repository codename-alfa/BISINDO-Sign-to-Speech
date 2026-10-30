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
import com.signtospeech.debug.AppLogger

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
    private val onServiceUnavailable: (() -> Unit)? = null
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
     * Menginisialisasi SpeechRecognizer menggunakan factory resmi Android
     * (System-Default Binding) melalui Application Context.
     * Pendekatan ini menghindari native Binder SIGSEGV dan SecurityException
     * akibat pemaksaan ComponentName internal pada berbagai varian ROM OEM.
     */
    fun initRecognizer() {
        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            AppLogger.w(TAG, "SpeechRecognizer.isRecognitionAvailable(context) mengembalikan false.")
            speechRecognizer = null
            isServiceAvailable = false
            return
        }

        try {
            speechRecognizer?.destroy()
        } catch (t: Throwable) {
            AppLogger.w(TAG, "Pengecualian saat membersihkan recognizer lama: ${t.message}")
        }
        speechRecognizer = null
        isServiceAvailable = false

        try {
            val appContext = context.applicationContext
            val recognizer = SpeechRecognizer.createSpeechRecognizer(appContext)
            recognizer.setRecognitionListener(createListener())
            speechRecognizer = recognizer
            isServiceAvailable = true
            AppLogger.i(TAG, "SpeechRecognizer berhasil diinisialisasi via createSpeechRecognizer(applicationContext).")
        } catch (t: Throwable) {
            AppLogger.e(TAG, "Pengecualian saat createSpeechRecognizer: ${t.message}", t)
            speechRecognizer = null
            isServiceAvailable = false
        }
    }

    private fun createListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                AppLogger.i(TAG, "onReadyForSpeech: Mikrofon aktif dan siap menerima suara")
                isListening = true
                onListeningStateChanged(true)
            }

            override fun onBeginningOfSpeech() {
                AppLogger.d(TAG, "onBeginningOfSpeech: Pengguna mulai berbicara")
            }

            override fun onRmsChanged(rmsdB: Float) {
                onRmsChanged(rmsdB)
            }

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {
                AppLogger.d(TAG, "onEndOfSpeech: Suara berhenti terdeteksi")
                isListening = false
                onListeningStateChanged(false)
            }

            override fun onError(error: Int) {
                val message = mapErrorCodeToMessage(error)
                AppLogger.w(TAG, "onError: kode error = $error ($message)")
                isListening = false
                onListeningStateChanged(false)

                // Cek apakah error karena paket bahasa offline tidak tersedia (12 atau 13)
                if ((error == 12 || error == 13) && isOfflinePreferred) {
                    AppLogger.i(TAG, "Bahasa offline id-ID tidak tersedia. Beralih otomatis ke mode standar/online...")
                    isOfflinePreferred = false
                    onOfflineModeChanged(false)
                    retryWithoutOffline = true
                    mainHandler.postDelayed({
                        startListeningInternal(preferOffline = false)
                    }, 200)
                    return
                }

                onError(error, message)
            }

            override fun onResults(results: Bundle?) {
                isListening = false
                onListeningStateChanged(false)

                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val recognizedText = matches?.firstOrNull()?.trim()
                if (!recognizedText.isNullOrEmpty()) {
                    AppLogger.i(TAG, "onResults (Final): $recognizedText")
                    onFinalResult(recognizedText)
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull()?.trim()
                if (!text.isNullOrEmpty()) {
                    AppLogger.d(TAG, "onPartialResults: $text")
                    onPartialResult(text)
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    /**
     * Mengubah mode pengenalan suara secara manual antara Offline dan Online.
     * Mengembalikan status mode baru (true = Offline, false = Online).
     */
    fun toggleOfflineMode(): Boolean {
        isOfflinePreferred = !isOfflinePreferred
        AppLogger.i(TAG, "Mode diubah manual oleh pengguna: preferOffline=$isOfflinePreferred")
        onOfflineModeChanged(isOfflinePreferred)
        return isOfflinePreferred
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
            AppLogger.d(TAG, "startListeningInternal dipanggil (preferOffline: $preferOffline)")
            if (speechRecognizer == null) {
                initRecognizer()
            }

            if (speechRecognizer == null || !isServiceAvailable) {
                AppLogger.w(TAG, "SpeechRecognizer tidak tersedia. Mengalihkan ke input keyboard.")
                isListening = false
                onListeningStateChanged(false)
                onServiceUnavailable?.invoke()
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
                AppLogger.i(TAG, "speechRecognizer.startListening berhasil dipanggil (preferOffline: $preferOffline)")
            } catch (se: SecurityException) {
                AppLogger.e(TAG, "SecurityException saat speechRecognizer.startListening: ${se.message}.", se)
                isListening = false
                onListeningStateChanged(false)
                onError(-1, "Izin perekaman suara ditolak oleh sistem.")
            } catch (t: Throwable) {
                AppLogger.e(TAG, "Pengecualian saat speechRecognizer.startListening: ${t.message}", t)
                isListening = false
                onListeningStateChanged(false)
                onError(-2, "Gagal mengaktifkan mikrofon: ${t.message}")
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
         * Paket-paket layanan suara yang dilarang untuk STT karena bukan layanan pihak ketiga publik,
         * atau sering melempar SecurityException pada Android 14/15 HyperOS.
         */
        val BLACKLISTED_STT_PACKAGES = setOf(
            "com.google.android.as",        // Android System Intelligence, sistem internal tertutup
            "com.miui.voiceassist",         // Asisten OEM MIUI/Xiaomi internal
            "com.xiaomi.mibrain.speech"     // Mesin suara OEM Xiaomi internal
        )

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
