LLM Provider Setup (OpenAI or Generic HTTP provider)
=====================================

This project supports two ways to enable an LLM for interview question generation and feedback:

1) OpenAI SDK (recommended when using OpenAI-compatible keys)
2) Generic HTTP LLM provider (e.g., Deepseek) via LLM_API_KEY + LLM_API_URL

Important: never commit your API keys to git. Use backend/.env (which should be gitignored) or set environment variables on your host.

Environment variables
---------------------
- OPENAI_API_KEY: (optional) OpenAI API key. If present and openai Python package is installed, the app will use OpenAI.
- OPENAI_MODEL: (optional) Model name (default gpt-3.5-turbo)

- LLM_API_KEY: (optional) API key for a generic HTTP LLM provider (Bearer auth)
- LLM_API_URL: (optional) HTTP endpoint that accepts JSON { prompt, max_tokens, temperature } and returns JSON with text/answer/output/result
- LLM_PROVIDER: (optional) Short name for provider used for logging (e.g., "deepseek")

Priority
--------
1. If OPENAI_API_KEY is set and the openai package is available, the backend will prefer OpenAI SDK calls.
2. Otherwise, if LLM_API_KEY and LLM_API_URL are set and requests is available, the backend will POST to LLM_API_URL with the prompt.
3. If neither is configured the backend falls back to deterministic local templates.

How to set locally (Windows PowerShell)
--------------------------------------
$env:OPENAI_API_KEY = "sk-..."    # for OpenAI
# or
$env:LLM_API_KEY = "<your-key>"
$env:LLM_API_URL = "https://api.deepseek.example/v1/generate"
$env:LLM_PROVIDER = "deepseek"

Linux / macOS (bash)
---------------------
export OPENAI_API_KEY="sk-..."
# or
export LLM_API_KEY="<your-key>"
export LLM_API_URL="https://api.deepseek.example/v1/generate"
export LLM_PROVIDER="deepseek"

Example curl (generate-answer)
------------------------------
curl -X POST http://127.0.0.1:5000/api/ai/generate-answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"Tell me about a time you faced a hard problem and how you solved it."}'

Example curl (analyze-answer)
-----------------------------
curl -X POST http://127.0.0.1:5000/api/ai/analyze-answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"...","user_answer":"...","model_answer":"..."}'

Notes
-----
- If you switch providers (OpenAI <-> HTTP provider) restart the backend server so environment variables are reloaded.
- The backend will never log secret values. It will only log which provider (openai / generic / none) is active for diagnostic purposes.
- If you accidentally paste an API key into a public chat or commit, rotate/revoke it immediately.
