package com.signtospeech.ml

/**
 * PredictionStabilizer menyaring hasil inferensi mentah per frame/evaluasi agar bebas flicker
 * dan bebas spam TTS:
 * - Mode LETTER (Huruf):
 *   * Top-1 confidence >= threshold (0.70) dan bukan kelas berawalan `_`.
 *   * Konsisten pada label yang sama minimal `staticMinFrames` (3 frame) DAN durasi tahan
 *     minimal `staticMinHoldMs` (400 ms) -> commit.
 * - Mode WORD (Kata):
 *   * Kelas non-`_idle` dengan confidence >= threshold (0.70) pada minimal
 *     `dynamicMinEvals` (2 evaluasi berturut-turut) -> commit, lalu aktifkan cooldown `dynamicCooldownMs` (1000 ms)
 *     dan minta `GestureBuffer` dibersihkan (`shouldClearBuffer = true`).
 * - Aturan umum:
 *   * Label yang persis sama tidak di-commit ulang dalam `sameLabelCooldownMs` (2000 ms).
 */
class PredictionStabilizer(
    private val confidenceThreshold: Float = ModelConfig.CONFIDENCE_THRESHOLD,
    private val staticMinFrames: Int = ModelConfig.STATIC_MIN_CONSISTENT_FRAMES,
    private val staticMinHoldMs: Long = ModelConfig.STATIC_MIN_HOLD_MS,
    private val dynamicMinEvals: Int = ModelConfig.DYNAMIC_MIN_CONSISTENT_EVALS,
    private val dynamicCooldownMs: Long = ModelConfig.DYNAMIC_COOLDOWN_MS,
    private val sameLabelCooldownMs: Long = ModelConfig.SAME_LABEL_RECOMMIT_COOLDOWN_MS
) {

    data class StabilizerOutput(
        val rawResult: PredictionResult?,
        val committedLabel: String?,
        val shouldClearBuffer: Boolean,
        val isCandidateConfident: Boolean
    )

    private var candidateLabel: String? = null
    private var candidateCount: Int = 0
    private var candidateStartMs: Long = 0L

    private var lastCommittedLabel: String? = null
    private var lastCommittedMs: Long = -100_000L
    private var cooldownUntilMs: Long = 0L

    @Synchronized
    fun reset() {
        candidateLabel = null
        candidateCount = 0
        candidateStartMs = 0L
        cooldownUntilMs = 0L
    }

    @Synchronized
    fun resetAllIncludingHistory() {
        reset()
        lastCommittedLabel = null
        lastCommittedMs = -100_000L
    }

    @Synchronized
    fun onNoHand() {
        candidateLabel = null
        candidateCount = 0
        candidateStartMs = 0L
    }

    @Synchronized
    fun update(
        mode: RecognitionMode,
        result: PredictionResult?,
        timestampMs: Long
    ): StabilizerOutput {
        if (result == null) {
            onNoHand()
            return StabilizerOutput(
                rawResult = null,
                committedLabel = null,
                shouldClearBuffer = false,
                isCandidateConfident = false
            )
        }

        // Kelas _idle (atau berawalan '_') tidak pernah ditampilkan sebagai kandidat komitmen maupun disuarakan
        if (result.isIdleClass || result.confidence < confidenceThreshold) {
            candidateLabel = null
            candidateCount = 0
            candidateStartMs = 0L
            return StabilizerOutput(
                rawResult = result,
                committedLabel = null,
                shouldClearBuffer = false,
                isCandidateConfident = false
            )
        }

        // Cek apakah masih dalam masa cooldown global pasca-commit kata dinamis
        if (timestampMs < cooldownUntilMs) {
            return StabilizerOutput(
                rawResult = result,
                committedLabel = null,
                shouldClearBuffer = false,
                isCandidateConfident = true
            )
        }

        if (result.label == candidateLabel) {
            candidateCount += 1
        } else {
            candidateLabel = result.label
            candidateCount = 1
            candidateStartMs = timestampMs
        }

        val readyToCommit = when (mode) {
            RecognitionMode.LETTER -> {
                val heldDuration = timestampMs - candidateStartMs
                candidateCount >= staticMinFrames && heldDuration >= staticMinHoldMs
            }
            RecognitionMode.WORD -> {
                candidateCount >= dynamicMinEvals
            }
        }

        if (!readyToCommit) {
            return StabilizerOutput(
                rawResult = result,
                committedLabel = null,
                shouldClearBuffer = false,
                isCandidateConfident = true
            )
        }

        // Cegah commit ulang untuk label yang persis sama dalam jendela sameLabelCooldownMs (2000 ms)
        val isDuplicateRecent = (result.label == lastCommittedLabel) &&
            ((timestampMs - lastCommittedMs) < sameLabelCooldownMs)

        if (isDuplicateRecent) {
            return StabilizerOutput(
                rawResult = result,
                committedLabel = null,
                shouldClearBuffer = false,
                isCandidateConfident = true
            )
        }

        val committed = result.label
        lastCommittedLabel = committed
        lastCommittedMs = timestampMs

        // Reset kandidat setelah commit
        candidateLabel = null
        candidateCount = 0
        candidateStartMs = timestampMs

        val clearBuf = if (mode == RecognitionMode.WORD) {
            cooldownUntilMs = timestampMs + dynamicCooldownMs
            true
        } else {
            false
        }

        return StabilizerOutput(
            rawResult = result,
            committedLabel = committed,
            shouldClearBuffer = clearBuf,
            isCandidateConfident = true
        )
    }
}

