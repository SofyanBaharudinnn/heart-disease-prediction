"""
ml_model.py
Modul Random Forest dengan Multi-Holdout Validation
untuk prediksi penyakit jantung.
"""

import os
import io
import base64
import warnings
import numpy as np
import pandas as pd
import joblib

# matplotlib & seaborn: lazy import (hanya diload saat training, bukan saat startup)
# Ini penting agar server bisa jalan meski matplotlib tidak terinstall
plt = None
sns = None

def _ensure_matplotlib():
    """Load matplotlib dan seaborn saat pertama kali dibutuhkan."""
    global plt, sns
    if plt is None:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as _plt
        import seaborn as _sns
        plt = _plt
        sns = _sns

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, roc_auc_score, roc_curve,
    classification_report
)

warnings.filterwarnings('ignore')

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'dataset', 'heart.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'media', 'models')
PLOT_DIR  = os.path.join(BASE_DIR, 'media', 'plots')

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(PLOT_DIR,  exist_ok=True)

MODEL_PATH  = os.path.join(MODEL_DIR, 'random_forest_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

# ─── Colour palette ─────────────────────────────────────────────────────────
COLORS = {
    'primary': '#1a3a5c',
    'secondary': '#e63946',
    'accent': '#2a9d8f',
    'light': '#f8f9fa',
    'dark': '#212529',
    'success': '#2dc653',
    'warning': '#ffc300',
}

# ─── Dataset loader / feature info ──────────────────────────────────────────
FEATURE_INFO = {
    'age':      {'label': 'Usia (tahun)',   'min': 20,  'max': 80,  'step': 1},
    'sex':      {'label': 'Jenis Kelamin',  'min': 0,   'max': 1,   'step': 1,
                 'choices': [(0, 'Perempuan'), (1, 'Laki-laki')]},
    'cp':       {'label': 'Tipe Nyeri Dada','min': 0,   'max': 3,   'step': 1,
                 'choices': [(0,'Typical Angina (Angina Pektoris Tipikal)'),(1,'Atypical Angina (Angina Pektoris Atipikal)'),
                             (2,'Non-anginal Pain (Nyeri Dada Non-Kardiak)'),(3,'Asymptomatic (Asimtomatik)')]},
    'trestbps': {'label': 'Tekanan Darah Istirahat (mmHg)', 'min': 90,  'max': 200, 'step': 1},
    'chol':     {'label': 'Kolesterol (mg/dl)',             'min': 100, 'max': 600, 'step': 1},
    'fbs':      {'label': 'Gula Darah Puasa > 120 mg/dl (Fasting Blood Sugar - FBS)',  'min': 0,   'max': 1,   'step': 1,
                 'choices': [(0,'Tidak'), (1,'Ya')]},
    'restecg':  {'label': 'Hasil ECG Istirahat',            'min': 0,   'max': 2,   'step': 1,
                 'choices': [(0,'Normal'),(1,'ST-T Wave Abnormality (Abnormalitas Gelombang ST-T)'),(2,'Left Ventricular Hypertrophy (Hipertrofi Ventrikel Kiri)')]},
    'thalach':  {'label': 'Detak Jantung Maksimum',         'min': 60,  'max': 220, 'step': 1},
    'exang':    {'label': 'Angina Akibat Olahraga',         'min': 0,   'max': 1,   'step': 1,
                 'choices': [(0,'Tidak'), (1,'Ya')]},
    'oldpeak':  {'label': 'ST Depression (Depresi ST)',                  'min': 0.0, 'max': 6.2, 'step': 0.1},
    'slope':    {'label': 'Slope ST Segment (Kemiringan Segmen ST)',               'min': 0,   'max': 2,   'step': 1,
                 'choices': [(0,'Upsloping (Melandai Naik)'),(1,'Flat (Datar)'),(2,'Downsloping (Melandai Turun)')]},
    'ca':       {'label': 'Jumlah Pembuluh Mayor',          'min': 0,   'max': 4,   'step': 1},
    'thal':     {'label': 'Thalassemia (Talasemia)',                    'min': 0,   'max': 3,   'step': 1,
                 'choices': [(0,'Normal'),(1,'Fixed Defect (Defek Menetap)'),(2,'Reversable Defect (Defek Reversibel)'),(3,'Unknown (Tidak Diketahui)')]},
}


def load_dataset():
    """Load dan validasi dataset."""
    if not os.path.exists(DATA_PATH):
        return None, "Dataset tidak ditemukan. Silakan upload file heart.csv ke folder dataset/"
    df = pd.read_csv(DATA_PATH)
    # Hapus duplikat & nilai hilang
    df.drop_duplicates(inplace=True)
    df.dropna(inplace=True)
    
    # Perbaiki inversi target: di dataset asli, 1 = normal/tidak sakit, 0 = sakit jantung.
    # Kita balik agar 1 = sakit jantung (positif) dan 0 = normal/tidak sakit (negatif).
    if 'target' in df.columns:
        df['target'] = 1 - df['target']
        
    return df, None


def plot_to_base64(fig):
    _ensure_matplotlib()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=120,
                facecolor='white', edgecolor='none')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64


# ─── Multi-Holdout Validation ────────────────────────────────────────────────
def multi_holdout_validation(X, y, n_splits=5, test_size=0.3,
                              n_estimators=100, random_state=42):
    """
    Multi-Holdout Validation:
    Menjalankan train/test split sebanyak n_splits kali dengan
    random_state berbeda, lalu merata-ratakan semua metrik.
    """
    results = []
    all_y_test, all_y_pred, all_y_prob = [], [], []

    for i in range(n_splits):
        seed = random_state + i
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=seed, stratify=y
        )

        scaler = StandardScaler()
        X_train_sc = scaler.fit_transform(X_train)
        X_test_sc  = scaler.transform(X_test)

        clf = RandomForestClassifier(
            n_estimators=n_estimators,
            random_state=seed,
            n_jobs=-1
        )
        clf.fit(X_train_sc, y_train)

        y_pred = clf.predict(X_test_sc)
        y_prob = clf.predict_proba(X_test_sc)[:, 1]

        results.append({
            'fold':       i + 1,
            'accuracy':   accuracy_score(y_test, y_pred),
            'precision':  precision_score(y_test, y_pred, zero_division=0),
            'recall':     recall_score(y_test, y_pred, zero_division=0),
            'f1':         f1_score(y_test, y_pred, zero_division=0),
            'roc_auc':    roc_auc_score(y_test, y_prob),
            'model':      clf,
            'scaler':     scaler,
        })

        all_y_test.extend(y_test)
        all_y_pred.extend(y_pred)
        all_y_prob.extend(y_prob)

    # Rata-rata metrik
    avg = {
        'accuracy':  np.mean([r['accuracy']  for r in results]),
        'precision': np.mean([r['precision'] for r in results]),
        'recall':    np.mean([r['recall']    for r in results]),
        'f1':        np.mean([r['f1']        for r in results]),
        'roc_auc':   np.mean([r['roc_auc']   for r in results]),
    }
    std = {
        'accuracy':  np.std([r['accuracy']  for r in results]),
        'precision': np.std([r['precision'] for r in results]),
        'recall':    np.std([r['recall']    for r in results]),
        'f1':        np.std([r['f1']        for r in results]),
        'roc_auc':   np.std([r['roc_auc']   for r in results]),
    }

    # Latih model final menggunakan keseluruhan dataset (100% data) agar prediksi real-time presisi
    final_scaler = StandardScaler()
    X_scaled = final_scaler.fit_transform(X)

    final_model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1
    )
    final_model.fit(X_scaled, y)

    # Simpan model final dan scaler ke disk
    joblib.dump(final_model, MODEL_PATH)
    joblib.dump(final_scaler, SCALER_PATH)

    # Dapatkan fold terbaik dari evaluasi Multi-Holdout untuk visualisasi dan detail metrik di UI
    best = max(results, key=lambda r: r['f1'])

    return results, avg, std, all_y_test, all_y_pred, all_y_prob, best


# ─── Plot generators ─────────────────────────────────────────────────────────
def generate_confusion_matrix_plot(y_true, y_pred):
    _ensure_matplotlib()
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Tidak Sakit', 'Sakit Jantung'],
                yticklabels=['Tidak Sakit', 'Sakit Jantung'],
                ax=ax, linewidths=0.5, linecolor='white')
    ax.set_title('Confusion Matrix (Gabungan Multi-Holdout)', fontsize=13, fontweight='bold', pad=12)
    ax.set_ylabel('Aktual', fontsize=11)
    ax.set_xlabel('Prediksi', fontsize=11)
    fig.tight_layout()
    return plot_to_base64(fig)


def generate_roc_curve_plot(y_true, y_prob):
    _ensure_matplotlib()
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    auc_val = roc_auc_score(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, color=COLORS['secondary'], lw=2.5,
            label=f'ROC Curve (AUC = {auc_val:.3f})')
    ax.plot([0,1],[0,1], color='gray', linestyle='--', lw=1.5, label='Random Classifier')
    ax.fill_between(fpr, tpr, alpha=0.08, color=COLORS['secondary'])
    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title('ROC Curve', fontsize=13, fontweight='bold', pad=12)
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return plot_to_base64(fig)


def generate_feature_importance_plot(model, feature_names):
    _ensure_matplotlib()
    importances = pd.Series(model.feature_importances_, index=feature_names)
    importances = importances.sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(7, 6))
    colors_bar = [COLORS['secondary'] if v >= importances.quantile(0.7)
                  else COLORS['accent'] for v in importances]
    ax.barh(importances.index, importances.values, color=colors_bar, edgecolor='white')
    ax.set_title('Feature Importance – Random Forest', fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel('Importance Score', fontsize=11)
    ax.grid(axis='x', alpha=0.3)
    fig.tight_layout()
    return plot_to_base64(fig)


def generate_holdout_comparison_plot(results):
    _ensure_matplotlib()
    folds      = [r['fold']      for r in results]
    accuracies = [r['accuracy']  for r in results]
    f1s        = [r['f1']        for r in results]
    aucs       = [r['roc_auc']   for r in results]

    x = np.arange(len(folds))
    width = 0.25

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width, accuracies, width, label='Accuracy',  color=COLORS['primary'],   alpha=0.85)
    ax.bar(x,         f1s,        width, label='F1-Score',  color=COLORS['accent'],    alpha=0.85)
    ax.bar(x + width, aucs,       width, label='ROC-AUC',   color=COLORS['secondary'], alpha=0.85)

    ax.set_xlabel('Holdout Ke-', fontsize=11)
    ax.set_ylabel('Score', fontsize=11)
    ax.set_title('Perbandingan Metrik Setiap Holdout', fontsize=13, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Holdout {f}' for f in folds])
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    return plot_to_base64(fig)


def generate_distribution_plots(df):
    """Distribusi target + usia vs kolesterol."""
    _ensure_matplotlib()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Target distribution
    # Urutkan berdasarkan index agar 0 (Tidak Sakit) berpasangan dengan label ke-1,
    # dan 1 (Sakit Jantung) berpasangan dengan label ke-2 secara konsisten.
    target_counts = df['target'].value_counts().sort_index()
    labels = ['Tidak Sakit Jantung', 'Sakit Jantung']
    colors = [COLORS['accent'], COLORS['secondary']]
    axes[0].pie(target_counts, labels=labels, colors=colors,
                autopct='%1.1f%%', startangle=140,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2})
    axes[0].set_title('Distribusi Kelas Target', fontsize=13, fontweight='bold')

    # Age vs Cholesterol scatter
    colors_scatter = [COLORS['secondary'] if t == 1 else COLORS['accent']
                      for t in df['target']]
    axes[1].scatter(df['age'], df['chol'], c=colors_scatter, alpha=0.6, edgecolors='white', s=50)
    axes[1].set_xlabel('Usia', fontsize=11)
    axes[1].set_ylabel('Kolesterol', fontsize=11)
    axes[1].set_title('Usia vs Kolesterol', fontsize=13, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    # pyrefly: ignore [missing-import]
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLORS['secondary'], label='Sakit Jantung'),
        Patch(facecolor=COLORS['accent'],    label='Tidak Sakit'),
    ]
    axes[1].legend(handles=legend_elements, fontsize=10)
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    return plot_to_base64(fig)


def generate_correlation_heatmap(df):
    _ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(10, 8))
    corr = df.corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdYlBu_r',
                ax=ax, linewidths=0.5, linecolor='white',
                annot_kws={'size': 8})
    ax.set_title('Korelasi Antar Fitur', fontsize=13, fontweight='bold', pad=12)
    fig.tight_layout()
    return plot_to_base64(fig)


# ─── Main training pipeline ──────────────────────────────────────────────────
def train_and_evaluate(n_splits=5, n_estimators=100):
    df, err = load_dataset()
    if err:
        return None, err

    feature_cols = [c for c in df.columns if c != 'target']
    X = df[feature_cols].values
    y = df['target'].values

    # Run Multi-Holdout Validation
    results, avg, std, all_y_test, all_y_pred, all_y_prob, best = \
        multi_holdout_validation(X, y, n_splits=n_splits, n_estimators=n_estimators)

    plots = {
        'confusion_matrix':   generate_confusion_matrix_plot(all_y_test, all_y_pred),
        'roc_curve':          generate_roc_curve_plot(all_y_test, all_y_prob),
        'feature_importance': generate_feature_importance_plot(best['model'], feature_cols),
        'holdout_comparison': generate_holdout_comparison_plot(results),
        'distribution':       generate_distribution_plots(df),
        'correlation':        generate_correlation_heatmap(df),
    }

    dataset_info = {
        'total_samples': len(df),
        'features':      len(feature_cols),
        'positive':      int(y.sum()),
        'negative':      int(len(y) - y.sum()),
        'feature_names': feature_cols,
    }

    return {
        'results':      results,
        'avg':          avg,
        'std':          std,
        'plots':        plots,
        'dataset_info': dataset_info,
        'best_fold':    best['fold'],
    }, None


# ─── Prediction ──────────────────────────────────────────────────────────────
def predict_single(input_data: dict):
    """Prediksi satu sampel."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        return None, "Model belum dilatih. Silakan latih model terlebih dahulu."

    model  = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    feature_order = list(FEATURE_INFO.keys())
    X = np.array([[float(input_data[f]) for f in feature_order]])
    X_sc = scaler.transform(X)

    pred  = model.predict(X_sc)[0]
    prob  = model.predict_proba(X_sc)[0]

    return {
        'prediction':  int(pred),
        'label':       'Positif Penyakit Jantung' if pred == 1 else 'Negatif Penyakit Jantung',
        'probability': {
            'negative': round(float(prob[0]) * 100, 2),
            'positive': round(float(prob[1]) * 100, 2),
        },
        'risk_level': (
            'Tinggi'   if prob[1] >= 0.7 else
            'Sedang'   if prob[1] >= 0.4 else
            'Rendah'
        ),
    }, None
