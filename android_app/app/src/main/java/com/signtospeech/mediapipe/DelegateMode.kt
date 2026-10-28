package com.signtospeech.mediapipe

/**
 * Mode akselerasi perangkat keras untuk MediaPipe HandLandmarker.
 * Classifier TFLite (MLP & LSTM) selalu berjalan di CPU karena ukurannya mikro (<150 KB).
 */
enum class DelegateMode {
    CPU,
    GPU
}

