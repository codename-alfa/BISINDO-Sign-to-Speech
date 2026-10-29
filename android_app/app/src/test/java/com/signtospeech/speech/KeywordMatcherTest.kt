package com.signtospeech.speech

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit Test untuk KeywordMatcher (Ekstraksi Kata Kunci Layanan Publik & Kartu Visual).
 * Berjalan murni di JVM (bebas android.jar dependency).
 */
class KeywordMatcherTest {

    @Test
    fun `test empty or blank sentence returns empty result`() {
        val emptyAnalysis = KeywordMatcher.match("")
        assertTrue(emptyAnalysis.highlights.isEmpty())
        assertTrue(emptyAnalysis.matchedCards.isEmpty())

        val blankAnalysis = KeywordMatcher.match("    ")
        assertTrue(blankAnalysis.highlights.isEmpty())
        assertTrue(blankAnalysis.matchedCards.isEmpty())

        val nullAnalysis = KeywordMatcher.match(null)
        assertTrue(nullAnalysis.highlights.isEmpty())
        assertTrue(nullAnalysis.matchedCards.isEmpty())
    }

    @Test
    fun `test single keyword exact match`() {
        val analysis = KeywordMatcher.match("Bawalah obat ini")
        assertEquals(1, analysis.highlights.size)
        assertEquals("obat", analysis.highlights[0].matchedWord.lowercase())
        assertEquals("OBAT", analysis.highlights[0].categoryId)
        assertEquals("#10B981", analysis.highlights[0].colorHex)

        assertEquals(1, analysis.matchedCards.size)
        val card = analysis.matchedCards[0]
        assertEquals("OBAT", card.categoryId)
        assertEquals("💊", card.icon)
        assertEquals("Obat & Farmasi", card.title)
    }

    @Test
    fun `test suffix variations in indonesian`() {
        // "obatnya" should match OBAT
        val analysis1 = KeywordMatcher.match("Tolong siapkan obatnya")
        assertEquals(2, analysis1.matchedCards.size) // tolong (BANTUAN) & obatnya (OBAT)
        val obatCard = analysis1.matchedCards.find { it.categoryId == "OBAT" }
        assertNotNull(obatCard)

        // "kasirnya" should match KASIR
        val analysis2 = KeywordMatcher.match("Menuju ke kasirnya sekarang")
        val kasirCard = analysis2.matchedCards.find { it.categoryId == "KASIR" }
        assertNotNull(kasirCard)
        assertEquals("💳", kasirCard?.icon)
    }

    @Test
    fun `test false positive protection for substring in other words`() {
        // "pilihan" must NOT trigger "pil"
        val analysis = KeywordMatcher.match("Ini adalah pilihan yang tepat")
        val pilHighlight = analysis.highlights.find { it.matchedWord.equals("pil", ignoreCase = true) }
        val pilCard = analysis.matchedCards.find { it.categoryId == "OBAT" }
        assertEquals(null, pilHighlight)
        assertEquals(null, pilCard)
    }

    @Test
    fun `test multi-word phrase matching`() {
        val analysis = KeywordMatcher.match("Selamat pagi dokter, saya mau periksa")
        val sapaanCard = analysis.matchedCards.find { it.categoryId == "SAPAAN" }
        val dokterCard = analysis.matchedCards.find { it.categoryId == "DOKTER" }

        assertNotNull("Sapaan card harus terdeteksi", sapaanCard)
        assertNotNull("Dokter card harus terdeteksi", dokterCard)
        assertEquals("👋", sapaanCard?.icon)
        assertEquals("🩺", dokterCard?.icon)
    }

    @Test
    fun `test multiple categories and card ordering`() {
        val sentence = "Silakan daftar di loket lalu periksa ke dokter dan bayar di kasir"
        val analysis = KeywordMatcher.match(sentence)

        // Harus menemukan pendaftaran, dokter, dan kasir
        val categoryIds = analysis.matchedCards.map { it.categoryId }
        assertTrue(categoryIds.contains("PENDAFTARAN"))
        assertTrue(categoryIds.contains("DOKTER"))
        assertTrue(categoryIds.contains("KASIR"))

        // Urutan kartu harus sesuai urutan kemunculan di teks
        val firstIdx = categoryIds.indexOf("PENDAFTARAN")
        val secondIdx = categoryIds.indexOf("DOKTER")
        val thirdIdx = categoryIds.indexOf("KASIR")
        assertTrue(firstIdx < secondIdx)
        assertTrue(secondIdx < thirdIdx)
    }

    @Test
    fun `test deduplication of same category in sentence`() {
        // "obat", "resep", "apotek" semuanya kategori OBAT
        val sentence = "Tolong bawa resep ini ke apotek untuk tebus obat"
        val analysis = KeywordMatcher.match(sentence)

        val obatCards = analysis.matchedCards.filter { it.categoryId == "OBAT" }
        assertEquals("Hanya boleh ada 1 kartu untuk kategori OBAT meskipun kata kuncinya muncul berulang", 1, obatCards.size)
    }

    @Test
    fun `test all nine categories can be triggered`() {
        val testInputs = mapOf(
            "OBAT" to "resep obat di apotek",
            "DOKTER" to "pemeriksaan dokter spesialis",
            "DARURAT" to "pasien darurat di igd butuh ambulans",
            "KASIR" to "total biaya bayar tunai",
            "TRANSPORTASI" to "jadwal kereta di stasiun",
            "ARAH" to "belok kiri lalu lurus",
            "PENDAFTARAN" to "siapkan ktp dan nomor antrean",
            "BANTUAN" to "tolong bantuan petugas",
            "SAPAAN" to "selamat pagi terima kasih"
        )

        for ((expectedCategory, text) in testInputs) {
            val analysis = KeywordMatcher.match(text)
            val found = analysis.matchedCards.any { it.categoryId == expectedCategory }
            assertTrue("Kategori $expectedCategory harus terpicu oleh teks '$text'", found)
        }
    }

    @Test
    fun `test quick presets are all valid`() {
        for (preset in KeywordMatcher.QUICK_PRESETS) {
            val analysis = KeywordMatcher.match(preset)
            assertFalse("Preset '$preset' tidak boleh kosong hasil analisanya", analysis.matchedCards.isEmpty())
        }
    }
}

