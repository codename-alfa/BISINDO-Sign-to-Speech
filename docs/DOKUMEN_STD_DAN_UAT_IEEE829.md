# SOFTWARE TEST DOCUMENTATION (STD) & USER ACCEPTANCE TESTING (UAT) REPORT
## Standar IEEE 829-2008 / ISO/IEC/IEEE 29119-3
### Sistem Penerjemah Dua Arah Bahasa Isyarat SIBI & Wicara (SignToSpeech v0.5.0-sibi)

---

**Mata Kuliah:** Rekayasa Perangkat Lunak (RPL) - Semester Ganjil 2026/2027  
**Fakultas / Departemen:** Fakultas Teknik Universitas Indonesia / Departemen Teknik Elektro  
**Program Studi:** Teknik Komputer  
**Dosen Pengampu:** Prof. Dr. Ir. Riri Fitri Sari, M.M., M.Sc.  
**Pihak Pengembang (Kelompok 5):**
1. Ahmad Malik Prasetyo (NPM: 2406416270)
2. Danish Al Fayyadh Sunarta (NPM: 2406416951)
3. Vanesa Kayla Zahra (NPM: 2306161901)  

**Mitra Pengguna (Pihak I MoU Kerja Sama):** Raihan Muhammad Nafis Al-Kautsar (NPM: 2406413451)  
**Status Evaluasi:** **DITERIMA PENUH (100% Passed STD & UAT)**  

---

## DAFTAR ISI

1. [BAB I: PENDAHULUAN & LANDASAN TEORI PENGUJIAN](#bab-i-pendahuluan--landasan-teori-pengujian)
   - 1.1 Definisi Software Test Document (STD / IEEE 829)
   - 1.2 Definisi User Acceptance Testing (UAT)
   - 1.3 Perbandingan Komprehensif STD vs. UAT
   - 1.4 Referensi Standar & Landasan Normatif
2. [BAB II: ARSITEKTUR SISTEM & SPESIFIKASI ITEM UJI](#bab-ii-arsitektur-sistem--spesifikasi-item-uji)
   - 2.1 Arsitektur Komponen Perangkat Lunak SignToSpeech
   - 2.2 Fitur yang Diuji (Features to be Tested)
   - 2.3 Fitur yang Tidak Diuji (Features Not to be Tested)
3. [BAB III: PENDEKATAN & STRATEGI PENGUJIAN](#bab-iii-pendekatan--strategi-pengujian)
   - 3.1 Tingkatan Pengujian (Testing Levels)
   - 3.2 Kriteria Keberhasilan (Pass/Fail Criteria)
   - 3.3 Kriteria Penangguhan & Dimulainya Kembali (Suspension & Resumption)
4. [BAB IV: SPESIFIKASI LINGKUNGAN PENGUJIAN](#bab-iv-spesifikasi-lingkungan-pengujian)
5. [BAB V: MATRIKS KASUS UJI STD & HASIL EKSEKUSI](#bab-v-matriks-kasus-uji-std--hasil-eksekusi)
   - 5.1 Rekapitulasi Unit Testing JVM (33 Unit Tests)
   - 5.2 Pengujian Paritas Model ML (Keras vs TFLite)
   - 5.3 Matriks Lengkap 25 Kasus Uji Fungsional & Integrasi
6. [BAB VI: LAPORAN USER ACCEPTANCE TESTING (UAT)](#bab-vi-laporan-user-acceptance-testing-uat)
   - 6.1 Informasi Pelaksanaan & Profil Partisipan UAT
   - 6.2 Evaluasi 3 Skenario Utama Komunikasi (User Journey)
   - 6.3 Kuesioner Evaluasi Usability & Kepuasan Pengguna (Skala Likert 1-5)
   - 6.4 Catatan Kualitatif & Rekomendasi Mitra Pengguna
7. [BAB VII: KESIMPULAN & PENGESAHAN HASIL PENGUJIAN](#bab-vii-kesimpulan--pengesahan-hasil-pengujian)
   - 7.1 Kesimpulan Kelayakan Rilis
   - 7.2 Lembar Pengesahan Resmi (Acceptance Sign-Off)
8. [BAB VIII: LAMPIRAN & INDEKS BUKTI UJI (ARTIFACTS)](#bab-viii-lampiran--indeks-bukti-uji-artifacts)

---

## BAB I: PENDAHULUAN & LANDASAN TEORI PENGUJIAN

### 1.1 Definisi Software Test Document (STD / IEEE 829)
Software Test Document (STD) adalah dokumen teknis formal yang merinci rencana pengujian, desain kasus uji, kriteria penerimaan teknis, serta rekapitulasi eksekusi pengujian perangkat lunak mengacu pada standar internasional **IEEE 829-2008** (diadopsi dalam **ISO/IEC/IEEE 29119-3**).

Dalam siklus hidup rekayasa perangkat lunak (SDLC), STD berperan utama dalam ranah **Verifikasi (*"Are we building the product right?"*)**. Verifikasi membuktikan secara empiris bahwa implementasi kode program, arsitektur modul, antarmuka antar-komponen, dan performa komputasi telah memenuhi spesifikasi kebutuhan perangkat lunak (Software Requirements Specification - SRS). STD mencakup:
- Pengujian unit (*Unit Testing*): pengujian fungsi dan kelas logika terisolasi.
- Pengujian integrasi (*Integration Testing*): pengujian aliran data antarmuka (CameraX -> MediaPipe -> TFLite -> State Buffer -> TTS/STT).
- Pengujian fungsional black-box (*System/Functional Testing*): pengujian batas (*Boundary Value Analysis*) dan partisi ekivalensi (*Equivalence Partitioning*).

### 1.2 Definisi User Acceptance Testing (UAT)
User Acceptance Testing (UAT) merupakan fase pengujian perangkat lunak tingkat akhir di mana pengguna aktual (*end-user*), klien bisnis, atau perwakilan mitra menguji sistem dalam lingkungan operasional nyata sebelum rilis produksi disetujui.

UAT berakar pada prinsip **Validasi (*"Are we building the right product?"*)**. Validasi membuktikan bahwa perangkat lunak yang dibangun benar-benar menyelesaikan permasalahan nyata pengguna, memberikan pengalaman interaksi yang ergonomis dan mudah dipahami, serta memenuhi butir kesepakatan dokumen kontrak/MoU. Pada proyek SignToSpeech, UAT memvalidasi apakah aplikasi secara efektif menjembatani komunikasi dua arah antara penyandang disabilitas rungu/tuli dan masyarakat dengar.

### 1.3 Perbandingan Komprehensif STD vs. UAT

| Dimensi Perbandingan | Software Test Document (STD) | User Acceptance Testing (UAT) |
| :--- | :--- | :--- |
| **Fokus Utama** | Verifikasi teknis kode, algoritma, arsitektur, dan performa. | Validasi kesesuaian alur kerja, kemudahan guna, dan kebutuhan nyata. |
| **Pertanyaan Kunci** | *"Are we building the product right?"* | *"Are we building the right product?"* |
| **Pelaksana Pengujian** | Tim Pengembang internal & QA Software Engineers. | Mitra Pengguna (Pihak I MoU) & Perwakilan Siswa/Pengguna Akhir. |
| **Tingkatan Uji** | Unit Testing, Integration Testing, System Testing. | Acceptance Testing, Field Usability Testing. |
| **Metodologi** | White-Box Code Coverage & Formal Black-Box Test Cases. | Scenario-Based User Journey & Kuesioner Kepuasan (Skala Likert). |
| **Lingkungan Uji** | Emulator Android (AVD Pixel 10 Pro XL), Test Harness JVM. | Lingkungan operasional nyata & simulasi interaksi langsung. |
| **Kriteria Kelulusan** | 100% Test Cases PASS, Zero Defect Severity 1 & 2. | 100% Skenario Sukses, Rata-rata Skor Likert Usability ≥ 4.00. |
| **Standar Acuan** | IEEE 829-2008 / ISO/IEC/IEEE 29119-3. | ISO 9241-11 (Ergonomics of Human-System Interaction). |
| **Bentuk Dokumen** | Matriks Kasus Uji, Traceability Matrix, Log Defek. | Formulir Skenario UAT, Lembar Kuesioner, Berita Acara Sign-Off. |

### 1.4 Referensi Standar & Landasan Normatif
1. **IEEE Std 829-2008:** *IEEE Standard for Software and System Test Documentation*.
2. **ISO/IEC 25010:2011:** *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models*.
3. **Surat Perjanjian Kerja Sama (MoU):** Proyek Pengembangan Aplikasi Mobile *"SIGN-TO-SPEECH"* antara Raihan Muhammad Nafis Al-Kautsar (Pihak I) dan Tim Pengembang Kelompok 5 RPL (Pihak II), Oktober 2026.

---

## BAB II: ARSITEKTUR SISTEM & SPESIFIKASI ITEM UJI

### 2.1 Arsitektur Komponen Perangkat Lunak SignToSpeech
Aplikasi SignToSpeech v0.5.0-sibi dirancang dengan arsitektur **Offline Edge AI** berlatensi rendah:
1. **CameraX & Vision Pipeline:** Menangkap frame kamera pada kecepatan 30 FPS dan mengekstrak 21 koordinat 3D landmark tangan menggunakan MediaPipe Tasks Vision v0.10.14.
2. **SIBI Static Classifier (Edge TFLite):** Model neural network terkuantisasi (36 kelas) yang mengklasifikasikan abjad SIBI statis A-Z dan angka 1-9 dalam waktu ~1.2 ms/frame.
3. **Temporal Rolling Buffer:** Buffer sirkular 30 frame temporal untuk menangkap sequence gestur dinamis kata SIBI (*"Halo"*, *"Terima kasih"*, *"Tolong"*).
4. **Speech Synthesis Engine (Android TextToSpeech API):** Mengonversi kalimat hasil terjemahan isyarat pada Arah 1 menjadi audio wicara bahasa Indonesia yang lantang dan jelas.
5. **Speech Recognition Engine (Android SpeechRecognizer API):** Menangkap suara wicara mitra dengar pada Arah 2 dan mentranskripsikannya ke dalam kartu teks visual kontras tinggi.
6. **Bidirectional State & Lifecycle Manager:** Mengatur state machine pergantian mode Arah 1 <-> Arah 2 secara aman, mematikan kamera saat di Arah 2 untuk menjaga privasi dan menghemat daya baterai.
7. **Circular Ergonomic Controls (Pembaruan v0.5.0):** Kontrol perekaman audio melingkar modern tanpa label teks (tombol mic biru dan tombol stop merah dengan rounded square putih proporsional).

### 2.2 Fitur yang Diuji (Features to be Tested)
- Inisialisasi dan preview kamera CameraX pada 30 FPS.
- Deteksi 21 titik koordinat landmark tangan pada Region of Interest (ROI).
- Klasifikasi alfabet statis SIBI A-Z dan angka 1-9.
- Akumulasi karakter ke dalam antrian teks (FIFO Queue) dan tombol backspace/clear.
- Quick suggestions (rekomendasi kata cepat 1-ketukan).
- Pelafalan Text-to-Speech (TTS) bahasa Indonesia.
- Pengenalan ucapan Speech-to-Text (STT) mitra dengar pada Arah 2.
- Visualisasi kartu teks berukuran besar dan preset kartu bantuan komunikasi.
- Kontrol tombol melingkar baru (Mic bulat biru & Stop bulat merah dengan rounded square putih).
- Peralihan mode dua arah (Arah 1 <-> Arah 2) dan manajemen siklus hidup Android (kamera/audio release).

### 2.3 Fitur yang Tidak Diuji (Features Not to be Tested)
- Fitur sinkronisasi cloud database multi-pengguna (aplikasi bersifat 100% offline standalone).
- Pemrosesan Natural Language Processing (NLP) berbasis konteks kalimat kompleks di luar kamus dasar SIBI.

---

## BAB III: PENDEKATAN & STRATEGI PENGUJIAN

### 3.1 Tingkatan Pengujian (Testing Levels)
Pengujian dieksekusi secara berjenjang mengacu pada piramida pengujian perangkat lunak:
- **Tingkat 1 - Unit Testing (JVM / JUnit 4 & Robolectric):** 33 kasus unit test independen untuk logika FIFO queue, parser bounding box, sanitasi string, dan state transitions.
- **Tingkat 2 - ML Parity Testing:** Validasi numerik antara model Keras float32 dan model TFLite terkuantisasi melalui skrip `smoke_test_dynamic_pipeline.py` (selisih numerik mutlak: 0.000000).
- **Tingkat 3 - Functional & Integration Testing (STD):** 25 skenario uji black-box fungsional dan integrasi pada emulator Pixel 10 Pro XL.
- **Tingkat 4 - User Acceptance Testing (UAT):** Pengujian skenario alur pengguna nyata (*user journey*) bersama mitra pengguna eksternal disertai kuesioner skala Likert 1-5.

### 3.2 Kriteria Keberhasilan (Pass/Fail Criteria)
Suatu pengujian dinyatakan **LULUS (PASS)** apabila:
1. Hasil aktual pada perangkat uji identik dengan hasil yang diharapkan.
2. Tidak terjadi crash, unhandled exception, ANR (*Application Not Responding*), atau kebocoran memori.
3. Latensi inferensi edge berada di bawah ambang batas toleransi (inferensi < 30 ms, total latensi < 100 ms).
4. Akurasi model pada test set mencapai minimal 85% (hasil aktual: 98.06%).
5. Rata-rata skor evaluasi penerimaan pengguna UAT mencapai minimal 4.00 dari skala 5.00 (hasil aktual: 4.88).

---

## BAB IV: SPESIFIKASI LINGKUNGAN PENGUJIAN

| Parameter Lingkungan | Spesifikasi Teknis Uji |
| :--- | :--- |
| **Perangkat Target (Emulator)** | Google Pixel 10 Pro XL AVD (Android 16 / API 36 Baklava) |
| **Resolusi & Kerapatan Layar** | 1344 x 2992 piksel (480 dpi - xxhdpi) |
| **Akselerasi Grafis & Hardware** | SwiftShader Indirect (OpenGL ES 3.0), CPU & GPU Delegate Support |
| **Target Build / Rilis** | SignToSpeech v0.5.0-sibi (`SignToSpeech-v0.5.0-sibi.apk`) |
| **Dataset & AI Pipeline** | MediaPipe Tasks Vision 0.10.14 + TFLite SIBI Static Classifier (36 Kelas) |
| **Speech Engine** | Android TextToSpeech API (id-ID) & Android SpeechRecognizer API |
| **Metode Pengujian** | IEEE 829 STD (Black-Box & Unit) + Scenario-Based UAT Likert 1-5 |

---

## BAB V: MATRIKS KASUS UJI STD & HASIL EKSEKUSI

### 5.1 Rekapitulasi Unit Testing JVM (33 Unit Tests)
Pengujian unit dijalankan melalui Gradle task `testDebugUnitTest` dengan hasil **33/33 tests PASS (100% Passed, durasi: 12.4s)**. Seluruh komponen logika FIFO buffer, parser landmark, state machine transisi arah, dan sanitasi teks terbukti bebas dari error logika.

### 5.2 Pengujian Paritas Model ML (Keras vs TFLite)
Pengujian kesetaraan inferensi model dijalankan menggunakan skrip `smoke_test_dynamic_pipeline.py`. Output probabilitas kelas antara model referensi Keras dan model terdistribusi TFLite menghasilkan **perbedaan numerik mutlak: 0.000000**, menjamin tidak terjadi degradasi akurasi akibat proses kuantisasi.

### 5.3 Matriks Lengkap 25 Kasus Uji Fungsional & Integrasi

| ID Kasus Uji | Modul / Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Aktual | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-CAM-01** | Kamera Feed | Inisialisasi CameraX saat aplikasi dibuka | Preview kamera aktif pada throughput 30 FPS | Kamera preview terbuka mulus pada 30 FPS | **PASS** |
| **TC-CAM-02** | Vision Pipeline | Deteksi 21 titik landmark tangan pada ROI | 21 landmark hijau ter-render stabil (<30 ms) | 21 Landmark hijau ter-render stabil (<30 ms) | **PASS** |
| **TC-CAM-03** | Vision Pipeline | Ketiadaan tangan pada frame kamera | Sistem idle, HUD pill menampilkan 'Siap mendeteksi' | Sistem idle, HUD menampilkan teks panduan | **PASS** |
| **TC-CLS-01** | Model SIBI | Pengenalan huruf statis vokal (A, I, U, E, O) | Prediksi tepat dengan confidence > 0.90 | Prediksi akurat 100% dengan confidence > 0.90 | **PASS** |
| **TC-CLS-02** | Model SIBI | Pengenalan huruf konsonan (B, D, K, L) | Huruf konsonan terprediksi dan masuk ke pill | Huruf terklasifikasi akurat dan masuk antrian | **PASS** |
| **TC-CLS-03** | Model SIBI | Pengenalan angka isyarat 1-tangan (1-9) | Angka terklasifikasi akurat tanpa false positive | Angka 1-9 terprediksi konsisten dan stabil | **PASS** |
| **TC-BUF-01** | Buffer Dinamis | Input sequence 30 frame gestur gerak kata | Rolling buffer FIFO bekerja stabil tanpa memory leak | Rolling buffer FIFO stabil tanpa kebocoran memori | **PASS** |
| **TC-BUF-02** | Buffer Dinamis | Prediksi kosa kata dinamis ('Halo', 'Terima kasih') | Kosa kata terdeteksi dan masuk ke kalimat | Kosa kata dinamis terdeteksi dan tertulis di HUD | **PASS** |
| **TC-TXT-01** | Manajemen Teks | Akumulasi karakter menjadi kata lengkap | Karakter tersusun rapi dengan spasi otomatis | Karakter terakumulasi dengan spasi otomatis | **PASS** |
| **TC-TXT-02** | Manajemen Teks | Tombol Hapus 1 Karakter (Backspace FIFO) | Karakter terakhir terhapus tepat 1 huruf | Karakter terakhir terhapus tepat 1 huruf | **PASS** |
| **TC-TXT-03** | Manajemen Teks | Tombol Bersihkan Semua (Clear All) | Seluruh teks di HUD pill bersih seketika | Seluruh teks terhapus dan kembali ke state kosong | **PASS** |
| **TC-QCK-01** | Quick Suggestion | Tampilan saran kata cepat berbasis awalan | 3 Chip saran kata muncul di atas kontrol | 3 Chip saran kata muncul otomatis dan relevan | **PASS** |
| **TC-QCK-02** | Quick Suggestion | Pemilihan saran kata cepat dengan 1-ketukan | Kata terpilih menggantikan draft secara instan | Kata terpilih masuk ke draft teks seketika | **PASS** |
| **TC-TTS-01** | Sintesis Wicara | Tekan tombol Bicara pada teks terakumulasi | Android TTS melafalkan kalimat bahasa Indonesia | Suara TTS bahasa Indonesia terdengar artikulatif | **PASS** |
| **TC-TTS-02** | Sintesis Wicara | Tekan tombol Bicara saat teks kosong | TTS tidak bersuara, muncul tooltip panduan | TTS tidak bersuara, sistem menampilkan feedback | **PASS** |
| **TC-STT-01** | Pengenalan Suara | Tekan tombol mic melingkar biru di Arah 2 | SpeechRecognizer aktif, audio visualizer bereaksi | Audio visualizer aktif dan siap menangkap suara | **PASS** |
| **TC-STT-02** | Pengenalan Suara | Ucapkan kalimat wicara dalam bahasa Indonesia | Suara tertranskripsi presisi menjadi teks visual | Suara tertranskripsi presisi ke teks kartu | **PASS** |
| **TC-AR2-01** | Kartu Bantuan | Visualisasi teks pada kontainer kartu besar | Teks tampil kontras tinggi, terbaca dari 1.5 m | Teks terbaca sangat jelas dengan kontras tinggi | **PASS** |
| **TC-AR2-02** | Kartu Bantuan | Pemilihan preset kartu bantuan cepat | Teks preset terisi otomatis ke kontainer kartu | Teks preset terisi otomatis ke kontainer kartu | **PASS** |
| **TC-AR2-03** | Kontrol Melingkar | Tombol stop merah lingkaran dengan kotak putih | Perekaman berhenti, shape proporsional tanpa overlap | Perekaman berhenti, bentuk proporsional & rapi | **PASS** |
| **TC-NAV-01** | Transisi Mode | Peralihan toggle switch Arah 1 ke Arah 2 | Transisi instan (<15 ms), layout berganti mulus | Transisi instan (<15 ms), layout berganti sempurna | **PASS** |
| **TC-NAV-02** | Lifecycle | Manajemen resource kamera saat beralih ke Arah 2 | Kamera off otomatis, hemat baterai & privasi | Kamera off otomatis, resource dilepas bersih | **PASS** |
| **TC-NAV-03** | Lifecycle | Minimalkan aplikasi ke background dan buka lagi | State aplikasi bertahan, kamera resume tanpa error | State aplikasi bertahan, kamera resume lancar | **PASS** |
| **TC-PERF-01** | Performa | Pengukuran throughput FPS kamera & inferensi | Konsisten 30 FPS, latensi inferensi total < 30 ms | Konsisten 30 FPS, latensi inferensi rata-rata 13.6 ms | **PASS** |
| **TC-LOG-01** | Diagnostik | Buka dialog diagnostik sistem dan salin log | Log sistem tampil lengkap dan dapat disalin | Log sistem tampil lengkap dan dapat disalin | **PASS** |

---

## BAB VI: LAPORAN USER ACCEPTANCE TESTING (UAT)

### 6.1 Informasi Pelaksanaan & Profil Partisipan UAT
- **Tanggal Pelaksanaan:** 11 - 12 November 2026
- **Lokasi Pelaksanaan:** Laboratorium Rekayasa Perangkat Lunak FTUI & Google Pixel 10 Pro XL AVD
- **Target Sistem:** SignToSpeech v0.5.0-sibi (APK Release Standalone Offline Edge AI)
- **Metode Pengujian:** *Scenario-Based Usability Testing* & Kuesioner Evaluasi Skala Likert 1-5

#### Daftar Partisipan Evaluator:
1. **Raihan Muhammad Nafis Al-Kautsar** (NPM: 2406413451) - Mitra Pengguna / Pihak I MoU (Eksternal Evaluator)
2. **Ahmad Malik Prasetyo** (NPM: 2406416270) - Lead Tester & Koordinator Lapangan (Kelompok 5 RPL)
3. **Danish Al Fayyadh Sunarta** (NPM: 2406416951) - ML & Edge AI Pipeline Specialist (Kelompok 5 RPL)
4. **Vanesa Kayla Zahra** (NPM: 2306161901) - QA Lead & Document Controller (Kelompok 5 RPL)

---

### 6.2 Evaluasi 3 Skenario Utama Komunikasi (User Journey)

#### Skenario UAT-01: Arah 1 (Bahasa Isyarat SIBI ke Wicara / TTS)
- **Peran Penguji:** Pengguna Tuli / Penutur Isyarat (*Signer*)
- **Langkah Pengujian:**
  1. Buka antarmuka Arah 1 (Sign -> Speech).
  2. Posisikan tangan di area tangkapan kamera smartphone.
  3. Peragakan alfabet SIBI statis (A, B, C, D).
  4. Amati deteksi landmark dan pembentukan kalimat pada HUD pill.
  5. Tekan tombol Bicara (TTS).
- **Kriteria Penerimaan (Acceptance Criteria):**
  - 21 landmark tangan hijau terdeteksi stabil (<30 ms).
  - Huruf terklasifikasi akurat (>95%).
  - Teks terakumulasi rapi di HUD pill tanpa duplikasi liar.
  - Suara sintesis Text-to-Speech terdengar jelas dalam bahasa Indonesia.
- **Hasil Observasi Lapangan:**
  Landmark hijau 21 titik sangat responsif mengikuti pergerakan tangan. Akurasi klasifikasi konsisten tinggi pada pencahayaan indoor. Teks terakumulasi mulus, dan suara TTS terdengar jelas tanpa jeda (latensi total <60 ms).
- **Status Evaluasi:** **PASS (LULUS & DITERIMA)**
- **Evaluator:** Raihan Muhammad Nafis Al-Kautsar & Ahmad Malik Prasetyo

---

#### Skenario UAT-02: Arah 2 (Wicara Mitra Dengar ke Teks Visual & Kartu Bantuan)
- **Peran Penguji:** Mitra Dengar / Petugas Pelayanan (*Speaker / Listener*)
- **Langkah Pengujian:**
  1. Buka antarmuka Arah 2 (Speech -> Sign).
  2. Tekan tombol melingkar mikrofon biru (*Ketuk untuk bicara*).
  3. Ucapkan kalimat komunikasi dalam bahasa Indonesia.
  4. Tekan tombol melingkar stop merah.
  5. Tinjau tampilan kartu teks bantuan dan pilihan kartu preset darurat/medis.
- **Kriteria Penerimaan (Acceptance Criteria):**
  - Input suara ditangkap tanpa distorsi audio.
  - Speech-to-Text mentranskripsi ucapan menjadi teks secara real-time.
  - Teks ditampilkan pada kontainer kartu besar dengan kontras tinggi.
  - Tombol kontrol melingkar (mic biru dan stop merah dengan rounded square putih) mudah diakses dan tidak bertumpukan dengan tombol switch arah.
- **Hasil Observasi Lapangan:**
  Transkripsi wicara sangat presisi untuk bahasa Indonesia standar. Kartu teks terbaca jelas dari jarak pandang 1.5 meter. Desain tombol lingkaran merah baru sangat ergonomis, elegan, dan proporsional.
- **Status Evaluasi:** **PASS (LULUS & DITERIMA)**
- **Evaluator:** Raihan Muhammad Nafis Al-Kautsar & Danish Al Fayyadh Sunarta

---

#### Skenario UAT-03: Transisi Dua Arah & Manajemen Lifecycle Aplikasi
- **Peran Penguji:** *Dual-User Interaction* (Simulasi Percakapan Dua Arah)
- **Langkah Pengujian:**
  1. Tekan tombol toggle switch Arah 1 <-> Arah 2 secara berulang.
  2. Minimalkan aplikasi ke background dan buka kembali.
  3. Periksa pelepasan resource kamera dan audio mikrofon.
- **Kriteria Penerimaan (Acceptance Criteria):**
  - Perpindahan mode berlangsung instan (<50 ms) tanpa glitch atau lag visual.
  - Kamera dimatikan secara otomatis saat berada di Arah 2 untuk menghemat daya dan menjaga privasi.
  - Audio mikrofon dilepas saat pengguna kembali ke Arah 1.
  - Tidak terjadi crash (*Application Not Responding*) atau kebocoran memori.
- **Hasil Observasi Lapangan:**
  Transkripsi state UI sangat mulus (<15 ms). Manajemen lifecycle kamera dan mikrofon berjalan sempurna sesuai arsitektur Android Jetpack. Aplikasi bebas dari kebocoran memori.
- **Status Evaluasi:** **PASS (LULUS & DITERIMA)**
- **Evaluator:** Raihan Muhammad Nafis Al-Kautsar & Vanesa Kayla Zahra

---

### 6.3 Kuesioner Evaluasi Usability & Kepuasan Pengguna (Skala Likert 1-5)

Evaluasi kuantitatif kepuasan pengguna dinilai oleh 4 partisipan (1 evaluator eksternal dan 3 tim pengembang) menggunakan skala Likert:  
*(1 = Sangat Tidak Setuju, 2 = Tidak Setuju, 3 = Netral, 4 = Setuju, 5 = Sangat Setuju)*

| ID | Parameter Evaluasi Usability | Pernyataan Kuesioner Evaluasi | Skor Responden (R / M / D / V) | Rata-rata Skor | Kategori Kelayakan |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **US-01** | Kemudahan Antarmuka (Usability) | Antarmuka aplikasi bersih, ergonomis, dan kontrol mudah diakses tanpa memerlukan pelatihan teknis khusus. | 5 / 5 / 5 / 5 | **5.00 / 5.00** | Sangat Baik |
| **US-02** | Responsivitas Inferensi (Performance) | Deteksi landmark tangan dan transkripsi wicara bekerja real-time tanpa lag yang menghambat dialog. | 4 / 5 / 5 / 5 | **4.75 / 5.00** | Sangat Baik |
| **US-03** | Kejelasan Suara Sintesis (TTS) | Output suara Text-to-Speech terdengar jelas, intonasi wajar, dan artikulatif dalam bahasa Indonesia. | 5 / 5 / 5 / 5 | **5.00 / 5.00** | Sangat Baik |
| **US-04** | Akurasi Pengenalan Suara (STT) | Speech-to-Text mentranskripsi kalimat mitra dengar ke teks visual secara presisi dan minim salah kata. | 4 / 5 / 4 / 5 | **4.50 / 5.00** | Baik |
| **US-05** | Keandalan Kontrol & Navigasi | Peralihan mode dua arah serta tombol melingkar (mic/stop) bekerja stabil tanpa freeze atau glitch. | 5 / 5 / 5 / 5 | **5.00 / 5.00** | Sangat Baik |
| **US-06** | Kemanfaatan Praktis (Value) | Aplikasi secara nyata memfasilitasi komunikasi inklusif antara penyandang disabilitas rungu dan masyarakat luas. | 5 / 5 / 5 / 5 | **5.00 / 5.00** | Sangat Baik |
| **TOTAL** | **SKOR RATA-RATA KESELURUHAN (UAT INDEX)** | **Tingkat Kepuasan Pengguna: 97.5%** | **Skala 1 - 5** | **4.88 / 5.00** | **SANGAT LAYAK (ACCEPTED)** |

---

### 6.4 Catatan Kualitatif & Rekomendasi Mitra Pengguna

#### Umpan Balik Mitra Pengguna (Raihan Muhammad Nafis Al-Kautsar - Pihak I MoU):
> *"Aplikasi SignToSpeech v0.5.0 telah memenuhi seluruh butir spesifikasi kebutuhan dalam MoU kerja sama. Pembaruan kontrol antarmuka berupa tombol melingkar (mic biru dan stop merah dengan kotak putih) membuat tampilan jauh lebih ergonomis, modern, dan tidak lagi menempel pada toggle switch arah. Deteksi alfabet isyarat SIBI sangat responsif di pencahayaan ruangan, dan kartu teks pada Arah 2 sangat membantu keterbacaan. Sistem ini secara resmi DITERIMA dan sangat layak dipresentasikan dalam ujian tugas akhir RPL."*

#### Umpan Balik Tim Pengembang (Kelompok 5 RPL):
> *"Seluruh hasil pengujian UAT menunjukkan konsistensi penuh terhadap 25 kasus uji fungsional STD dan 33 unit test JVM sebelumnya. Integrasi MediaPipe Tasks Vision dan TFLite berjalan efisien di level edge tanpa ketergantungan internet. Responsivitas audio pipeline (TTS dan STT) berada jauh di bawah batas toleransi latensi komunikasi manusia (<100 ms)."*

#### Rekomendasi Pengembangan Lanjutan:
1. Eksplorasi penambahan dialek dan kosa kata isyarat BISINDO di samping SIBI untuk cakupan pengguna yang lebih luas.
2. Pengembangan model avatar 3D interaktif pada Arah 2 untuk memvisualisasikan isyarat secara langsung dari suara wicara.

---

## BAB VII: KESIMPULAN & PENGESAHAN HASIL PENGUJIAN

### 7.1 Kesimpulan Kelayakan Rilis
Berdasarkan seluruh tahapan pengujian verifikasi (STD) dan validasi pengguna (UAT) yang telah dilaksanakan:
1. **Verifikasi Teknis (STD):** 100% kasus uji unit testing (33 unit tests) dan pengujian integrasi (25 kasus uji) berstatus **LULUS (PASS)** dengan 0 defek terbuka.
2. **Performa Edge AI:** Model klasifikasi SIBI mencapai akurasi test set **98.06%** dengan latensi inferensi rata-rata hanya **13.6 ms/frame** pada throughput 30 FPS.
3. **Validasi Pengguna (UAT):** Seluruh 3 skenario alur komunikasi utama berstatus **PASS** dengan skor indeks kepuasan pengguna **4.88 / 5.00 (97.5%)**.

Sistem **SignToSpeech v0.5.0-sibi** dinyatakan **SELESAI, DITERIMA PENUH, DAN SIAP DIRILIS**.

---

### 7.2 Lembar Pengesahan Resmi (Acceptance Sign-Off)

Dokumen ini disahkan pada tanggal **12 November 2026** di Depok sebagai bukti pemenuhan kewajiban tugas pengujian perangkat lunak mata kuliah Rekayasa Perangkat Lunak 2026:

| PIHAK PERTAMA (MITRA PENGGUNA) | PIHAK KEDUA (TIM PENGEMBANG) | MENGETAHUI (DOSEN PENGAMPU) |
| :---: | :---: | :---: |
| *(Tanda Tangan Digital)* | *(Tanda Tangan Digital)* | *(Tanda Tangan Digital)* |
| <br><br><br> | <br><br><br> | <br><br><br> |
| **Raihan Muhammad Nafis Al-Kautsar**<br>NPM: 2406413451<br>*(Mitra Pengguna / Pihak I MoU)* | **Ahmad Malik Prasetyo** (2406416270)<br>**Danish Al Fayyadh S.** (2406416951)<br>**Vanesa Kayla Zahra** (2306161901)<br>*(Tim Pengembang Kelompok 5)* | **Prof. Dr. Ir. Riri Fitri Sari, M.M., M.Sc.**<br>NIP: 197007071994032001<br>*(Dosen Pengampu Mata Kuliah RPL)* |

---

## BAB VIII: LAMPIRAN & INDEKS BUKTI UJI (ARTIFACTS)

| No | Nama Berkas Bukti Uji | Tipe Bukti Uji | Deskripsi Fungsional Bukti Uji | Relevansi Kasus Uji |
| :---: | :--- | :---: | :--- | :--- |
| 1 | `live_check.png` | Screenshot Emulator | Deteksi 21 titik landmark tangan hijau pada preview CameraX | TC-CAM-01, TC-CAM-02 |
| 2 | `live_submitted.png` | Screenshot Emulator | Karakter SIBI terklasifikasi dan masuk ke dalam HUD Pill | TC-CLS-01, TC-CLS-02 |
| 3 | `live_edit.png` | Screenshot Emulator | Uji fungsi FIFO Queue: tombol backspace menghapus 1 karakter | TC-TXT-02 |
| 4 | `live_cleared.png` | Screenshot Emulator | Uji tombol Clear All: seluruh antrian teks terhapus seketika | TC-TXT-03 |
| 5 | `live_back_arah1.png` | Screenshot Emulator | Transisi navigasi dari Arah 2 kembali ke Arah 1 tanpa lag | TC-NAV-01, TC-NAV-03 |
| 6 | `android_screen_arah2.png` | Screenshot Emulator | Antarmuka Arah 2 dengan tombol melingkar mic biru dan stop merah | TC-STT-01, TC-AR2-03 |
| 7 | `stop_button_3way_comparison.png` | Komparasi UI | Verifikasi tombol stop merah lingkaran dengan rounded square putih | TC-AR2-03 |
| 8 | `screen_card_obat.png` | Screenshot Emulator | Visualisasi kartu teks wicara kontras tinggi untuk kebutuhan darurat | TC-AR2-01, TC-AR2-02 |
| 9 | `screen_log_dialog.png` | Screenshot Emulator | Dialog diagnostik log sistem Android untuk pelaporan bug | TC-LOG-01 |
| 10 | `confusion_matrix_static.png` | Plot Matriks AI | Heatmap Confusion Matrix model statis SIBI (36 kelas) | TC-CLS-01, TC-CLS-02 |
| 11 | `classification_report_static.txt` | Laporan Teks AI | Rincian Precision, Recall, F1-Score 3.600 frame uji (98.06%) | TC-CLS-01, TC-CLS-03 |
| 12 | `panduan_sibi_abjad_angka_1_tangan.png` | Dokumen Acuan | Kamus gestur SIBI resmi 1 tangan sebagai ground truth | TC-CLS-01, TC-CLS-02 |
| 13 | `screen_home_launcher.png` | Screenshot Emulator | Ikon launcher aplikasi SignToSpeech v0.5.0 pada layar Android | TC-NAV-03 |
| 14 | `ui_dump.xml` | Dump UI Automator | Hierarki komponen XML antarmuka saat input aktif | TC-NAV-01, TC-AR2-03 |
| 15 | `smoke_test_dynamic_pipeline.py` | Skrip Uji Paritas | Pembuktian selisih numerik Keras vs TFLite = 0.000000 | TC-BUF-01, TC-BUF-02 |

