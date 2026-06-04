from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class PredictionHistory(models.Model):
    """Menyimpan riwayat prediksi."""
    user     = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    # Input fitur
    age      = models.IntegerField()
    sex      = models.IntegerField()
    cp       = models.IntegerField()
    trestbps = models.IntegerField()
    chol     = models.IntegerField()
    fbs      = models.IntegerField()
    restecg  = models.IntegerField()
    thalach  = models.IntegerField()
    exang    = models.IntegerField()
    oldpeak  = models.FloatField()
    slope    = models.IntegerField()
    ca       = models.IntegerField()
    thal     = models.IntegerField()

    # Output
    prediction        = models.IntegerField()  # 0 or 1
    probability_pos   = models.FloatField()
    probability_neg   = models.FloatField()
    risk_level        = models.CharField(max_length=20)
    created_at        = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Riwayat Prediksi'
        verbose_name_plural = 'Riwayat Prediksi'

    def __str__(self):
        label = 'Positif' if self.prediction == 1 else 'Negatif'
        return f"[{self.created_at.strftime('%d-%m-%Y %H:%M')}] {label} – Risiko {self.risk_level}"


class ModelMetrics(models.Model):
    """Menyimpan hasil evaluasi model terakhir."""
    accuracy     = models.FloatField()
    precision    = models.FloatField()
    recall       = models.FloatField()
    f1_score     = models.FloatField()
    roc_auc      = models.FloatField()
    n_splits     = models.IntegerField(default=5)
    n_estimators = models.IntegerField(default=100)
    trained_at   = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-trained_at']
        verbose_name = 'Metrik Model'

    def __str__(self):
        return f"Model {self.trained_at.strftime('%d-%m-%Y %H:%M')} – Acc: {self.accuracy:.3f}"
