package com.signtospeech.debug

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.speech.RecognizerIntent
import android.util.Log
import androidx.core.content.ContextCompat
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.LinkedList
import java.util.Locale

/**
 * AppLogger adalah singleton diagnostik internal untuk merekam kondisi perangkat,
 * jejak eksekusi speech recognition, dan pencegah crash.
 * Menggunakan Circular Ring Buffer (maksimal 100 entri) agar ukuran tidak membengkak,
 * serta menyimpan salinan ke berkas fisik internal (app_debug.log).
 */
object AppLogger {

    private const val TAG = "AppLogger"
    private const val MAX_ENTRIES = 100
    private const val LOG_FILE_NAME = "app_debug.log"
    private const val CRASH_FILE_NAME = "latest_crash.txt"

    private val timeFormat = SimpleDateFormat("HH:mm:ss.SSS", Locale.getDefault())
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())

    private val logBuffer = LinkedList<String>()
    private var appContext: Context? = null

    // Cache metadata perangkat
    var deviceSummary: String = "Unknown"
        private set
    var detectedSpeechServices: List<String> = emptyList()
        private set
    var detectedSpeechActivities: List<String> = emptyList()
        private set

    @Synchronized
    fun init(context: Context) {
        val appCtx = context.applicationContext
        appContext = appCtx

        // Kumpulkan metadata perangkat
        deviceSummary = "Model: ${Build.MANUFACTURER} ${Build.MODEL} (${Build.DEVICE}) | " +
                "Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}) | " +
                "Build: ${Build.DISPLAY}"

        // Deteksi paket RecognitionService yang terdaftar di OS
        try {
            val serviceIntent = Intent("android.speech.RecognitionService")
            val services = appCtx.packageManager.queryIntentServices(serviceIntent, 0)
            detectedSpeechServices = services.map {
                "${it.serviceInfo.packageName}/${it.serviceInfo.name}"
            }
        } catch (t: Throwable) {
            detectedSpeechServices = listOf("Error querying services: ${t.message}")
        }

        // Deteksi aktivitas yang merespons ACTION_RECOGNIZE_SPEECH (Dialog suara)
        try {
            val actionIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            val activities = appCtx.packageManager.queryIntentActivities(actionIntent, 0)
            detectedSpeechActivities = activities.map {
                "${it.activityInfo.packageName}/${it.activityInfo.name}"
            }
        } catch (t: Throwable) {
            detectedSpeechActivities = listOf("Error querying activities: ${t.message}")
        }

        i("AppLogger", "=== App Initialized ===")
        i("AppLogger", deviceSummary)
        i("AppLogger", "RecognitionServices terdeteksi: $detectedSpeechServices")
        i("AppLogger", "SpeechActivities terdeteksi: $detectedSpeechActivities")

        // Verifikasi izin
        val hasMic = ContextCompat.checkSelfPermission(appCtx, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        val hasNet = ContextCompat.checkSelfPermission(appCtx, Manifest.permission.INTERNET) == PackageManager.PERMISSION_GRANTED
        i("AppLogger", "Permissions: RECORD_AUDIO=$hasMic, INTERNET=$hasNet")
    }

    @Synchronized
    fun d(tag: String, message: String) {
        Log.d(tag, message)
        appendEntry("DEBUG", tag, message)
    }

    @Synchronized
    fun i(tag: String, message: String) {
        Log.i(tag, message)
        appendEntry("INFO", tag, message)
    }

    @Synchronized
    fun w(tag: String, message: String) {
        Log.w(tag, message)
        appendEntry("WARN", tag, message)
    }

    @Synchronized
    fun e(tag: String, message: String, tr: Throwable? = null) {
        Log.e(tag, message, tr)
        val fullMsg = if (tr != null) {
            val sw = StringWriter()
            tr.printStackTrace(PrintWriter(sw))
            "$message\n$sw"
        } else {
            message
        }
        appendEntry("ERROR", tag, fullMsg)
    }

    private fun appendEntry(level: String, tag: String, message: String) {
        val timestamp = timeFormat.format(Date())
        val entry = "[$timestamp][$level][$tag] $message"

        if (logBuffer.size >= MAX_ENTRIES) {
            logBuffer.removeFirst()
        }
        logBuffer.addLast(entry)

        // Tulis berkala ke file
        appContext?.let { ctx ->
            try {
                flushToFile(ctx)
            } catch (ignored: Throwable) {}
        }
    }

    /**
     * Menghasilkan teks diagnostik lengkap yang siap disalin ke clipboard.
     */
    @Synchronized
    fun getFormattedDiagnostics(): String {
        val sb = StringBuilder()
        sb.append("========================================\n")
        sb.append("SIGN-TO-SPEECH DIAGNOSTIC REPORT\n")
        sb.append("Waktu: ").append(dateFormat.format(Date())).append("\n")
        sb.append("========================================\n\n")

        sb.append("--- SPESIFIKASI PERANGKAT ---\n")
        sb.append(deviceSummary).append("\n\n")

        sb.append("--- LAYANAN SUARA TERDETEKSI (RecognitionService) ---\n")
        if (detectedSpeechServices.isEmpty()) {
            sb.append("TIDAK ADA LAYANAN PENGENAL SUARA TERDAFTAR!\n")
        } else {
            detectedSpeechServices.forEach { sb.append("• ").append(it).append("\n") }
        }
        sb.append("\n")

        sb.append("--- AKTIVITAS DIALOG SUARA (ACTION_RECOGNIZE_SPEECH) ---\n")
        if (detectedSpeechActivities.isEmpty()) {
            sb.append("TIDAK ADA DIALOG SUARA SISTEM TERSEDIA!\n")
        } else {
            detectedSpeechActivities.forEach { sb.append("• ").append(it).append("\n") }
        }
        sb.append("\n")

        appContext?.let { ctx ->
            if (hasPreviousCrash(ctx)) {
                sb.append("--- CRASH TERAKHIR TERCATAT ---\n")
                sb.append(getLatestCrashDump(ctx)).append("\n\n")
            }
        }

        sb.append("--- RIWAYAT EVENT TERAKHIR (Maks ").append(MAX_ENTRIES).append(" Event) ---\n")
        logBuffer.forEach { sb.append(it).append("\n") }

        return sb.toString()
    }

    /**
     * Menyimpan seluruh laporan diagnostik lengkap ke berkas fisik internal app_debug.log,
     * termasuk metadata perangkat, layanan suara terdeteksi, riwayat crash fatal (jika ada),
     * dan seluruh buffer event log.
     */
    @Synchronized
    fun flushToFile(context: Context) {
        val logFile = File(context.filesDir, LOG_FILE_NAME)
        val fullReport = getFormattedDiagnostics()
        logFile.writeText(fullReport)
    }

    /**
     * Alias publik untuk mendapatkan seluruh laporan diagnostik terformat.
     */
    fun exportFullDiagnosticReport(): String = getFormattedDiagnostics()

    /**
     * Mendapatkan referensi berkas log fisik untuk keperluan dibagikan (Share Intent).
     */
    fun getLogFile(context: Context): File {
        flushToFile(context)
        return File(context.filesDir, LOG_FILE_NAME)
    }

    /**
     * Menyimpan dump exception crash ke berkas permanen latest_crash.txt.
     */
    @Synchronized
    fun saveCrashDump(context: Context, throwable: Throwable) {
        val sw = StringWriter()
        throwable.printStackTrace(PrintWriter(sw))
        val rawStackTrace = sw.toString()
        val stackTrace = if (rawStackTrace.length > 20_000) {
            rawStackTrace.take(10_000) + "\n... [Stack trace dipotong karena terlalu panjang: ${rawStackTrace.length} karakter] ...\n" + rawStackTrace.takeLast(5_000)
        } else {
            rawStackTrace
        }

        e("CRASH_SENTINEL", "FATAL UNCAUGHT EXCEPTION: ${throwable.javaClass.name}: ${throwable.message}", throwable)

        val crashFile = File(context.filesDir, CRASH_FILE_NAME)
        crashFile.printWriter().use { out ->
            out.println("========================================")
            out.println("FATAL CRASH DUMP")
            out.println("Waktu: ${dateFormat.format(Date())}")
            out.println("Perangkat: $deviceSummary")
            out.println("RecognitionServices: $detectedSpeechServices")
            out.println("SpeechActivities: $detectedSpeechActivities")
            out.println("========================================")
            out.println("Exception: ${throwable.javaClass.name}")
            out.println("Pesan: ${throwable.message}")
            out.println("\nStack Trace Lengkap:")
            out.println(stackTrace)
            out.println("========================================")
            out.println("Riwayat Event Sebelum Crash:")
            logBuffer.forEach { out.println(it) }
        }
        flushToFile(context)
    }

    fun hasPreviousCrash(context: Context): Boolean {
        val crashFile = File(context.filesDir, CRASH_FILE_NAME)
        return crashFile.exists() && crashFile.length() > 0
    }

    fun getLatestCrashDump(context: Context): String? {
        val crashFile = File(context.filesDir, CRASH_FILE_NAME)
        return if (crashFile.exists()) {
            crashFile.readText()
        } else {
            null
        }
    }

    @Synchronized
    fun clearCrashDump(context: Context) {
        val crashFile = File(context.filesDir, CRASH_FILE_NAME)
        if (crashFile.exists()) {
            crashFile.delete()
        }
    }

    @Synchronized
    fun clearLogs(context: Context) {
        logBuffer.clear()
        clearCrashDump(context)
        val logFile = File(context.filesDir, LOG_FILE_NAME)
        if (logFile.exists()) {
            logFile.delete()
        }
        i("AppLogger", "Log dan crash dump telah dibersihkan.")
    }
}

