# pyrefly: ignore [missing-import]
from django.db import models
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
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
    serial_number     = models.CharField(max_length=30, blank=True, default='', verbose_name='Nomor Seri')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Riwayat Prediksi'
        verbose_name_plural = 'Riwayat Prediksi'

    def __str__(self):
        label = 'Positif' if self.prediction == 1 else 'Negatif'
        ref = self.serial_number if self.serial_number else f'#{self.id}'
        return f"[{ref}] {self.created_at.strftime('%d-%m-%Y %H:%M')} – {label} – Risiko {self.risk_level}"


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


class UserProfile(models.Model):
    THEME_CHOICES = [
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('red', 'Red'),
        ('purple', 'Purple'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='green')

    def __str__(self):
        return f"{self.user.username}'s Profile (Theme: {self.theme})"


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    reply_sent = models.BooleanField(default=False)
    admin_reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Pesan Kontak'
        verbose_name_plural = 'Pesan Kontak'

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"

