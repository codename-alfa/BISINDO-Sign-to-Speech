package com.signtospeech.speech

import java.util.Locale
import java.util.regex.Pattern

/**
 * Data class penanda rentang karakter kata kunci untuk visual highlight.
 */
data class HighlightSpan(
    val start: Int,
    val end: Int,
    val categoryId: String,
    val colorHex: String,
    val matchedWord: String
)

/**
 * Kartu visual pendamping komunikasi untuk pengguna Tuli.
 */
data class ServiceCard(
    val categoryId: String,
    val title: String,
    val icon: String,
    val colorHex: String,
    val advice: String,
    val triggerKeyword: String
)

/**
 * Hasil analisis pencocokan kata kunci pada kalimat transkripsi.
 */
data class MatchAnalysis(
    val text: String,
    val highlights: List<HighlightSpan>,
    val matchedCards: List<ServiceCard>
)

/**
 * Kategori Layanan Publik dengan kamus kata kunci dan regex pencocokan.
 */
data class ServiceCategory(
    val id: String,
    val title: String,
    val icon: String,
    val colorHex: String,
    val advice: String,
    val multiWordPhrases: List<String>,
    val singleKeywords: List<String>
)

/**
 * KeywordMatcher: Parser kata kunci layanan publik Bahasa Indonesia bebas dependensi Android SDK.
 * 100% kompatibel diuji pada unit test JVM.
 */
object KeywordMatcher {

    // Regex suffix bahasa Indonesia yang valid (bukan sembarang substring)
    private const val SUFFIX_PATTERN = "(?:nya|mu|ku|lah|kan)?"

    val CATEGORIES: List<ServiceCategory> = listOf(
        ServiceCategory(
            id = "OBAT",
            title = "Obat & Farmasi",
            icon = "💊",
            colorHex = "#10B981",
            advice = "Tunjukkan resep atau tebus obat di loket apotek",
            multiWordPhrases = listOf("resep dokter", "ambil obat", "tebus resep"),
            singleKeywords = listOf("obat", "resep", "farmasi", "apotek", "pil", "kapsul", "dosis", "puyer", "sirup", "salep")
        ),
        ServiceCategory(
            id = "DOKTER",
            title = "Pemeriksaan Dokter / Poli",
            icon = "🩺",
            colorHex = "#3B82F6",
            advice = "Silakan masuk ke ruang poli / konsultasi dokter",
            multiWordPhrases = listOf("ruang dokter", "konsultasi dokter", "cek tensi", "pemeriksaan medis"),
            singleKeywords = listOf("dokter", "pemeriksaan", "periksa", "konsultasi", "poli", "medis", "perawat", "suster", "tensi")
        ),
        ServiceCategory(
            id = "DARURAT",
            title = "Kondisi Sakit / Darurat",
            icon = "🚨",
            colorHex = "#EF4444",
            advice = "Segera arahkan ke Instalasi Gawat Darurat (IGD)",
            multiWordPhrases = listOf("gawat darurat", "sesak napas", "pertolongan pertama"),
            singleKeywords = listOf("sakit", "darurat", "igd", "ugd", "luka", "pusing", "nyeri", "sesak", "demam", "ambulans", "pingsan", "parah")
        ),
        ServiceCategory(
            id = "KASIR",
            title = "Kasir & Pembayaran",
            icon = "💳",
            colorHex = "#F59E0B",
            advice = "Siapkan pembayaran (tunai, kartu, atau QRIS)",
            multiWordPhrases = listOf("kartu debit", "kartu kredit", "loket kasir", "uang pas", "biaya pendaftaran"),
            singleKeywords = listOf("bayar", "kasir", "tagihan", "pembayaran", "biaya", "uang", "qris", "tunai", "harga", "total", "struk", "bpjs")
        ),
        ServiceCategory(
            id = "TRANSPORTASI",
            title = "Transportasi & Perjalanan",
            icon = "🚆",
            colorHex = "#0EA5E9",
            advice = "Perhatikan peron, halte, atau jadwal keberangkatan",
            multiWordPhrases = listOf("naik krl", "naik bus", "kereta api"),
            singleKeywords = listOf("stasiun", "halte", "bus", "kereta", "krl", "mrt", "lrt", "transjakarta", "tiket", "peron", "jadwal", "berangkat", "gerbong")
        ),
        ServiceCategory(
            id = "ARAH",
            title = "Petunjuk Arah & Lokasi",
            icon = "🧭",
            colorHex = "#14B8A6",
            advice = "Ikuti arah petunjuk (kiri / kanan / lurus / lantai)",
            multiWordPhrases = listOf("belok kiri", "belok kanan", "pintu keluar", "pintu masuk"),
            singleKeywords = listOf("kiri", "kanan", "lurus", "depan", "belakang", "lantai", "lift", "tangga", "ruang", "loket", "masuk", "keluar", "toilet", "belok")
        ),
        ServiceCategory(
            id = "PENDAFTARAN",
            title = "Pendaftaran & Dokumen",
            icon = "🪪",
            colorHex = "#6366F1",
            advice = "Siapkan kartu identitas (KTP) dan ambil nomor antrean",
            multiWordPhrases = listOf("ambil antrean", "nomor antrean", "loket pendaftaran", "kartu identitas"),
            singleKeywords = listOf("ktp", "kartu", "daftar", "pendaftaran", "antrean", "antri", "antrian", "nomor", "formulir", "identitas", "registrasi")
        ),
        ServiceCategory(
            id = "BANTUAN",
            title = "Bantuan Petugas",
            icon = "🆘",
            colorHex = "#F97316",
            advice = "Petugas siap mendampingi atau memandu Anda",
            multiWordPhrases = listOf("minta tolong", "butuh bantuan", "panduan arah"),
            singleKeywords = listOf("tolong", "bantu", "bantuan", "petugas", "panduan", "tunggu", "silakan", "mohon")
        ),
        ServiceCategory(
            id = "SAPAAN",
            title = "Sapaan & Apresiasi",
            icon = "👋",
            colorHex = "#8B5CF6",
            advice = "Komunikasi dua arah yang ramah dan inklusif",
            multiWordPhrases = listOf(
                "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
                "terima kasih", "terimakasih", "sama-sama"
            ),
            singleKeywords = listOf("halo", "hai", "makasih", "maaf", "permisi")
        )
    )

    /**
     * Preset kalimat cepat untuk pengetikan cepat atau lingkungan bising.
     */
    val QUICK_PRESETS = listOf(
        "Tebus obat resep di apotek",
        "Berapa total biaya di kasir?",
        "Poli pemeriksaan dokter di lantai 2",
        "Tolong pandu ke stasiun terdekat",
        "Silakan ambil nomor antrean dan siapkan KTP"
    )

    // Precompiled regex cache untuk efisiensi eksekusi realtime (tidak kompilasi ulang tiap frame)
    private val compiledPatterns: List<Pair<ServiceCategory, Pattern>> by lazy {
        CATEGORIES.map { category ->
            val multiPatterns = category.multiWordPhrases.map { phrase ->
                // Frasa multi-kata: cocokkan utuh dengan batas kata
                Pattern.quote(phrase)
            }
            val singlePatterns = category.singleKeywords.map { word ->
                // Kata tunggal: dukung imbuhan akhiran (misal: obatnya, kasirnya)
                "${Pattern.quote(word)}$SUFFIX_PATTERN"
            }
            val combined = (multiPatterns + singlePatterns).joinToString("|")
            val regex = Pattern.compile("(?i)\\b($combined)\\b")
            Pair(category, regex)
        }
    }

    /**
     * Mencocokkan kata kunci pada teks kalimat dan mengembalikan span sorotan serta kartu visual.
     */
    fun match(sentence: String?): MatchAnalysis {
        if (sentence.isNullOrBlank()) {
            return MatchAnalysis(sentence.orEmpty(), emptyList(), emptyList())
        }

        val highlights = mutableListOf<HighlightSpan>()
        val matchedCategories = LinkedHashMap<String, ServiceCard>()

        for ((category, pattern) in compiledPatterns) {
            val matcher = pattern.matcher(sentence)
            while (matcher.find()) {
                val start = matcher.start()
                val end = matcher.end()
                val matchedWord = matcher.group()

                // Cek apakah span tumpang tindih dengan highlight yang sudah ada
                val overlaps = highlights.any { existing ->
                    (start in existing.start until existing.end) || (end - 1 in existing.start until existing.end)
                }

                if (!overlaps) {
                    highlights.add(
                        HighlightSpan(
                            start = start,
                            end = end,
                            categoryId = category.id,
                            colorHex = category.colorHex,
                            matchedWord = matchedWord
                        )
                    )

                    // Simpan satu kartu per kategori sesuai kemunculan pertama
                    if (!matchedCategories.containsKey(category.id)) {
                        matchedCategories[category.id] = ServiceCard(
                            categoryId = category.id,
                            title = category.title,
                            icon = category.icon,
                            colorHex = category.colorHex,
                            advice = category.advice,
                            triggerKeyword = matchedWord
                        )
                    }
                }
            }
        }

        // Urutkan sorotan berdasarkan posisi teks
        highlights.sortBy { it.start }

        // Urutkan kartu visual berdasarkan kemunculan pertama kata kuncinya di teks
        val sortedCards = highlights.mapNotNull { span ->
            matchedCategories[span.categoryId]
        }.distinctBy { it.categoryId }

        return MatchAnalysis(
            text = sentence,
            highlights = highlights,
            matchedCards = sortedCards
        )
    }
}

