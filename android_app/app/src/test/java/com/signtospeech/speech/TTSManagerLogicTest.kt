package com.signtospeech.speech

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for TTSManager playback gating and debounce logic.
 */
class TTSManagerLogicTest {

    @Test
    fun `test rejects muted, unready, blank, or internal idle labels`() {
        assertFalse(TTSManager.shouldSpeak("Halo", isMuted = true, isReady = true, force = false, lastSpokenText = "", elapsedSinceLastMs = 5000L))
        assertFalse(TTSManager.shouldSpeak("Halo", isMuted = false, isReady = false, force = false, lastSpokenText = "", elapsedSinceLastMs = 5000L))
        assertFalse(TTSManager.shouldSpeak("   ", isMuted = false, isReady = true, force = false, lastSpokenText = "", elapsedSinceLastMs = 5000L))
        assertFalse(TTSManager.shouldSpeak("_idle", isMuted = false, isReady = true, force = true, lastSpokenText = "", elapsedSinceLastMs = 5000L))
    }

    @Test
    fun `test debounces duplicate text within window unless forced`() {
        assertFalse(TTSManager.shouldSpeak("Terima kasih", isMuted = false, isReady = true, force = false, lastSpokenText = "Terima kasih", elapsedSinceLastMs = 600L))
        assertTrue(TTSManager.shouldSpeak("Terima kasih", isMuted = false, isReady = true, force = true, lastSpokenText = "Terima kasih", elapsedSinceLastMs = 600L))
        assertTrue(TTSManager.shouldSpeak("Terima kasih", isMuted = false, isReady = true, force = false, lastSpokenText = "Terima kasih", elapsedSinceLastMs = 1500L))
        assertTrue(TTSManager.shouldSpeak("Tolong", isMuted = false, isReady = true, force = false, lastSpokenText = "Terima kasih", elapsedSinceLastMs = 200L))
    }
}
