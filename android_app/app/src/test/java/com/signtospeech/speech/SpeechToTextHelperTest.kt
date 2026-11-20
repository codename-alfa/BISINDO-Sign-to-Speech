package com.signtospeech.speech

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit test for production SpeechToTextManager helpers (error mapping, SecurityException constant, RMS dB normalization).
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
    fun `test production normalizeRmsDb clamps and maps microphone decibels`() {
        assertEquals(0, SpeechToTextManager.normalizeRmsDb(-2f))
        assertEquals(100, SpeechToTextManager.normalizeRmsDb(10f))
        assertEquals(50, SpeechToTextManager.normalizeRmsDb(4f))
        assertEquals(0, SpeechToTextManager.normalizeRmsDb(-10f))
        assertEquals(100, SpeechToTextManager.normalizeRmsDb(20f))
    }

    @Test
    fun `test security exception error code is exported for UI keyboard fallback`() {
        assertEquals(-1, SpeechToTextManager.ERROR_SECURITY_EXCEPTION)
    }
}
