# 🎯 Project Development Context: Codebase Workspace

**Mata Kuliah**: Rekayasa Perangkat Lunak (RPL) — Universitas Indonesia  
**Proyek**: Real-Time BISINDO Sign Language Translator Based on Edge AI & Bi-Directional Speech  
**Lokasi Workspace**: `d:\programming\python\RPL\projectRepo\`  
**Status Repositori**: Isolated Codebase Repository (Di-ignore di root `.gitignore`)

---

## 📌 1. Gambaran Umum Repositori Kode

Folder `projectRepo/` merupakan repositori tempat pengembangan kode aplikasi **Android Native (Kotlin)** dan **Pipeline ML (Python)** dilakukan secara langsung. 

Seluruh aktivitas koding, *environment setup*, pelatihan model, dan *build* APK berpusat di direktori ini.

---

## 🗺️ 2. Structure Map Repositori Kode

```text
projectRepo/
├── README.md                       # Halaman utama GitHub: setup, branching, handoff model
├── projectDevelopmentContext.md    # [FILE INI] Dashboard konteks operasional kodingan
├── DEVELOPMENT_PLAN.md             # ⚙️ Kontrak interface & checklist teknis
├── .gitignore
│
├── android_app/                    # 📱 Project Android Studio (Native Kotlin) — dibuat Ahmad
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/signtospeech/
│   │   │   ├── assets/             # hand_landmarker.task, *.tflite, *_labels.txt
│   │   │   └── res/
│   │   └── build.gradle.kts
│   └── build.gradle.kts
│
├── ml_pipeline/                    # 🧠 Project Python Machine Learning (Python 3.12)
│   ├── requirements.txt            # Versi ter-pin & terverifikasi
│   ├── setup_check.py              # Verifikasi environment end-to-end
│   ├── feature_utils.py            # Kontrak normalisasi (mirror FeatureExtractor.kt)
│   ├── labels/                     # static_labels.txt (A-Z), dynamic_labels.txt (6 kelas termasuk _idle)
│   ├── tests/                      # normalization/model_space/dynamic test vectors JSON (parity Python ↔ Kotlin)
│   ├── assets/                     # hand_landmarker.task
│   ├── data/                       # static/ (CSV) · dynamic_raw/ (.npz 874 take valid 3 signer)
│   ├── models/                     # dynamic_model.tflite (149.6 KB, LOSO 88.03%) & static_model.tflite
│   └── sync_android_assets.py      # Otomasi sinkronisasi model & label ke Android assets
│
└── bisindo-web-mockup/             # 🌐 Prototipe web interaktif (Vite) untuk presentasi
```

---

## ⚙️ 3. Quick Start & Execution Commands

### A. Setup Python ML Pipeline (`ml_pipeline/`)
> Wajib **Python 3.10–3.12** — TensorFlow & MediaPipe belum mendukung 3.13/3.14. MediaPipe memakai **Tasks API** (`HandLandmarker`), bukan legacy `mp.solutions`.

```bash
# 0. (Sekali saja) install Python 3.12 via Python Install Manager
py install 3.12

# 1. Masuk ke folder ML
cd ml_pipeline

# 2. Buat & aktifkan virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate      # Windows PowerShell / CMD

# 3. Install dependensi ML & verifikasi environment
pip install -r requirements.txt
python setup_check.py        # harus: ALL CHECKS PASSED

# 4. Jalankan script perekaman data dinamis via webcam (opsional review per file)
python collect_dynamic_data.py --signer danish
python collect_dynamic_data.py --file data/dynamic_raw/Terima_kasih/danish_053.npz

# 5. Latih model MLP (Statis) & LSTM 66D (Dinamis LOSO)
python train_static_model.py
python train_dynamic_model.py

# 6. Sinkronisasi aset model & label ke Android app
python sync_android_assets.py
```

### B. Setup Android Native App (`android_app/`)
1. Buka **Android Studio**.
2. Pilih **Open an Existing Project** ➔ Arahkan ke folder `projectRepo/android_app`.
3. Pastikan `hand_landmarker.task`, `static_model.tflite`, `dynamic_model.tflite`, `dynamic_model_meta.json`, dan `*_labels.txt` sudah tersinkronisasi di `app/src/main/assets/`.
4. Hubungkan HP Android fisik (Samsung A30s / Xiaomi 15 / Redmi Pad 2) via USB Debugging.
5. Tekan **Run App (`Shift + F10`)** di Android Studio atau jalankan `.\gradlew.bat installDebug`.

---

### C. Web Mockup (`bisindo-web-mockup/`)
```bash
cd bisindo-web-mockup
npm install
npm run dev
```

---

## 🌿 4. Alur Git: Branch per Anggota ➔ Pull Request

| Anggota | Branch |
|:---|:---|
| Danish (ML) | `alfa` |
| Ahmad (Android) | `malik` |
| Vanesa (QA & Data) | `vanesa` |

1. `git pull origin main` sebelum mulai kerja.
2. Commit dengan format `type(scope): pesan` (mis. `feat(ml): train static MLP`).
3. `git push origin <branch>` ➔ buka Pull Request ke `main` ➔ 1 anggota review ➔ merge.
4. `main` diproteksi: tidak ada push langsung.

---

## 🔗 5. Referensi Spesifikasi Teknis Complete
Spesifikasi arsitektur, diagram UML, dan target SLA ada di repositori dokumentasi [`RPL-sign-to-speech-context`](https://github.com/codename-alfa/RPL-sign-to-speech-context):
- [01_uml_and_architecture.md](https://github.com/codename-alfa/RPL-sign-to-speech-context/blob/main/docs/specs/01_uml_and_architecture.md)
- [02_ml_pipeline_spec.md](https://github.com/codename-alfa/RPL-sign-to-speech-context/blob/main/docs/specs/02_ml_pipeline_spec.md)
- [03_android_app_spec.md](https://github.com/codename-alfa/RPL-sign-to-speech-context/blob/main/docs/specs/03_android_app_spec.md)
- [04_operational_timeline.md](https://github.com/codename-alfa/RPL-sign-to-speech-context/blob/main/docs/specs/04_operational_timeline.md)
