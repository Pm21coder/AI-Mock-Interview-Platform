import { NextResponse } from "next/server";

// Server-side proxy to a generic LLM (DeepSeek-compatible).
// Reads configuration from environment variables (do NOT commit API keys):
// - LLM_API_URL (or DEEPSEEK_API_URL)
// - LLM_API_KEY (or DEEPSEEK_API_KEY)
// - LLM_PROVIDER (optional, defaults to 'deepseek')

const LLM_API_URL = process.env.LLM_API_URL || process.env.DEEPSEEK_API_URL;
const LLM_API_KEY = process.env.LLM_API_KEY || process.env.DEEPSEEK_API_KEY;
const LLM_PROVIDER = (process.env.LLM_PROVIDER || process.env.DEEPSEEK_PROVIDER || "deepseek").toLowerCase();

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
    // outputs can be objects with "content" or simple strings
    const out = json.outputs[0];
    if (typeof out === "string") return out;
    if (out.content) return typeof out.content === "string" ? out.content : JSON.stringify(out.content);
  }

  if (json.result && typeof json.result === "string") return json.result;
  if (json.result && json.result.output) return json.result.output;

  if (json.data && json.data.text) return json.data.text;

  // Fallback: try a few nested properties
  if (json.output && typeof json.output === "string") return json.output;
  if (json.message && typeof json.message === "string") return json.message;

  // Last resort: stringify useful parts
  try {
    return JSON.stringify(json);
  } catch (e) {
    return null;
  }
}

export async function POST(req: Request) {
  let body: any;
  try {
    body = await req.json();
  } catch (e) {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { action, prompt, params = {} } = body || {};

  // Basic validation
  if (!prompt && !body.input) {
    return NextResponse.json({ error: "Missing 'prompt' or 'input' in request body." }, { status: 400 });
  }

  // If no LLM configured, fallback to the backend API (Flask) using NEXT_PUBLIC_API_URL
  if (!LLM_API_URL || !LLM_API_KEY) {
    const backendBase = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_API_URL || 'http://localhost:5000';
    // Map actions to backend endpoints
    const actionMap: Record<string, string> = {
      generate_questions: '/api/interview/generate-questions',
      analyze_qa_pairs: '/api/interview/analyze-answer',
      analyze_answer: '/api/interview/analyze-answer',
      default: '/api/interview/analyze-answer',
    };

    const targetPath = action && actionMap[action] ? actionMap[action] : actionMap['default'];
    const targetUrl = backendBase.replace(/\/$/, '') + targetPath;

    try {
      const forwardRes = await fetchWithTimeout(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...(params || {}), prompt, input: body.input }),
      }, DEFAULT_TIMEOUT);

      const text = await forwardRes.text();
      const parsed = safeJsonParse(text);
      return NextResponse.json(parsed, { status: forwardRes.status });
    } catch (err: any) {
      const isAbort = err && (err.name === 'AbortError' || err.type === 'aborted');
      const message = isAbort ? `Upstream request timed out after ${DEFAULT_TIMEOUT}ms` : (err.message || String(err));
      return NextResponse.json({ ok: false, error: message }, { status: 502 });
    }
  }

  // Build provider payload. This is a reasonable DeepSeek/OpenAI-compatible default.
  const model = params.model || params.model_name || params.modelName || "deepseek-chat";
  const temperature = typeof params.temperature === "number" ? params.temperature : 0.7;
  const max_tokens = params.max_tokens || params.maxTokens || 800;

  // Normalize the prompt field
  const inputText = prompt || body.input || "";

  // Construct a generic payload that DeepSeek-style endpoints often accept.
  const payload: any = LLM_PROVIDER === "deepseek"
    ? {
        input: inputText,
        model,
        temperature,
        max_tokens,
        // pass-through any other params the client sent
        ...(params || {}),
      }
    : {
        // Fallback generic OpenAI-compatible shape
        model,
        messages: [
          { role: "system", content: params.system || "You are an expert interviewer and evaluator." },
          { role: "user", content: inputText },
        ],
        temperature,
        max_tokens,
        ...(params || {}),
      };

  try {
    const upstreamRes = await fetchWithTimeout(LLM_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${LLM_API_KEY}`,
      },
      body: JSON.stringify(payload),
    });

    const text = await upstreamRes.text();
    const parsed = safeJsonParse(text);

    // Try to extract a human-readable string from the provider response
    const extracted = extractTextFromLLMResponse(parsed);

    return NextResponse.json(
      {
        ok: true,
        provider: LLM_PROVIDER,
        // prefer a concise extracted result but also return raw for debugging (no secrets)
        result: extracted,
        raw: parsed,
      },
      { status: 200 }
    );
  } catch (err: any) {
    // Map AbortError to a nicer timeout message
    const isAbort = err && (err.name === "AbortError" || err.type === "aborted");
    const message = isAbort ? `Upstream request timed out after ${DEFAULT_TIMEOUT}ms` : (err.message || String(err));
    return NextResponse.json({ ok: false, error: message }, { status: 502 });
  }
}
