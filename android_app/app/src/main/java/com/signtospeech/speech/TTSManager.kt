package com.signtospeech.speech

import android.content.Context
import android.content.Intent
import android.speech.tts.TextToSpeech
import android.util.Log
import java.util.Locale

/**
 * TTSManager mengelola Android TextToSpeech untuk Bahasa Indonesia (`id-ID`):
 * - Mendeteksi ketersediaan data suara Bahasa Indonesia (`LANG_MISSING_DATA` / `LANG_NOT_SUPPORTED`).
 * - Menyediakan `speak(text)` dengan `QUEUE_FLUSH` dan debounce agar tidak menumpuk antrean suara.
 * - Mendukung fitur mute/unmute dari UI.
 */
class TTSManager(
    private val context: Context,
    private val onMissingVoiceData: (() -> Unit)? = null
) : TextToSpeech.OnInitListener {

    private var tts: TextToSpeech? = null

    @Volatile
    var isReady: Boolean = false
        private set

    @Volatile
    var isMuted: Boolean = false

    private var lastSpokenText: String? = null
    private var lastSpokenTimeMs: Long = 0L

    init {
        try {
            tts = TextToSpeech(context.applicationContext, this)
        } catch (e: Exception) {
            Log.e(TAG, "Gagal menginisialisasi TextToSpeech: ${e.message}", e)
        }
    }

    override fun onInit(status: Int) {
        if (status != TextToSpeech.SUCCESS) {
            Log.w(TAG, "Inisialisasi TextToSpeech gagal dengan status: $status")
            isReady = false
            return
        }

        val engine = tts ?: return
        val indoLocale = Locale("id", "ID")
        val result = engine.setLanguage(indoLocale)

        when (result) {
            TextToSpeech.LANG_MISSING_DATA, TextToSpeech.LANG_NOT_SUPPORTED -> {
                Log.w(TAG, "Paket suara Bahasa Indonesia (id-ID) belum terinstal (code=$result)")
                // Tetap aktifkan engine dengan locale default agar di emulator tetap bisa bersuara
                isReady = true
                onMissingVoiceData?.invoke()
            }
            else -> {
                engine.setPitch(1.0f)
                engine.setSpeechRate(1.0f)
                isReady = true
                Log.d(TAG, "TextToSpeech Bahasa Indonesia (id-ID) siap digunakan")
            }
        }
    }

    fun speak(text: String, force: Boolean = false) {
        if (isMuted || !isReady || text.isBlank() || text.startsWith("_")) return

        val now = System.currentTimeMillis()
        if (!force && text == lastSpokenText && (now - lastSpokenTimeMs) < DEBOUNCE_MS) {
            return
        }

        lastSpokenText = text
        lastSpokenTimeMs = now
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "utt_${now}")
    }

    fun toggleMute(): Boolean {
        isMuted = !isMuted
        if (isMuted) {
            tts?.stop()
        }
        return isMuted
    }

    fun createInstallVoiceDataIntent(): Intent {
        return Intent(TextToSpeech.Engine.ACTION_INSTALL_TTS_DATA).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }

    fun shutdown() {
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (e: Exception) {
            Log.w(TAG, "Error saat menutup TextToSpeech: ${e.message}")
        } finally {
            tts = null
            isReady = false
        }
    }

    companion object {
        private const val TAG = "TTSManager"
        private const val DEBOUNCE_MS = 1200L
    }
}

