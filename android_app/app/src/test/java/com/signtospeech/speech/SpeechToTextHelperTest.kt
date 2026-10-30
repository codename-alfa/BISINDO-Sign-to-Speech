package com.signtospeech.speech

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit Test untuk fungsi pembantu Speech-to-Text (pemetaan error dan penanganan nilai desibel).
 */
class SpeechToTextHelperTest {

    @Test
    fun `test error code mapping returns user friendly indonesian strings`() {
        val audioMsg = SpeechToTextManager.mapErrorCodeToMessage(3) // ERROR_AUDIO
        assertTrue(audioMsg.contains("audio") || audioMsg.contains("mikrofon"))

        val permMsg = SpeechToTextManager.mapErrorCodeToMessage(9) // ERROR_INSUFFICIENT_PERMISSIONS
        assertTrue(permMsg.contains("izin") || permMsg.contains("RECORD_AUDIO"))

        val offline12 = SpeechToTextManager.mapErrorCodeToMessage(12)
        assertTrue(offline12.contains("offline"))

        val offline13 = SpeechToTextManager.mapErrorCodeToMessage(13)
        assertTrue(offline13.contains("offline"))

        val unknown = SpeechToTextManager.mapErrorCodeToMessage(999)
        assertTrue(unknown.contains("999"))
    }

    @Test
    fun `test rms audio decibel normalization range`() {
        // Rentang rmsdB mikrofon -2dB s.d 10dB dinormalisasi ke 0 s.d. 100%
        val minRms = -2f
        val maxRms = 10f
        val midRms = 4f

        fun normalize(rmsdB: Float): Int {
            return (((rmsdB + 2f) / 12f) * 100f).coerceIn(0f, 100f).toInt()
        }

        assertEquals(0, normalize(minRms))
        assertEquals(100, normalize(maxRms))
        assertEquals(50, normalize(midRms))
        assertEquals(0, normalize(-10f)) // bawah batas
        assertEquals(100, normalize(20f)) // atas batas
    }

    @Test
    fun `test blacklisted stt packages protects against security exceptions`() {
        val blacklist = SpeechToTextManager.BLACKLISTED_STT_PACKAGES
        // Memastikan paket yang unexported atau internal di-blacklist
        assertTrue(blacklist.contains("com.google.android.tts"))
        assertTrue(blacklist.contains("com.google.android.as"))
        assertTrue(blacklist.contains("com.miui.voiceassist"))
        assertTrue(blacklist.contains("com.xiaomi.mibrain.speech"))

        // Memastikan Google Search app resmi TIDAK di-blacklist
        assertTrue(!blacklist.contains("com.google.android.googlequicksearchbox"))
    }
}

