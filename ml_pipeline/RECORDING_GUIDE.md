# 🎥 Panduan Sesi Perekaman Dataset Gestur Dinamis BISINDO (Sprint 2)

Dokumen ini menjadi panduan langkah demi langkah bagi anggota tim (**Danish**, **Vanesa**, dan **Ahmad**) dalam merekam dataset sekuens dinamis menggunakan skrip [`collect_dynamic_data.py`](file:///d:/programming/python/RPL/projectRepo/ml_pipeline/collect_dynamic_data.py).

---

## 🎯 1. Target Kuota Perekaman per Anggota Tim

Setiap anggota tim merekam **6 kelas** yang terdaftar di [`labels/dynamic_labels.txt`](file:///d:/programming/python/RPL/projectRepo/ml_pipeline/labels/dynamic_labels.txt):

| No | Kelas / Label | Nama Folder (`data/dynamic_raw/`) | Target per Orang | Total Tim (3 Orang) | Deskripsi Gerakan Acuan |
|:--:|:---|:---|:---:|:---:|:---|
| 1 | **Halo** | `Halo` | **50 take** | 150 take | Telapak tangan terbuka di samping kepala/bahu, melambai kiri-kanan selama ~1.5 detik |
| 2 | **Terima kasih** | `Terima_kasih` | **50 take** | 150 take | Ujung jari menyentuh dagu/bibir lalu bergerak maju-turun ke arah lawan bicara |
| 3 | **Tolong** | `Tolong` | **50 take** | 150 take | Tangan terbuka/mengatup di depan dada digerakkan naik-turun memohon |
| 4 | **Ya** | `Ya` | **50 take** | 150 take | Tangan mengepal (seperti huruf S/A) mengangguk naik-turun di depan bahu |
| 5 | **Tidak** | `Tidak` | **50 take** | 150 take | Jari telunjuk & tengah (atau telapak) digoyangkan kiri-kanan menolak |
| 6 | **`_idle`** | `_idle` | **40 take** | 120 take | Tangan diam santai, menurunkan tangan, menggaruk, atau transisi tanpa makna isyarat |
| — | **TOTAL** | — | **290 take** | **870 take** | Estimasi waktu: **±45–60 menit per orang** |

---

## 🛠️ 2. Cara Menjalankan Perekam (`collect_dynamic_data.py`)

Buka terminal PowerShell pada direktori `projectRepo/ml_pipeline`, aktifkan virtual environment, lalu jalankan dengan nama signer masing-masing:

```powershell
cd d:\programming\python\RPL\projectRepo\ml_pipeline

# Untuk Danish:
.\.venv\Scripts\python.exe collect_dynamic_data.py --signer danish

# Untuk Vanesa:
.\.venv\Scripts\python.exe collect_dynamic_data.py --signer vanesa

# Untuk Ahmad:
.\.venv\Scripts\python.exe collect_dynamic_data.py --signer ahmad
```

### Kontrol Tombol Saat Jendela Kamera Aktif:
* **`r`** : Mulai *countdown* 3 detik, diikuti perekaman otomatis selama **2.0 detik**.
* **`u`** : **Undo** — menghapus rekaman terakhir milik Anda di kelas yang sedang dipilih (gunakan jika gerakan salah atau muncul peringatan merah `Tangan hilang > 300 ms`).
* **`n` / `p`** : Pindah ke kelas berikutnya (`n`) atau sebelumnya (`p`).
* **`q`** : Keluar dari program (semua rekaman `.npz` yang sudah selesai otomatis tersimpan di disk).

---

## 📏 3. Aturan Variasi Wajib (Agar Model Tahan Uji di Live Demo)

Agar model LSTM lulus validasi **Leave-One-Signer-Out (LOSO)** dan akurat saat diuji di Xiaomi 13T / Redmi Pad 2, bagi 50 take per kata ke dalam variasi berikut:

1. **Kondisi Pencahayaan (25 take vs 25 take)**:
   * **25 take Pertama**: Ruangan terang merata (lampu utama menyala / dekat jendela).
   * **25 take Kedua**: Pencahayaan kamar standar / agak redup atau arah cahaya dari samping.
2. **Variasi Jarak Kamera**:
   * Sekitar separuh take pada jarak **~40–50 cm** (setengah badan terlihat), dan separuh lagi pada jarak **~70–80 cm**.
3. **Variasi Kecepatan & Posisi Awal**:
   * Mulai gerakan tepat saat tulisan `MEREKAM` muncul (jangan terlalu cepat selesai di 0.5 detik pertama; usahakan gerakan berlangsung natural selama **1.2 – 1.8 detik**).
4. **Khusus Kelas `_idle` (40 take)**:
   * 15 take: tangan diam di berbagai posisi layar (kiri, tengah, kanan, bawah).
   * 15 take: gerakan non-isyarat seperti menurunkan tangan ke bawah layar, mengangkat tangan lalu diam, atau menggaruk pipi/dagu.
   * 10 take: transisi acak antar posisi jari tanpa pola lambaian/anggukan.

---

## 🔍 4. Pemeriksaan Kualitas (Review) & Pengumpulan Data

Setelah selesai merekam seluruh kelas, jalankan mode **Review** untuk memutar ulang 3 sampel acak per kelas:

```powershell
.\.venv\Scripts\python.exe collect_dynamic_data.py --review
```

1. Pastikan kerangka tangan hijau bergerak mulus dan tidak muncul tulisan `TANGAN TIDAK TERDETEKSI (NaN)` di tengah-tengah gerakan kata utama.
2. Unggah seluruh isi folder `ml_pipeline/data/dynamic_raw/` ke **Google Drive Bersama** tim.
3. Setelah rekaman dari ke-3 anggota tim terkumpul di `data/dynamic_raw/`, **Danish** menjalankan pelatihan & sinkronisasi ke Android:

```powershell
.\.venv\Scripts\python.exe train_dynamic_model.py
.\.venv\Scripts\python.exe sync_android_assets.py
```

