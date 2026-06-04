# pyrefly: ignore [missing-import]
from django.apps import AppConfig

class HeartDiseaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'heart_disease'
    verbose_name = 'Prediksi Penyakit Jantung'
