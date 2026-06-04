# HeartGuard — Prediksi Penyakit Jantung
### Proyek Akhir Mata Kuliah Pengembangan Sistem Informasi

Sistem prediksi penyakit jantung menggunakan **Random Forest** dengan metode evaluasi **Multi-Holdout Validation**, dibangun dengan Django + Scikit-learn.

---

## 🗂️ Struktur Proyek

```
heart_disease_project/
├── config/                     ← Konfigurasi Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── heart_disease/              ← Aplikasi utama
│   ├── ml_model.py             ← Random Forest + Multi-Holdout
│   ├── models.py               ← Database models
│   ├── views.py                ← Controller
│   ├── urls.py                 ← URL routing
│   ├── admin.py
│   ├── templatetags/
│   │   └── custom_filters.py
│   └── templates/
│       └── heart_disease/
│           ├── base.html
│           ├── index.html
│           ├── dashboard.html
│           ├── training_result.html
│           ├── predict.html
│           ├── result.html
│           ├── history.html
│           └── about.html
├── static/                     ← CSS, JS, assets
├── media/
│   ├── models/                 ← Model .pkl tersimpan di sini
│   └── plots/
├── dataset/
│   └── heart.csv               ← Upload dataset Kaggle di sini
├── manage.py
├── requirements.txt
└── generate_sample_dataset.py  ← Generator dataset contoh
```

---

## ⚡ Cara Menjalankan

### 1. Clone / extract project
```bash
cd heart_disease_project
```

### 2. Buat virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Siapkan Dataset
**Opsi A — Dataset asli dari Kaggle:**
Download dari https://www.kaggle.com/datasets/johnsmith88/heart-disease-dataset
Simpan sebagai `dataset/heart.csv`

**Opsi B — Dataset contoh (untuk testing):**
```bash
python generate_sample_dataset.py
```

### 5. Migrasi database
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. (Opsional) Buat superuser admin
```bash
python manage.py createsuperuser
```

### 7. Jalankan server
```bash
python manage.py runserver
```

Buka browser: **http://127.0.0.1:8000**

---

## 🔄 Alur Penggunaan

1. **Beranda** → Lihat overview sistem
2. **Dashboard** → Konfigurasi dan latih model (pilih n_splits & n_estimators)
3. **Hasil Training** → Lihat metrik, grafik confusion matrix, ROC curve, dll.
4. **Prediksi** → Isi form data klinis pasien
5. **Hasil** → Lihat prediksi, probabilitas, dan tingkat risiko
6. **Riwayat** → Semua prediksi tersimpan

---

## 🧠 Metode Multi-Holdout Validation

```
Dataset (100%)
    │
    ├── Holdout 1: Train (80%) / Test (20%) → RF Model 1 → Metrics 1
    ├── Holdout 2: Train (80%) / Test (20%) → RF Model 2 → Metrics 2
    ├── Holdout 3: Train (80%) / Test (20%) → RF Model 3 → Metrics 3
    ├── Holdout 4: Train (80%) / Test (20%) → RF Model 4 → Metrics 4
    └── Holdout 5: Train (80%) / Test (20%) → RF Model 5 → Metrics 5
                                                              │
                                              Rata-rata semua Metrics
                                              Simpan model F1 terbaik
```

---

## 📊 Fitur Dataset (Heart Disease UCI)

| Fitur | Keterangan |
|-------|-----------|
| age | Usia pasien |
| sex | Jenis kelamin (0=P, 1=L) |
| cp | Tipe nyeri dada (0-3) |
| trestbps | Tekanan darah istirahat |
| chol | Kolesterol serum |
| fbs | Gula darah puasa >120 |
| restecg | Hasil ECG istirahat |
| thalach | Detak jantung maksimum |
| exang | Angina akibat olahraga |
| oldpeak | ST depression |
| slope | Slope segmen ST |
| ca | Jumlah pembuluh mayor |
| thal | Thalassemia |
| **target** | **0=Tidak sakit, 1=Sakit jantung** |

---

## 🛠️ Teknologi

- **Backend**: Django 4.2 (Python)
- **ML**: Scikit-learn (Random Forest)
- **Data**: Pandas, NumPy
- **Visualisasi**: Matplotlib, Seaborn
- **Frontend**: Bootstrap 5, Bootstrap Icons
- **Database**: SQLite (Django ORM)

---

*Proyek Akhir — Pengembangan Sistem Informasi*
