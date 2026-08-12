from app.config import Config

try:
    import google.genai as genai_new
    print('google.genai imported successfully')
    print('Available attributes:', [a for a in dir(genai_new) if not a.startswith('_')])
    print('Has Client?:', hasattr(genai_new, 'Client'))
    if hasattr(genai_new, 'Client'):
        print('Client:', genai_new.Client)
except Exception as e:
    print('Import failed:', e)

try:
    from importlib import import_module
    mod = import_module('google.genai')
    print('import_module succeeded')
except Exception as e:
    print('import_module failed:', e)
