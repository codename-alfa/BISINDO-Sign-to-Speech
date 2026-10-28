package com.signtospeech.mediapipe

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DelegateGuardTest {

    private class FakeDelegateStore : DelegateStore {
        private val strings = mutableMapOf<String, String>()
        private val booleans = mutableMapOf<String, Boolean>()

        override fun getString(key: String, def: String): String = strings[key] ?: def
        override fun getBoolean(key: String, def: Boolean): Boolean = booleans[key] ?: def

        override fun commit(key: String, value: String) {
            strings[key] = value
        }

        override fun commit(key: String, value: Boolean) {
            booleans[key] = value
        }
    }

    @Test
    fun testScenario1_FreshInstallStartsOnCpu() {
        val store = FakeDelegateStore()
        val guard = DelegateGuard(store, isEmulator = false)

        assertTrue(guard.isGpuAvailable())
        assertFalse(guard.wasBlockedByCrash())
        assertEquals(DelegateMode.CPU, guard.resolveStartupMode())
    }

    @Test
    fun testScenario2_EmulatorAlwaysLockedToCpu() {
        val store = FakeDelegateStore()
        val guard = DelegateGuard(store, isEmulator = true)

        guard.savePreferred(DelegateMode.GPU)
        guard.markGpuConfirmed()

        assertFalse(guard.isGpuAvailable())
        assertEquals(DelegateMode.CPU, guard.resolveStartupMode())
    }

    @Test
    fun testScenario3_UnconfirmedGpuAttemptBlocksGpuOnNextRestart() {
        val store = FakeDelegateStore()
        val session1 = DelegateGuard(store, isEmulator = false)

        session1.savePreferred(DelegateMode.GPU)
        session1.markGpuAttempt()
        // Simulasikan native C++ SIGABRT crash sebelum markGpuConfirmed() sempat dipanggil

        val session2 = DelegateGuard(store, isEmulator = false)
        assertEquals(DelegateMode.CPU, session2.resolveStartupMode())
        assertTrue(session2.wasBlockedByCrash())
        assertFalse(session2.isGpuAvailable())
    }

    @Test
    fun testScenario4_ConfirmedGpuPersistsAcrossRestart() {
        val store = FakeDelegateStore()
        val session1 = DelegateGuard(store, isEmulator = false)

        session1.savePreferred(DelegateMode.GPU)
        session1.markGpuAttempt()
        session1.markGpuConfirmed()

        val session2 = DelegateGuard(store, isEmulator = false)
        assertEquals(DelegateMode.GPU, session2.resolveStartupMode())
        assertFalse(session2.wasBlockedByCrash())
        assertTrue(session2.isGpuAvailable())
    }

    @Test
    fun testScenario5_GracefulFailureDoesNotBlockPermanently() {
        val store = FakeDelegateStore()
        val session1 = DelegateGuard(store, isEmulator = false)

        session1.savePreferred(DelegateMode.GPU)
        session1.markGpuAttempt()
        session1.markGpuFailedGracefully()

        val session2 = DelegateGuard(store, isEmulator = false)
        // Karena belum pernah confirmed, startup tetap aman di CPU, tetapi tidak terblokir permanen
        assertEquals(DelegateMode.CPU, session2.resolveStartupMode())
        assertFalse(session2.wasBlockedByCrash())
        assertTrue(session2.isGpuAvailable())
    }

    @Test
    fun testScenario6_ResetBlockReEnablesGpuOption() {
        val store = FakeDelegateStore()
        val guard = DelegateGuard(store, isEmulator = false)

        guard.markGpuAttempt()
        // Restart mendeteksi crash -> memblokir GPU
        assertEquals(DelegateMode.CPU, guard.resolveStartupMode())
        assertTrue(guard.wasBlockedByCrash())
        assertFalse(guard.isGpuAvailable())

        // Pengguna menekan lama tombol GPU untuk mereset blokir
        guard.resetBlock()
        assertFalse(guard.wasBlockedByCrash())
        assertTrue(guard.isGpuAvailable())
        assertEquals(DelegateMode.CPU, guard.resolveStartupMode())
    }
}

