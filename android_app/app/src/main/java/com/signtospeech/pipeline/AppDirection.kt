package com.signtospeech.pipeline

/**
 * Mendefinisikan arah komunikasi dalam aplikasi Sign-to-Speech:
 * - SIGN_TO_SPEECH : Arah 1 (Tuli -> Dengar): Kamera + MediaPipe + TFLite BiLSTM/MLP + TTS
 * - SPEECH_TO_TEXT  : Arah 2 (Dengar -> Tuli): Mikrofon + Android SpeechRecognizer + KeywordMatcher + TextCardDisplay
 */
enum class AppDirection {
    SIGN_TO_SPEECH,
    SPEECH_TO_TEXT
}

