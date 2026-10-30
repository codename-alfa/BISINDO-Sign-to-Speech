package com.signtospeech.debug

import android.content.Context
import android.util.Log

/**
 * CrashHandler mencegat seluruh uncaught exception di thread mana pun,
 * mencatat stack trace lengkap dan metadata diagnostik via AppLogger,
 * serta memastikan log tersimpan ke disk sebelum proses dihentikan OS.
 */
class CrashHandler private constructor(
    private val context: Context,
    private val defaultHandler: Thread.UncaughtExceptionHandler?
) : Thread.UncaughtExceptionHandler {

    override fun uncaughtException(thread: Thread, throwable: Throwable) {
        try {
            Log.e(TAG, "Uncaught exception terdeteksi pada thread [${thread.name}]", throwable)
            AppLogger.saveCrashDump(context, throwable)
        } catch (t: Throwable) {
            Log.e(TAG, "Gagal menyimpan crash dump di CrashHandler", t)
        } finally {
            // Teruskan ke default Android system handler
            defaultHandler?.uncaughtException(thread, throwable)
        }
    }

    companion object {
        private const val TAG = "CrashHandler"

        fun install(context: Context) {
            val currentHandler = Thread.getDefaultUncaughtExceptionHandler()
            if (currentHandler !is CrashHandler) {
                val handler = CrashHandler(context.applicationContext, currentHandler)
                Thread.setDefaultUncaughtExceptionHandler(handler)
                Log.d(TAG, "CrashHandler berhasil dipasang sebagai default uncaught exception handler.")
            }
        }
    }
}

