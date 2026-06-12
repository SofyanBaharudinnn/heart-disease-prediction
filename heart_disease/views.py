import io
import base64
import json
import os
import shutil
import socket
# pyrefly: ignore [missing-import]
from django.urls import reverse
# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.core.mail import send_mail
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
from django.contrib import messages
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import user_passes_test, login_required
# pyrefly: ignore [missing-import]
from django.views.decorators.http import require_POST
# pyrefly: ignore [missing-import]
from django.contrib.auth.forms import UserCreationForm
# pyrefly: ignore [missing-import]
from django.contrib.auth import login, logout
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .ml_model import (
    FEATURE_INFO, load_dataset, train_and_evaluate, predict_single
)
from .models import PredictionHistory, ModelMetrics, ContactMessage

def is_admin(user):
    return user.is_authenticated and user.is_staff


# ─── QR Code Generator ───────────────────────────────────────────────────────
def generate_qr_base64(url):
    """Generate QR code dari URL dan kembalikan sebagai base64 PNG string."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=3,
        )
        qr.add_data(url)
        qr.make(fit=True)
        # Theme: lime (#AAFF00) background, near-black fill — sesuai brand HeartGuard
        img = qr.make_image(fill_color="#0A0A0A", back_color="#AAFF00")
        buffer = io.BytesIO()
        # pyrefly: ignore [unexpected-keyword]
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception:
        return None


# ─── LAN IP Detector ──────────────────────────────────────────────────────────
def get_local_network_ip():
    """Deteksi IP LAN mesin agar QR code bisa diakses dari HP di jaringan yang sama."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Tidak perlu koneksi nyata — hanya untuk mendapatkan interface yang digunakan
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


# ─── Home ────────────────────────────────────────────────────────────────────
def index(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        return redirect('predict')
        
    df, err = load_dataset()
    dataset_ready = df is not None

    last_metrics = ModelMetrics.objects.first()
    total_predictions = PredictionHistory.objects.count()
    positive_count    = PredictionHistory.objects.filter(prediction=1).count()
    negative_count    = PredictionHistory.objects.filter(prediction=0).count()

    context = {
        'dataset_ready':    dataset_ready,
        'last_metrics':     last_metrics,
        'total_predictions': total_predictions,
        'positive_count':   positive_count,
        'negative_count':   negative_count,
        'dataset_size':     len(df) if df is not None else 0,
    }
    return render(request, 'heart_disease/index.html', context)


# ─── Dashboard / Training ─────────────────────────────────────────────────────
@user_passes_test(is_admin, login_url='login')
def dashboard(request):
    df, err = load_dataset()
    dataset_size = len(df) if df is not None else 0

    last_metrics  = ModelMetrics.objects.first()
    history       = PredictionHistory.objects.all().order_by('-created_at')[:10]
    
    total_predictions = PredictionHistory.objects.count()
    positive_count    = PredictionHistory.objects.filter(prediction=1).count()
    negative_count    = PredictionHistory.objects.filter(prediction=0).count()
    
    risk_low = PredictionHistory.objects.filter(risk_level='Rendah').count()
    risk_med = PredictionHistory.objects.filter(risk_level='Sedang').count()
    risk_high = PredictionHistory.objects.filter(risk_level='Tinggi').count()

    context = {
        'dataset_size': dataset_size,
        'total_predictions': total_predictions,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'risk_low': risk_low,
        'risk_med': risk_med,
        'risk_high': risk_high,
        'last_metrics': last_metrics,
        'history':      history,
    }
    return render(request, 'heart_disease/dashboard.html', context)


@user_passes_test(is_admin, login_url='login')
def train_page_view(request):
    last_metrics = ModelMetrics.objects.first()
    all_metrics = ModelMetrics.objects.all()
    context = {
        'last_metrics': last_metrics,
        'all_metrics': all_metrics
    }
    return render(request, 'heart_disease/training_page.html', context)


@user_passes_test(is_admin, login_url='login')
def train_model(request):
    if request.method == 'POST':
        try:
            n_splits     = int(request.POST.get('n_splits', 5))
            n_estimators = int(request.POST.get('n_estimators', 100))
        except ValueError:
            messages.error(
                request,
                'Parameter pelatihan harus berupa angka bulat.'
                if request.session.get('lang', 'id') == 'id'
                else 'Training parameters must be integers.'
            )
            return redirect('train_page')

        if n_splits < 2 or n_splits > 20:
            messages.error(
                request,
                'Jumlah split holdout harus di antara 2 dan 20.'
                if request.session.get('lang', 'id') == 'id'
                else 'Number of holdout splits must be between 2 and 20.'
            )
            return redirect('train_page')

        if n_estimators < 10 or n_estimators > 1000:
            messages.error(
                request,
                'Jumlah estimator Random Forest harus di antara 10 dan 1000.'
                if request.session.get('lang', 'id') == 'id'
                else 'Number of Random Forest estimators must be between 10 and 1000.'
            )
            return redirect('train_page')

        data, err = train_and_evaluate(n_splits=n_splits, n_estimators=n_estimators)

        if err:
            messages.error(request, err)
            return redirect('train_page')

        # Simpan metrik ke DB
        metrics_obj = ModelMetrics.objects.create(
            accuracy     = data['avg']['accuracy'],
            precision    = data['avg']['precision'],
            recall       = data['avg']['recall'],
            f1_score     = data['avg']['f1'],
            roc_auc      = data['avg']['roc_auc'],
            n_splits     = n_splits,
            n_estimators = n_estimators,
        )

        # Kirim data ke template hasil
        fold_data = []
        for r in data['results']:
            fold_data.append({
                'fold':      r['fold'],
                'accuracy':  round(r['accuracy']  * 100, 2),
                'precision': round(r['precision'] * 100, 2),
                'recall':    round(r['recall']    * 100, 2),
                'f1':        round(r['f1']        * 100, 2),
                'roc_auc':   round(r['roc_auc']   * 100, 2),
            })
        context = {
            'data': {
                'plots': data['plots'],
                'dataset_info': data['dataset_info'],
                'best_fold': data['best_fold'],
                'results': [{'fold': r['fold']} for r in data['results']] # Only needed for length
            },
            'fold_data': fold_data,
            'avg': {k: round(v * 100, 2) for k, v in data['avg'].items()},
            'std': {k: round(v * 100, 2) for k, v in data['std'].items()},
        }

        # Simpan context ke file JSON agar bisa dilihat ulang
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', 'models')
        os.makedirs(model_dir, exist_ok=True)
        with open(os.path.join(model_dir, f'results_{metrics_obj.id}.json'), 'w') as f:
            json.dump(context, f)

        # Copy to last_results.json for PDF report generator
        shutil.copy2(os.path.join(model_dir, f'results_{metrics_obj.id}.json'), os.path.join(model_dir, 'last_results.json'))

        return render(request, 'heart_disease/training_result.html', context)

    return redirect('train_page')


@user_passes_test(is_admin, login_url='login')
def training_result_view(request, id):
    """Menampilkan hasil evaluasi dari file JSON berdasarkan ID."""
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', 'models')
    json_path = os.path.join(model_dir, f'results_{id}.json')
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            context = json.load(f)
        return render(request, 'heart_disease/training_result.html', context)
    
    messages.error(request, 'Hasil evaluasi tidak ditemukan. Silakan latih model lagi.')
    return redirect('train_page')


@user_passes_test(is_admin, login_url='login')
@require_POST
def delete_model(request, id):
    # pyrefly: ignore [missing-import]
    from django.shortcuts import get_object_or_404
    metrics_obj = get_object_or_404(ModelMetrics, id=id)
    is_latest = (ModelMetrics.objects.first() == metrics_obj)
    
    # Hapus dari DB
    metrics_obj.delete()
    
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', 'models')
    
    # Hapus file JSON spesifik
    json_path = os.path.join(model_dir, f'results_{id}.json')
    if os.path.exists(json_path):
        os.remove(json_path)
        
    # Jika model yang dihapus adalah model yang paling baru, hapus juga file fisiknya
    if is_latest:
        pkl_model = os.path.join(model_dir, 'random_forest_model.pkl')
        pkl_scaler = os.path.join(model_dir, 'scaler.pkl')
        if os.path.exists(pkl_model):
            os.remove(pkl_model)
        if os.path.exists(pkl_scaler):
            os.remove(pkl_scaler)
            
    messages.success(request, 'Riwayat pelatihan berhasil dihapus.')
    return redirect('train_page')


# ─── Prediction ──────────────────────────────────────────────────────────────
def predict_view(request):
    if request.method == 'POST':
        try:
            # ─── Security Input Validation ───
            input_data = {}
            for field, info in FEATURE_INFO.items():
                val_str = request.POST.get(field, '').strip()
                if not val_str:
                    messages.error(
                        request,
                        f"Field '{info['label']}' tidak boleh kosong." 
                        if request.session.get('lang', 'id') == 'id' 
                        else f"Field '{info['label']}' cannot be empty."
                    )
                    return redirect('predict')
                
                try:
                    val = float(val_str) if field == 'oldpeak' else int(val_str)
                except ValueError:
                    messages.error(
                        request,
                        f"Format nilai untuk '{info['label']}' tidak valid." 
                        if request.session.get('lang', 'id') == 'id' 
                        else f"Invalid value format for '{info['label']}'."
                    )
                    return redirect('predict')
                
                if val < info['min'] or val > info['max']:
                    messages.error(
                        request,
                        f"Nilai untuk '{info['label']}' harus berada di antara {info['min']} dan {info['max']}." 
                        if request.session.get('lang', 'id') == 'id' 
                        else f"Value for '{info['label']}' must be between {info['min']} and {info['max']}."
                    )
                    return redirect('predict')
                
                input_data[field] = val

            result, err = predict_single(input_data)

            if err:
                messages.error(request, err)
                return redirect('predict')

            # Simpan riwayat
            history_obj = PredictionHistory.objects.create(
                user     = request.user if request.user.is_authenticated else None,
                age      = int(input_data['age']),
                sex      = int(input_data['sex']),
                cp       = int(input_data['cp']),
                trestbps = int(input_data['trestbps']),
                chol     = int(input_data['chol']),
                fbs      = int(input_data['fbs']),
                restecg  = int(input_data['restecg']),
                thalach  = int(input_data['thalach']),
                exang    = int(input_data['exang']),
                oldpeak  = float(input_data['oldpeak']),
                slope    = int(input_data['slope']),
                ca       = int(input_data['ca']),
                thal     = int(input_data['thal']),
                prediction      = result['prediction'],
                probability_pos = result['probability']['positive'],
                probability_neg = result['probability']['negative'],
                risk_level      = result['risk_level'],
            )

            # Generate nomor seri unik: HG-YYYYMMDD-XXXX
            serial = f"HG-{history_obj.created_at.strftime('%Y%m%d')}-{history_obj.id:04d}"
            history_obj.serial_number = serial
            history_obj.save(update_fields=['serial_number'])

            # Generate QR code yang menuju halaman detail prediksi
            # Gunakan IP LAN agar QR bisa dipindai dari HP di jaringan yang sama
            detail_path = reverse('prediction_detail', args=[history_obj.id])
            detail_url_browser = request.build_absolute_uri(detail_path)

            local_ip = get_local_network_ip()
            port = request.get_port()
            if local_ip and request.get_host() in ('127.0.0.1:' + port, 'localhost:' + port,
                                                    '127.0.0.1', 'localhost'):
                # Ganti localhost/127.0.0.1 dengan IP LAN yang bisa diakses HP
                detail_url_qr = detail_url_browser.replace(
                    request.get_host(), f"{local_ip}:{port}"
                )
            else:
                detail_url_qr = detail_url_browser

            qr_b64 = generate_qr_base64(detail_url_qr)

            current_lang = request.session.get('lang', 'id')
            recs = get_lifestyle_recommendations(input_data, lang=current_lang)

            context = {
                'result':             result,
                'input_data':         input_data,
                'feature_info':       FEATURE_INFO,
                'prediction_record':  history_obj,
                'qr_code_b64':        qr_b64,
                'detail_url':         detail_url_qr,   # URL versi LAN untuk QR
                'detail_url_browser': detail_url_browser,  # URL browser untuk tombol "Buka Halaman"
                'local_ip':           local_ip,
                'lifestyle_recommendations': recs,
            }
            return render(request, 'heart_disease/result.html', context)

        except Exception as e:
            messages.error(request, f'Error saat prediksi: {str(e)}')
            return redirect('predict')

    context = {'feature_info': FEATURE_INFO}
    return render(request, 'heart_disease/predict.html', context)


# ─── History ─────────────────────────────────────────────────────────────────
@login_required(login_url='login')
def history_view(request):
    if request.user.is_staff:
        history = PredictionHistory.objects.all().order_by('-created_at')
    else:
        history = PredictionHistory.objects.filter(user=request.user).order_by('-created_at')
    context = {'history': history}
    return render(request, 'heart_disease/history.html', context)


# ─── Prediction Detail (QR scan destination) ──────────────────────────────────
@login_required(login_url='login')
def prediction_detail_view(request, id):
    """Halaman detail prediksi — tujuan scan QR code."""
    record = get_object_or_404(PredictionHistory, id=id)
    # Hanya pemilik atau admin yang boleh melihat
    if not request.user.is_staff and record.user != request.user:
        messages.error(request, 'Anda tidak memiliki akses ke rekam medis ini.')
        return redirect('history')

    current_lang = request.session.get('lang', 'id')
    recs = get_lifestyle_recommendations(record, lang=current_lang)

    context = {
        'record':       record,
        'feature_info': FEATURE_INFO,
        'lifestyle_recommendations': recs,
    }
    return render(request, 'heart_disease/prediction_detail.html', context)


@login_required(login_url='login')
@require_POST
def delete_history(request, id):
    history_obj = get_object_or_404(PredictionHistory, id=id)
    if not request.user.is_staff and history_obj.user != request.user:
        messages.error(request, 'Anda tidak memiliki izin untuk menghapus riwayat ini.')
        return redirect('history')
    history_obj.delete()
    messages.success(request, 'Riwayat prediksi berhasil dihapus.')
    return redirect('history')

# ─── Auth ───────────────────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('predict')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Pendaftaran berhasil! Selamat datang.')
            return redirect('predict')
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = UserCreationForm()
        
    return render(request, 'heart_disease/register.html', {'form': form})


def social_login_view(request, provider):
    messages.error(request, 'Metode login sosial dinonaktifkan / Social login is disabled.')
    return redirect('login')


def social_login_callback(request, provider):
    return redirect('login')


# ─── User Management ─────────────────────────────────────────────────────────
@user_passes_test(is_admin, login_url='login')
def manage_users_view(request):
    users = User.objects.all().order_by('-date_joined')
    # Count predictions for each user
    users_with_counts = []
    for u in users:
        count = PredictionHistory.objects.filter(user=u).count()
        users_with_counts.append({
            'user': u,
            'prediction_count': count
        })
    
    context = {'users_with_counts': users_with_counts}
    return render(request, 'heart_disease/manage_users.html', context)


@user_passes_test(is_admin, login_url='login')
@require_POST
def delete_user(request, id):
    user_to_delete = get_object_or_404(User, id=id)
    if user_to_delete == request.user:
        messages.error(request, 'Anda tidak bisa menghapus akun Anda sendiri.')
    else:
        user_to_delete.delete()
        messages.success(request, f'Akun {user_to_delete.username} berhasil dihapus.')
    return redirect('manage_users')


@user_passes_test(is_admin, login_url='login')
@require_POST
def toggle_admin(request, id):
    target_user = get_object_or_404(User, id=id)
    if target_user == request.user:
        messages.error(request, 'Anda tidak bisa mengubah hak akses Anda sendiri.')
    else:
        target_user.is_staff = not target_user.is_staff
        # Superuser flag can also be set if desired, but is_staff is enough for admin dashboard.
        target_user.save()
        status = "Admin" if target_user.is_staff else "User"
        messages.success(request, f'Hak akses {target_user.username} diubah menjadi {status}.')
    return redirect('manage_users')

# ─── Dataset Management ───────────────────────────────────────────────────────
@user_passes_test(is_admin, login_url='login')
def dataset_management_view(request):
    """Halaman manajemen dataset: lihat info dan upload CSV baru."""
    df, err = load_dataset()
    dataset_info = None
    if df is not None:
        dataset_info = {
            'total': len(df),
            'columns': list(df.columns),
            'features': len(df.columns) - 1,
            'positive': int(df['target'].sum()) if 'target' in df.columns else 0,
            'negative': int(len(df) - df['target'].sum()) if 'target' in df.columns else 0,
            'file_size': os.path.getsize(
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset', 'heart.csv')
            ),
        }
    context = {
        'dataset_info': dataset_info,
        'dataset_error': err,
    }
    return render(request, 'heart_disease/dataset_management.html', context)


@user_passes_test(is_admin, login_url='login')
@require_POST
def upload_dataset_view(request):
    """Handle upload file CSV dataset baru."""
    REQUIRED_COLUMNS = {
        'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs',
        'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal', 'target'
    }

    uploaded_file = request.FILES.get('dataset_file')
    if not uploaded_file:
        messages.error(request, 'Tidak ada file yang dipilih. Silakan pilih file CSV.')
        return redirect('dataset_management')

    if not uploaded_file.name.endswith('.csv'):
        messages.error(request, 'Format file tidak valid. Hanya file .csv yang diperbolehkan.')
        return redirect('dataset_management')

    if uploaded_file.size > 10 * 1024 * 1024:  # 10 MB limit
        messages.error(request, 'Ukuran file terlalu besar. Maksimal 10 MB.')
        return redirect('dataset_management')

    try:
        import pandas as pd
        import io as _io
        content = uploaded_file.read()
        df_new = pd.read_csv(_io.BytesIO(content))

        # Validasi kolom
        missing_cols = REQUIRED_COLUMNS - set(df_new.columns)
        if missing_cols:
            messages.error(
                request,
                f'Kolom berikut tidak ditemukan: {", ".join(sorted(missing_cols))}. '
                f'Dataset harus memiliki 14 kolom standar heart disease.'
            )
            return redirect('dataset_management')

        if len(df_new) < 50:
            messages.error(request, 'Dataset terlalu kecil. Minimal 50 baris data diperlukan.')
            return redirect('dataset_management')

        # Simpan dataset lama sebagai backup
        dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset')
        os.makedirs(dataset_dir, exist_ok=True)
        dataset_path = os.path.join(dataset_dir, 'heart.csv')

        if os.path.exists(dataset_path):
            backup_path = os.path.join(dataset_dir, 'heart_backup.csv')
            shutil.copy2(dataset_path, backup_path)

        # Simpan dataset baru
        with open(dataset_path, 'wb') as f:
            f.write(content)

        total_rows = len(df_new)
        messages.success(
            request,
            f'Dataset berhasil diupload! Total {total_rows} baris data dimuat. '
            f'Dataset lama disimpan sebagai backup.'
        )

    except Exception as e:
        messages.error(request, f'Gagal memproses file CSV: {str(e)}')

    return redirect('dataset_management')


@user_passes_test(is_admin, login_url='login')
@require_POST
def delete_dataset_view(request):
    """Hapus dataset yang ada (hanya jika ada backup)."""
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset')
    dataset_path = os.path.join(dataset_dir, 'heart.csv')
    backup_path = os.path.join(dataset_dir, 'heart_backup.csv')

    if not os.path.exists(dataset_path):
        messages.error(request, 'Dataset tidak ditemukan.')
        return redirect('dataset_management')

    if os.path.exists(backup_path):
        # Restore dari backup
        shutil.copy2(backup_path, dataset_path)
        os.remove(backup_path)
        messages.success(request, 'Dataset aktif diganti dengan backup sebelumnya.')
    else:
        os.remove(dataset_path)
        messages.warning(request, 'Dataset dihapus. Tidak ada backup tersedia. Upload dataset baru untuk melanjutkan.')

    return redirect('dataset_management')


# ─── About ───────────────────────────────────────────────────────────────────
def about(request):
    return render(request, 'heart_disease/about.html')


# ─── API: dataset info (AJAX) ─────────────────────────────────────────────────
def dataset_info_api(request):
    df, err = load_dataset()
    if err:
        return JsonResponse({'error': err}, status=400)
    info = {
        'total':    len(df),
        'features': len(df.columns) - 1,
        'positive': int(df['target'].sum()),
        'negative': int(len(df) - df['target'].sum()),
        'columns':  list(df.columns),
    }
    return JsonResponse(info)


def toggle_language(request):
    """View to toggle system language between English and Indonesian."""
    current_lang = request.session.get('lang', 'id')
    new_lang = 'en' if current_lang == 'id' else 'id'
    request.session['lang'] = new_lang
    return redirect(request.META.get('HTTP_REFERER', '/'))


def logout_view(request):
    """Custom logout view to preserve language settings across session flushes."""
    lang = request.session.get('lang', 'id')
    logout(request)
    request.session['lang'] = lang
    return redirect('/')


def get_lifestyle_recommendations(data, lang='id'):
    """
    Generate personalized lifestyle recommendations based on clinical inputs.
    `data` can be a dictionary (for predict view) or a model object (for history detail).
    """
    def get_val(key, default=0):
        if hasattr(data, key):
            val = getattr(data, key)
        else:
            val = data.get(key, default)
        
        try:
            return float(val) if key == 'oldpeak' else int(val)
        except (ValueError, TypeError):
            return default

    chol = get_val('chol')
    trestbps = get_val('trestbps')
    fbs = get_val('fbs')
    exang = get_val('exang')
    age = get_val('age')

    recs = []

    # 1. Cholesterol Recommendation
    if chol > 200:
        if lang == 'en':
            recs.append({
                'title': 'Dietary Adjustments (High Cholesterol)',
                'icon': 'bi-egg-fried',
                'color': '#FFA800',
                'desc': f'Your cholesterol level is {chol} mg/dl (Target: < 200 mg/dl). It is recommended to reduce intake of saturated fats, trans fats, and high-cholesterol foods (red meat, fried food, butter). Increase soluble fiber consumption (oats, legumes, fruits) and healthy fats like olive oil or omega-3 fatty acids.'
            })
        else:
            recs.append({
                'title': 'Penyesuaian Pola Makan (Kolesterol Tinggi)',
                'icon': 'bi-egg-fried',
                'color': '#FFA800',
                'desc': f'Kadar kolesterol Anda adalah {chol} mg/dl (Target: < 200 mg/dl). Direkomendasikan untuk membatasi konsumsi lemak jenuh, lemak trans, dan makanan tinggi kolesterol (daging merah, gorengan, mentega). Tingkatkan konsumsi serat larut (oatmeal, kacang-kacangan, buah-buahan) serta lemak sehat seperti minyak zaitun atau asam lemak omega-3.'
            })

    # 2. Blood Pressure Recommendation
    if trestbps > 120:
        if lang == 'en':
            recs.append({
                'title': 'Exercise & Sodium Control (High Blood Pressure)',
                'icon': 'bi-activity',
                'color': '#FFA800',
                'desc': f'Your resting blood pressure is {trestbps} mmHg (Target: < 120 mmHg). Engage in moderate-intensity aerobic exercise (brisk walking, cycling, swimming) for 30 minutes a day, at least 5 days a week. Additionally, limit dietary sodium (salt) to under 2,000 mg per day and practice stress-reduction techniques.'
            })
        else:
            recs.append({
                'title': 'Olahraga & Kontrol Natrium (Tekanan Darah Tinggi)',
                'icon': 'bi-activity',
                'color': '#FFA800',
                'desc': f'Tekanan darah istirahat Anda adalah {trestbps} mmHg (Target: < 120 mmHg). Lakukan olahraga aerobik dengan intensitas sedang (jalan cepat, bersepeda, berenang) selama 30 menit sehari, minimal 5 hari seminggu. Batasi juga konsumsi natrium (garam dapur) di bawah 2.000 mg per hari serta terapkan teknik manajemen stres.'
            })

    # 3. Blood Sugar Recommendation
    if fbs == 1:
        if lang == 'en':
            recs.append({
                'title': 'Carbohydrate Control (High Fasting Blood Sugar)',
                'icon': 'bi-droplet-half',
                'color': '#F64E60',
                'desc': 'Your fasting blood sugar is indicated above 120 mg/dl. Limit refined sugars, sweetened drinks, and processed carbohydrates (white bread, white rice). Focus on low-glycemic index food options like whole grains, brown rice, vegetables, and lean proteins to stabilize glucose levels.'
            })
        else:
            recs.append({
                'title': 'Kontrol Karbohidrat (Gula Darah Puasa Tinggi)',
                'icon': 'bi-droplet-half',
                'color': '#F64E60',
                'desc': 'Gula darah puasa Anda terindikasi di atas 120 mg/dl. Batasi konsumsi gula olahan, minuman manis, dan karbohidrat sederhana (roti putih, nasi putih). Prioritaskan makanan dengan indeks glikemik rendah seperti gandum utuh, beras merah, sayuran, dan protein tanpa lemak guna menjaga kestabilan glukosa.'
            })

    # 4. Exercise-induced Angina Recommendation
    if exang == 1:
        if lang == 'en':
            recs.append({
                'title': 'Cardiovascular Exercise Caution (Exercise Angina)',
                'icon': 'bi-exclamation-octagon-fill',
                'color': '#F64E60',
                'desc': 'You have exercise-induced angina (chest pain triggered by physical exertion). Avoid sudden, high-intensity workouts. Always warm up for 10-15 minutes before activity and cool down afterward. Stop exercise immediately and rest if you feel chest pain, tightness, or shortness of breath.'
            })
        else:
            recs.append({
                'title': 'Kewaspadaan Aktivitas Fisik (Angina Akibat Olahraga)',
                'icon': 'bi-exclamation-octagon-fill',
                'color': '#F64E60',
                'desc': 'Anda mengalami angina akibat olahraga (nyeri dada yang dipicu aktivitas fisik). Hindari olahraga berat yang mendadak. Selalu lakukan pemanasan 10-15 menit sebelum beraktivitas dan pendinginan setelahnya. Segera hentikan aktivitas jika merasakan nyeri, sesak, atau ketidaknyamanan di dada.'
            })

    # 5. Age Recommendation
    if age > 60:
        if lang == 'en':
            recs.append({
                'title': 'Activity & Bone Health (Seniors aged 60+)',
                'icon': 'bi-person-walking',
                'color': '#2a9d8f',
                'desc': 'For patients over 60 years old, physical activity should focus on maintaining muscle strength, joint flexibility, and balance to prevent falls (e.g., low-impact yoga, stretching, light walking). Ensure adequate calcium and Vitamin D intake, and consult a doctor before starting any new fitness routine.'
            })
        else:
            recs.append({
                'title': 'Kesehatan Aktivitas & Tulang (Lansia usia 60+)',
                'icon': 'bi-person-walking',
                'color': '#2a9d8f',
                'desc': 'Untuk pasien di atas 60 tahun, aktivitas fisik sebaiknya difokuskan pada kekuatan otot, fleksibilitas sendi, dan keseimbangan untuk mencegah risiko jatuh (seperti yoga low-impact, peregangan, jalan santai). Pastikan asupan kalsium dan Vitamin D tercukupi, serta konsultasikan program latihan ke dokter.'
            })

    # If no specific risk triggers, provide a general health maintenance advice
    if not recs:
        if lang == 'en':
            recs.append({
                'title': 'Lifestyle Maintenance (Standard Metrics)',
                'icon': 'bi-heart-fill',
                'color': '#AAFF00',
                'desc': 'All clinical metrics analyzed (cholesterol, blood pressure, fasting blood sugar, exercise tolerance) are within standard ranges. Maintain this state by continuing a balanced nutrition plan, sleeping 7-8 hours per night, exercising regularly, and scheduling regular annual medical check-ups.'
            })
        else:
            recs.append({
                'title': 'Pemeliharaan Pola Hidup Sehat (Indikator Normal)',
                'icon': 'bi-heart-fill',
                'color': '#AAFF00',
                'desc': 'Seluruh indikator klinis Anda (kolesterol, tekanan darah, gula darah puasa, toleransi olahraga) berada dalam rentang normal. Pertahankan kondisi ini dengan melanjutkan diet gizi seimbang, tidur 7-8 jam per malam, rutin berolahraga, serta melakukan pemeriksaan kesehatan tahunan.'
            })

    return recs


@login_required(login_url='login')
def theme_selection_view(request):
    from heart_disease.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        selected_theme = request.POST.get('theme', 'green')
        if selected_theme in ['blue', 'green', 'red', 'purple']:
            profile.theme = selected_theme
            profile.save()
            
            from heart_disease.translations import TRANSLATIONS
            lang = request.session.get('lang', 'id')
            t = TRANSLATIONS.get(lang, TRANSLATIONS['id'])
            success_msg = t.get('theme_saved', 'Tema warna berhasil diperbarui!')
            
            messages.success(request, success_msg)
            return redirect('theme_selection')
            
    context = {
        'profile': profile,
    }
    return render(request, 'heart_disease/theme_selection.html', context)


@require_POST
def submit_contact_view(request):
    try:
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        company = request.POST.get('company', '').strip() or None
        phone = request.POST.get('phone', '').strip() or None
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not subject or not message:
            return JsonResponse({
                'status': 'error', 
                'message': 'Semua field wajib diisi.' if request.session.get('lang', 'id') == 'id' else 'All required fields must be filled.'
            }, status=400)

        # ─── Email Format Security Validation ───
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'status': 'error', 
                'message': 'Format alamat email tidak valid.' if request.session.get('lang', 'id') == 'id' else 'Invalid email address format.'
            }, status=400)

        # Simpan ke Database
        msg = ContactMessage.objects.create(
            name=name,
            email=email,
            company=company,
            phone=phone,
            subject=subject,
            message=message
        )

        lang = request.session.get('lang', 'id')
        
        if lang == 'en':
            success_msg = 'Message sent successfully! We will get back to you shortly.'
            auto_reply_msg = f"Auto-Reply: Hello {name}, thank you for contacting us! We have received your inquiry. A team member will respond to your email address within 24 hours. For immediate medical screening, please use the Predict tool."
        else:
            success_msg = 'Pesan berhasil dikirim! Kami akan menghubungi Anda segera.'
            auto_reply_msg = f"Balasan Otomatis: Halo {name}, terima kasih telah menghubungi kami! Kami telah menerima pesan Anda. Tim kami akan membalas ke email Anda dalam waktu 24 jam. Untuk pemeriksaan medis segera, silakan gunakan fitur Prediksi."

        # Kirim email balasan otomatis (auto-reply) menggunakan Django send_mail
        email_subject = "HeartGuard Inquiry Auto-Reply" if lang == 'en' else "Balasan Otomatis Pertanyaan HeartGuard"
        send_mail(
            subject=email_subject,
            message=auto_reply_msg,
            from_email=None,  # Menggunakan DEFAULT_FROM_EMAIL dari settings.py
            recipient_list=[email],
            fail_silently=True  # Agar request tidak error jika SMTP belum dikonfigurasi secara nyata
        )

        return JsonResponse({
            'status': 'success',
            'message': success_msg,
            'auto_reply': auto_reply_msg,
            'name': name
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@user_passes_test(is_admin, login_url='login')
@require_POST
def reply_contact_view(request, id):
    try:
        msg = get_object_or_404(ContactMessage, id=id)
        reply_text = request.POST.get('reply_text', '').strip()
        
        if not reply_text:
            return JsonResponse({'status': 'error', 'message': 'Reply text cannot be empty.'}, status=400)
            
        msg.admin_reply = reply_text
        msg.reply_sent = True
        msg.replied_at = timezone.now()
        msg.save()
        
        # Kirim email balasan manual dari Admin ke Klien
        email_subject = f"Re: {msg.subject}"
        email_body = (
            f"Halo {msg.name},\n\n"
            f"Berikut adalah tanggapan dari tim dukungan HeartGuard mengenai pesan Anda:\n\n"
            f"----------------------------------------\n"
            f"Pesan Anda:\n"
            f"\"{msg.message}\"\n"
            f"----------------------------------------\n\n"
            f"Jawaban Kami:\n"
            f"\"{reply_text}\"\n\n"
            f"Salam hangat,\n"
            f"Tim Dukungan HeartGuard"
        )
        
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=None,
            recipient_list=[msg.email],
            fail_silently=True
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Reply sent successfully!',
            'reply_text': reply_text,
            'replied_at': msg.replied_at.strftime('%d/%m %H:%M')
        })
    except Exception as e:
        import traceback
        with open('error_log.txt', 'a') as f:
            f.write(f"=== Exception in reply_contact_view at {timezone.now()} ===\n")
            traceback.print_exc(file=f)
            f.write("-" * 50 + "\n")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@user_passes_test(is_admin, login_url='login')
def manage_inquiries_view(request):
    contact_messages = ContactMessage.objects.all().order_by('-created_at')
    context = {
        'contact_messages': contact_messages,
    }
    return render(request, 'heart_disease/manage_inquiries.html', context)


@user_passes_test(is_admin, login_url='login')
@require_POST
def edit_inquiry_view(request, id):
    try:
        msg = get_object_or_404(ContactMessage, id=id)
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip() or None
        company = request.POST.get('company', '').strip() or None
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not name or not email or not subject or not message:
            return JsonResponse({'status': 'error', 'message': 'All required fields must be filled.'}, status=400)
            
        msg.name = name
        msg.email = email
        msg.phone = phone
        msg.company = company
        msg.subject = subject
        msg.message = message
        msg.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Pertanyaan berhasil diubah!' if request.session.get('lang', 'id') == 'id' else 'Inquiry updated successfully!'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@user_passes_test(is_admin, login_url='login')
@require_POST
def delete_inquiry_view(request, id):
    try:
        msg = get_object_or_404(ContactMessage, id=id)
        msg.delete()
        lang = request.session.get('lang', 'id')
        success_msg = 'Pertanyaan berhasil dihapus!' if lang == 'id' else 'Inquiry successfully deleted!'
        messages.success(request, success_msg)
    except Exception as e:
        messages.error(request, f'Gagal menghapus pertanyaan: {str(e)}' if request.session.get('lang', 'id') == 'id' else f'Failed to delete inquiry: {str(e)}')
    return redirect('manage_inquiries')


