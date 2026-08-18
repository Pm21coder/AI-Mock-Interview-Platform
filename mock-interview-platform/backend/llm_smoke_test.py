"""
Small smoke-test to validate the configured LLM (DeepSeek-compatible) from the server-side environment.

Usage:
  python backend/llm_smoke_test.py

It reads LLM_API_URL and LLM_API_KEY from the environment and sends a short test prompt.
It prints the HTTP status, raw JSON response (safe to display), and attempts to extract a human-friendly text result
using the same heuristics as the frontend proxy.

Do NOT commit API keys to source control. This script expects keys to be present in the environment.
"""

import os
import sys
import json
import requests

LLM_API_URL = os.environ.get('LLM_API_URL') or os.environ.get('DEEPSEEK_API_URL')
LLM_API_KEY = os.environ.get('LLM_API_KEY') or os.environ.get('DEEPSEEK_API_KEY')
LLM_PROVIDER = (os.environ.get('LLM_PROVIDER') or os.environ.get('DEEPSEEK_PROVIDER') or 'deepseek').lower()
TIMEOUT = 30

if not LLM_API_URL or not LLM_API_KEY:
    print('ERROR: LLM_API_URL and LLM_API_KEY must be set in the environment.')
    sys.exit(2)

prompt = "Please generate one short interview question for a frontend engineer and a 1-2 sentence model answer."

if LLM_PROVIDER == 'deepseek':
    payload = {
        'input': prompt,
        'model': os.environ.get('LLM_MODEL', 'deepseek-chat'),
        'temperature': 0.0,
        'max_tokens': 200,
    }
else:
    # Generic OpenAI-compatible fallback
    payload = {
        'model': os.environ.get('LLM_MODEL', 'gpt-3.5-turbo'),
        'messages': [
            { 'role': 'system', 'content': 'You are a helpful interviewer.' },
            { 'role': 'user', 'content': prompt }
        ],
        'temperature': 0.0,
        'max_tokens': 200,
    }

headers = {
    'Authorization': f'Bearer {LLM_API_KEY}',
    'Content-Type': 'application/json',
}

print('Sending test request to', LLM_API_URL)
try:
    resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=TIMEOUT)
except Exception as e:
    print('Request failed:', e)
    sys.exit(3)

print('Status:', resp.status_code)

text = None
raw = None
try:
    raw = resp.json()
except Exception:
    raw = None
    text = resp.text

print('\n=== Raw response (truncated) ===')
if raw is not None:
    try:
        print(json.dumps(raw, indent=2)[:8000])
    except Exception:
        print(str(raw)[:8000])
else:
    print(str(text)[:8000])

# Heuristic extraction
def extract_text(json_obj, text_body):
    if not json_obj:
        return text_body
    # OpenAI-like
    if isinstance(json_obj, dict):
        if 'choices' in json_obj and isinstance(json_obj['choices'], list) and len(json_obj['choices']) > 0:
            ch = json_obj['choices'][0]
            if isinstance(ch, dict):
                if 'message' in ch and isinstance(ch['message'], dict):
                    return ch['message'].get('content') or ch.get('text')
                if 'text' in ch:
                    return ch.get('text')
        if 'outputs' in json_obj and isinstance(json_obj['outputs'], list) and len(json_obj['outputs']) > 0:
            out = json_obj['outputs'][0]
            if isinstance(out, str):
                return out
            if isinstance(out, dict) and 'content' in out:
                return out['content'] if isinstance(out['content'], str) else json.dumps(out['content'])
        if 'result' in json_obj:
            r = json_obj['result']
            if isinstance(r, str):
                return r
            if isinstance(r, dict) and 'output' in r:
                return r['output']
        if 'data' in json_obj and isinstance(json_obj['data'], dict) and 'text' in json_obj['data']:
            return json_obj['data']['text']
        # try nested 'output' or 'message'
        if 'output' in json_obj and isinstance(json_obj['output'], str):
            return json_obj['output']
        if 'message' in json_obj and isinstance(json_obj['message'], str):
            return json_obj['message']
    return None

extracted = extract_text(raw, text)
print('\n=== Extracted text (heuristic) ===')
print(extracted or 'No text could be extracted using heuristics')

if resp.status_code >= 400:
    sys.exit(1)

print('\nSmoke test completed successfully.')
