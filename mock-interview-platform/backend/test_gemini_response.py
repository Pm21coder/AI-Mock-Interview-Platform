import os
from app.config import Config
try:
    import google.generativeai as genai
except Exception as e:
    print('Import error:', e)
    raise

print('Using API key:', Config.GOOGLE_GEMINI_API_KEY[:10] + '...')
try:
    genai.configure(api_key=Config.GOOGLE_GEMINI_API_KEY)
    model = genai.GenerativeModel(Config.GOOGLE_GEMINI_MODEL)
    print('Model created:', model)
    resp = model.generate_content('Return a JSON object {"ok": true, "value": 42}', request_options={'timeout': 10})
    print('RESPONSE TYPE:', type(resp))
    print('RESPONSE DIR:', [x for x in dir(resp) if not x.startswith('_')])
    print('REPR:', repr(resp)[:1000])
    print('TEXT ATTR:', getattr(resp, 'text', None))
    candidates = getattr(resp, 'candidates', None)
    print('CANDIDATES:', candidates)
    if candidates:
        first = candidates[0]
        print('FIRST CAND DIR:', [x for x in dir(first) if not x.startswith('_')])
        print('FIRST CAND repr:', repr(first)[:1000])
        print('FIRST CAND content attr:', getattr(first, 'content', None))
        print('FIRST CAND output attr:', getattr(first, 'output', None))
        print('FIRST CAND text attr:', getattr(first, 'text', None))
except Exception as exc:
    print('Error during generate_content:', exc)
    raise
