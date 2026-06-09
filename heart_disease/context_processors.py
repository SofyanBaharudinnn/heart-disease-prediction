from heart_disease.translations import TRANSLATIONS
from heart_disease.ml_model import FEATURE_INFO

def translation_processor(request):
    lang_code = request.session.get('lang', 'id')
    t = TRANSLATIONS.get(lang_code, TRANSLATIONS['id'])
    
    # Build localized feature info
    localized_feature_info = {}
    lang_feature_info = t.get('feature_info', {})
    for key, spec in FEATURE_INFO.items():
        localized_spec = spec.copy()
        if key in lang_feature_info:
            localized_spec.update(lang_feature_info[key])
        localized_feature_info[key] = localized_spec

    return {
        'current_lang': lang_code,
        't': t,
        'feature_info': localized_feature_info
    }


def theme_processor(request):
    from heart_disease.models import UserProfile
    theme = 'green'
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            theme = profile.theme
        except Exception:
            pass
    return {
        'current_theme': theme
    }


