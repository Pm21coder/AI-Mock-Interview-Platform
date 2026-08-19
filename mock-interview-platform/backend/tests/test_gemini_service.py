from app.services.gemini_service import GeminiService


def test_model_name_is_normalized_for_google_sdk():
    assert GeminiService.normalize_model_name('models/gemini-3.6-flash') == 'gemini-3.6-flash'
    assert GeminiService.normalize_model_name(' gemini-2.0-flash ') == 'gemini-2.0-flash'
    assert GeminiService.normalize_model_name('') == 'gemini-3.6-flash'


def test_generate_json_uses_supported_google_genai_args():
    class FakeResponse:
        text = '{"ok": true}'

    class FakeModelClient:
        def __init__(self):
            self.calls = []

        def generate_content(self, **kwargs):
            assert 'request_options' not in kwargs
            self.calls.append(kwargs)
            return FakeResponse()

    class FakeClient:
        def __init__(self):
            self.models = FakeModelClient()

    service = GeminiService.__new__(GeminiService)
    service.model_candidates_list = ['gemini-3.6-flash']
    service.use_new_sdk = True
    service.client = FakeClient()
    service.model = None
    service.last_error = None

    assert service._generate_json('hello', max_output_tokens=512) == '{"ok": true}'
    assert service.client.models.calls[0]['model'] == 'models/gemini-3.6-flash'
