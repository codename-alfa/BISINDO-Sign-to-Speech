package com.signtospeech.ml

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PredictionStabilizerTest {

    private fun pred(label: String, conf: Float): PredictionResult {
        return PredictionResult(
            label = label,
            confidence = conf,
            top3 = listOf(ScoredLabel(label, conf)),
            inferenceTimeMs = 1.0f
        )
    }

    @Test
    fun testStaticLetterThresholdAndHoldConsistency() {
        val stabilizer = PredictionStabilizer(
            confidenceThreshold = 0.70f,
            staticMinFrames = 3,
            staticMinHoldMs = 400L,
            sameLabelCooldownMs = 2000L
        )

        // Di bawah threshold (< 70%) -> tidak pernah commit
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("A", 0.65f), 0L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("A", 0.68f), 250L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("A", 0.69f), 500L).committedLabel)

        // Di atas threshold (>= 70%) selama 3 frame dan >= 400 ms -> commit tepat satu kali
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("B", 0.92f), 1000L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("B", 0.90f), 1200L).committedLabel)
        val out3 = stabilizer.update(RecognitionMode.LETTER, pred("B", 0.95f), 1450L)
        assertEquals("B", out3.committedLabel)

        // Jika "B" terus ditahan dalam < 2000 ms, tidak di-commit ulang (anti-spam TTS)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("B", 0.95f), 1600L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("B", 0.95f), 1850L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("B", 0.95f), 2100L).committedLabel)

        // Huruf berbeda ("C") langsung bisa di-commit tanpa menunggu 2 detik dari "B"
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("C", 0.88f), 2200L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.LETTER, pred("C", 0.88f), 2400L).committedLabel)
        assertEquals("C", stabilizer.update(RecognitionMode.LETTER, pred("C", 0.91f), 2650L).committedLabel)
    }

    @Test
    fun testDynamicWordIdleNeverCommitsAndCooldownApplies() {
        val stabilizer = PredictionStabilizer(
            confidenceThreshold = 0.70f,
            dynamicMinEvals = 2,
            dynamicCooldownMs = 1000L,
            sameLabelCooldownMs = 2000L
        )

        // _idle dengan confidence 99% sekalipun TIDAK PERNAH di-commit
        for (i in 0..5) {
            val out = stabilizer.update(RecognitionMode.WORD, pred("_idle", 0.99f), i * 200L)
            assertNull(out.committedLabel)
            assertFalse(out.shouldClearBuffer)
        }

        // Kata "Halo" muncul 2 evaluasi berturut-turut (>= 70%) -> commit + clear buffer
        val eval1 = stabilizer.update(RecognitionMode.WORD, pred("Halo", 0.85f), 2000L)
        assertNull(eval1.committedLabel)
        val eval2 = stabilizer.update(RecognitionMode.WORD, pred("Halo", 0.88f), 2200L)
        assertEquals("Halo", eval2.committedLabel)
        assertTrue(eval2.shouldClearBuffer)

        // Dalam cooldown 1000 ms (sampai t=3200), kata lain pun ditahan agar tidak dobel trigger
        assertNull(stabilizer.update(RecognitionMode.WORD, pred("Ya", 0.90f), 2500L).committedLabel)
        assertNull(stabilizer.update(RecognitionMode.WORD, pred("Ya", 0.92f), 2800L).committedLabel)

        // Setelah cooldown selesai (> 3200 ms), kata "Ya" bisa di-commit dalam 2 evaluasi
        assertNull(stabilizer.update(RecognitionMode.WORD, pred("Ya", 0.90f), 3300L).committedLabel)
        val evalYa = stabilizer.update(RecognitionMode.WORD, pred("Ya", 0.93f), 3500L)
        assertEquals("Ya", evalYa.committedLabel)
        assertTrue(evalYa.shouldClearBuffer)
    }
}

