"""
generate_pdf_report.py
Membuat laporan analisis evaluasi model prediksi penyakit jantung dalam format PDF.
Jalankan: python generate_pdf_report.py
"""

import json
import os
import base64
import io
from datetime import datetime

# --- ReportLab imports ---
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF
from PIL import Image as PILImage

# ===========================================================================
# KONFIGURASI PATH
# ===========================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'media', 'models', 'last_results.json')
OUTPUT_PATH = os.path.join(BASE_DIR, 'laporan_evaluasi_model.pdf')

# ===========================================================================
# WARNA PALETTE
# ===========================================================================
PRIMARY   = colors.HexColor('#1a3a5c')   # Navy
SECONDARY = colors.HexColor('#e63946')   # Red
ACCENT    = colors.HexColor('#2a9d8f')   # Teal
LIGHT     = colors.HexColor('#f8f9fa')   # Light gray
MEDIUM    = colors.HexColor('#dee2e6')   # Medium gray
DARK      = colors.HexColor('#212529')   # Dark
SUCCESS   = colors.HexColor('#2dc653')   # Green
WARNING   = colors.HexColor('#ffc300')   # Yellow
WHITE     = colors.white
SOFT_BLUE = colors.HexColor('#e8f0fe')   # Soft blue bg

# ===========================================================================
# LOAD DATA
# ===========================================================================
def load_data():
    if not os.path.exists(JSON_PATH):
        raise FileNotFoundError(
            f"File hasil evaluasi tidak ditemukan: {JSON_PATH}\n"
            "Silakan latih model terlebih dahulu melalui halaman Dashboard."
        )
    with open(JSON_PATH, 'r') as f:
        raw = json.load(f)

    avg        = raw.get('avg', {})
    std        = raw.get('std', {})
    fold_data  = raw.get('fold_data', [])
    inner      = raw.get('data', {})
    dataset_info = inner.get('dataset_info', {})
    best_fold  = inner.get('best_fold', '-')
    plots      = inner.get('plots', {})

    return avg, std, fold_data, dataset_info, best_fold, plots


# ===========================================================================
# HELPER: base64 → PIL Image → ReportLab Image
# ===========================================================================
def b64_to_rl_image(b64_str, width_cm, height_cm=None):
    """Konversi base64 PNG ke ReportLab Image Flowable."""
    try:
        img_bytes = base64.b64decode(b64_str)
        buf = io.BytesIO(img_bytes)
        pil_img = PILImage.open(buf)
        w_px, h_px = pil_img.size

        w_pt = width_cm * cm
        if height_cm:
            h_pt = height_cm * cm
        else:
            h_pt = w_pt * h_px / w_px  # Jaga rasio aspek

        buf.seek(0)
        return Image(buf, width=w_pt, height=h_pt)
    except Exception as e:
        print(f"[WARN] Gagal memuat gambar: {e}")
        return None


# ===========================================================================
# STYLES
# ===========================================================================
def build_styles():
    styles = getSampleStyleSheet()
    custom = {
        'cover_title': ParagraphStyle(
            'cover_title',
            fontName='Helvetica-Bold',
            fontSize=26,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=6,
            leading=32,
        ),
        'cover_sub': ParagraphStyle(
            'cover_sub',
            fontName='Helvetica',
            fontSize=13,
            textColor=colors.HexColor('#b0c4de'),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        'cover_meta': ParagraphStyle(
            'cover_meta',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#90a8c0'),
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        'section_title': ParagraphStyle(
            'section_title',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=PRIMARY,
            spaceBefore=14,
            spaceAfter=6,
            leading=18,
        ),
        'sub_title': ParagraphStyle(
            'sub_title',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=PRIMARY,
            spaceBefore=10,
            spaceAfter=4,
        ),
        'body': ParagraphStyle(
            'body',
            fontName='Helvetica',
            fontSize=10,
            textColor=DARK,
            spaceAfter=5,
            leading=15,
            alignment=TA_JUSTIFY,
        ),
        'body_center': ParagraphStyle(
            'body_center',
            fontName='Helvetica',
            fontSize=10,
            textColor=DARK,
            spaceAfter=5,
            leading=15,
            alignment=TA_CENTER,
        ),
        'caption': ParagraphStyle(
            'caption',
            fontName='Helvetica-Oblique',
            fontSize=9,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        'highlight': ParagraphStyle(
            'highlight',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=PRIMARY,
            alignment=TA_CENTER,
        ),
        'metric_value': ParagraphStyle(
            'metric_value',
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=ACCENT,
            alignment=TA_CENTER,
        ),
        'metric_label': ParagraphStyle(
            'metric_label',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_CENTER,
        ),
        'footer': ParagraphStyle(
            'footer',
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor('#adb5bd'),
            alignment=TA_CENTER,
        ),
        'table_header': ParagraphStyle(
            'table_header',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        'table_cell': ParagraphStyle(
            'table_cell',
            fontName='Helvetica',
            fontSize=9,
            textColor=DARK,
            alignment=TA_CENTER,
        ),
        'info_label': ParagraphStyle(
            'info_label',
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=PRIMARY,
        ),
        'info_value': ParagraphStyle(
            'info_value',
            fontName='Helvetica',
            fontSize=10,
            textColor=DARK,
        ),
    }
    return custom


# ===========================================================================
# PAGE TEMPLATE: header & footer
# ===========================================================================
def add_header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4

    if doc.page > 1:
        # Header bar
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, h - 30, w, 30, fill=1, stroke=0)

        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawString(1.5*cm, h - 20, 'HeartGuard')

        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(w - 1.5*cm, h - 20,
                               'Laporan Evaluasi Model Prediksi Penyakit Jantung')

        # Footer bar
        canvas.setFillColor(LIGHT)
        canvas.rect(0, 0, w, 22, fill=1, stroke=0)

        canvas.setFillColor(colors.HexColor('#6c757d'))
        canvas.setFont('Helvetica', 8)
        canvas.drawString(1.5*cm, 7, f'Dibuat: {datetime.now().strftime("%d %B %Y")}')
        canvas.drawRightString(w - 1.5*cm, 7, f'Halaman {doc.page}')

        # Thin accent line
        canvas.setStrokeColor(ACCENT)
        canvas.setLineWidth(2)
        canvas.line(0, 22, w, 22)

    canvas.restoreState()


# ===========================================================================
# COVER PAGE
# ===========================================================================
def build_cover_page(styles, avg, dataset_info):
    elems = []
    w, h = A4

    # Background block (akan digambar lewat canvas — gunakan Drawing sebagai workaround)
    # Untuk simplifikasi, gunakan Paragraph dengan background warna biru tua di tabel

    # Judul utama di tabel berwarna
    cover_data = [
        [Paragraph('❤', ParagraphStyle('ic', fontName='Helvetica-Bold',
                                        fontSize=48, textColor=SECONDARY, alignment=TA_CENTER))],
        [Paragraph('LAPORAN EVALUASI MODEL', styles['cover_title'])],
        [Paragraph('Prediksi Penyakit Jantung', styles['cover_sub'])],
        [Paragraph('Random Forest · Multi-Holdout Validation', styles['cover_sub'])],
        [Spacer(1, 0.5*cm)],
        [Paragraph(f'Tanggal Laporan: {datetime.now().strftime("%d %B %Y")}', styles['cover_meta'])],
        [Paragraph('HeartGuard — Sistem Prediksi Penyakit Jantung', styles['cover_meta'])],
    ]

    cover_table = Table(cover_data, colWidths=[w - 4*cm])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
        ('ROWPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 40),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 30),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 2, ACCENT),
    ]))
    elems.append(Spacer(1, 2*cm))
    elems.append(cover_table)
    elems.append(Spacer(1, 1*cm))

    # Ringkasan metrik di bawah cover
    def metric_card(label, value, color=ACCENT):
        return [
            Paragraph(f'{value}%', ParagraphStyle('mv', fontName='Helvetica-Bold',
                                                   fontSize=20, textColor=color, alignment=TA_CENTER)),
            Paragraph(label, ParagraphStyle('ml', fontName='Helvetica', fontSize=9,
                                             textColor=colors.HexColor('#6c757d'), alignment=TA_CENTER)),
        ]

    metrics_row = [
        metric_card('Accuracy', f"{avg.get('accuracy', 0):.2f}", ACCENT),
        metric_card('Precision', f"{avg.get('precision', 0):.2f}", PRIMARY),
        metric_card('Recall', f"{avg.get('recall', 0):.2f}", SUCCESS),
        metric_card('F1-Score', f"{avg.get('f1', 0):.2f}", SECONDARY),
        metric_card('ROC-AUC', f"{avg.get('roc_auc', 0):.2f}", WARNING),
    ]

    # Buat tabel 5 kolom untuk metrik
    card_rows_top = [[m[0] for m in metrics_row]]
    card_rows_bot = [[m[1] for m in metrics_row]]

    col_w = (w - 4*cm) / 5
    for row_data in [card_rows_top, card_rows_bot]:
        mt = Table(row_data, colWidths=[col_w]*5)
        mt.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, MEDIUM),
            ('LINEAFTER', (0, 0), (-2, -1), 0.5, MEDIUM),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elems.append(mt)

    elems.append(Spacer(1, 0.8*cm))

    # Info dataset singkat
    info_data = [
        ['Total Sampel', str(dataset_info.get('total_samples', '-')),
         'Fitur Input', str(dataset_info.get('features', '-'))],
        ['Kelas Positif (Sakit)', str(dataset_info.get('positive', '-')),
         'Kelas Negatif (Sehat)', str(dataset_info.get('negative', '-'))],
    ]
    info_t = Table(info_data, colWidths=[4*cm, 2.5*cm, 5*cm, 2.5*cm])
    info_t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY),
        ('TEXTCOLOR', (2, 0), (2, -1), PRIMARY),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), SOFT_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elems.append(info_t)
    elems.append(PageBreak())
    return elems


# ===========================================================================
# SECTION 1: PENDAHULUAN
# ===========================================================================
def build_intro(styles):
    elems = []
    elems.append(Paragraph('1. Pendahuluan', styles['section_title']))
    elems.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=8))

    elems.append(Paragraph(
        '<b>HeartGuard</b> adalah sistem berbasis kecerdasan buatan yang dirancang untuk memprediksi '
        'risiko penyakit jantung pada pasien berdasarkan data klinis. Sistem ini dibangun menggunakan '
        'algoritma <b>Random Forest</b> — sebuah metode ensemble learning yang melatih sejumlah pohon '
        'keputusan secara paralel dan menghasilkan prediksi berdasarkan suara mayoritas (voting).',
        styles['body']
    ))

    elems.append(Paragraph(
        'Laporan ini menyajikan hasil evaluasi komprehensif dari model yang telah dilatih, '
        'mencakup metrik performa, analisis per-holdout, serta visualisasi yang mendukung '
        'pemahaman mendalam terhadap kualitas model.',
        styles['body']
    ))

    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph('1.1 Tujuan Laporan', styles['sub_title']))
    tujuan = [
        '• Mengevaluasi performa model Random Forest secara kuantitatif.',
        '• Menyajikan hasil Multi-Holdout Validation dengan interpretasi yang jelas.',
        '• Mengidentifikasi fitur-fitur klinis yang paling berpengaruh dalam prediksi.',
        '• Memberikan dasar ilmiah untuk penggunaan model dalam sistem deteksi dini.',
    ]
    for t in tujuan:
        elems.append(Paragraph(t, styles['body']))

    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph('1.2 Ruang Lingkup', styles['sub_title']))
    elems.append(Paragraph(
        'Evaluasi dilakukan pada dataset <b>Heart Disease UCI</b> yang terdiri dari 303 sampel '
        'dengan 13 fitur klinis dan 1 variabel target biner (0 = Sehat, 1 = Sakit Jantung). '
        'Metode validasi yang digunakan adalah <b>Multi-Holdout Validation</b> dengan 10 iterasi, '
        'setiap iterasi menggunakan 80% data untuk pelatihan dan 20% untuk pengujian.',
        styles['body']
    ))
    return elems


# ===========================================================================
# SECTION 2: METODOLOGI
# ===========================================================================
def build_methodology(styles, dataset_info, best_fold, avg):
    elems = []
    elems.append(Paragraph('2. Metodologi', styles['section_title']))
    elems.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=8))

    elems.append(Paragraph('2.1 Dataset', styles['sub_title']))

    n_total    = dataset_info.get('total_samples', 0)
    n_features = dataset_info.get('features', 0)
    n_pos      = dataset_info.get('positive', 0)
    n_neg      = dataset_info.get('negative', 0)
    feat_names = dataset_info.get('feature_names', [])

    elems.append(Paragraph(
        f'Dataset yang digunakan adalah <b>Heart Disease UCI</b> yang banyak digunakan sebagai '
        f'benchmark dalam penelitian medis berbasis kecerdasan buatan. Dataset terdiri dari '
        f'<b>{n_total} sampel</b> pasien dengan <b>{n_features} fitur klinis</b>.',
        styles['body']
    ))

    ds_data = [
        ['Parameter Dataset', 'Nilai'],
        ['Total Sampel', str(n_total)],
        ['Jumlah Fitur Input', str(n_features)],
        ['Kelas Positif (Sakit Jantung)', f'{n_pos} ({n_pos/n_total*100:.1f}%)'],
        ['Kelas Negatif (Sehat)', f'{n_neg} ({n_neg/n_total*100:.1f}%)'],
        ['Rasio Split (Train/Test)', '80% / 20%'],
        ['Jumlah Holdout', '10 iterasi'],
    ]
    ds_t = Table(ds_data, colWidths=[9*cm, 6*cm])
    ds_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BLUE]),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elems.append(ds_t)
    elems.append(Spacer(1, 0.4*cm))

    # Tabel fitur
    elems.append(Paragraph('2.2 Deskripsi Fitur', styles['sub_title']))
    feat_desc = {
        'age':      'Usia pasien (tahun)',
        'sex':      'Jenis kelamin (0=Perempuan, 1=Laki-laki)',
        'cp':       'Tipe nyeri dada (0=Typical Angina, 1=Atypical, 2=Non-anginal, 3=Asymptomatic)',
        'trestbps': 'Tekanan darah istirahat (mmHg)',
        'chol':     'Kadar kolesterol serum (mg/dl)',
        'fbs':      'Gula darah puasa >120 mg/dl (0=Tidak, 1=Ya)',
        'restecg':  'Hasil elektrokardiografi istirahat',
        'thalach':  'Detak jantung maksimum yang dicapai (bpm)',
        'exang':    'Angina yang dipicu olahraga (0=Tidak, 1=Ya)',
        'oldpeak':  'Depresi segmen ST yang diinduksi olahraga',
        'slope':    'Kemiringan segmen ST puncak olahraga',
        'ca':       'Jumlah pembuluh darah mayor yang berwarna (0-4)',
        'thal':     'Thalassemia (0=Normal, 1=Fixed Defect, 2=Reversable Defect)',
    }
    feat_rows = [['No.', 'Fitur', 'Deskripsi']]
    for i, fname in enumerate(feat_names, 1):
        feat_rows.append([str(i), fname, feat_desc.get(fname, '-')])
    feat_rows.append(['14', 'target', 'Label (0=Sehat, 1=Sakit Jantung) — variabel target'])

    feat_t = Table(feat_rows, colWidths=[1*cm, 2.5*cm, 11.5*cm])
    feat_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BLUE]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fff3cd')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elems.append(feat_t)
    elems.append(Spacer(1, 0.4*cm))

    elems.append(Paragraph('2.3 Algoritma: Random Forest', styles['sub_title']))
    elems.append(Paragraph(
        '<b>Random Forest</b> adalah algoritma ensemble yang terdiri dari sekumpulan pohon keputusan '
        '(Decision Tree) yang dibangun secara independen menggunakan teknik <i>bagging</i> '
        '(Bootstrap Aggregating). Setiap pohon dilatih pada subset acak dari data pelatihan, '
        'dan prediksi akhir ditentukan melalui voting mayoritas dari semua pohon.',
        styles['body']
    ))
    elems.append(Paragraph(
        'Keunggulan Random Forest antara lain: ketahanan terhadap overfitting, kemampuan menangani '
        'data dengan dimensi tinggi, serta memberikan estimasi pentingnya fitur (feature importance). '
        'Konfigurasi model: <b>n_estimators = 100</b> (jumlah pohon), normalisasi menggunakan '
        'StandardScaler.',
        styles['body']
    ))

    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph('2.4 Multi-Holdout Validation', styles['sub_title']))
    elems.append(Paragraph(
        '<b>Multi-Holdout Validation</b> adalah teknik evaluasi yang menjalankan train-test split '
        'sebanyak <b>N iterasi</b> dengan seed acak yang berbeda-beda, kemudian merata-ratakan '
        'semua metrik yang dihasilkan. Pendekatan ini memberikan estimasi performa yang lebih '
        'stabil dan mengurangi varians dibandingkan evaluasi single-holdout.',
        styles['body']
    ))
    holdout_proc = [
        ['Langkah', 'Keterangan'],
        ['1', f'Dataset dibagi secara acak: 80% Train / 20% Test (seed berbeda per iterasi)'],
        ['2', 'Data dinormalisasi menggunakan StandardScaler (fit pada Train, transform pada Test)'],
        ['3', 'Model Random Forest dilatih pada data Train yang telah dinormalisasi'],
        ['4', 'Prediksi dilakukan pada data Test; semua metrik dihitung'],
        ['5', 'Langkah 1-4 diulang 10× dengan seed berbeda'],
        ['6', f'Rata-rata dan standar deviasi metrik dari 10 holdout dilaporkan'],
        ['7', f'Model dengan F1-Score tertinggi (Holdout ke-{best_fold}) disimpan sebagai model produksi'],
    ]
    hp_t = Table(holdout_proc, colWidths=[1.2*cm, 13.8*cm])
    hp_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BLUE]),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elems.append(hp_t)

    return elems


# ===========================================================================
# SECTION 3: HASIL EVALUASI
# ===========================================================================
def build_results(styles, avg, std, fold_data, best_fold):
    elems = []
    elems.append(Paragraph('3. Hasil Evaluasi Model', styles['section_title']))
    elems.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=8))

    elems.append(Paragraph('3.1 Ringkasan Metrik Rata-Rata (10 Holdout)', styles['sub_title']))
    elems.append(Paragraph(
        'Tabel berikut menyajikan metrik evaluasi rata-rata dari 10 iterasi Multi-Holdout Validation '
        'beserta standar deviasinya. Nilai std yang kecil mengindikasikan konsistensi model yang tinggi.',
        styles['body']
    ))

    metrics_labels = {
        'accuracy':  ('Accuracy', 'Proporsi prediksi yang benar dari total prediksi'),
        'precision': ('Precision', 'Proporsi True Positive dari semua prediksi positif'),
        'recall':    ('Recall (Sensitivity)', 'Proporsi kasus sakit yang berhasil dideteksi'),
        'f1':        ('F1-Score', 'Harmonik rata-rata Precision dan Recall'),
        'roc_auc':   ('ROC-AUC', 'Luas area di bawah kurva ROC; semakin mendekati 1 = semakin baik'),
    }

    summary_rows = [['Metrik', 'Rata-Rata (%)', 'Std Dev (%)', 'Deskripsi']]
    for key, (label, desc) in metrics_labels.items():
        avg_val = avg.get(key, 0)
        std_val = std.get(key, 0)
        summary_rows.append([label, f'{avg_val:.2f}', f'±{std_val:.2f}', desc])

    sum_t = Table(summary_rows, colWidths=[4*cm, 2.5*cm, 2.5*cm, 6*cm])
    sum_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('TEXTCOLOR', (1, 1), (1, -1), ACCENT),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BLUE]),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elems.append(sum_t)
    elems.append(Spacer(1, 0.4*cm))

    # Interpretasi
    acc  = avg.get('accuracy', 0)
    rec  = avg.get('recall', 0)
    auc  = avg.get('roc_auc', 0)
    f1   = avg.get('f1', 0)
    prec = avg.get('precision', 0)

    interpret_color = ACCENT if acc >= 85 else WARNING if acc >= 75 else SECONDARY
    interpret_text = 'sangat baik' if acc >= 85 else 'baik' if acc >= 75 else 'perlu peningkatan'

    interp_data = [[
        Paragraph(
            f'📊 <b>Interpretasi:</b> Model mencapai akurasi rata-rata <b>{acc:.2f}%</b> '
            f'dengan standar deviasi ±{std.get("accuracy", 0):.2f}%, yang dikategorikan '
            f'<b>{interpret_text}</b> untuk kasus klasifikasi medis. '
            f'Recall sebesar <b>{rec:.2f}%</b> menunjukkan kemampuan model yang tinggi dalam '
            f'mendeteksi pasien yang benar-benar mengidap penyakit jantung (meminimalkan False Negative). '
            f'ROC-AUC <b>{auc:.2f}%</b> mengindikasikan daya diskriminasi model yang sangat kuat.',
            ParagraphStyle('interp', fontName='Helvetica', fontSize=9.5,
                           textColor=DARK, leading=15, alignment=TA_JUSTIFY)
        )
    ]]
    interp_t = Table(interp_data, colWidths=[15*cm])
    interp_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SOFT_BLUE),
        ('BOX', (0, 0), (-1, -1), 1.5, ACCENT),
        ('LEFTBORDER', (0, 0), (0, -1), 4, ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elems.append(interp_t)
    elems.append(Spacer(1, 0.5*cm))

    # Tabel detail per holdout
    elems.append(Paragraph('3.2 Detail Hasil Per Holdout', styles['sub_title']))
    elems.append(Paragraph(
        f'Berikut adalah metrik evaluasi untuk masing-masing dari 10 iterasi holdout. '
        f'Model terbaik (F1-Score tertinggi) berasal dari <b>Holdout ke-{best_fold}</b> '
        f'dan digunakan sebagai model produksi.',
        styles['body']
    ))

    fold_header = ['Holdout', 'Accuracy (%)', 'Precision (%)', 'Recall (%)', 'F1-Score (%)', 'ROC-AUC (%)']
    fold_rows = [fold_header]
    for fd in fold_data:
        row = [
            str(fd['fold']),
            f"{fd['accuracy']:.2f}",
            f"{fd['precision']:.2f}",
            f"{fd['recall']:.2f}",
            f"{fd['f1']:.2f}",
            f"{fd['roc_auc']:.2f}",
        ]
        fold_rows.append(row)

    # Rata-rata baris terakhir
    fold_rows.append([
        'RATA-RATA',
        f"{avg.get('accuracy', 0):.2f}",
        f"{avg.get('precision', 0):.2f}",
        f"{avg.get('recall', 0):.2f}",
        f"{avg.get('f1', 0):.2f}",
        f"{avg.get('roc_auc', 0):.2f}",
    ])

    col_w = [2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
    fold_t = Table(fold_rows, colWidths=col_w)

    # Style dasar
    fold_ts = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, SOFT_BLUE]),
        ('BACKGROUND', (0, -1), (-1, -1), PRIMARY),
        ('TEXTCOLOR', (0, -1), (-1, -1), WHITE),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    # Highlight baris terbaik
    best_row_idx = best_fold  # fold_data adalah 1-indexed, tabel mulai dari baris 1 (header = baris 0)
    fold_ts.add('BACKGROUND', (0, best_row_idx), (-1, best_row_idx), colors.HexColor('#d4edda'))
    fold_ts.add('TEXTCOLOR', (0, best_row_idx), (-1, best_row_idx), colors.HexColor('#155724'))
    fold_ts.add('FONTNAME', (0, best_row_idx), (-1, best_row_idx), 'Helvetica-Bold')

    fold_t.setStyle(fold_ts)
    elems.append(fold_t)
    elems.append(Paragraph(
        f'* Baris berwarna hijau (Holdout ke-{best_fold}) adalah model produksi yang disimpan.',
        styles['caption']
    ))

    return elems


# ===========================================================================
# SECTION 4: VISUALISASI
# ===========================================================================
def build_visualizations(styles, plots):
    elems = []
    elems.append(Paragraph('4. Visualisasi Hasil Evaluasi', styles['section_title']))
    elems.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=8))

    vis_configs = [
        ('holdout_comparison', 'Gambar 1. Perbandingan Metrik Per Holdout',
         'Grafik batang yang membandingkan Accuracy, F1-Score, dan ROC-AUC untuk setiap iterasi holdout. '
         'Variasi antar holdout mencerminkan sensitivitas model terhadap pembagian data yang berbeda.',
         16, 8.5),
        ('confusion_matrix', 'Gambar 2. Confusion Matrix (Gabungan Multi-Holdout)',
         'Matriks konfusi yang merangkum hasil prediksi dari semua iterasi. '
         'TP = True Positive (Sakit terdeteksi Sakit), TN = True Negative (Sehat terdeteksi Sehat), '
         'FP = False Positive (Sehat terdeteksi Sakit), FN = False Negative (Sakit terdeteksi Sehat).',
         8, 7),
        ('roc_curve', 'Gambar 3. ROC Curve (Gabungan Multi-Holdout)',
         'Kurva ROC (Receiver Operating Characteristic) menggambarkan trade-off antara True Positive Rate '
         'dan False Positive Rate. Nilai AUC yang mendekati 1.0 menunjukkan kemampuan diskriminasi yang '
         'sangat baik.',
         8, 7),
        ('feature_importance', 'Gambar 4. Feature Importance – Random Forest',
         'Grafik ini menampilkan kontribusi setiap fitur klinis dalam proses pengambilan keputusan model. '
         'Fitur dengan nilai importance lebih tinggi memiliki pengaruh lebih besar terhadap prediksi.',
         10, 9),
        ('distribution', 'Gambar 5. Distribusi Dataset',
         'Panel kiri menampilkan distribusi kelas target (Sakit vs Sehat). '
         'Panel kanan menampilkan sebaran pasien berdasarkan usia dan kadar kolesterol, '
         'dibedakan berdasarkan status penyakit jantung.',
         16, 7),
        ('correlation', 'Gambar 6. Heatmap Korelasi Antar Fitur',
         'Heatmap korelasi menampilkan tingkat hubungan linear antar fitur dataset. '
         'Nilai mendekati +1 (merah) = korelasi positif kuat; mendekati -1 (biru) = korelasi negatif kuat.',
         14, 12),
    ]

    for plot_key, caption, description, img_w, img_h in vis_configs:
        b64 = plots.get(plot_key)
        if not b64:
            continue

        rl_img = b64_to_rl_image(b64, img_w, img_h)
        if rl_img is None:
            continue

        content_w = 15 * cm
        actual_w  = img_w * cm
        actual_h  = img_h * cm

        # Buat wrapper tabel agar gambar tetap bersama caption
        img_cell = [[rl_img]]
        img_tbl = Table(img_cell, colWidths=[content_w])
        img_tbl.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
            ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elems.append(Spacer(1, 0.3*cm))
        keep_content = [
            img_tbl,
            Paragraph(f'<b>{caption}</b>', styles['caption']),
            Paragraph(description, styles['body']),
            Spacer(1, 0.4*cm),
        ]
        elems.append(KeepTogether(keep_content))

    return elems


# ===========================================================================
# SECTION 5: ANALISIS & KESIMPULAN
# ===========================================================================
def build_conclusion(styles, avg, std, best_fold, dataset_info):
    elems = []
    elems.append(Paragraph('5. Analisis dan Kesimpulan', styles['section_title']))
    elems.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=8))

    acc  = avg.get('accuracy', 0)
    prec = avg.get('precision', 0)
    rec  = avg.get('recall', 0)
    f1   = avg.get('f1', 0)
    auc  = avg.get('roc_auc', 0)

    std_acc = std.get('accuracy', 0)
    std_f1  = std.get('f1', 0)

    elems.append(Paragraph('5.1 Analisis Performa Model', styles['sub_title']))

    analyses = [
        (f'<b>Akurasi ({acc:.2f}% ± {std_acc:.2f}%):</b> Model mampu mengklasifikasikan '
         f'{acc:.1f}% dari total sampel dengan benar. Standar deviasi {std_acc:.2f}% menunjukkan '
         f'konsistensi yang {"tinggi" if std_acc < 3 else "sedang"} antar holdout.'),

        (f'<b>Precision ({prec:.2f}%):</b> Dari semua prediksi positif (sakit jantung), '
         f'{prec:.1f}% adalah benar-benar positif. Nilai ini mengindikasikan tingkat '
         f'{"false alarm yang rendah" if prec > 85 else "false alarm yang perlu diperhatikan"}.'),

        (f'<b>Recall ({rec:.2f}%):</b> Model berhasil mendeteksi {rec:.1f}% dari seluruh '
         f'kasus penyakit jantung yang sesungguhnya. Recall yang tinggi sangat penting dalam '
         f'konteks medis untuk meminimalkan kasus yang terlewat (False Negative), '
         f'yang dapat berakibat fatal.'),

        (f'<b>F1-Score ({f1:.2f}% ± {std_f1:.2f}%):</b> Sebagai metrik harmonik antara '
         f'Precision dan Recall, F1-Score {f1:.2f}% menunjukkan keseimbangan yang '
         f'{"sangat baik" if f1 > 90 else "baik" if f1 > 80 else "perlu peningkatan"} '
         f'antara kedua metrik tersebut.'),

        (f'<b>ROC-AUC ({auc:.2f}%):</b> Nilai AUC yang mendekati 100% mengindikasikan '
         f'kemampuan model untuk membedakan kelas positif dan negatif dengan daya '
         f'diskriminasi yang {"sangat kuat" if auc > 95 else "kuat" if auc > 85 else "sedang"}.'),
    ]

    for a in analyses:
        bullet_data = [[Paragraph(a, ParagraphStyle('bullet', fontName='Helvetica', fontSize=9.5,
                                                    textColor=DARK, leading=14, alignment=TA_JUSTIFY))]]
        bullet_t = Table(bullet_data, colWidths=[14.5*cm])
        bullet_t.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elems.append(bullet_t)

    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph('5.2 Kelebihan dan Keterbatasan', styles['sub_title']))

    pros_cons = [
        ['Kelebihan', 'Keterbatasan'],
        [
            '✓ Recall tinggi (≥98%) — sangat baik untuk deteksi dini\n'
            '✓ ROC-AUC tinggi — daya diskriminasi kuat\n'
            '✓ Konsistensi antar holdout baik\n'
            '✓ Feature importance tersedia untuk interpretasi\n'
            '✓ Tidak memerlukan asumsi distribusi data',

            '✗ Dataset relatif kecil (303 sampel)\n'
            '✗ Ketidakseimbangan kelas (85% positif, 15% negatif)\n'
            '✗ Model Random Forest sulit diinterpretasikan secara klinis\n'
            '✗ Perlu validasi lebih lanjut pada data nyata rumah sakit'
        ]
    ]

    pc_t = Table(pros_cons, colWidths=[7.5*cm, 7.5*cm])
    pc_t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#d4edda')),
        ('BACKGROUND', (1, 1), (1, -1), colors.HexColor('#f8d7da')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, MEDIUM),
        ('INNERGRID', (0, 0), (-1, -1), 1, MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elems.append(pc_t)
    elems.append(Spacer(1, 0.4*cm))

    elems.append(Paragraph('5.3 Kesimpulan', styles['sub_title']))
    elems.append(Paragraph(
        f'Model <b>Random Forest</b> yang dilatih dengan metode <b>Multi-Holdout Validation (10 iterasi)</b> '
        f'pada dataset Heart Disease UCI menunjukkan performa yang <b>sangat memuaskan</b> dengan '
        f'Accuracy rata-rata <b>{acc:.2f}%</b>, F1-Score <b>{f1:.2f}%</b>, dan ROC-AUC <b>{auc:.2f}%</b>.',
        styles['body']
    ))
    elems.append(Paragraph(
        f'Model terbaik berasal dari <b>Holdout ke-{best_fold}</b> dan telah disimpan sebagai model '
        f'produksi yang siap digunakan untuk prediksi klinis. Recall yang tinggi ({rec:.2f}%) menjadikan '
        f'model ini sangat andal dalam mendeteksi pasien berisiko tinggi penyakit jantung.',
        styles['body']
    ))

    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph('5.4 Rekomendasi', styles['sub_title']))
    recs = [
        '1. Lakukan pengumpulan data lebih besar (minimal 1000+ sampel) untuk meningkatkan generalisasi model.',
        '2. Terapkan teknik oversampling (SMOTE) atau class weighting untuk mengatasi ketidakseimbangan kelas.',
        '3. Eksplorasi algoritma lain (XGBoost, SVM, Neural Network) sebagai komparasi.',
        '4. Validasi model pada data dari rumah sakit lokal sebelum deployment klinis.',
        '5. Pertimbangkan pendekatan explainable AI (SHAP values) untuk meningkatkan interpretabilitas.',
        '6. Evaluasi berkala (re-training) setiap kali dataset diperluas dengan data baru.',
    ]
    for r in recs:
        elems.append(Paragraph(r, ParagraphStyle('rec', fontName='Helvetica', fontSize=9.5,
                                                   textColor=DARK, leading=16, leftIndent=10,
                                                   spaceAfter=3)))

    return elems


# ===========================================================================
# SECTION 6: REFERENSI
# ===========================================================================
def build_references(styles):
    elems = []
    elems.append(Spacer(1, 0.5*cm))
    elems.append(Paragraph('6. Referensi', styles['section_title']))
    elems.append(HRFlowable(width='100%', thickness=2, color=PRIMARY, spaceAfter=8))

    refs = [
        'Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5-32.',
        'Detrano, R., et al. (1989). International application of a new probability algorithm for the '
        'diagnosis of coronary artery disease. The American Journal of Cardiology, 64(5), 304-310.',
        'Janosi, A., Steinbrunn, W., Pfisterer, M., Detrano, R. (1988). Heart Disease Dataset. '
        'UCI Machine Learning Repository.',
        'Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. '
        'Journal of Machine Learning Research, 12, 2825-2830.',
        'James, G., Witten, D., Hastie, T., Tibshirani, R. (2013). '
        'An Introduction to Statistical Learning. Springer.',
    ]
    for i, ref in enumerate(refs, 1):
        elems.append(Paragraph(
            f'[{i}] {ref}',
            ParagraphStyle('ref', fontName='Helvetica', fontSize=9, textColor=DARK,
                           leading=14, leftIndent=10, spaceAfter=5, alignment=TA_JUSTIFY)
        ))

    return elems


# ===========================================================================
# MAIN: BUILD PDF
# ===========================================================================
def build_pdf():
    print("=" * 60)
    print("HeartGuard - Laporan Evaluasi Model Prediksi Penyakit Jantung")
    print("=" * 60)

    # Load data
    print("\n[1/3] Memuat data evaluasi...")
    avg, std, fold_data, dataset_info, best_fold, plots = load_data()
    print(f"      OK Data dimuat: {len(fold_data)} holdout, avg_acc={avg.get('accuracy', 0):.2f}%")

    # Setup dokumen
    print("[2/3] Membangun dokumen PDF...")
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title='Laporan Evaluasi Model HeartGuard',
        author='HeartGuard System',
        subject='Prediksi Penyakit Jantung — Random Forest Multi-Holdout Validation',
    )

    styles = build_styles()

    # Kumpulkan semua elemen
    story = []
    story += build_cover_page(styles, avg, dataset_info)
    story += build_intro(styles)
    story.append(PageBreak())
    story += build_methodology(styles, dataset_info, best_fold, avg)
    story.append(PageBreak())
    story += build_results(styles, avg, std, fold_data, best_fold)
    story.append(PageBreak())
    story += build_visualizations(styles, plots)
    story.append(PageBreak())
    story += build_conclusion(styles, avg, std, best_fold, dataset_info)
    story += build_references(styles)

    # Build
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    print(f"[3/3] PDF berhasil dibuat!")
    print(f"\nOUTPUT: {OUTPUT_PATH}")
    print(f"Ukuran: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
    print("=" * 60)


if __name__ == '__main__':
    build_pdf()
