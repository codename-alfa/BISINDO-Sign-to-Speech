package com.signtospeech.ui

import com.signtospeech.speech.ServiceCard
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class HapticFeedbackHelperTest {

    @Test
    fun resolvePulseForCards_returnsNull_whenCardsEmpty() {
        val result = HapticFeedbackHelper.resolvePulseForCards(emptyList())
        assertNull(result)
    }

    @Test
    fun resolvePulseForCards_returnsServiceCardMatched_whenStandardCardsPresent() {
        val cards = listOf(
            ServiceCard(
                categoryId = "OBAT",
                title = "Obat & Farmasi",
                icon = "💊",
                colorHex = "#10B981",
                advice = "Tunjukkan resep ke apotek",
                triggerKeyword = "obat"
            ),
            ServiceCard(
                categoryId = "KASIR",
                title = "Kasir & Pembayaran",
                icon = "💳",
                colorHex = "#F59E0B",
                advice = "Siapkan pembayaran",
                triggerKeyword = "kasir"
            )
        )
        val result = HapticFeedbackHelper.resolvePulseForCards(cards)
        assertEquals(HapticFeedbackHelper.PulseType.SERVICE_CARD_MATCHED, result)
    }

    @Test
    fun resolvePulseForCards_prioritizesEmergencyAlert_whenEmergencyCardPresent() {
        val cards = listOf(
            ServiceCard(
                categoryId = "DOKTER",
                title = "Pemeriksaan Dokter / Poli",
                icon = "🩺",
                colorHex = "#3B82F6",
                advice = "Masuk ke ruang dokter",
                triggerKeyword = "dokter"
            ),
            ServiceCard(
                categoryId = "DARURAT",
                title = "Kondisi Sakit / Darurat",
                icon = "🚨",
                colorHex = "#EF4444",
                advice = "Segera ke IGD",
                triggerKeyword = "darurat"
            )
        )
        val result = HapticFeedbackHelper.resolvePulseForCards(cards)
        assertEquals(HapticFeedbackHelper.PulseType.EMERGENCY_ALERT, result)
    }
}

