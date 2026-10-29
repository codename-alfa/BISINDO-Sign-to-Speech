# 📱 Checklist Pengujian Perangkat & Evaluasi CPU vs GPU (Sprint 2 — Pipeline Arah 1)

Dokumen ini digunakan oleh **Vanesa** dan **Ahmad** untuk memverifikasi aplikasi Android pada Emulator (AVD) dan perangkat keras fisik (**Redmi Pad 2**, **Samsung Galaxy A30s**, **Xiaomi 15**).

---

## ⚙️ 1. Cara Install & Menjalankan Pengujian

```powershell
cd d:\programming\python\RPL\projectRepo\android_app
$env:JAVA_HOME = "$env:USERPROFILE\.jdks\jbr-17.0.14"

# Jalankan seluruh unit test JVM (paritas Python <-> Kotlin + DelegateGuard)
.\gradlew.bat testDebugUnitTest

# Build & install APK ke perangkat/emulator yang terhubung via ADB
.\gradlew.bat installDebug
```

---

## 📊 2. Tabel Perbandingan Delegate `CPU` vs `GPU` per Perangkat

Uji selama **60 detik per delegate** dengan 1 tangan bergerak aktif di depan kamera depan. Catat angka dari HUD bar atas (`FPS · MP ms · Cls ms · CPU/GPU`):

| Perangkat | Delegate | Rata-rata FPS | FPS Minimum | Rata-rata `MP ms` | Rata-rata `Cls ms` | Cold-Start Switch (s) | Suhu / Stabilitas | Crash / Freeze? | Keputusan Demo |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---:|:---:|
| **Emulator AVD (`x86_64`)** | **CPU** | ... | ... | ... | ... | — | Stabil | Tidak | Default Dev |
| **Emulator AVD (`x86_64`)** | **GPU** | *(Terkunci)* | — | — | — | — | Tombol GPU abu-abu | Tidak | Terkunci Aman |
| **Xiaomi Redmi Pad 2** | **CPU** | ... | ... | ... | ... | — | ... | ... | ... |
| **Xiaomi Redmi Pad 2** | **GPU** | ... | ... | ... | ... | ... | ... | ... | ... |
| **Samsung Galaxy A30s** | **CPU** | ... | ... | ... | ... | — | ... | ... | ... |
| **Samsung Galaxy A30s** | **GPU** | ... | ... | ... | ... | ... | ... | ... | ... |
| **Xiaomi 15 (Live Demo)** | **CPU** | ... | ... | ... | ... | — | ... | ... | ... |
| **Xiaomi 15 (Live Demo)** | **GPU** | ... | ... | ... | ... | ... | ... | ... | ... |

> **Aturan Keputusan Demo**: Gunakan `GPU` saat Live Demo **hanya jika** rata-rata FPS atau `MP ms` membaik **≥ 20%** tanpa adanya gejala *crash* atau *freeze*. Jika tidak, tetap gunakan `CPU`.

---

## 🧪 3. Skenario Uji Keandalan `DelegateGuard` & Mode

- [ ] **Skenario A (Pindah Delegate Berulang)**: Pada HP fisik, tekan bergantian `CPU ➔ GPU ➔ CPU` sebanyak **5 kali**. Pastikan kamera dan deteksi landmark tetap berjalan tanpa *force close*.
- [ ] **Skenario B (Proteksi Emulator AVD)**: Pada AVD Android Studio, pastikan tombol `GPU` berwarna abu-abu dan menampilkan pesan *"GPU dinonaktifkan otomatis pada Emulator (AVD)"* saat diketuk.
- [ ] **Skenario C (Pemulihan Pasca-Crash & Long-Press Reset)**: Jika ada perangkat fisik yang mengalami crash saat beralih ke `GPU`, buka ulang aplikasi: pastikan aplikasi otomatis menyala dalam mode `CPU` dengan pesan *Snackbar* pemblokiran, lalu tekan lama (*long-press*) tombol `GPU` untuk membuka kembali blokir.
- [ ] **Skenario D (Isolasi Buffer Saat Ganti Mode/Kamera)**: Saat `GPU` atau `CPU` aktif, berpindah antara **Huruf (A–Z)** dan **Kata**, serta tekan tombol **Switch Camera**. Pastikan transisi bersih tanpa prediksi palsu.

---

## 🔤 4. Evaluasi Akurasi Manual Mode Huruf (26 Alfabet × 3 Percobaan)

 Uji di depan kamera depan pada pencahayaan ruangan normal:
- [ ] A – G : `... / 21` berhasil dikenali (≥ 70%) dan disuarakan TTS.
- [ ] H – N : `... / 21` berhasil dikenali (≥ 70%) dan disuarakan TTS.
- [ ] O – T : `... / 18` berhasil dikenali (≥ 70%) dan disuarakan TTS.
- [ ] U – Z : `... / 18` berhasil dikenali (≥ 70%) dan disuarakan TTS.
- **Catatan Mirror**: Jika huruf asimetris (seperti J, Z, G, H) terbalik secara sistematis antara tangan kanan dan kiri, ubah konstanta `MIRROR_X_FOR_MODEL` di [`ModelConfig.kt`](file:///d:/programming/python/RPL/projectRepo/android_app/app/src/main/java/com/signtospeech/ml/ModelConfig.kt) lalu uji ulang.

---

## 🗣️ 5. Evaluasi Mode Kata Dinamis & TTS Bahasa Indonesia

Setelah model dilatih dengan rekaman nyata 3 signer:

| Kata Target | Percobaan Berhasil (dari 5x) | Confidence Rata-rata (%) | Suara TTS Jelas & Tanpa Dobel? |
|:---|:---:|:---:|:---:|
| **Halo** | `... / 5` | ... % | Ya / Tidak |
| **Terima kasih** | `... / 5` | ... % | Ya / Tidak |
| **Tolong** | `... / 5` | ... % | Ya / Tidak |
| **Ya** | `... / 5` | ... % | Ya / Tidak |
| **Tidak** | `... / 5` | ... % | Ya / Tidak |
| **Tangan Diam / Acak 30 detik (`_idle`)** | False trigger: `...` kali (Target: 0, Maks: ≤ 1) | — | Tidak ada suara bocor |

- [ ] **Uji Tombol `Suara ON / MUTE`**: Saat `Suara MUTE` aktif, transkrip tetap bertambah tetapi suara TTS berhenti seketika.
- [ ] **Uji Tombol `Hapus`**: Menghapus baris transkrip dan me-reset riwayat duplikat 2 detik.
