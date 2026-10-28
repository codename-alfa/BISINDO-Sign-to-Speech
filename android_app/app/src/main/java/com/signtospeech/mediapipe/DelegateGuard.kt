package com.signtospeech.mediapipe

import android.content.SharedPreferences

/**
 * Abstraksi penyimpanan sinkron untuk DelegateGuard.
 * Di produksi menggunakan SharedPreferences dengan `commit()` sinkron (bukan `apply()`)
 * agar penanda crash (sentinel) pasti tertulis ke disk sebelum native C++ init GPU dijalankan.
 */
interface DelegateStore {
    fun getString(key: String, def: String): String
    fun getBoolean(key: String, def: Boolean): Boolean
    fun commit(key: String, value: String)
    fun commit(key: String, value: Boolean)
}

class SharedPreferencesDelegateStore(
    private val prefs: SharedPreferences
) : DelegateStore {
    override fun getString(key: String, def: String): String =
        prefs.getString(key, def) ?: def

    override fun getBoolean(key: String, def: Boolean): Boolean =
        prefs.getBoolean(key, def)

    @Suppress("ApplySharedPref")
    override fun commit(key: String, value: String) {
        prefs.edit().putString(key, value).commit()
    }

    @Suppress("ApplySharedPref")
    override fun commit(key: String, value: Boolean) {
        prefs.edit().putBoolean(key, value).commit()
    }
}

/**
 * Pengaman 3 lapis untuk pemilihan delegate MediaPipe (CPU vs GPU):
 * 1. Emulator (AVD) otomatis terkunci di CPU (`isGpuAvailable() == false`).
 * 2. Crash Sentinel: sebelum init GPU, `markGpuAttempt()` menulis `KEY_PENDING = true` secara sinkron.
 *    Setelah hasil inferensi GPU pertama berhasil diterima, `markGpuConfirmed()` menghapus `KEY_PENDING`
 *    dan menandai `KEY_CONFIRMED = true`. Jika aplikasi mati (mis. native SIGABRT di C++ OpenGL/OpenCL)
 *    sebelum konfirmasi, maka pada saat startup berikutnya `resolveStartupMode()` mendeteksi
 *    `KEY_PENDING == true`, memblokir GPU (`KEY_BLOCKED = true`), dan menjalankan aplikasi di CPU.
 * 3. Graceful Fallback: jika kegagalan tertangkap sebagai exception Kotlin biasa, panggil
 *    `markGpuFailedGracefully()` yang mereset `KEY_PENDING = false` tanpa memblokir permanen.
 */
class DelegateGuard(
    private val store: DelegateStore,
    val isEmulator: Boolean
) {

    /**
     * Apakah segmen GPU boleh dipilih oleh pengguna di UI?
     */
    fun isGpuAvailable(): Boolean = !isEmulator && !store.getBoolean(KEY_BLOCKED, false)

    /**
     * Dipanggil tepat satu kali saat aplikasi mulai untuk menentukan delegate awal
     * sekaligus memeriksa apakah sesi sebelumnya mati mendadak saat menginisialisasi GPU.
     */
    fun resolveStartupMode(): DelegateMode {
        if (store.getBoolean(KEY_PENDING, false)) {
            // Sesi sebelumnya crash di level native sebelum GPU menghasilkan frame pertama
            store.commit(KEY_BLOCKED, true)
            store.commit(KEY_PENDING, false)
            store.commit(KEY_CONFIRMED, false)
            return DelegateMode.CPU
        }
        val saved = store.getString(KEY_PREFERRED, DelegateMode.CPU.name)
        return if (
            saved == DelegateMode.GPU.name &&
            isGpuAvailable() &&
            store.getBoolean(KEY_CONFIRMED, false)
        ) {
            DelegateMode.GPU
        } else {
            DelegateMode.CPU
        }
    }

    fun markGpuAttempt() {
        store.commit(KEY_PENDING, true)
    }

    fun markGpuConfirmed() {
        store.commit(KEY_PENDING, false)
        store.commit(KEY_CONFIRMED, true)
    }

    fun markGpuFailedGracefully() {
        store.commit(KEY_PENDING, false)
    }

    fun savePreferred(mode: DelegateMode) {
        store.commit(KEY_PREFERRED, mode.name)
    }

    fun wasBlockedByCrash(): Boolean = store.getBoolean(KEY_BLOCKED, false)

    fun resetBlock() {
        store.commit(KEY_BLOCKED, false)
        store.commit(KEY_PENDING, false)
        store.commit(KEY_CONFIRMED, false)
    }

    companion object {
        const val PREFS_NAME = "signtospeech_delegate_prefs"
        const val KEY_PREFERRED = "delegate_preferred"
        const val KEY_PENDING = "gpu_init_pending"
        const val KEY_CONFIRMED = "gpu_confirmed_working"
        const val KEY_BLOCKED = "gpu_blocked_by_crash"
    }
}

