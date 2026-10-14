# 🌐 BISINDO Sign-to-Speech Web Mockup (Interactive Living Prototype)

> **Mata Kuliah**: Rekayasa Perangkat Lunak (RPL) — Program Studi Teknik Komputer, Universitas Indonesia  
> **Proyek**: *Real-Time BISINDO Sign Language Translator Based on Edge AI & Bi-Directional Speech*  
> **Tim Pengembang**: Ahmad Malik Prasetyo (2406416270), Danish Al Fayyadh Sunarta (2406416951), Vanesa Kayla Zahra (2306161901)  

Repositori prototipe interaktif ini dibangun secara terpisah untuk keperluan demonstrasi dan presentasi progres mata kuliah RPL. Prototipe ini mengimplementasikan seluruh spesifikasi desain pada `docs/one_week_mockup_plan.md` dan siap dideploy ke **Vercel**.

---

## ✨ Fitur Utama Prototipe Web

1. **Arah 1: Tuli ➔ Dengar (Sign to Speech)**
   - 📷 **Kamera Real-Time**: Menggunakan HTML5 `getUserMedia` dengan toggle kamera depan/belakang, mirror, dan overlay AR MediaPipe 21 Hand Landmarks.
   - 🧠 **Simulasi Edge AI Latency**: Latensi inferensi < 50 ms (memenuhi target SLA < 100 ms).
   - 🔊 **Web Speech Synthesis (TTS)**: Pelafalan otomatis suara Bahasa Indonesia (`id-ID`) dengan animasi equalizer soundwave.
   - 🛡️ **Mekanisme Fallback (Confidence < 70%)**: Memunculkan tombol *Quick Suggestions* saat model ragu.

2. **Arah 2: Dengar ➔ Tuli (Speech to Sign)**
   - 🎤 **Web Speech Recognition (STT)**: Transkripsi suara real-time Bahasa Indonesia dengan tombol mikrofon pulsing wave.
   - 🔤 **Aksesibilitas Tipografi**: Teks transkripsi kontras tinggi (OLED True Black `#090C10`).
   - 🏷️ **NLU Keyword Matcher & Visual Cards**: Mendeteksi kata kunci layanan publik (*Obat* 💊, *Dokter* 🩺, *Bayar/Kasir* 💳, *Tolong* 🆘, *Sakit/Darurat* 🚨, dll.) dan memunculkan kartu visual interaktif.

3. **🎮 Presenter Demo Controller (Fail-Safe)**
   - Drawer kendali demonstrasi (tekan tombol `D`) agar presentasi di depan dosen/aslab 100% mulus dan bebas kegagalan teknis.
   - **Pintasan Keyboard (Hotkeys)**:
     - `1`: Simulasi gestur *"Terima Kasih"* (94% Keyakinan)
     - `2`: Simulasi gestur *"Halo"* (92% Keyakinan)
     - `3`: Simulasi gestur *"Tolong"* (88% Keyakinan)
     - `4`: Simulasi gestur *"Ya"* (95% Keyakinan)
     - `5`: Simulasi gestur *"Tidak"* (91% Keyakinan)
     - `0`: Simulasi gestur *Ragu / Ambigu* (<70% Keyakinan memicu Fallback)
     - `M`: Tukar Mode (Arah 1 ⬌ Arah 2)
     - `D`: Buka / Tutup Demo Controller
     - `Space`: Ucapkan suara (TTS) / Merekam suara (STT)

---

## 💻 Menjalankan di Lokal (Local Development)

```bash
# Masuk ke direktori web mockup
cd bisindo-web-mockup

# Jalankan development server
npm run dev
```

Buka URL lokal yang muncul di terminal (biasanya `http://localhost:5173`) di browser Google Chrome atau Microsoft Edge.

---

## 🚀 Panduan Deploy ke Vercel

### Cara 1: Menggunakan Vercel CLI (Paling Cepat & Praktis)

1. Buka terminal di folder `bisindo-web-mockup`:
   ```bash
   cd bisindo-web-mockup
   ```
2. Jalankan perintah Vercel:
   ```bash
   npx vercel
   ```
3. Ikuti prompt interaktif (tekan `Enter` untuk default):
   - Set up and deploy? **Y**
   - Which scope? **Pilih akun Vercel Anda**
   - Link to existing project? **N**
   - What's your project's name? **bisindo-sign-to-speech**
   - In which directory is your code located? **./**
   - Want to modify these settings? **N**
4. Dalam beberapa detik, URL produksi Vercel (`https://bisindo-sign-to-speech.vercel.app`) akan langsung aktif dengan HTTPS gratis!

---

### Cara 2: Deploy Melalui Repositori GitHub Baru

Jika Anda ingin menghubungkannya ke repositori GitHub terpisah:

1. Buat repositori baru di GitHub (misal: `bisindo-web-mockup`).
2. Di dalam folder `bisindo-web-mockup`, inisialisasi Git:
   ```bash
   cd bisindo-web-mockup
   git init
   git add .
   git commit -m "feat: initial release of bisindo web mockup prototype"
   git branch -M main
   git remote add origin https://github.com/<username-github-anda>/bisindo-web-mockup.git
   git push -u origin main
   ```
3. Buka dashboard [Vercel](https://vercel.com/new).
4. Klik **Import Project** dan pilih repositori `bisindo-web-mockup`.
5. Vercel akan otomatis mengenali framework **Vite** dan pengaturan `vercel.json`. Klik **Deploy**!

---

### Cara 3: Drag & Drop Manual (Deploy Tanpa Git)

1. Jalankan build di lokal:
   ```bash
   npm run build
   ```
2. Buka [Vercel Dashboard](https://vercel.com).
3. Seret (*drag & drop*) folder `dist` yang baru dihasilkan langsung ke halaman dashboard Vercel.

---

## 📱 Tips Presentasi ke Dosen & Aslab

- Buka tautan Vercel di browser smartphone (Samsung / Xiaomi / iPhone).
- Klik tombol menu browser (titik tiga) ➔ **"Add to Home screen"** / **"Tambahkan ke Layar Utama"** untuk mengaktifkan mode PWA full-screen tanpa address bar.
- Siapkan QR code tautan Vercel pada slide presentasi Anda agar dosen dapat langsung mencoba interaksi di smartphone mereka sendiri.
