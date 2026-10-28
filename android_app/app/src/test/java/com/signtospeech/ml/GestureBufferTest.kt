package com.signtospeech.ml

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GestureBufferTest {

    private fun makeValidHandFrame(offsetX: Float = 0f): FloatArray {
        val pts = FloatArray(63)
        // Wrist di (0.5 + offsetX, 0.8, 0.0)
        pts[0] = 0.5f + offsetX
        pts[1] = 0.8f
        pts[2] = 0.0f
        // Middle MCP (index 9) di (0.5 + offsetX, 0.55, 0.0) -> handSize = 0.25
        pts[9 * 3 + 0] = 0.5f + offsetX
        pts[9 * 3 + 1] = 0.55f
        pts[9 * 3 + 2] = 0.0f
        return pts
    }

    @Test
    fun testTimeBasedEviction() {
        val buffer = GestureBuffer(windowMs = 1500L, maxGapMs = 300L)

        // Tambahkan frame setiap 100 ms dari t=0 sampai t=2000
        for (i in 0..20) {
            val tMs = i * 100L
            buffer.addFrame(tMs, makeValidHandFrame(i * 0.01f))
        }

        // Pada t=2000, batas simpan minimum adalah 2000 - (1500 + 300) = 200 ms
        val snap = buffer.snapshot()
        assertTrue(snap.isNotEmpty())
        assertEquals(200L, snap.first().timestampMs)
        assertEquals(2000L, snap.last().timestampMs)
    }

    @Test
    fun testGapResetOnAddFrameAndNoHand() {
        val buffer = GestureBuffer(windowMs = 1500L, maxGapMs = 300L)
        buffer.addFrame(100L, makeValidHandFrame())
        buffer.addFrame(250L, makeValidHandFrame())
        assertEquals(2, buffer.size())

        // Jeda 400 ms (> 300 ms maxGapMs) saat frame baru masuk -> entri lama dihapus otomatis
        buffer.addFrame(650L, makeValidHandFrame())
        assertEquals(1, buffer.size())
        assertEquals(650L, buffer.snapshot().first().timestampMs)

        // Jeda tanpa tangan > 300 ms -> buffer dikosongkan
        buffer.onNoHandDetected(1000L)
        assertTrue(buffer.isEmpty())
    }
}

