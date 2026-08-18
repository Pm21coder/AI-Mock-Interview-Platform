"""
Monkey-patch requests.post to inject Authorization header from configured LLM API key
if one is not provided. This helps ensure generic HTTP LLM calls receive the key even
if a caller inadvertently used a redacted placeholder.

This module is safe to import; it no-ops if requests is not available or no key is set.
"""

try:
    import requests
except Exception:
    requests = None

from app.config import Config

if requests:
    try:
        _real_post = requests.post

        def _injecting_post(url, *args, **kwargs):
            headers = kwargs.get('headers') or {}
            try:
                auth = headers.get('Authorization')
                if not auth or auth == '******':
                    key = getattr(Config, 'LLM_API_KEY', '') or getattr(Config, 'OPENAI_API_KEY', '')
                    if key:
                        headers['Authorization'] = f'Bearer {key}'
                        kwargs['headers'] = headers
            except Exception:
                pass
            return _real_post(url, *args, **kwargs)

        requests.post = _injecting_post
    except Exception:
        # If monkey-patch fails, silently continue; callers will still be able to set headers.
        pass
