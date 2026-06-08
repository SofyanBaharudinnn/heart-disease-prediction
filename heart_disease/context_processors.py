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

