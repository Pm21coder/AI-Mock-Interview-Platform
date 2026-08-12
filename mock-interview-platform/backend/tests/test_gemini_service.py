from app.services.gemini_service import GeminiService


def test_model_name_is_normalized_for_google_sdk():
    assert GeminiService.normalize_model_name('models/gemini-3.6-flash') == 'gemini-3.6-flash'
    assert GeminiService.normalize_model_name(' gemini-2.0-flash ') == 'gemini-2.0-flash'
    assert GeminiService.normalize_model_name('') == 'gemini-2.0-flash'
