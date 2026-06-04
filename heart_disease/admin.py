# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import PredictionHistory, ModelMetrics

@admin.register(PredictionHistory)
class PredictionHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'age', 'sex', 'prediction', 'risk_level', 'probability_pos', 'created_at']
    list_filter  = ['prediction', 'risk_level']
    readonly_fields = ['created_at']

@admin.register(ModelMetrics)
class ModelMetricsAdmin(admin.ModelAdmin):
    list_display = ['id', 'accuracy', 'f1_score', 'roc_auc', 'n_splits', 'n_estimators', 'trained_at']
    readonly_fields = ['trained_at']
