package com.signtospeech.ui

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import com.signtospeech.debug.AppLogger
import com.signtospeech.speech.ServiceCard

/**
 * HapticFeedbackHelper menyediakan getaran haptik aksesibilitas bagi pengguna Tuli:
 * - GESTURE_COMMITTED: getaran singkat (45ms) saat gestur huruf/kata Arah 1 stabil terkunci (>= 70%).
 * - SERVICE_CARD_MATCHED: getaran ganda saat kartu bantuan layanan publik Arah 2 muncul.
 * - EMERGENCY_ALERT: getaran tiga kali tegas saat terdeteksi kategori DARURAT pada transkrip Arah 2.
 */
class HapticFeedbackHelper(private val context: Context) {

    enum class PulseType {
        GESTURE_COMMITTED,
        SERVICE_CARD_MATCHED,
        EMERGENCY_ALERT
    }

    private val vibrator: Vibrator? by lazy {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val vibratorManager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
                vibratorManager?.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
            }
        } catch (e: Exception) {
            AppLogger.w(TAG, "Gagal menginisialisasi Vibrator: ${e.message}")
            null
        }
    }

    fun vibrate(type: PulseType) {
        try {
            val vib = vibrator ?: return
            if (!vib.hasVibrator()) {
                AppLogger.d(TAG, "Perangkat tidak memiliki hardware motor getar.")
                return
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val effect = when (type) {
                    PulseType.GESTURE_COMMITTED -> {
                        VibrationEffect.createOneShot(45L, VibrationEffect.DEFAULT_AMPLITUDE)
                    }
                    PulseType.SERVICE_CARD_MATCHED -> {
                        val timings = longArrayOf(0L, 55L, 65L, 80L)
                        VibrationEffect.createWaveform(timings, -1)
                    }
                    PulseType.EMERGENCY_ALERT -> {
                        val timings = longArrayOf(0L, 110L, 70L, 110L, 70L, 160L)
                        VibrationEffect.createWaveform(timings, -1)
                    }
                }
                vib.vibrate(effect)
            } else {
                @Suppress("DEPRECATION")
                when (type) {
                    PulseType.GESTURE_COMMITTED -> vib.vibrate(45L)
                    PulseType.SERVICE_CARD_MATCHED -> vib.vibrate(longArrayOf(0L, 55L, 65L, 80L), -1)
                    PulseType.EMERGENCY_ALERT -> vib.vibrate(longArrayOf(0L, 110L, 70L, 110L, 70L, 160L), -1)
                }
            }
            AppLogger.d(TAG, "Haptic pulse triggered: $type")
        } catch (e: Exception) {
            AppLogger.w(TAG, "Gagal memicu haptic feedback: ${e.message}")
        }
    }

    companion object {
        private const val TAG = "HapticFeedbackHelper"

        /**
         * Menentukan tipe getaran berdasarkan daftar kartu visual yang cocok.
         * Mengutamakan EMERGENCY_ALERT jika terdapat kategori DARURAT.
         */
        fun resolvePulseForCards(cards: List<ServiceCard>): PulseType? {
            if (cards.isEmpty()) return null
            val hasEmergency = cards.any { it.categoryId.equals("DARURAT", ignoreCase = true) }
            return if (hasEmergency) PulseType.EMERGENCY_ALERT else PulseType.SERVICE_CARD_MATCHED
        }
    }
}

