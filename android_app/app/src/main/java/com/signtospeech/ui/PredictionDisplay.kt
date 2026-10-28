package com.signtospeech.ui

import android.view.View
import androidx.core.content.ContextCompat
import com.signtospeech.R
import com.signtospeech.databinding.ActivityMainBinding
import com.signtospeech.ml.ModelConfig
import com.signtospeech.ml.RecognitionMode
import com.signtospeech.pipeline.TranslationPipeline
import java.util.Locale

/**
 * Mengelola pembaruan komponen UI bawah untuk menampilkan:
 * - Prediksi utama (Huruf A-Z atau Kata Dinamis) beserta persentase confidence & progress bar.
 * - Baris Top-3 fallback suggestions ("Mungkin: A 45% · S 30% · E 10%") saat confidence < 70%.
 * - Baris transkrip hasil commit beserta tombol hapus.
 */
class PredictionDisplay(
    private val binding: ActivityMainBinding,
    onClearTranscript: () -> Unit
) {

    init {
        binding.btnClearTranscript.setOnClickListener {
            onClearTranscript()
            binding.tvTranscript.text = binding.root.context.getString(R.string.transcript_placeholder)
        }
    }

    fun render(state: TranslationPipeline.UiState) {
        val ctx = binding.root.context

        // 1. Update transkrip
        if (state.committedTranscript.isEmpty()) {
            binding.tvTranscript.text = ctx.getString(R.string.transcript_placeholder)
        } else {
            binding.tvTranscript.text = state.committedTranscript.joinToString(" · ")
        }

        // 2. Jika mode Kata belum siap
        if (state.mode == RecognitionMode.WORD && !state.dynamicModelReady) {
            binding.tvPredictionLabel.text = "—"
            binding.tvPredictionLabel.setTextColor(ContextCompat.getColor(ctx, R.color.confidence_low))
            binding.tvConfidencePercent.text = "Mode Kata belum siap"
            binding.progressConfidence.progress = 0
            binding.tvSuggestions.visibility = View.VISIBLE
            binding.tvSuggestions.text = state.dynamicStatusNote ?: "Model kata dinamis belum tersedia"
            return
        }

        // 3. Jika tangan tidak terdeteksi
        if (!state.handDetected || state.currentResult == null) {
            binding.tvPredictionLabel.text = "—"
            binding.tvPredictionLabel.setTextColor(ContextCompat.getColor(ctx, R.color.white))
            binding.tvConfidencePercent.text = state.dynamicStatusNote ?: ctx.getString(R.string.waiting_gesture)
            binding.progressConfidence.progress = 0
            binding.tvSuggestions.visibility = View.GONE
            return
        }

        val res = state.currentResult
        val pct = (res.confidence * 100f).toInt().coerceIn(0, 100)

        // Jika model dinamis memprediksi _idle, tampilkan status tenang (tidak menampilkan '_idle' mentah)
        if (res.isIdleClass) {
            binding.tvPredictionLabel.text = "…"
            binding.tvPredictionLabel.setTextColor(ContextCompat.getColor(ctx, R.color.white))
            binding.tvConfidencePercent.text = state.dynamicStatusNote ?: "Menunggu gerakan isyarat kata..."
            binding.progressConfidence.progress = 0
            if (res.top3.isNotEmpty()) {
                binding.tvSuggestions.visibility = View.VISIBLE
                binding.tvSuggestions.text = formatTop3(res.top3.map { it.label to it.confidence })
            } else {
                binding.tvSuggestions.visibility = View.GONE
            }
            return
        }

        val isConfident = res.confidence >= ModelConfig.CONFIDENCE_THRESHOLD
        val accentColor = ContextCompat.getColor(
            ctx,
            if (isConfident) R.color.landmark_point else R.color.confidence_low
        )

        binding.tvPredictionLabel.text = res.label
        binding.tvPredictionLabel.setTextColor(accentColor)
        binding.progressConfidence.progress = pct

        val statusBadge = if (isConfident) "≥70% Stabil" else "<70% Ragu"
        val noteSuffix = if (!state.dynamicStatusNote.isNullOrBlank()) " · ${state.dynamicStatusNote}" else ""
        binding.tvConfidencePercent.text = String.format(
            Locale.US,
            "%d%% (%s)%s",
            pct,
            statusBadge,
            noteSuffix
        )

        if (!isConfident && res.top3.isNotEmpty()) {
            binding.tvSuggestions.visibility = View.VISIBLE
            binding.tvSuggestions.text = formatTop3(res.top3.map { it.label to it.confidence })
        } else {
            binding.tvSuggestions.visibility = View.GONE
        }
    }

    private fun formatTop3(items: List<Pair<String, Float>>): String {
        val formatted = items.joinToString(" · ") { (lbl, prob) ->
            String.format(Locale.US, "%s %d%%", lbl, (prob * 100f).toInt())
        }
        return "Mungkin: $formatted"
    }
}

