package com.signtospeech.ui

import android.graphics.Typeface
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.signtospeech.R
import com.signtospeech.databinding.ActivityMainBinding
import com.signtospeech.ml.ModelConfig
import com.signtospeech.ml.RecognitionMode
import com.signtospeech.pipeline.TranslationPipeline
import java.util.Locale

/**
 * Mengelola pembaruan komponen UI bawah untuk menampilkan:
 * - Prediksi utama (Huruf A-Z, Angka 1-10, atau Kata Dinamis) beserta persentase confidence & progress bar.
 * - Baris Top-3 fallback suggestions ("Mungkin: A 45% · S 30% · E 10%") saat confidence < 70%.
 * - Baris Interactive Quick Suggestion Chips (tombol koreksi mandiri 1-ketukan untuk pasangan
 *   Huruf <-> Angka yang bentuk jarinya mirip seperti V <-> 2, D <-> 1, W <-> 6, B <-> 4).
 * - Baris transkrip hasil commit beserta tombol Hapus (hapus 1 terakhir) dan Clear (hapus semua).
 */
class PredictionDisplay(
    private val binding: ActivityMainBinding,
    private val onSuggestionSelected: (String) -> Unit = {},
    private val onDeleteLastTranscript: () -> Unit = {},
    onClearTranscript: () -> Unit
) {

    private var lastRenderedSuggestionBase: String? = null
    private var lastRenderedCandidates: List<String> = emptyList()

    init {
        binding.btnDeleteLastTranscript.setOnClickListener {
            lastRenderedSuggestionBase = null
            lastRenderedCandidates = emptyList()
            onDeleteLastTranscript()
        }

        binding.btnClearTranscript.setOnClickListener {
            lastRenderedSuggestionBase = null
            lastRenderedCandidates = emptyList()
            onClearTranscript()
            binding.tvTranscript.text = binding.root.context.getString(R.string.transcript_placeholder)
            binding.llQuickSuggestions.visibility = View.GONE
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
            binding.llQuickSuggestions.visibility = View.GONE
            return
        }

        // 3. Jika tangan tidak terdeteksi, tetap pertahankan Quick Suggestion dari label terakhir yang di-commit
        // agar user Tuli leluasa mengetuk tombol koreksi setelah menurunkan tangan!
        if (!state.handDetected || state.currentResult == null) {
            binding.tvPredictionLabel.text = state.lastCommittedLabel ?: "—"
            binding.tvPredictionLabel.setTextColor(ContextCompat.getColor(ctx, R.color.white))
            binding.tvConfidencePercent.text = state.dynamicStatusNote ?: ctx.getString(R.string.waiting_gesture)
            binding.progressConfidence.progress = 0
            binding.tvSuggestions.visibility = View.GONE

            val committedBase = state.lastCommittedLabel
            if (committedBase != null && state.mode == RecognitionMode.LETTER) {
                val quickAlts = ModelConfig.resolveQuickSuggestions(committedBase, emptyList())
                renderQuickSuggestionChips(committedBase, quickAlts)
            } else {
                binding.llQuickSuggestions.visibility = View.GONE
            }
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
            binding.llQuickSuggestions.visibility = View.GONE
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

        if (state.mode == RecognitionMode.LETTER) {
            val baseLabel = state.lastCommittedLabel ?: res.label
            val quickAlts = ModelConfig.resolveQuickSuggestions(baseLabel, res.top3)
            renderQuickSuggestionChips(baseLabel, quickAlts)
        } else {
            binding.llQuickSuggestions.visibility = View.GONE
        }
    }

    private fun renderQuickSuggestionChips(baseLabel: String, candidates: List<String>) {
        if (candidates.isEmpty()) {
            binding.llQuickSuggestions.visibility = View.GONE
            lastRenderedSuggestionBase = null
            lastRenderedCandidates = emptyList()
            return
        }

        binding.llQuickSuggestions.visibility = View.VISIBLE
        if (baseLabel == lastRenderedSuggestionBase && candidates == lastRenderedCandidates) {
            return
        }
        lastRenderedSuggestionBase = baseLabel
        lastRenderedCandidates = candidates

        val ctx = binding.root.context
        val density = ctx.resources.displayMetrics.density
        fun dp(v: Int): Int = (v * density).toInt()

        binding.llQuickSuggestions.removeAllViews()

        val titleView = TextView(ctx).apply {
            text = "Koreksi cepat:"
            textSize = 11f
            setTextColor(ContextCompat.getColor(ctx, R.color.text_muted))
            setPadding(0, 0, dp(6), 0)
        }
        binding.llQuickSuggestions.addView(titleView)

        for (altLabel in candidates) {
            val chip = TextView(ctx).apply {
                val kindPrefix = if (altLabel.all { it.isDigit() }) "Angka" else "Huruf"
                text = "↻ $kindPrefix $altLabel"
                textSize = 11f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(ContextCompat.getColor(ctx, R.color.white))
                setBackgroundColor(ContextCompat.getColor(ctx, R.color.chip_inactive_bg))
                setPadding(dp(10), dp(4), dp(10), dp(4))
                gravity = Gravity.CENTER
                isClickable = true
                isFocusable = true
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    marginEnd = dp(6)
                }
                layoutParams = params
                setOnClickListener {
                    onSuggestionSelected(altLabel)
                }
            }
            binding.llQuickSuggestions.addView(chip)
        }
    }

    private fun formatTop3(items: List<Pair<String, Float>>): String {
        val formatted = items.joinToString(" · ") { (lbl, prob) ->
            String.format(Locale.US, "%s %d%%", lbl, (prob * 100f).toInt())
        }
        return "Mungkin: $formatted"
    }
}
