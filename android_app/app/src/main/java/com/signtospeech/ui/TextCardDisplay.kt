package com.signtospeech.ui

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.text.SpannableString
import android.text.Spanned
import android.text.style.BackgroundColorSpan
import android.text.style.ForegroundColorSpan
import android.text.style.StyleSpan
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.signtospeech.R
import com.signtospeech.speech.HighlightSpan
import com.signtospeech.speech.KeywordMatcher
import com.signtospeech.speech.MatchAnalysis
import com.signtospeech.speech.ServiceCard

/**
 * TextCardDisplay mengontrol tampilan Arah 2 (Dengar -> Tuli):
 * - Menampilkan transkripsi suara berukuran besar (26sp High-Contrast).
 * - Memberi sorotan warna cerah (Spannable) pada kata kunci konteks layanan publik.
 * - Merender Kartu Visual (Visual Assistance Cards) kontekstual.
 * - Mengelola bar visualisasi audio level input mikrofon.
 * - Mengelola baris input keyboard inline dan chip kalimat cepat (Quick Presets).
 */
class TextCardDisplay(
    private val context: Context,
    private val tvSpeechTranscript: TextView,
    private val tvSpeechStatus: TextView,
    private val tvCardsHeader: TextView,
    private val llVisualCards: LinearLayout,
    private val llQuickPresets: LinearLayout,
    private val progressAudioLevel: ProgressBar,
    private val btnToggleMic: View,
    private val tvMicIcon: TextView,
    private val tvMicLabel: TextView,
    private val tvArah2ModeBadge: TextView,
    private val btnArah2DebugLog: View,
    private val btnArah2Clear: TextView,
    private val scrollArah2Content: ScrollView,
    private val etArah2KeyboardInput: EditText,
    private val btnSubmitKeyboard: View,
    private val onPresetSelected: (String) -> Unit,
    private val onManualInputSubmitted: (String) -> Unit,
    private val onClearClicked: () -> Unit,
    private val onToggleMicClicked: () -> Unit,
    private val onToggleModeClicked: () -> Unit,
    private val onShowLogClicked: () -> Unit
) {

    init {
        setupListeners()
        populateQuickPresets()
    }

    private fun setupListeners() {
        btnToggleMic.setOnClickListener {
            onToggleMicClicked()
        }

        btnArah2Clear.setOnClickListener {
            clear()
            onClearClicked()
        }

        tvArah2ModeBadge.setOnClickListener {
            onToggleModeClicked()
        }

        btnArah2DebugLog.setOnClickListener {
            onShowLogClicked()
        }

        btnSubmitKeyboard.setOnClickListener {
            submitKeyboardText()
        }

        etArah2KeyboardInput.setOnEditorActionListener { _, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_SEND ||
                actionId == EditorInfo.IME_ACTION_DONE ||
                (event != null && event.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)
            ) {
                submitKeyboardText()
                true
            } else {
                false
            }
        }
    }

    private fun populateQuickPresets() {
        llQuickPresets.removeAllViews()
        for (preset in KeywordMatcher.QUICK_PRESETS) {
            val chip = TextView(context).apply {
                text = preset
                textSize = 12f
                setTextColor(Color.WHITE)
                setBackgroundResource(R.color.chip_inactive_bg)
                setPadding(dpToPx(12), dpToPx(6), dpToPx(12), dpToPx(6))
                isClickable = true
                isFocusable = true
                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    setMargins(0, 0, dpToPx(8), 0)
                }
                layoutParams = params
                setOnClickListener {
                    onPresetSelected(preset)
                }
            }
            llQuickPresets.addView(chip)
        }
    }

    /**
     * Memperbarui tampilan transkrip teks dan kartu visual berdasarkan analisis kata kunci.
     */
    fun updateAnalysis(analysis: MatchAnalysis) {
        if (analysis.text.isBlank()) {
            clear()
            return
        }

        // 1. Format teks dengan SpannableString untuk highlight kata kunci
        val spannable = SpannableString(analysis.text)
        for (highlight in analysis.highlights) {
            val parsedColor = try {
                Color.parseColor(highlight.colorHex)
            } catch (e: Exception) {
                Color.parseColor("#38BDF8")
            }

            // Foreground warna terang
            spannable.setSpan(
                ForegroundColorSpan(parsedColor),
                highlight.start,
                highlight.end,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            // Style Bold
            spannable.setSpan(
                StyleSpan(Typeface.BOLD),
                highlight.start,
                highlight.end,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            // Background tint lembut (30% alpha)
            val bgTint = Color.argb(
                70,
                Color.red(parsedColor),
                Color.green(parsedColor),
                Color.blue(parsedColor)
            )
            spannable.setSpan(
                BackgroundColorSpan(bgTint),
                highlight.start,
                highlight.end,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
        }

        tvSpeechTranscript.text = spannable

        // 2. Render Kartu Visual jika kata kunci ditemukan
        renderVisualCards(analysis.matchedCards)

        // 3. Auto-scroll ke bawah agar teks terbaru selalu terbaca
        scrollArah2Content.post {
            scrollArah2Content.fullScroll(View.FOCUS_DOWN)
        }
    }

    private fun renderVisualCards(cards: List<ServiceCard>) {
        llVisualCards.removeAllViews()

        if (cards.isEmpty()) {
            tvCardsHeader.visibility = View.GONE
            return
        }

        tvCardsHeader.visibility = View.VISIBLE

        for (card in cards) {
            val cardView = createCardView(card)
            llVisualCards.addView(cardView)
        }
    }

    private fun createCardView(card: ServiceCard): View {
        val parsedColor = try {
            Color.parseColor(card.colorHex)
        } catch (e: Exception) {
            Color.parseColor("#38BDF8")
        }

        val cardLayout = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dpToPx(14), dpToPx(12), dpToPx(14), dpToPx(12))
            setBackgroundColor(ContextCompat.getColor(context, R.color.color_card_bg))
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, 0, 0, dpToPx(10))
            }
            layoutParams = params
            gravity = Gravity.CENTER_VERTICAL
        }

        // Ikon emoji besar
        val tvIcon = TextView(context).apply {
            text = card.icon
            textSize = 28f
            gravity = Gravity.CENTER
            setPadding(0, 0, dpToPx(12), 0)
        }
        cardLayout.addView(tvIcon)

        // Kontainer judul & panduan
        val textContainer = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            val params = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            )
            layoutParams = params
        }

        // Header: Kategori & Badge Kata Pemicu
        val headerRow = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val tvTitle = TextView(context).apply {
            text = card.title
            textSize = 15f
            setTextColor(parsedColor)
            typeface = Typeface.DEFAULT_BOLD
            val params = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            )
            layoutParams = params
        }
        headerRow.addView(tvTitle)

        val tvTrigger = TextView(context).apply {
            text = card.triggerKeyword.uppercase()
            textSize = 10f
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.argb(120, Color.red(parsedColor), Color.green(parsedColor), Color.blue(parsedColor)))
            setPadding(dpToPx(6), dpToPx(2), dpToPx(6), dpToPx(2))
            typeface = Typeface.DEFAULT_BOLD
        }
        headerRow.addView(tvTrigger)
        textContainer.addView(headerRow)

        // Subtitle panduan / arahan tindakan
        val tvAdvice = TextView(context).apply {
            text = card.advice
            textSize = 13f
            setTextColor(Color.WHITE)
            setPadding(0, dpToPx(4), 0, 0)
        }
        textContainer.addView(tvAdvice)

        cardLayout.addView(textContainer)
        return cardLayout
    }

    /**
     * Memperbarui visual tombol mikrofon dan status teks saat perekaman aktif / tidak aktif.
     */
    fun updateListeningState(isListening: Boolean) {
        if (isListening) {
            btnToggleMic.setBackgroundColor(ContextCompat.getColor(context, R.color.color_mic_active))
            tvMicIcon.text = "⏹️"
            tvMicLabel.text = context.getString(R.string.arah2_tap_to_stop)
            tvSpeechStatus.text = context.getString(R.string.arah2_listening)
            tvSpeechStatus.setTextColor(ContextCompat.getColor(context, R.color.color_mic_active))
        } else {
            btnToggleMic.setBackgroundColor(ContextCompat.getColor(context, R.color.color_mic_idle))
            tvMicIcon.text = "🎤"
            tvMicLabel.text = context.getString(R.string.arah2_tap_to_start)
            tvSpeechStatus.text = context.getString(R.string.arah2_instruction)
            tvSpeechStatus.setTextColor(ContextCompat.getColor(context, R.color.text_muted))
            progressAudioLevel.progress = 0
        }
    }

    /**
     * Memperbarui progress bar audio level dari desibel mikrofon (-2 s.d. +10 dB).
     */
    fun updateAudioLevel(rmsdB: Float) {
        // Normalisasi rmsdB (-2 s.d. 10 dB) ke rentang 0 s.d. 100%
        val normalized = (((rmsdB + 2f) / 12f) * 100f).coerceIn(0f, 100f).toInt()
        progressAudioLevel.progress = normalized
    }

    /**
     * Memperbarui indikator status offline vs online.
     */
    fun updateOfflineBadge(isOffline: Boolean) {
        if (isOffline) {
            tvArah2ModeBadge.text = context.getString(R.string.arah2_mode_offline)
            tvArah2ModeBadge.setTextColor(ContextCompat.getColor(context, R.color.landmark_point))
        } else {
            tvArah2ModeBadge.text = context.getString(R.string.arah2_mode_online)
            tvArah2ModeBadge.setTextColor(ContextCompat.getColor(context, R.color.color_nav_active))
        }
    }

    /**
     * Menghapus transkrip dan kartu visual kembali ke kondisi awal.
     */
    fun clear() {
        tvSpeechTranscript.text = context.getString(R.string.arah2_placeholder)
        llVisualCards.removeAllViews()
        tvCardsHeader.visibility = View.GONE
        progressAudioLevel.progress = 0
        etArah2KeyboardInput.text?.clear()
    }

    /**
     * Mengirim teks yang diketik via keyboard inline ke pemroses kata kunci dan kartu visual.
     */
    private fun submitKeyboardText() {
        val text = etArah2KeyboardInput.text.toString().trim()
        if (text.isNotEmpty()) {
            onManualInputSubmitted(text)
            etArah2KeyboardInput.text?.clear()
            hideSoftKeyboard(etArah2KeyboardInput)
        }
    }

    /**
     * Menyembunyikan virtual soft keyboard setelah teks dikirimkan.
     */
    private fun hideSoftKeyboard(view: View) {
        val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.hideSoftInputFromWindow(view.windowToken, 0)
        view.clearFocus()
    }

    private fun dpToPx(dp: Int): Int {
        val density = context.resources.displayMetrics.density
        return (dp * density).toInt()
    }
}

