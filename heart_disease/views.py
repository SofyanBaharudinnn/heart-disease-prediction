import json
import os
import shutil
# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
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
from django.contrib.auth import login
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User

from .ml_model import (
    FEATURE_INFO, load_dataset, train_and_evaluate, predict_single
)
from .models import PredictionHistory, ModelMetrics

def is_admin(user):
    return user.is_authenticated and user.is_staff


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
        n_splits     = int(request.POST.get('n_splits', 5))
        n_estimators = int(request.POST.get('n_estimators', 100))

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
            input_data = {f: request.POST.get(f, 0) for f in FEATURE_INFO}
            result, err = predict_single(input_data)

            if err:
                messages.error(request, err)
                return redirect('predict')

            # Simpan riwayat
            PredictionHistory.objects.create(
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

            context = {
                'result':     result,
                'input_data': input_data,
                'feature_info': FEATURE_INFO,
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
