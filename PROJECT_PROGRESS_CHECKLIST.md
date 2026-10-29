# 📊 Project Development Progress & Master Checklist — BISINDO Sign-to-Speech

**Proyek**: Real-Time BISINDO Sign Language Translator Based on Edge AI & Bi-Directional Speech  
**Mata Kuliah**: Rekayasa Perangkat Lunak (RPL) — Fakultas Teknik Universitas Indonesia  
**Tim Pengembang (Kelompok 5)**:
- **Danish Al-Fayyadh Sunarta (2406416951)** — *Person A: ML & Data Engineer*
- **Ahmad Malik Prasetyo (2406416270)** — *Person B: Android Developer & UI Lead*
- **Vanesa Kayla Zahra (2306161901)** — *Person C: Data Collector, QA Tester & Documentation*

**Pembaruan Terakhir**: 29 Oktober 2026 (Pasca-Eksekusi Kode Sprint 2, Branch `alfa` Commit `380537f`)

---

## 📈 1. Perkiraan Persentase Progres Keseluruhan

Progres proyek dihitung menggunakan dua metrik: **(A) Progres Implementasi Kode & Arsitektur Teknis** dan **(B) Progres Keseluruhan Proyek End-to-End** (mencakup perekaman dataset manusia, pengujian lintas perangkat fisik, dan kesiapan Live Demo).

| Metrik Evaluasi | Persentase Saat Ini | Visualisasi | Keterangan |
|:---|:---:|:---|:---|
| **A. Progres Kode & Rekayasa Perangkat Lunak** | **96%** | `███████████████████░` | Seluruh kode ML Pipeline (Statis & Dinamis BiLSTM 66D) dan Android Native Dua Arah Penuh (Arah 1: Tuli ➔ Dengar + Arah 2: Dengar ➔ Tuli via STT & 9 Kartu Visual) telah **100% selesai & lulus 26/26 unit test**. Rilis GitHub `v0.3.0-bidirectional` telah dipublikasikan. |
| **B. Progres Keseluruhan Proyek (End-to-End)** | **88%** | `█████████████████░░░` | Sistem dua arah penuh telah terintegrasi end-to-end ke build APK debug. Tersisa pengujian lintas perangkat fisik (`DEVICE_TEST_CHECKLIST.md`), UAT/SUS, serta perekaman video dan gladi bersih Live Demo. |

---

### Rincian Bobot & Capaian per Sub-Sistem

| No | Sub-Sistem / Komponen Proyek | Bobot Total | Status PenyelesaianSub-Sistem | Kontribusi ke Total (%) | Catatan Status |
|:--:|:---|:---:|:---:|:---:|:---|
| **1** | **Pre-Development, Arsitektur & Spesifikasi (SRS, UML, MoU)** | 10% | **100%** | **10.0%** | Proposal Bab 1–4, MoU Klien, Jira Board, Git Repo & Kontrak Paritas selesai. |
| **2** | **ML Pipeline — Alfabet Statis (A–Z, MLP 63 Fitur)** | 15% | **100%** | **15.0%** | 3.890 sampel nyata Kaggle, Val Acc **92.42%**, `static_model.tflite` (73.5 KB), paritas 100%. |
| **3** | **ML Pipeline — Kata Dinamis (LSTM 30×66 Fitur, LOSO)** | 20% | **100%** | **20.0%** | 874 take valid dari 3 signer, Val Acc **88.03%** (LOSO held-out Vanesa), `dynamic_model.tflite` (149.6 KB), paritas 100%. |
| **4** | **Android Fondasi Vision (CameraX + MediaPipe + Overlay + DelegateGuard)** | 15% | **100%** | **15.0%** | Berjalan mulus di Redmi Pad 2 (15–20 FPS), dilengkapi toggle `CPU \| GPU` + `DelegateGuard` anti-crash & proteksi AVD. |
| **5** | **Android Pipeline Arah 1 (Tuli ➔ Dengar: Classifier + Buffer + Stabilizer + TTS)** | 15% | **100%** | **15.0%** | Selesai 100%, terintegrasi TTS Bahasa Indonesia, Mute toggle, dan 16 unit test. |
| **6** | **Android Pipeline Arah 2 (Dengar ➔ Tuli: STT + KeywordMatcher + Visual Card)** | 12% | **100%** | **12.0%** | Selesai 100% (Fast-Track): Android native STT (id-ID), fallback offline, 9 kategori kartu visual, teks 26sp, toggle mic, dan 10 unit test baru (Total 26 unit test lulus). |
| **7** | **Pengujian Lintas Perangkat, Optimasi & Persiapan Live Demo** | 13% | **45%** | **5.85%** | Build rilis `v0.3.0-bidirectional.apk` telah tersedia di GitHub. Tersisa pengisian matriks evaluasi lapangan, UAT/SUS, dan video demo. |
| — | **TOTAL PROGRES KESELURUHAN PROYEK** | **100%** | — | **~87.85%** | **Sangat Maju (Fast-Track Roadmap Berhasil)** |

---

### Ringkasan Status per Fase Sprint

| Fase Sprint | Rentang Jadwal | Target Utama | Status Kode | Status Tugas Tim (Human Tasks) | Progres Sprint |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Sprint 1** | Minggu 1–2 (26 Okt – 6 Nov) | Environment, Dataset & Model Statis A–Z, CameraX + MediaPipe + OverlayView di HP fisik | ✅ **100%** | ✅ **100%** (Teruji di Redmi Pad 2) | **100%** |
| **Sprint 2** | Minggu 3–4 (9 Nov – 20 Nov) | Kontrak 66D Dinamis, Perekam `.npz`, Training LSTM (LOSO 88.03%), Full Pipeline Arah 1 + TTS + Toggle CPU/GPU | ✅ **100%** | ✅ **100%** (Dataset 874 take tuntas, APK rilis v0.2.0) | **100%** |
| **Sprint 3 (Fast-Track)** | Minggu 5–6 (Dipercepat ke 30 Okt) | Pipeline Arah 2 (`SpeechToTextManager`, `KeywordMatcher`, `TextCardDisplay`), Bottom Nav Bi-Directional, Rilis GitHub v0.3.0 | ✅ **100%** | 🔄 **50%** (Tersisa verifikasi pengujian fisik & UAT) | **85%** |

---

## ✅ 2. Master Checklist Keseluruhan Proyek

### Fase 0: Pre-Development & Governance (100% Selesai)
- [x] Pembagian peran tim (Danish = ML Lead, Ahmad = Android Lead, Vanesa = Data & QA Lead)
- [x] Pembuatan Project Task Board Jira (27 tasks terpetakan) & penandatanganan MoU Klien
- [x] Inisialisasi Git repository (`main` & `alfa`) beserta `.gitignore`
- [x] Penyusunan spesifikasi arsitektur UML, ML Pipeline, Android Spec, dan Operational Timeline
- [x] Validasi prototipe alur UI pada [`bisindo-web-mockup/`](bisindo-web-mockup/)

---

### Fase 1 / Sprint 1: Foundation, Static Model & Android Vision Plumbing (100% Selesai)

#### A. Machine Learning & Dataset Statis (Danish & Vanesa)
- [x] Setup Python 3.12 virtual environment (`ml_pipeline/.venv`) & [`requirements.txt`](ml_pipeline/requirements.txt)
- [x] Validasi runtime MediaPipe Tasks & TFLite melalui [`setup_check.py`](ml_pipeline/setup_check.py)
- [x] Audit 5 dataset Kaggle BISINDO melalui [`inspect_kaggle_datasets.py`](ml_pipeline/inspect_kaggle_datasets.py)
- [x] Ekstraksi 3.890 sampel landmark tangan nyata (A–Z) ke `data/static/static_data.csv` ([`collect_static_data.py`](ml_pipeline/collect_static_data.py) & [`enrich_static_dataset.py`](ml_pipeline/enrich_static_dataset.py))
- [x] Pelatihan model MLP Alfabet Statis A–Z ([`train_static_model.py`](ml_pipeline/train_static_model.py)) — **Val Accuracy: 92.42%** (Target $\ge 90\%$)
- [x] Ekspor & verifikasi paritas [`static_model.tflite`](ml_pipeline/models/static_model.tflite) (73.5 KB, *0.0% mismatch*, selisih maks $10^{-6}$)
- [x] Pembuatan grafik [`training_curves_static.png`](ml_pipeline/models/training_curves_static.png) & [`confusion_matrix_static.png`](ml_pipeline/models/confusion_matrix_static.png)
- [x] Pembuatan penguji inferensi webcam real-time ([`test_webcam_static.py`](ml_pipeline/test_webcam_static.py))

#### B. Android Native Skeleton & MediaPipe Tracking (Ahmad)
- [x] Inisialisasi proyek Android Kotlin DSL (`minSdk 26`, `targetSdk 34`, `noCompress "tflite", "task"`) di [`android_app/`](android_app/)
- [x] Implementasi [`CameraManager.kt`](android_app/app/src/main/java/com/signtospeech/camera/CameraManager.kt) (CameraX `Preview` + `ImageAnalysis` dengan `STRATEGY_KEEP_ONLY_LATEST`)
- [x] Implementasi [`HandLandmarkerHelper.kt`](android_app/app/src/main/java/com/signtospeech/mediapipe/HandLandmarkerHelper.kt) (MediaPipe Tasks Vision `LIVE_STREAM`)
- [x] Implementasi [`OverlayView.kt`](android_app/app/src/main/java/com/signtospeech/ui/OverlayView.kt) (Render 21 titik sendi & tulang dengan koreksi cermin kamera depan)
- [x] Pengujian lapangan langsung pada tablet fisik **Xiaomi Redmi Pad 2** (Android 15 HyperOS, rata-rata 15–20 FPS stabil)

---

### Fase 2 / Sprint 2: Dynamic Gesture Pipeline & Full Arah 1 Translation (75% — Kode 100% Selesai)

#### A. Kontrak Fitur 66D & Pipeline Pelatihan Dinamis (Danish)
- [x] Perluasan [`feature_utils.py`](ml_pipeline/feature_utils.py):
  - [x] Transformasi isotropik `to_model_space()` (koreksi rasio aspek 3:4 vs 1:1 & mirror X)
  - [x] Resampling berbasis waktu `resample_window()` (jendela `1500 ms` ➔ `30` frame, toleransi gap $\le 300\text{ ms}$)
  - [x] Ekstraksi 66 fitur dinamis `dynamic_features()` (`63` bentuk tangan + `dx, dy` lintasan wrist + `ds` perubahan skala)
  - [x] Pembuatan test vectors lintas bahasa: [`normalization_vectors.json`](ml_pipeline/tests/normalization_vectors.json), [`model_space_vectors.json`](ml_pipeline/tests/model_space_vectors.json), dan [`dynamic_feature_vectors.json`](ml_pipeline/tests/dynamic_feature_vectors.json)
- [x] Penambahan kelas ke-6 `_idle` pada [`labels/dynamic_labels.txt`](ml_pipeline/labels/dynamic_labels.txt) untuk mencegah *false trigger* saat tangan diam
- [x] Pembaruan perekam [`collect_dynamic_data.py`](ml_pipeline/collect_dynamic_data.py) (rekam 2.0s @ 640×480 ke format `.npz`, mendukung `--signer`, `--review`, dan tombol undo `u`)
- [x] Pembaruan skrip training [`train_dynamic_model.py`](ml_pipeline/train_dynamic_model.py) (augmentasi *time-shift crop* $\times 4$, validasi **Leave-One-Signer-Out**, ekspor `.tflite` & `dynamic_model_meta.json`)
- [x] Pembuatan skrip otomasi [`sync_android_assets.py`](ml_pipeline/sync_android_assets.py) & [`smoke_test_dynamic_pipeline.py`](ml_pipeline/smoke_test_dynamic_pipeline.py)

#### B. Integrasi Penuh Android Pipeline Arah 1 & Proteksi GPU (Ahmad)
- [x] Implementasi `toModelSpace` & paritas penuh pada [`FeatureExtractor.kt`](android_app/app/src/main/java/com/signtospeech/ml/FeatureExtractor.kt)
- [x] Implementasi [`ModelConfig.kt`](android_app/app/src/main/java/com/signtospeech/ml/ModelConfig.kt), [`GestureBuffer.kt`](android_app/app/src/main/java/com/signtospeech/ml/GestureBuffer.kt), dan [`DynamicFeatureBuilder.kt`](android_app/app/src/main/java/com/signtospeech/ml/DynamicFeatureBuilder.kt)
- [x] Implementasi [`TfliteClassifier.kt`](android_app/app/src/main/java/com/signtospeech/ml/TfliteClassifier.kt), [`StaticClassifier.kt`](android_app/app/src/main/java/com/signtospeech/ml/StaticClassifier.kt) (`[1,63]➔[1,26]`), dan [`DynamicClassifier.kt`](android_app/app/src/main/java/com/signtospeech/ml/DynamicClassifier.kt) (`[1,30,66]➔[1,6]`)
- [x] Implementasi [`PredictionStabilizer.kt`](android_app/app/src/main/java/com/signtospeech/ml/PredictionStabilizer.kt) (ambang keyakinan $\ge 70\%$, konsistensi frame/waktu, cooldown, anti-spam `_idle`)
- [x] Implementasi [`DelegateMode.kt`](android_app/app/src/main/java/com/signtospeech/mediapipe/DelegateMode.kt) & [`DelegateGuard.kt`](android_app/app/src/main/java/com/signtospeech/mediapipe/DelegateGuard.kt) (default CPU, kunci otomatis di Emulator AVD, *crash sentinel* sinkron via `SharedPreferences.commit()`, dan *long-press reset*)
- [x] Implementasi [`TranslationPipeline.kt`](android_app/app/src/main/java/com/signtospeech/pipeline/TranslationPipeline.kt), [`TTSManager.kt`](android_app/app/src/main/java/com/signtospeech/speech/TTSManager.kt) (Bahasa Indonesia `id-ID` + tombol Mute), dan [`PredictionDisplay.kt`](android_app/app/src/main/java/com/signtospeech/ui/PredictionDisplay.kt) (baris transkrip + *Top-3 fallback suggestions*)
- [x] Pembaruan UI [`activity_main.xml`](android_app/app/src/main/res/layout/activity_main.xml) & [`MainActivity.kt`](android_app/app/src/main/java/com/signtospeech/MainActivity.kt) (toggle **Huruf | Kata**, toggle **CPU | GPU**, HUD latensi **FPS · MP ms · Cls ms**)
- [x] Konfigurasi `abiFilters` (`arm64-v8a`, `armeabi-v7a`) di [`app/build.gradle.kts`](android_app/app/build.gradle.kts) untuk mencegah `UnsatisfiedLinkError` pada Emulator AVD `x86_64`
- [x] Verifikasi 15 Unit Test JVM (`FeatureExtractorTest`, `ModelSpaceTest`, `DynamicFeatureBuilderTest`, `GestureBufferTest`, `PredictionStabilizerTest`, `DelegateGuardTest`) — **100% Lulus (15/15)**

#### C. Tugas Lapangan Tim yang Sedang Berjalan (Danish, Vanesa, Ahmad)
- [x] **Sesi Rekam Mandiri** sesuai [`ml_pipeline/RECORDING_GUIDE.md`](ml_pipeline/RECORDING_GUIDE.md):
  - [x] Danish: Rekam 50 take × 5 kata + 45 take `_idle` (309 file `.npz` valid)
  - [x] Vanesa: Rekam 50 take × 5 kata + 34 take `_idle` (284 file `.npz` valid)
  - [x] Ahmad: Rekam 50 take × 5 kata + 33 take `_idle` (281 file `.npz` valid)
- [x] **Penggabungan & Retraining Data Nyata** (Danish):
  - [x] Gabungkan 874 file `.npz` bersih ke `ml_pipeline/data/dynamic_raw/`
  - [x] Jalankan `python train_dynamic_model.py` — **Akurasi LOSO: 88.03%** (Macro F1: **86.04%**, melampaui target $\ge 75\%$)
  - [x] Jalankan `python sync_android_assets.py` & verifikasi paritas TFLite (149.6 KB, max diff 0.000000)
- [ ] **Pengujian Perangkat Fisik Sprint 2** (Ahmad & Vanesa):
  - [ ] Isi tabel perbandingan `CPU` vs `GPU` dan akurasi manual di [`android_app/DEVICE_TEST_CHECKLIST.md`](android_app/DEVICE_TEST_CHECKLIST.md)

---

### Fase 3 / Sprint 3: Bi-Directional Speech (Arah 2), Optimasi & Live Demo (Fast-Track Selesai 30 Okt 2026)

#### A. Subsistem Arah 2: Dengar ➔ Tuli (Ahmad & Vanesa)
- [x] Buat `AppDirection.kt`: Enum arah komunikasi (`SIGN_TO_SPEECH` vs `SPEECH_TO_TEXT`)
- [x] Buat `SpeechToTextManager.kt`: Wrapper Android `SpeechRecognizer` Bahasa Indonesia (`EXTRA_PREFER_OFFLINE=true` dengan *smart fallback* online & toggle mic)
- [x] Buat `KeywordMatcher.kt`: Ekstraksi kata kunci 9 kategori layanan publik (obat, dokter, darurat, kasir, transportasi, arah, pendaftaran, bantuan, sapaan)
- [x] Buat `TextCardDisplay.kt`: Mode tampilan kartu visual kontras tinggi berukuran besar (26sp) untuk pengguna Tuli
- [x] Integrasikan tombol mikrofon, chip kalimat cepat, dialog ketik manual, dan Bottom Navigation Bar pada `MainActivity.kt` & `activity_main.xml`
- [x] Tambahkan 11 unit test baru (8 tes KeywordMatcher + 2 tes STT Helper) — **Total 26/26 Unit Test Lulus 100%**
- [x] Rilis APK GitHub: [`SignToSpeech-v0.3.0-bidirectional.apk`](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/releases/tag/v0.3.0-bidirectional)

#### B. Pengujian Lintas Perangkat, UAT & Live Demo Readiness (Semua Anggota)
- [ ] Pengujian stabilitas 5 menit kontinu tanpa *crash* pada **Xiaomi 15**, **Redmi Pad 2**, dan **Samsung Galaxy A30s**
- [ ] Pelaksanaan *User Acceptance Testing (UAT)* & pengisian kuesioner *System Usability Scale (SUS)* sesuai MoU
- [ ] Penyempurnaan akhir UI (*app icon*, *splash screen*, *haptic feedback*)
- [ ] Perekaman video demonstrasi (30–60 detik) & finalisasi laporan akhir/slide presentasi
- [ ] Gladi bersih & pelaksanaan **Live Demonstration (7 Desember 2026)**

