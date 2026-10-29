# 📋 Sprint 2 To-Do List: Full Translation Pipeline Arah 1 (Tuli ➔ Dengar)

**Timeline Target**: Sprint 2 (Fase Pengembangan Pasca-UTS)  
**Status Fondasi Kode**: ✅ Selesai 100% (Skrip ML, Paritas Kotlin-Python 66 fitur, UI Mode Huruf/Kata, DelegateGuard CPU/GPU, dan Suara TTS telah teruji di 15 Unit Test JVM).  
**Fokus Utama Saat Ini**: Eksekusi Tugas Lapangan Manusia (*Human Tasks*), Perekaman Dataset Mandiri, Retraining Model Nyata, serta Pengujian Lintas Perangkat.

---

## 👥 Matriks Pembagian Peran Anggota Tim

| Nama Anggota | Inisial / Peran | Tanggung Jawab Utama Sprint 2 |
|:---|:---:|:---|
| **Danish Al-Fayyadh Sunarta** | **Person A (ML Lead)** | Rekam 290 take gestur, gabungkan dataset mentah, jalankan training LSTM (LOSO), ekspor TFLite, dan sinkronisasi assets Android. |
| **Ahmad Malik Prasetyo** | **Person B (Android Lead)** | Rekam 290 take gestur, build/install APK ke perangkat fisik/AVD, uji coba mode Huruf (A–Z) & TTS, evaluasi toggle CPU/GPU. |
| **Vanesa Kayla Zahra** | **Person C (Data & QA Lead)** | Rekam 290 take gestur, koordinasi drive dataset, uji coba akurasi 5 kata dinamis di HP fisik, pencatatan hasil di checklist. |

---

## 📅 Tahapan Eksekusi Rinci (Step-by-Step)

### TAHAP 1: Perekaman Mandiri Dataset Dinamis (Semua Anggota Tim)
> 🎯 **Target**: Terkumpul **870 file rekaman `.npz`** valid (290 take × 3 orang).  
> ⏱️ **Estimasi Waktu**: ±45–60 menit per orang.  
> 📖 **Panduan Lengkap**: Baca [`ml_pipeline/RECORDING_GUIDE.md`](file:///d:/programming/python/RPL/projectRepo/ml_pipeline/RECORDING_GUIDE.md).

#### 1.1 Menjalankan di Laptop Masing-Masing (Variasi Lingkungan Nyata)
* **Mengapa Wajib di Laptop Masing-Masing?**
  * Setiap anggota tim (Danish, Vanesa, Ahmad) memiliki webcam laptop dengan karakteristik sensor berbeda, pencahayaan kamar/ruangan berbeda, serta ukuran dan kelenturan tangan yang berbeda.
  * Variasi alami ini sangat penting agar model AI tidak menghafal satu latar belakang saja, melainkan benar-benar belajar mengenali pola gerakan tangan murni (*generalized gesture tracking*).
* **Setup untuk Teman Tim (Vanesa & Ahmad)**:
  1. Clone atau `git pull origin main` dari repository proyek.
  2. Buka folder `projectRepo/ml_pipeline` di terminal laptop masing-masing:
     ```powershell
     cd d:\programming\python\RPL\projectRepo\ml_pipeline
     ```
  3. **Wajib gunakan Python 3.12** (TensorFlow & MediaPipe belum mendukung Python 3.14). Buat & aktifkan virtual environment:
     ```powershell
     # Buat venv dengan Python 3.12
     py -3.12 -m venv .venv

     # Aktifkan venv di PowerShell
     .\.venv\Scripts\Activate.ps1
     ```
  4. Pasang seluruh dependensi ter-pin:
     ```powershell
     pip install -r requirements.txt
     ```

#### 1.2 Mekanisme Tombol: Memulai & Menghentikan Rekaman
* **Memulai Setiap Take (Tombol `r`)**:
  * Tekan tombol keyboard **`r`** saat status menunjukkan `STATUS: SIAP (warna hijau)`.
  * Layar akan menampilkan hitung mundur besar selama 3 detik: **`BERSIAP: 3 ➔ 2 ➔ 1`**.
  * Manfaatkan 3 detik ini untuk bersiap dan memposisikan tangan di depan kamera.
* **Menghentikan Setiap Take (Berhenti Otomatis 2.0 Detik)**:
  * **Tidak perlu menekan tombol stop manual!** Sistem otomatis merekam selama tepat **2.0 detik** lalu langsung berhenti dan menyimpannya ke disk.
  * *Alasan Rekayasa*: Jika penghentian memakai tombol keyboard, gerakan tangan saat meraih tombol keyboard di akhir rekaman akan ikut terekam dan merusak kemurnian data isyarat!
  * **Durasi Gerakan Ideal**: Lakukan gerakan isyarat secara natural selama **1.2 hingga 1.8 detik**, lalu tahan posisi tangan sejenak hingga bar merah di bawah layar penuh.
* **Tombol Pembatalan / Salah Gerakan (Tombol `u` - Undo)**:
  * Jika tangan sempat keluar frame, gerakan salah, atau muncul peringatan merah `TANGAN HILANG > 300 MS`, langsung tekan tombol **`u`**. File rekaman yang baru saja dibuat akan otomatis dihapus seketika dari disk.
* **Navigasi Kelas**:
  * Tekan **`n`** untuk berpindah ke kata berikutnya (Next).
  * Tekan **`p`** untuk berpindah ke kata sebelumnya (Previous).
  * Tekan **`q`** jika sudah selesai semua kelas (Quit).

#### 1.3 Kuota Rekaman per Orang (6 Kelas):
- [x] **`Halo`** (50 take): Lambaian telapak tangan terbuka di samping kepala/bahu (~1.5 detik) — **Tuntas (150/150 total tim)**.
- [x] **`Terima_kasih`** (50 take): Ujung jari menyentuh dagu/bibir lalu bergerak maju-turun ke depan — **Tuntas (150/150 total tim)**.
- [x] **`Tolong`** (50 take): Dua tangan / satu tangan mengatup di dada digerakkan naik-turun memohon — **Tuntas (155/150 total tim)**.
- [x] **`Ya`** (50 take): Tangan mengepal mengangguk turun-naik tegas di depan bahu — **Tuntas (153/150 total tim)**.
- [x] **`Tidak`** (50 take): Jari telunjuk atau telapak tangan digoyangkan ke kiri dan kanan — **Tuntas (154/150 total tim)**.
- [x] **`_idle`** (40 take): Tangan diam rileks, menurunkan tangan, menggaruk pipi, atau gerakan transisi santai — **Tuntas (112/120 total tim, 100% valid)**.

#### 1.4 Aturan Variasi Wajib Saat Merekam:
- [x] **Pencahayaan**: 25 take di ruangan terang + 25 take di ruangan agak redup / cahaya samping.
- [x] **Jarak Kamera**: 25 take pada jarak dekat (~40–50 cm) + 25 take pada jarak sedang (~70–80 cm).

---

### 📦 TAHAP KHUSUS: Prosedur Danish Mengumpulkan & Menggabungkan Seluruh Rekaman

Sebagai ML Lead, Danish bertugas mengumpulkan file rekaman `.npz` dari Vanesa dan Ahmad untuk digabungkan dengan rekaman milik Danish sendiri sebelum proses *training* dimulai.

#### Langkah 1: Struktur File yang Dihasilkan
Saat skrip perekam dijalankan, file otomatis tersimpan di folder laptop masing-masing dengan format penamaan unik:
```text
ml_pipeline/data/dynamic_raw/
├── Halo/
│   ├── danish_000.npz, danish_001.npz, ...
│   ├── vanesa_000.npz, vanesa_001.npz, ...
│   └── ahmad_000.npz,  ahmad_001.npz, ...
├── Terima_kasih/
├── Tolong/
├── Ya/
├── Tidak/
└── _idle/
```
Karena nama file diawali dengan nama signer (`danish_...`, `vanesa_...`, `ahmad_...`), file dari ketiga orang **tidak akan pernah saling menimpa (*no name collision*)** meskipun digabungkan ke dalam folder yang sama!

#### Langkah 2: Mengunggah ke Google Drive Bersama
1. Vanesa dan Ahmad membuka folder lokal mereka:
   `d:\programming\python\RPL\projectRepo\ml_pipeline\data\dynamic_raw\`
2. Vanesa dan Ahmad mengompres (ZIP) atau langsung mengunggah folder `dynamic_raw` milik mereka ke folder Google Drive bersama tim:
   `Google Drive Tim > Dataset_Sprint2 > dynamic_raw_vanesa.zip` & `dynamic_raw_ahmad.zip`.

#### Langkah 3: Danish Mengunduh & Menggabungkan di Laptop Utama
1. Danish mengunduh file rekaman Vanesa dan Ahmad dari Google Drive.
2. Ekstrak dan salin (Copy-Paste) seluruh isi folder rekaman Vanesa dan Ahmad ke dalam folder lokal Danish di:
   `d:\programming\python\RPL\projectRepo\ml_pipeline\data\dynamic_raw\`
3. Cukup lakukan *merge folder*:
   - Isi subfolder `Halo` milik Vanesa & Ahmad dicampur ke dalam subfolder `Halo` milik Danish.
   - Isi subfolder `Terima_kasih` dicampur ke subfolder `Terima_kasih`, dan seterusnya untuk ke-6 kelas.

#### Langkah 4: Danish Memverifikasi Kelengkapan Dataset
Sebelum menjalankan training, Danish cukup menjalankan perintah verifikasi cepat ini di PowerShell:
```powershell
cd d:\programming\python\RPL\projectRepo\ml_pipeline

# Cek total file .npz per kelas dan per signer:
Get-ChildItem data\dynamic_raw -Directory | ForEach-Object {
    $folderName = $_.Name
    $total = (Get-ChildItem $_.FullName -Filter *.npz).Count
    $danishCount = (Get-ChildItem $_.FullName -Filter "danish_*.npz").Count
    $vanesaCount = (Get-ChildItem $_.FullName -Filter "vanesa_*.npz").Count
    $ahmadCount  = (Get-ChildItem $_.FullName -Filter "ahmad_*.npz").Count
    "[$folderName] Total: $total takes | Danish: $danishCount, Vanesa: $vanesaCount, Ahmad: $ahmadCount"
}
```

*Kriteria Siap Training*:
* Setiap kelas minimal memiliki **≥ 30–50 rekaman per orang** (Total $\ge 120–150$ file per kelas).
* Jika semua kelas sudah lengkap terisi oleh ketiga signer, Danish siap melanjutkan ke **TAHAP 2 (Training Model)**!

---

### TAHAP 2: Pelatihan Model Dinamis & Sinkronisasi Assets (PIC: Danish)
> 🎯 **Target**: Menghasilkan model LSTM `dynamic_model.tflite` (30x66 fitur) berbasis data manusia nyata dengan akurasi LOSO $\ge 75\%$.  
> ⏱️ **Estimasi Waktu**: ±10–15 menit.

- [x] Pastikan folder `data/dynamic_raw/` telah terisi minimal 30–50 take per kelas dari ke-3 signer (Terkumpul 874 take valid).
- [x] Jalankan skrip pelatihan:
  ```powershell
  cd d:\programming\python\RPL\projectRepo\ml_pipeline
  .\.venv\Scripts\python.exe train_dynamic_model.py
  ```
- [x] Periksa luaran evaluasi:
  - [x] Mode validasi otomatis menggunakan **Leave-One-Signer-Out (LOSO, held_out=vanesa)**.
  - [x] Akurasi validasi akhir: **88.03%** (Macro F1-score: **86.04%** — melampaui target $\ge 75\%$).
  - [x] Grafik tersimpan di `models/training_curves_dynamic.png` dan `models/confusion_matrix_dynamic.png`.
- [x] Jalankan sinkronisasi model dan label ke proyek Android:
  ```powershell
  .\.venv\Scripts\python.exe sync_android_assets.py
  ```
- [x] Verifikasi otomatis di terminal menampilkan tanda `[OK]` untuk `dynamic_model.tflite: input=[1, 30, 66], output=[1, 6]` (149.6 KB, parity check max diff = 0.000000).

---

### TAHAP 3: Instalasi, Pengujian di Perangkat & Checklist (PIC: Ahmad & Vanesa)
> 🎯 **Target**: Verifikasi kestabilan aplikasi di perangkat fisik dan pengisian matriks evaluasi kinerja.  
> ⏱️ **Estimasi Waktu**: ±30–45 menit.  
> 📖 **Form Pengujian**: Buka [`android_app/DEVICE_TEST_CHECKLIST.md`](file:///d:/programming/python/RPL/projectRepo/android_app/DEVICE_TEST_CHECKLIST.md).

#### 3.1 Kompilasi & Pemasangan Aplikasi
- [x] Kompilasi APK Debug & Rilis GitHub:
  - **Download APK Siap Pasang**: [SignToSpeech-v0.2.0-sprint2.apk](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/releases/download/v0.2.0-sprint2/SignToSpeech-v0.2.0-sprint2.apk)
  - **Halaman GitHub Release**: [v0.2.0-sprint2](https://github.com/codename-alfa/BISINDO-Sign-to-Speech/releases/tag/v0.2.0-sprint2)
- [ ] Opsi Pasang via ADB / Android Studio (bagi pengembang):
  ```powershell
  cd d:\programming\python\RPL\projectRepo\android_app
  $env:JAVA_HOME = "$env:USERPROFILE\.jdks\jbr-17.0.14"
  .\gradlew.bat installDebug
  ```

#### 3.2 Pengujian Mode Huruf Statis (A–Z) — Arah 1
- [ ] Pilih tombol **Huruf (A–Z)** di bar atas aplikasi.
- [ ] Peragakan abjad alfabet statis di depan kamera depan.
- [ ] Verifikasi indikator keyakinan:
  - Huruf berubah hijau dan stabil jika keyakinan $\ge 70\%$.
  - Muncul saran alternatif ("Mungkin: ...") jika keyakinan $< 70\%$.
- [ ] Verifikasi audio TTS: Huruf yang stabil otomatis disuarakan dalam Bahasa Indonesia.
- [ ] Cek tombol **Mute**: Saat ditekan menjadi `Suara MUTE`, transkrip tetap bertambah namun suara berhenti.
- [ ] Cek tombol **Hapus**: Menghapus teks transkrip di bar bawah.

#### 3.3 Pengujian Mode Kata Dinamis (5 Kosakata) — Arah 1
- [ ] Pilih tombol **Kata** di bar atas aplikasi.
- [ ] Peragakan masing-masing kata sebanyak 5 kali (*Halo, Terima kasih, Tolong, Ya, Tidak*).
- [ ] Uji Kestabilan Tangan Diam (**Anti-Spam / `_idle` Guard**):
  - Letakkan tangan diam atau lakukan gerakan acak di depan kamera selama 30 detik.
  - **Kriteria Lulus**: Tidak boleh ada kata yang tertebak secara palsu (*false trigger $\le 1$ kali*).

#### 3.4 Evaluasi Komparatif Delegate `CPU` vs `GPU`
- [ ] Di HP fisik (**Xiaomi 15** dan **Redmi Pad 2**):
  - Catat FPS dan nilai `MP: ... ms` di bar status atas saat menggunakan `CPU`.
  - Ketuk tombol `GPU`: tunggu transisi singkat, lalu catat FPS dan `MP: ... ms` saat menggunakan `GPU`.
  - **Uji Keandalan**: Tekan bergantian `CPU ➔ GPU ➔ CPU` sebanyak 5 kali, pastikan aplikasi tidak *force close*.
- [ ] Di **Emulator AVD**:
  - Pastikan tombol `GPU` berwarna abu-abu dan tidak dapat ditekan (terkunci aman oleh `DelegateGuard`).
- [ ] Catat seluruh hasil angka pengukuran pada tabel di [`DEVICE_TEST_CHECKLIST.md`](file:///d:/programming/python/RPL/projectRepo/android_app/DEVICE_TEST_CHECKLIST.md).

---

## 🎯 Kriteria Keberhasilan Sprint 2 (Definition of Done)

- [x] Seluruh 6 kelas dinamis (`Halo`, `Terima kasih`, `Tolong`, `Ya`, `Tidak`, `_idle`) memiliki minimal 30–50 rekaman nyata per kelas dari 3 orang (Total 874 take valid).
- [x] Model `dynamic_model.tflite` dilatih dengan arsitektur 66 fitur dan lolos pengujian paritas Keras vs TFLite (Max Diff = 0.000000, Akurasi LOSO = 88.03%).
- [x] Unit test paritas Android JUnit lolos 100% (15/15 test passed).
- [ ] Mode Huruf (A–Z) dan Mode Kata berfungsi *end-to-end* (Kamera ➔ Deteksi Landmark ➔ Klasifikasi TFLite ➔ Teks UI ➔ Suara TTS Bahasa Indonesia) saat diuji di HP fisik.
- [ ] Matriks pada file `DEVICE_TEST_CHECKLIST.md` terisi lengkap sebagai bukti progres untuk laporan mingguan proyek RPL.

