package com.signtospeech.ui

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
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
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.core.content.res.ResourcesCompat
import com.signtospeech.R
import com.signtospeech.speech.KeywordMatcher
import com.signtospeech.speech.MatchAnalysis
import com.signtospeech.speech.ServiceCard

/**
 * TextCardDisplay mengontrol antarmuka Arah 2 (Dengar -> Tuli):
 * - Menampilkan transkripsi suara berukuran besar (28sp High-Contrast Inter).
 * - Memberi sorotan warna cerah (Spannable) pada kata kunci konteks layanan publik.
 * - Merender Kartu Bantuan Visual berikon vektor (Material Symbols Rounded) dan bebas emoji.
 * - Mengelola bar visualisasi audio level input mikrofon di kartu transkrip.
 * - Mengelola baris input keyboard inline dan chip kalimat cepat (Quick Presets).
 * - Mendukung Alur Keputusan Q2: Klik preset mengisi kolom input untuk diedit sebelum klik Tampilkan.
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
    private val tvMicIcon: TextView? = null,
    private val tvMicLabel: TextView,
    private val tvArah2ModeBadge: TextView,
    private val btnArah2DebugLog: View,
    private val btnArah2Clear: TextView,
    private val scrollArah2Content: ScrollView,
    private val etArah2KeyboardInput: EditText,
    private val btnSubmitKeyboard: View,
    private val btnArah2Edit: View? = null,
    private val ivMicIcon: ImageView? = null,
    private val hudDot: View? = null,
    private val hudContainer: View? = null,
    private val onPresetSelected: (String) -> Unit,
    private val onManualInputSubmitted: (String) -> Unit,
    private val onClearClicked: () -> Unit,
    private val onToggleMicClicked: () -> Unit,
    private val onToggleModeClicked: () -> Unit,
    private val onShowLogClicked: () -> Unit,
    private val onCardsMatched: ((List<ServiceCard>) -> Unit)? = null
) {

    private var lastMatchedCardSignatures = emptySet<String>()
    private var lastRenderedRawText = ""
    private var activePresetView: View? = null

    private val fontBold: Typeface by lazy {
        try {
            ResourcesCompat.getFont(context, R.font.inter_bold) ?: Typeface.DEFAULT_BOLD
        } catch (e: Exception) {
            Typeface.DEFAULT_BOLD
        }
    }

    private val fontSemibold: Typeface by lazy {
        try {
            ResourcesCompat.getFont(context, R.font.inter_semibold) ?: Typeface.DEFAULT_BOLD
        } catch (e: Exception) {
            Typeface.DEFAULT_BOLD
        }
    }

    private val fontRegular: Typeface by lazy {
        try {
            ResourcesCompat.getFont(context, R.font.inter_regular) ?: Typeface.DEFAULT
        } catch (e: Exception) {
            Typeface.DEFAULT
        }
    }

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

        btnArah2Edit?.setOnClickListener {
            editCurrentTranscript()
        }

        tvArah2ModeBadge.setOnClickListener {
            onToggleModeClicked()
        }

        btnArah2DebugLog.setOnClickListener {
            onShowLogClicked()
        }

        hudContainer?.setOnLongClickListener {
            onShowLogClicked()
            true
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

        val labelMap = mapOf(
            "Tebus obat resep di apotek" to "Tebus obat di apotek",
            "Berapa total biaya di kasir?" to "Total biaya di kasir",
            "Poli pemeriksaan dokter di lantai 2" to "Poli pemeriksaan dokter",
            "Kondisi darurat medis! Segera bawa pasien ke ruang IGD sekarang." to "Kondisi darurat IGD",
            "Silakan ambil nomor antrean dan siapkan KTP" to "Nomor antrean & KTP"
        )

        for (preset in KeywordMatcher.QUICK_PRESETS) {
            val shortLabel = labelMap[preset] ?: preset
            val chip = TextView(context).apply {
                text = shortLabel
                textSize = 12f
                setTextColor(Color.WHITE)
                typeface = fontSemibold
                setBackgroundResource(R.drawable.bg_figma_action_chip)
                setPadding(dpToPx(12), dpToPx(7), dpToPx(12), dpToPx(7))
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
                    // Keputusan Opsi 2: Mengisi templat ke kolom input agar pengguna bisa memodifikasi (misal: lantai)
                    etArah2KeyboardInput.setText(preset)
                    etArah2KeyboardInput.setSelection(preset.length)
                    focusKeyboardInput()
                    highlightActivePreset(this)
                }
            }
            llQuickPresets.addView(chip)
        }
    }

    private fun highlightActivePreset(selectedView: View) {
        for (i in 0 until llQuickPresets.childCount) {
            val child = llQuickPresets.getChildAt(i)
            if (child == selectedView) {
                child.setBackgroundResource(R.drawable.bg_figma_sound_on)
            } else {
                child.setBackgroundResource(R.drawable.bg_figma_action_chip)
            }
        }
        activePresetView = selectedView
    }

    private fun clearPresetHighlight() {
        for (i in 0 until llQuickPresets.childCount) {
            val child = llQuickPresets.getChildAt(i)
            child.setBackgroundResource(R.drawable.bg_figma_action_chip)
        }
        activePresetView = null
    }

    private fun editCurrentTranscript() {
        if (lastRenderedRawText.isNotBlank()) {
            etArah2KeyboardInput.setText(lastRenderedRawText)
            etArah2KeyboardInput.setSelection(lastRenderedRawText.length)
            focusKeyboardInput()
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

        lastRenderedRawText = analysis.text

        // 1. Format teks dengan SpannableString untuk highlight kata kunci
        val spannable = SpannableString(analysis.text)
        for (highlight in analysis.highlights) {
            val parsedColor = try {
                Color.parseColor(highlight.colorHex)
            } catch (e: Exception) {
                Color.parseColor("#38BDF8")
            }

            spannable.setSpan(
                ForegroundColorSpan(parsedColor),
                highlight.start,
                highlight.end,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            spannable.setSpan(
                StyleSpan(Typeface.BOLD),
                highlight.start,
                highlight.end,
                Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
            )
            val bgTint = Color.argb(
                60,
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
        btnArah2Edit?.visibility = View.VISIBLE

        // 2. Render Kartu Visual jika kata kunci ditemukan
        renderVisualCards(analysis.matchedCards)

        if (analysis.matchedCards.isNotEmpty()) {
            val currentSignatures = analysis.matchedCards.map { "${it.categoryId}:${it.triggerKeyword}" }.toSet()
            if (currentSignatures != lastMatchedCardSignatures) {
                lastMatchedCardSignatures = currentSignatures
                onCardsMatched?.invoke(analysis.matchedCards)
            }
            tvSpeechStatus.text = context.getString(R.string.arah2_cards_header, analysis.matchedCards.size)
        } else {
            lastMatchedCardSignatures = emptySet()
            tvSpeechStatus.text = "Ucapan ditampilkan"
        }

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
        tvCardsHeader.text = context.getString(R.string.arah2_cards_header, cards.size)

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

        val cardBackground = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            setColor(ContextCompat.getColor(context, R.color.panel_bg))
            cornerRadius = dpToPx(14).toFloat()
            setStroke(dpToPx(1), Color.parseColor("#26FFFFFF"))
        }

        val cardLayout = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dpToPx(14), dpToPx(12), dpToPx(14), dpToPx(12))
            background = cardBackground
            val params = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            ).apply {
                setMargins(0, 0, 0, dpToPx(10))
            }
            layoutParams = params
            gravity = Gravity.CENTER_VERTICAL
        }

        // Ikon Vektor Material Symbols Rounded (Bebas Emoji)
        val iconRes = getVectorIconForCategory(card.categoryId)
        val iconBox = LinearLayout(context).apply {
            gravity = Gravity.CENTER
            setBackgroundResource(R.drawable.bg_figma_action_chip)
            setPadding(dpToPx(8), dpToPx(8), dpToPx(8), dpToPx(8))
            val params = LinearLayout.LayoutParams(dpToPx(40), dpToPx(40)).apply {
                setMargins(0, 0, dpToPx(12), 0)
            }
            layoutParams = params
        }

        val ivIcon = ImageView(context).apply {
            setImageResource(iconRes)
            imageTintList = ColorStateList.valueOf(parsedColor)
            val params = LinearLayout.LayoutParams(dpToPx(24), dpToPx(24))
            layoutParams = params
        }
        iconBox.addView(ivIcon)
        cardLayout.addView(iconBox)

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
            typeface = fontBold
            val params = LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            )
            layoutParams = params
        }
        headerRow.addView(tvTitle)

        val tvTrigger = TextView(context).apply {
            text = card.triggerKeyword.lowercase()
            textSize = 10f
            setTextColor(Color.WHITE)
            typeface = fontSemibold
            setBackgroundResource(R.drawable.bg_figma_action_chip)
            setPadding(dpToPx(8), dpToPx(3), dpToPx(8), dpToPx(3))
        }
        headerRow.addView(tvTrigger)
        textContainer.addView(headerRow)

        // Subtitle panduan / arahan tindakan
        val tvAdvice = TextView(context).apply {
            text = card.advice
            textSize = 13f
            setTextColor(Color.WHITE)
            typeface = fontRegular
            setPadding(0, dpToPx(4), 0, 0)
        }
        textContainer.addView(tvAdvice)

        cardLayout.addView(textContainer)
        return cardLayout
    }

    private fun getVectorIconForCategory(categoryId: String): Int {
        return when (categoryId.uppercase()) {
            "OBAT" -> R.drawable.ic_cat_obat
            "DOKTER" -> R.drawable.ic_cat_dokter
            "DARURAT" -> R.drawable.ic_cat_darurat
            "KASIR" -> R.drawable.ic_cat_kasir
            "TRANSPORTASI" -> R.drawable.ic_cat_transportasi
            "ARAH" -> R.drawable.ic_cat_arah
            "PENDAFTARAN" -> R.drawable.ic_cat_pendaftaran
            "BANTUAN" -> R.drawable.ic_cat_bantuan
            "SAPAAN" -> R.drawable.ic_cat_sapaan
            else -> R.drawable.ic_cat_obat
        }
    }

    /**
     * Memperbarui visual tombol mikrofon dan status teks saat perekaman aktif / tidak aktif.
     */
    fun updateListeningState(isListening: Boolean) {
        if (isListening) {
            btnToggleMic.setBackgroundResource(R.drawable.bg_figma_mic_active)
            ivMicIcon?.setImageResource(R.drawable.ic_mic_off_24dp)
            btnToggleMic.contentDescription = "Mute mikrofon"
            tvMicLabel.text = ""
            tvMicLabel.visibility = View.GONE
            tvSpeechStatus.text = context.getString(R.string.arah2_listening)
            val redColor = ContextCompat.getColor(context, R.color.color_mic_active)
            tvSpeechStatus.setTextColor(redColor)
            hudDot?.backgroundTintList = ColorStateList.valueOf(redColor)
        } else {
            btnToggleMic.setBackgroundResource(R.drawable.bg_figma_mic_idle)
            ivMicIcon?.setImageResource(R.drawable.ic_mic_24dp)
            btnToggleMic.contentDescription = "Mulai rekam"
            tvMicLabel.text = ""
            tvMicLabel.visibility = View.GONE
            tvSpeechStatus.text = context.getString(R.string.arah2_instruction)
            val greenColor = ContextCompat.getColor(context, R.color.landmark_point)
            tvSpeechStatus.setTextColor(greenColor)
            hudDot?.backgroundTintList = ColorStateList.valueOf(greenColor)
            progressAudioLevel.progress = 0
        }
    }

    /**
     * Memperbarui progress bar audio level dari desibel mikrofon (-2 s.d. +10 dB).
     */
    fun updateAudioLevel(rmsdB: Float) {
        val normalized = (((rmsdB + 2f) / 12f) * 100f).coerceIn(0f, 100f).toInt()
        progressAudioLevel.progress = normalized
    }

    /**
     * Memperbarui indikator status offline vs online.
     */
    fun updateOfflineBadge(isOffline: Boolean) {
        if (isOffline) {
            tvArah2ModeBadge.text = context.getString(R.string.arah2_mode_offline)
            tvArah2ModeBadge.setTextColor(Color.WHITE)
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
        lastMatchedCardSignatures = emptySet()
        lastRenderedRawText = ""
        btnArah2Edit?.visibility = View.GONE
        clearPresetHighlight()
        val greenColor = ContextCompat.getColor(context, R.color.landmark_point)
        tvSpeechStatus.text = context.getString(R.string.arah2_instruction)
        tvSpeechStatus.setTextColor(greenColor)
        hudDot?.backgroundTintList = ColorStateList.valueOf(greenColor)
    }

    /**
     * Mengirim teks yang diketik via keyboard inline ke pemroses kata kunci dan kartu visual.
     */
    private fun submitKeyboardText() {
        val text = etArah2KeyboardInput.text.toString().trim()
        if (text.isNotEmpty()) {
            onManualInputSubmitted(text)
            hideSoftKeyboard(etArah2KeyboardInput)
        }
    }

    /**
     * Meminta fokus pada input keyboard inline dan menampilkan virtual soft keyboard.
     */
    fun focusKeyboardInput() {
        etArah2KeyboardInput.requestFocus()
        val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
        imm?.showSoftInput(etArah2KeyboardInput, InputMethodManager.SHOW_IMPLICIT)
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
