import { NextResponse } from "next/server";

// Server-side proxy to the configured LLM provider. Default provider set to Gemini.
// Reads configuration from environment variables (do NOT commit API keys):
// - GEMINI_API_URL or LLM_API_URL
// - GEMINI_API_KEY or LLM_API_KEY
// - LLM_PROVIDER (optional)

const LLM_API_URL = process.env.GEMINI_API_URL || process.env.LLM_API_URL || process.env.DEEPSEEK_API_URL;
const LLM_API_KEY = process.env.GEMINI_API_KEY || process.env.LLM_API_KEY || process.env.DEEPSEEK_API_KEY;
const LLM_PROVIDER = (process.env.LLM_PROVIDER || process.env.GEMINI_PROVIDER || "gemini").toLowerCase();

// Timeout for upstream LLM calls (ms)
const DEFAULT_TIMEOUT = 30_000;

function safeJsonParse(input: any) {
  try {
    return typeof input === "string" ? JSON.parse(input) : input;
  } catch (e) {
    return input;
  }
}

async function fetchWithTimeout(url: string, init: RequestInit, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    clearTimeout(id);
    return res;
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
}

function extractTextFromLLMResponse(json: any): string | null {
  if (!json) return null;

  // Common OpenAI-like shape
  if (json.choices && Array.isArray(json.choices) && json.choices.length) {
    const choice = json.choices[0];
    if (choice.message && (choice.message.content || choice.message.content === "")) return choice.message.content;
    if (choice.text) return choice.text;
  }

  // DeepSeek-like shapes
  if (json.outputs && Array.isArray(json.outputs) && json.outputs.length) {
    const out = json.outputs[0];
    if (typeof out === "string") return out;
    if (out.content) return typeof out.content === "string" ? out.content : JSON.stringify(out.content);
  }

  if (json.result && typeof json.result === "string") return json.result;
  if (json.result && json.result.output) return json.result.output;

  if (json.data && json.data.text) return json.data.text;

  if (json.output && typeof json.output === "string") return json.output;
  if (json.message && typeof json.message === "string") return json.message;

  try { return JSON.stringify(json); } catch (e) { return null; }
}

export async function POST(req: Request) {
  let body: any;
  try { body = await req.json(); } catch (e) { return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 }); }

  const { action, prompt, params = {} } = body || {};

  if (!prompt && !body.input) {
    return NextResponse.json({ error: "Missing 'prompt' or 'input' in request body." }, { status: 400 });
  }

  // If no LLM configured, use local fallback
  if (!LLM_API_URL || !LLM_API_KEY) {
    try {
      const { handleLocalFallback } = await import('./localFallback');
      const out = await handleLocalFallback(action, prompt, params || {});
      return NextResponse.json(out, { status: 200 });
    } catch (e: any) {
      const message = e?.message || String(e);
      return NextResponse.json({ ok: false, error: `Local fallback failed: ${message}` }, { status: 500 });
    }
  }

  const model = params.model || params.model_name || params.modelName || (LLM_PROVIDER === 'gemini' ? 'gemini-1' : 'default-model');
  const temperature = typeof params.temperature === 'number' ? params.temperature : 0.7;
  const max_tokens = params.max_tokens || params.maxTokens || 800;
  const inputText = prompt || body.input || "";

  // Construct payload depending on provider
  let payload: any;
  if (LLM_PROVIDER === 'gemini') {
    payload = {
      model,
      messages: [
        { role: 'system', content: params.system || 'You are an expert interviewer and evaluator.' },
        { role: 'user', content: inputText },
      ],
      temperature,
      max_tokens,
      ...(params || {}),
    };
  } else if (LLM_PROVIDER === 'deepseek') {
    payload = { input: inputText, model, temperature, max_tokens, ...(params || {}) };
  } else {
    payload = {
      model,
      messages: [ { role: 'system', content: params.system || 'You are an expert interviewer and evaluator.' }, { role: 'user', content: inputText } ],
      temperature,
      max_tokens,
      ...(params || {}),
    };
  }

  try {
    const headers: Record<string,string> = { 'Content-Type':'application/json', 'Accept':'application/json' };
    if (LLM_API_KEY) {
      // Use Bearer token and also set x-api-key as a fallback for providers that expect it
      headers['Authorization'] = 'Bearer ' + LLM_API_KEY;
      headers['x-api-key'] = LLM_API_KEY;
    }

    const upstreamRes = await fetchWithTimeout(LLM_API_URL, { method: 'POST', headers, body: JSON.stringify(payload) }, DEFAULT_TIMEOUT);

    const text = await upstreamRes.text();
    const parsed = safeJsonParse(text);

    if (!upstreamRes.ok) {
      // Upstream returned a non-2xx - surface the parsed body for debugging
      return NextResponse.json({ ok: false, provider: LLM_PROVIDER, status: upstreamRes.status, statusText: upstreamRes.statusText, raw: parsed }, { status: 502 });
    }

    const extracted = extractTextFromLLMResponse(parsed);

    return NextResponse.json({ ok: true, provider: LLM_PROVIDER, result: extracted ?? parsed, raw: parsed }, { status: 200 });
  } catch (err: any) {
    const isAbort = err && (err.name === 'AbortError' || err.type === 'aborted');
    const message = isAbort ? `Upstream request timed out after ${DEFAULT_TIMEOUT}ms` : (err.message || String(err));
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}
