# Device Testing Checklist & Bidirectional Evaluation (v0.6.0)

This checklist is used by **Ahmad** and **Vanesa** to verify `SignToSpeech v0.6.0` across Android Emulator (AVD API 37) and physical devices (**Redmi Pad 2**, **Samsung Galaxy A30s**, **Xiaomi 15**). Physical hardware cells below remain marked `PENDING_PHYSICAL_RUN` until executed on hardware before the December 7, 2026 live demo.

---

## 1. Download, Install & Run

### A. Direct Install on Phone / Tablet:
1. Open the official release page: [GitHub Release v0.6.0](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/releases/tag/v0.6.0).
2. Download the Android package: **[SignToSpeech-v0.6.0.apk](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/releases/download/v0.6.0/SignToSpeech-v0.6.0.apk)**.
3. Open the downloaded `.apk` and allow installation from unknown sources (*Install Unknown Apps*).

### B. Install via USB Debugging (Developers):
```powershell
cd d:\programming\python\RPL\projectRepo\android_app

# Run all 35 JVM unit tests (model space, stabilizer, DelegateGuard, KeywordMatcher, STT, TTS)
.\gradlew.bat testDebugUnitTest --rerun-tasks

# Build and install APK via connected ADB device/emulator
.\gradlew.bat installDebug
```

### C. Automated ADB Evidence & Benchmark Runner:
```powershell
python d:\programming\python\RPL\scripts\capture_v060_evidence.py --mode screenshots
python d:\programming\python\RPL\scripts\capture_v060_evidence.py --mode benchmark --duration 30
```

---

## 2. Delegate Benchmark Comparison (`CPU` vs `GPU`) per Device

Run for **60 seconds per delegate** with active single-hand gestures in front of the **front-facing camera** (default in `v0.6.0`). Record HUD metrics (`FPS · MP ms · Cls ms · CPU/GPU`):

| Device | Delegate | Mean FPS | Min FPS | Mean `MP ms` | Mean `Cls ms` | Cold-Start Switch (s) | Stability / Thermal | Crash / Freeze? | Demo Decision |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---:|:---:|
| **Emulator AVD API 37 (`x86_64`)** | **CPU** | 1.8 - 2.9 FPS (arm64 ndk_translation) | 1.6 FPS | 365 - 1013 ms | < 1.0 ms (0.0 ms HUD rounded) | < 1.0 s | Stable | No | Default Dev / CI |
| **Emulator AVD API 37 (`x86_64`)** | **GPU** | *(Locked)* | — | — | — | — | Greyed out (`DelegateGuard`) | No | Safe Lock Active |
| **Xiaomi Redmi Pad 2** | **CPU** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | Pending |
| **Xiaomi Redmi Pad 2** | **GPU** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | Pending |
| **Samsung Galaxy A30s** | **CPU** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | Pending |
| **Samsung Galaxy A30s** | **GPU** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | Pending |
| **Xiaomi 15 (Live Demo)** | **CPU** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | Pending |
| **Xiaomi 15 (Live Demo)** | **GPU** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | Pending |

> **Demo Decision Rule**: Use `GPU` for the December 7, 2026 live demo only if mean FPS or `MP ms` improves by **>= 20%** with zero crash/freeze symptoms. Otherwise keep `CPU`.

---

## 3. Reliability, UX Fixes & State Preservation (`v0.6.0`)

- [x] **Emulator `DelegateGuard` Protection (AVD API 37)**: `GPU` pill stays disabled and displays `"GPU dinonaktifkan otomatis pada Emulator (AVD)"` on tap.
- [ ] **Scenario A (Repeated Delegate Switch)**: On physical device, toggle `CPU -> GPU -> CPU` 5 times and confirm zero force-close (`PENDING_PHYSICAL_RUN`).
- [ ] **Scenario B (Post-Crash Recovery & Long-Press Reset)**: Simulate GPU failure, reopen app to verify automatic `CPU` fallback + Snackbar, then long-press `GPU` to unblock (`PENDING_PHYSICAL_RUN`).
- [ ] **Scenario C (v0.6.0 Front Camera Default & Switch)**: Verify first launch opens on front-facing selfie camera (`LENS_FACING_FRONT`), and pressing Switch Camera cleanly toggles rear camera and clears `OverlayView` + `TranslationPipeline` (`PENDING_PHYSICAL_RUN`).
- [ ] **Scenario D (v0.6.0 Orientation / Rotation State Preservation)**: Rotate device (or trigger activity recreation) with committed transcript items, mute toggle, active mode, and Direction 2 card visible; confirm all state restores cleanly without re-triggering TTS.
- [ ] **Scenario E (v0.6.0 SecurityException Keyboard Fallback)**: When OEM STT raises `SecurityException` (error code `-1`), confirm warning Toast appears and inline keyboard `EditText` gains focus automatically (`focusKeyboardInput()`).
- [ ] **Scenario F (Release Build Debug Intent Hardening)**: Verify release APK (`isDebuggable = false`) ignores `debug_hold_splash`, `debug_commit_label`, `debug_direction`, and `debug_arah2_text` extras while fading out splash screen after 1100 ms.

---

## 4. Direction 1 Letter Mode Evaluation (36 SIBI Classes: A-Z, 1-10)

Test under normal indoor lighting using the front camera:
- [ ] Letters A - G (`PENDING_PHYSICAL_RUN`)
- [ ] Letters H - N (`PENDING_PHYSICAL_RUN`)
- [ ] Letters O - T (`PENDING_PHYSICAL_RUN`)
- [ ] Letters U - Z (`PENDING_PHYSICAL_RUN`)
- [ ] Digits 1 - 10 (`PENDING_PHYSICAL_RUN`)
- **Mirror Note**: If asymmetric signs (J, Z, G, H) invert systematically between left and right hands, inspect `MIRROR_X_FOR_MODEL` in [`ModelConfig.kt`](file:///d:/programming/python/RPL/projectRepo/android_app/app/src/main/java/com/signtospeech/ml/ModelConfig.kt).

---

## 5. Direction 1 Word Mode (Dynamic BISINDO BiLSTM 30x66) & TTS

Evaluated using the new `Bidirectional(LSTM(32, unroll=True))` (`TFLITE_BUILTINS` only) model across the 6 classes:

| Target Word | Successful Trials (out of 5) | Mean Confidence (%) | Clear Indonesian TTS Without Duplicates? |
|:---|:---:|:---:|:---:|
| **Halo** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` |
| **Terima kasih** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` |
| **Tolong** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` |
| **Ya** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` |
| **Tidak** | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` | `PENDING_PHYSICAL_RUN` |
| **30s Idle / Non-sign motion (`_idle`)** | False triggers: `PENDING_PHYSICAL_RUN` (Target: <= 1) | — | No phantom speech |

- [ ] **Mute / Unmute Toggle**: When `Suara MUTE` is active, transcript updates while `TTSManager.speak()` stays suppressed.
- [ ] **Backspace / Clear Controls**: Single-item FIFO delete and full transcript clear reset stabilizer history cleanly.

---

## 6. Direction 2 Evaluation (`SPEECH -> CARD`: STT, Keyboard & 6 Presets)

Verify all 9 keyword categories plus all **6 Quick Presets** (including the newly restored **Emergency IGD** chip):

| Scenario | Test Phrase | Expected Category | Text & Highlight | Visual Card Displayed? |
|:---|:---|:---:|:---:|:---:|
| **Pharmacy / Medicine** | *"Tebus obat resep di apotek"* | `OBAT` | 26sp + Emerald `#10B981` | `PENDING_PHYSICAL_RUN` |
| **Doctor / Clinic** | *"Poli pemeriksaan dokter di lantai 2"* | `DOKTER` | 26sp + Blue `#3B82F6` | `PENDING_PHYSICAL_RUN` |
| **Emergency IGD Preset (New v0.6.0)** | *"Kondisi darurat medis! Segera bawa pasien ke ruang IGD sekarang."* | `DARURAT` | 26sp + Red `#EF4444` (Chip: *"Kondisi darurat IGD"*) | `PENDING_PHYSICAL_RUN` |
| **Cashier / Payment** | *"Berapa total biaya di kasir?"* | `KASIR` | 26sp + Amber `#F59E0B` | `PENDING_PHYSICAL_RUN` |
| **Transportation** | *"Tolong pandu ke stasiun terdekat"* | `TRANSPORTASI` | 26sp + Cyan `#0EA5E9` | `PENDING_PHYSICAL_RUN` |
| **Registration & ID** | *"Silakan ambil nomor antrean dan siapkan KTP"* | `PENDAFTARAN` | 26sp + Indigo `#6366F1` | `PENDING_PHYSICAL_RUN` |
| **Directions** | *"Toilet belok kiri lalu lurus ke depan"* | `ARAH` | 26sp + Teal `#14B8A6` | `PENDING_PHYSICAL_RUN` |
| **Staff Assistance** | *"Tolong tunggu sebentar, petugas kami akan membantu"* | `BANTUAN` | 26sp + Orange `#F97316` | `PENDING_PHYSICAL_RUN` |
| **Greeting** | *"Selamat pagi, terima kasih atas kunjungannya"* | `SAPAAN` | 26sp + Purple `#8B5CF6` | `PENDING_PHYSICAL_RUN` |

### Additional Direction 2 Controls:
- [ ] **Mic Toggle & Offline Badge**: Mic starts/stops listening cleanly; badge switches `Mode: Offline` / `Mode: Online`.
- [ ] **Audio RMS Level Bar**: Progress bar responds across `-2 dB` to `+10 dB` via `SpeechToTextManager.normalizeRmsDb`.
- [ ] **In-App Log Viewer (`Log`)**: Displays live `AppLogger` entries with clipboard copy and Android Share Sheet export.
- [ ] **Directional Toggle Isolation**: Bottom segmented pill displays `SIGN -> SPEECH` and `SPEECH -> CARD`, pausing CameraX & TTS when switching to Direction 2 and resuming cleanly on return.
