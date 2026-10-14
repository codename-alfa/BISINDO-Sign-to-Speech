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
├── projectDevelopmentContext.md   # [FILE INI] Dashboard konteks operasional kodingan
├── DEVELOPMENT_PLAN.md             # ⚙️ Technical Code Implementation & Execution Plan
│
├── android_app/                    # 📱 Project Android Studio (Native Kotlin)
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/signtospeech/
│   │   │   ├── assets/             # Tempat menyimpan static_model.tflite & dynamic_model.tflite
│   │   │   └── res/
│   │   └── build.gradle.kts
│   └── build.gradle.kts
│
└── ml_pipeline/                    # 🧠 Project Python Machine Learning
    ├── requirements.txt
    ├── data/                       # Dataset static (CSV) & dynamic (.npy)
    └── models/                     # Output model .h5 & .tflite
```

---

## ⚙️ 3. Quick Start & Execution Commands

### A. Setup Python ML Pipeline (`ml_pipeline/`)
```bash
# 1. Masuk ke folder ML
cd ml_pipeline

# 2. Buat & aktifkan virtual environment
python -m venv venv
venv\Scripts\activate       # Windows PowerShell / CMD

# 3. Install dependensi ML
pip install -r requirements.txt

# 4. Jalankan script perekaman data dinamis via webcam
python collect_dynamic_data.py

# 5. Latih model MLP & LSTM
python train_static_model.py
python train_dynamic_model.py

# 6. Konversi model ke .tflite
python convert_to_tflite.py
```

### B. Setup Android Native App (`android_app/`)
1. Buka **Android Studio**.
2. Pilih **Open an Existing Project** ➔ Arahkan ke folder `projectRepo/android_app`.
3. Pastikan `static_model.tflite` dan `dynamic_model.tflite` sudah disalin ke `app/src/main/assets/`.
4. Hubungkan HP Android fisik (Samsung A30s / Xiaomi 13T) via USB Debugging.
5. Tekan **Run App (`Shift + F10`)** di Android Studio.

---

## 🔗 4. Referensi Spesifikasi Teknis Complete
Untuk melihat spesifikasi arsitektur teoretis, diagram UML (Use Case, Sequence, Class Diagram), dan target SLA, rujuk berkas spesifikasi di root dokumentasi:
- [01_uml_and_architecture.md](file:///d:/programming/python/RPL/docs/specs/01_uml_and_architecture.md)
- [02_ml_pipeline_spec.md](file:///d:/programming/python/RPL/docs/specs/02_ml_pipeline_spec.md)
- [03_android_app_spec.md](file:///d:/programming/python/RPL/docs/specs/03_android_app_spec.md)
- [04_operational_timeline.md](file:///d:/programming/python/RPL/docs/specs/04_operational_timeline.md)
