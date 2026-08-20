import axios from 'axios';

// Simple in-memory cache with TTL for reducing duplicate API calls
const apiCache = new Map();
const CACHE_TTL = {
  questionCategories: 5 * 60 * 1000, // 5 minutes
  dashboardStats: 60 * 1000, // 1 minute
  features: 5 * 60 * 1000, // 5 minutes
  default: 2 * 60 * 1000, // 2 minutes
};

const REQUEST_TIMEOUTS = {
  // Resume/text analysis related timeouts
  resumeAnalysis: 20_000, // increased from 10s to tolerate backend cold-starts
  resumeHistory: 20_000, // increased from 10s
  // Subscription status can occasionally be slow during billing calls
  // Increase client timeout to 30s to tolerate backend processing (billing lookups, Stripe checks)
  subscriptionStatus: 30_000, // increased from 15s -> 30s
  // Increase dashboard and question-category lookups timeout to be tolerant of
  // cold starts and occasional backend latency (e.g., pre-warming, DB rebuilds).
  questionCategories: 30_000,
  dashboardStats: 30_000,
  createOrder: 15_000,
  // Allow longer AI generation time in environments with higher server limits.
  // Question generation can be expensive; keep a generous timeout.
  interviewQuestions: 120_000,
  // Client-side timeout for answer analysis. Increase to 60s to cover longer LLM runs
  // while still relying on background-job/polling as primary flow.
  interviewAnalysis: 60_000,
};

function responseBodyForLog(error) {
  if (!error?.response) return 'No response received from the server';

  const body = error.response.data;
  if (body == null || (typeof body === 'object' && Object.keys(body).length === 0)) {
    return 'Empty server response body';
  }
  return body;
}

// Simple throttle to avoid spamming the console with repeated identical
// API error dumps during transient backend issues. Keyed by endpoint + status.
const API_LOG_THROTTLE_TTL = 30_000; // 30 seconds
const _apiLogLast = new Map();

function logApiError(endpoint, error) {
  // Treat request cancellations as non-error-level diagnostics. These are
  // expected when users navigate away or abort a request, and shouldn't
  // be noisy in the console.
  try {
    const isCanceled = (
      error && (
        // Prefer axios.isCancel if available; fall back to common cancel markers
        (typeof axios !== 'undefined' && typeof axios.isCancel === 'function' && axios.isCancel(error)) ||
        error.code === 'ERR_CANCELED' ||
        error.name === 'CanceledError' ||
        error.name === 'AbortError' ||
        (typeof error.message === 'string' && error.message.toLowerCase().includes('canceled'))
      )
    );
    if (isCanceled) {
      // Keep cancellations at debug level and avoid spammy stack traces.
      // Use debug in both dev and production to reduce noise from expected cancels.
      console.debug(`API request canceled at ${endpoint}:`, error?.message || error);
      return;
    }
  } catch (e) {
    // ignore cancellation detection failures and continue to normal logging
  }

  // Throttle repeated logs for the same endpoint/status to reduce noise.
  try {
    const now = Date.now();
    const status = error?.response?.status ?? error?.status ?? 'no-status';
    const throttleKey = `${endpoint}:${status}`;
    const last = _apiLogLast.get(throttleKey) || 0;
    if (now - last < API_LOG_THROTTLE_TTL) {
      // Emit a concise warning only and skip the heavy serialization.
      console.warn(`API error at ${endpoint} (repeated): ${error?.message || 'See server logs'}`);
      return;
    }
    _apiLogLast.set(throttleKey, now);
  } catch (e) {
    // If throttle bookkeeping fails for any reason, continue to log normally.
    // fall through
  }

  // Build a plain object with enumerable properties so consoles and remote
  // logging systems receive meaningful diagnostics even when Axios stores
  // data on non-enumerable properties.
  const serialized = {
    message: error?.message || null,
    code: error?.code || null,
    status: error?.response?.status ?? null,
    statusText: error?.response?.statusText ?? null,
    data: null,
    method: error?.config?.method ?? null,
    url: error?.config?.url ?? null,
    headers: null,
  };

  try {
    serialized.data = responseBodyForLog(error);
  } catch (e) {
    serialized.data = 'Unable to read response body';
  }

  try {
    const rawHeaders = error?.config?.headers || error?.response?.config?.headers;
    if (rawHeaders && typeof rawHeaders === 'object') {
      const safeHeaders = {};
      Object.entries(rawHeaders).forEach(([name, value]) => {
        const lower = String(name).toLowerCase();
        safeHeaders[name] = ['authorization', 'cookie', 'proxy-authorization', 'x-api-key'].includes(lower)
          ? '[REDACTED]'
          : value;
      });
      serialized.headers = safeHeaders;
    }
  } catch (e) {
    serialized.headers = null;
  }

  // Enrich messages for common failure modes (timeouts and server crashes)
  if (serialized.code === 'ECONNABORTED' || (serialized.message && serialized.message.toLowerCase().includes('timeout'))) {
    serialized.human_readable = 'Request timed out. The server or AI provider may be slow.';
  } else if (serialized.status === 500) {
    serialized.human_readable = 'Server error (500). Check backend logs for stack trace.';
  }

  // Print a stable, serialized representation so TurboPack/DevTools show details
  try {
    const out = { endpoint, ...serialized };
    const isDev = typeof process !== 'undefined' && process.env && process.env.NODE_ENV !== 'production';

    // If this is a network error (no response), asynchronously probe the health endpoint
    // to help determine whether the backend is reachable from the browser.
    if (!serialized.status && typeof window !== 'undefined') {
      (async () => {
        try {
          const base = api?.defaults?.baseURL || '';
          const healthPath = base.endsWith('/') ? `${base}api/health` : `${base}/api/health`;
          const controller = new AbortController();
          const id = setTimeout(() => controller.abort(), 3000);
          const res = await fetch(healthPath, { method: 'GET', cache: 'no-store', signal: controller.signal });
          clearTimeout(id);
          if (res.ok) {
            console.debug(`Backend health check OK at ${healthPath}`);
          } else {
            console.warn(`Backend health check returned ${res.status} at ${healthPath}`);
          }
        } catch (probeErr) {
          console.warn('Backend health check failed to reach server:', probeErr?.message || probeErr);
        }
      })();
    }

    if (isDev) {
      // Development: show the full serialized payload for easier debugging
      console.error(`API error at ${endpoint}: ${JSON.stringify(out, null, 2)}`);
      // Also emit a debug-level object for richer inspection when supported
      console.debug('API error (debug):', out);
    } else {
      // Production: avoid dumping potentially large or sensitive JSON into the
      // user's console. Log a concise human-readable message and keep a debug
      // copy available for tooling that consumes console.debug.
      console.error(`API error at ${endpoint}: ${serialized.human_readable || serialized.message || 'See server logs'}`);
      // Non-fatal: still emit a debug-level object when available (won't appear
      // in many production consoles but can be captured by remote logging).
      if (console.debug) console.debug('API error (debug):', out);
    }
  } catch (e) {
    // Fallback if serialization fails for any reason
    console.error('API error (unserializable):', endpoint, serialized, e);
  }
}

function invalidResumeIdError(resumeId) {
  const error = new Error('A valid resume ID is required to load an analysis.');
  error.code = 'INVALID_RESUME_ID';
  console.error('Resume analysis request skipped:', {
    reason: error.message,
    resumeIdPresent: Boolean(resumeId),
  });
  return error;
}

// Notify the application about a transient network issue so UI components
// can listen and display a user-visible hint (non-blocking). We dispatch a
// CustomEvent 'app:network-issue' and also persist a short-lived record in
// localStorage for debugging/visibility across tabs.
function notifyNetworkIssue(details) {
  try {
    if (typeof window === 'undefined') return;
    const payload = {
      ts: Date.now(),
      details,
    };
    try {
      window.localStorage.setItem('last_network_issue', JSON.stringify(payload));
    } catch (e) {
      // ignore storage failures
    }
    try {
      const ev = new CustomEvent('app:network-issue', { detail: payload });
      window.dispatchEvent(ev);
    } catch (e) {
      // CustomEvent may fail in older browsers — ignore
    }
  } catch (e) {
    // non-fatal
  }
}

function getCacheKey(method, url, params) {
  const paramStr = params ? JSON.stringify(params) : '';
  return `${method}:${url}:${paramStr}`;
}

function getCachedData(key) {
  const cached = apiCache.get(key);
  if (cached && Date.now() - cached.timestamp < cached.ttl) {
    return cached.data;
  }
  apiCache.delete(key);
  return null;
}

function setCachedData(key, data, ttl = CACHE_TTL.default) {
  apiCache.set(key, {
    data,
    timestamp: Date.now(),
    ttl,
  });
}

function clearCacheForKey(key) {
  apiCache.delete(key);
}

export function invalidateQuestionCategoriesCache() {
  const cacheKey = getCacheKey('GET', '/api/subscription/question-categories');
  clearCacheForKey(cacheKey);
}

/**
 * Clear all subscription-related caches.
 * Called after auth changes or when subscription is updated.
 */
export function invalidateAllSubscriptionCaches() {
  // Clear localStorage subscription cache
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem('subscription_data');
  }
  // Clear API response caches
  invalidateQuestionCategoriesCache();
}

const api = axios.create({
  // Use NEXT_PUBLIC_API_URL when provided so client can call backend directly
  // in environments where the Next.js proxy is not configured. Fall back to
  // same-origin '' for local development where rewrites are convenient.
  baseURL: (typeof process !== 'undefined' && process.env && process.env.NEXT_PUBLIC_API_URL)
    ? process.env.NEXT_PUBLIC_API_URL
    : (typeof window !== 'undefined' ? window.location.origin : ''),
  // Increase default axios timeout to accommodate long-running AI requests
  timeout: 120_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Simple built-in retry mechanism to handle transient network issues and
// backend cold-starts. This avoids adding a new dependency (axios-retry)
// while providing exponential backoff retries for common conditions.
api.interceptors.response.use(undefined, async (error) => {
  const config = error.config || {};
  // Do not retry for requests that opt-out explicitly
  if (config.__noRetry) return Promise.reject(error);

  config.__retryCount = config.__retryCount || 0;
  const maxRetries = typeof config.__maxRetries === 'number' ? config.__maxRetries : 2;

  // Determine if error is retryable: network error, timeout, or 5xx without body
  const isTimeout = error && (error.code === 'ECONNABORTED' || (error.message && error.message.toLowerCase().includes('timeout')));
  const isNetworkError = !error.response;
  const isServerError = error.response && error.response.status >= 500 && error.response.status < 600;

  const shouldRetry = isTimeout || isNetworkError || isServerError;

  if (shouldRetry && config.__retryCount < maxRetries) {
    config.__retryCount += 1;
    const delayMs = Math.min(1000 * Math.pow(2, config.__retryCount - 1), 5000);
    await new Promise((res) => setTimeout(res, delayMs));
    try {
      return api(config);
    } catch (e) {
      return Promise.reject(e);
    }
  }

  return Promise.reject(error);
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = window.localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = 'Bearer ' + token;
  }
  return config;
});

// Practice features support guest sessions. If a token left over from an
// earlier login has expired (or was signed with an old server secret), retry
// the request once without it instead of blocking the interview or resume
// workflow with a 401 response.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isPracticeRequest =
      originalRequest?.url?.startsWith('/api/interview/') ||
      originalRequest?.url?.startsWith('/api/resume/');

    if (
      error.response?.status === 401 &&
      isPracticeRequest &&
      !originalRequest._guestFallback &&
      typeof window !== 'undefined'
    ) {
      originalRequest._guestFallback = true;
      window.localStorage.removeItem('auth_token');
      window.localStorage.removeItem('auth_email');
      delete originalRequest.headers.Authorization;
      return api(originalRequest);
    }

    return Promise.reject(error);
  },
);

export const register = async (credentials) => {
  const response = await api.post('/api/auth/register', credentials);
  return response.data;
};

export const login = async (credentials) => {
  const response = await api.post('/api/auth/login', credentials);
  return response.data;
};

export const getQuestions = async (params, options = {}) => {
  const maxAttempts = 2;
  let attempt = 0;
  let lastError = null;
  let timeout = REQUEST_TIMEOUTS.interviewQuestions;

  while (attempt < maxAttempts) {
    attempt += 1;
    let fallbackController = null;
    let onAbort = null;

    try {
      let signalForAttempt = undefined;
      if (options && options.signal) {
        fallbackController = new AbortController();
        onAbort = () => {
          try { fallbackController.abort(); } catch (e) { /* ignore */ }
        };
        if (options.signal.addEventListener) options.signal.addEventListener('abort', onAbort);
        if (options.signal.aborted) fallbackController.abort();
        signalForAttempt = fallbackController.signal;
      }

      const response = await api.post('/api/interview/generate-questions', params, {
        timeout,
        validateStatus: (s) => s < 500,
        signal: signalForAttempt,
      });

      if (response.status === 200) return response.data;
      lastError = new Error('Unexpected response from generate-questions');
      break;
    } catch (err) {
      lastError = err;
      const isTimeout = err?.code === 'ECONNABORTED' || err?.message?.toLowerCase?.().includes('timeout');
      if (isTimeout && attempt < maxAttempts) {
        const backoffMs = 1000 * Math.pow(2, attempt - 1);
        console.warn(`getQuestions attempt ${attempt} timed out (timeout=${timeout}ms).`);
        await new Promise((res) => setTimeout(res, backoffMs));
        timeout = Math.min(timeout * 2, 180_000);
        continue;
      }

      logApiError('/api/interview/generate-questions', err || new Error('Unknown error'));
      break;
    } finally {
      try {
        if (options && options.signal && onAbort && options.signal.removeEventListener) {
          options.signal.removeEventListener('abort', onAbort);
        }
      } catch (cleanupErr) {
        // Non-fatal, ignore listener cleanup failures
      }
    }
  }

  const err = lastError;
  const status = err?.response?.status;
  if (!err?.response || (status && status >= 500)) {
    console.warn('Using local fallback questions because interview API is unavailable.');
    const fallbackQuestions = [
      {
        question: 'Tell me about a challenging bug you fixed. What was the root cause and how did you resolve it?',
        category: params?.category || 'technical',
        difficulty: params?.difficulty || 'medium',
        expected_answer: 'Look for technical diagnosis, stepwise debugging, and learning outcome.',
      },
      {
        question: 'Describe a time you led a project from idea to delivery. What obstacles did you face?',
        category: params?.category || 'behavioral',
        difficulty: params?.difficulty || 'medium',
        expected_answer: 'Look for leadership, planning, stakeholder management, and results.',
      },
      {
        question: 'How would you design a scalable notification system for millions of users?',
        category: params?.category || 'system_design',
        difficulty: params?.difficulty || 'hard',
        expected_answer: 'Discuss queuing, delivery guarantees, backpressure, and horizontal scaling.',
      },
    ];

    const requested = Number(params?.num_questions) || 3;
    const count = Math.min(Math.max(1, requested), 10);
    return {
      session_id: `local_fallback_${Date.now()}`,
      questions: fallbackQuestions.slice(0, count),
      fallback: true,
    };
  }

  throw err;
};

export const submitAnswer = async (data, options = {}) => {
  // Use the server-side LLM proxy at /api/interview for answer analysis.
  // Keep the existing retry/backoff behavior and friendly error mappings.
  const maxAttempts = 2;
  let attempt = 0;
  let lastError = null;
  let timeout = REQUEST_TIMEOUTS.interviewAnalysis * 2; // generous timeout for provider calls

  while (attempt < maxAttempts) {
    attempt += 1;
    try {
      const payload = {
        action: 'analyze_answer',
        prompt: data?.answer || data?.transcript || data?.text || '',
        params: data,
      };

      const response = await api.post('/api/interview', payload, {
        timeout,
        validateStatus: (s) => s < 500,
        signal: options.signal,
      });

      if (response.status === 200) return response.data;

      lastError = new Error('Unexpected response from analysis endpoint');
      break;
    } catch (err) {
      lastError = err;
      // If aborted by caller, propagate immediately
      if (err && (err.name === 'AbortError' || err.code === 'ERR_CANCELED' || err.name === 'CanceledError')) throw err;

      const isTimeout = err?.code === 'ECONNABORTED' || err?.message?.toLowerCase?.().includes('timeout');
      const isNetwork = !err?.response;

      // For transient timeouts/network errors, retry once with backoff
      if ((isTimeout || isNetwork) && attempt < maxAttempts) {
        const backoffMs = 1000 * Math.pow(2, attempt - 1);
        console.warn(`submitAnswer attempt ${attempt} failed; retrying after ${backoffMs}ms.`, err?.message || err);
        await new Promise((res) => setTimeout(res, backoffMs));
        // increase timeout for second attempt
        timeout = Math.min(timeout * 2, 180_000);
        continue;
      }

      // Non-retriable or final failure: log structured error and map to friendly object
      logApiError('/api/interview (analyze_answer)', err);

      // Map common cases to structured responses callers can use
      if (isTimeout) {
        return { error: 'Analysis timed out', details: 'The analysis service is taking too long. Try again later or shorten the response.' };
      }
      if (err?.response && err.response.status >= 500) {
        return { error: 'Server error', details: err?.message || 'The analysis service encountered an internal error.', status: err.response.status };
      }
      if (!err?.response) {
        return { error: 'Network error', details: err?.message || 'Could not reach analysis service' };
      }

      return { error: err?.response?.data?.error || 'Request failed', details: err?.response?.data?.details || err?.message || 'Request failed', status: err?.response?.status || null };
    }
  }

  // If we exit loop, return the last error mapped
  logApiError('/api/interview (analyze_answer)', lastError || new Error('Unknown error'));
  return { error: 'Analysis failed', details: lastError?.message || 'Unknown error' };
};

export const getFeedback = async (sessionId) => {
  const response = await api.get(`/api/interview/get-feedback/${sessionId}`);
  return response.data;
};

export const saveResponse = async (data) => {
  const response = await api.post('/api/interview/save-response', data);
  return response.data;
};

// In-memory cache + cooldown for dashboard stats to avoid rapid-fire requests (429)
let _cachedDashboardStats = null;
let _cachedDashboardTs = 0;
const DASHBOARD_CACHE_TTL = 30_000; // 30 seconds
let _dashboardCooldownUntil = 0; // ms timestamp when we can resume requests after a 429

export function invalidateDashboardStatsCache() {
  _cachedDashboardStats = null;
  _cachedDashboardTs = 0;
  _dashboardCooldownUntil = 0;
}

export const getDashboardStats = async (options = { forceRefresh: false }) => {
  try {
    const now = Date.now();

    if (options?.forceRefresh) {
      invalidateDashboardStatsCache();
    }

    // If we are currently in a cooldown window (due to recent 429), return cached or guest fallback
    if (now < _dashboardCooldownUntil) {
      console.warn('Dashboard stats request suppressed due to upstream rate limit until', new Date(_dashboardCooldownUntil).toISOString());
      if (_cachedDashboardStats && (now - _cachedDashboardTs) < (DASHBOARD_CACHE_TTL * 10)) {
        // Return slightly stale cached data during cooldown
        return _cachedDashboardStats;
      }
      // Provide graceful guest fallback if no cache present
      return {
        fallback: true,
        stats: { interviews_completed: 0, average_score: 0, confidence_score: 0 },
        recent_interviews: [],
        rate_limited: true,
      };
    }

    if (!options?.forceRefresh && _cachedDashboardStats && (now - _cachedDashboardTs) < DASHBOARD_CACHE_TTL) {
      // Return cached payload to avoid hammering the backend (helps avoid 429)
      return _cachedDashboardStats;
    }

    // Fetch fresh data from the backend with retries and exponential backoff
    const attemptTimeouts = [8000, REQUEST_TIMEOUTS.dashboardStats];
    let lastFetchError = null;
    let response = null;
    for (let i = 0; i < attemptTimeouts.length; i++) {
      try {
        response = await api.get('/api/interview/dashboard-stats', { timeout: attemptTimeouts[i] });
        break; // success
      } catch (err) {
        lastFetchError = err;
        const status = err?.response?.status;
        const isTimeout = err?.code === 'ECONNABORTED' || (err?.message || '').toLowerCase().includes('timeout');

        // If rate limited, respect Retry-After header or back off for a sensible default
        if (status === 429) {
          try {
            const ra = err.response?.headers?.['retry-after'] || err.response?.headers?.['x-rate-limit-reset'];
            // retry-after may be seconds or a HTTP-date
            let cooldownMs = 60_000; // default 60s
            if (ra) {
              const n = Number(ra);
              if (!Number.isNaN(n)) {
                cooldownMs = n * 1000;
              } else {
                // try parse HTTP-date
                const dt = Date.parse(ra);
                if (!Number.isNaN(dt)) cooldownMs = Math.max(0, dt - Date.now());
              }
            }
            _dashboardCooldownUntil = Date.now() + cooldownMs;
            console.warn(`getDashboardStats received 429 - backing off for ${Math.round(cooldownMs/1000)}s until ${new Date(_dashboardCooldownUntil).toISOString()}`);
          } catch (e) {
            _dashboardCooldownUntil = Date.now() + 60_000;
            console.warn('getDashboardStats received 429 - backing off for 60s (default)');
          }
          // Don't retry further in this loop
          break;
        }

        console.warn(`getDashboardStats attempt ${i + 1} failed (timeout=${attemptTimeouts[i]}ms):`, isTimeout ? 'timeout' : err?.message || err);
        // brief backoff before retrying
        if (i < attemptTimeouts.length - 1) await new Promise((res) => setTimeout(res, 500 * Math.pow(2, i)));
      }
    }

    if (!response) {
      // No successful response after retries � surface the last error into the existing catch handling
      throw lastFetchError || new Error('Failed to fetch dashboard stats');
    }

    _cachedDashboardStats = response.data;
    _cachedDashboardTs = Date.now();
    return response.data;
  } catch (error) {
    // Build a plain object for logging; Axios Error properties are non-enumerable
    const serializedError = typeof error?.toJSON === 'function' ? error.toJSON() : null;

    // Try to sanitize headers if present
    const serializedHeaders = serializedError?.config?.headers;
    if (serializedHeaders && typeof serializedHeaders === 'object') {
      const safeHeaders = Object.fromEntries(
        Object.entries(serializedHeaders).map(([name, value]) => [
          name,
          ['authorization', 'cookie', 'proxy-authorization', 'x-api-key'].includes(name.toLowerCase()) ? '[REDACTED]' : value,
        ]),
      );
      serializedError.config = { ...serializedError.config, headers: safeHeaders };
    }

    const errorDetails = {
      message: error?.message || serializedError?.message || 'Unknown request error',
      status: error?.response?.status ?? serializedError?.status,
      statusText: error?.response?.statusText,
      data: error?.response?.data,
      code: error?.code,
      method: error?.config?.method,
      url: error?.config?.url,
    };

    console.error('getDashboardStats error:', errorDetails);
    if (serializedError) console.debug('getDashboardStats Axios error:', serializedError);

    // Notify the app that a network issue occurred (non-fatal)
    if (!error?.response) {
      try {
        notifyNetworkIssue({ endpoint: '/api/interview/dashboard-stats', message: error?.message });
      } catch (e) {
        // ignore
      }
    }

    // Handle rate limiting explicitly: return cached or a rate-limited fallback
    if (error?.response?.status === 429) {
      console.warn('Dashboard stats rate-limited by backend. Serving cached or rate_limited fallback.');
      if (_cachedDashboardStats) return _cachedDashboardStats;
      return { fallback: true, rate_limited: true, stats: { interviews_completed: 0, average_score: 0, confidence_score: 0 }, recent_interviews: [] };
    }

    if (!error?.response) {
      console.warn('Dashboard stats API unavailable (network error), using guest fallback payload.', error?.message || error);
      return {
        fallback: true,
        stats: {
          interviews_completed: 18,
          average_score: 82,
          confidence_score: 88,
        },
        recent_interviews: [
          { role: 'Software Engineer', score: 88, date: '2026-08-01', confidence: 90 },
          { role: 'Product Manager', score: 79, date: '2026-07-29', confidence: 85 },
          { role: 'Data Analyst', score: 91, date: '2026-07-24', confidence: 92 },
          { role: 'UX Designer', score: 75, date: '2026-07-20', confidence: 80 },
          { role: 'DevOps Engineer', score: 85, date: '2026-07-15', confidence: 88 },
        ],
      };
    }

    if (error.response?.status >= 500) {
      console.warn('Dashboard stats API returned 5xx error, using guest fallback payload.');
      return {
        fallback: true,
        stats: {
          interviews_completed: 18,
          average_score: 82,
          confidence_score: 88,
        },
        recent_interviews: [
          { role: 'Software Engineer', score: 88, date: '2026-08-01', confidence: 90 },
          { role: 'Product Manager', score: 79, date: '2026-07-29', confidence: 85 },
          { role: 'Data Analyst', score: 91, date: '2026-07-24', confidence: 92 },
          { role: 'UX Designer', score: 75, date: '2026-07-20', confidence: 80 },
          { role: 'DevOps Engineer', score: 85, date: '2026-07-15', confidence: 88 },
        ],
      };
    }

    throw error;
  }
};

export const uploadResume = async (formData) => {
  const response = await api.post('/api/resume/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getResumeAnalysis = async (resumeId) => {
  if (typeof resumeId !== 'string' || !resumeId.trim()) {
    throw invalidResumeIdError(resumeId);
  }

  const endpoint = `/api/resume/analysis/${encodeURIComponent(resumeId.trim())}`;
  try {
    const response = await api.get(endpoint, { timeout: REQUEST_TIMEOUTS.resumeAnalysis });
    return response.data;
  } catch (error) {
    logApiError(endpoint, error);
    throw error;
  }
};

export const getResumeHistory = async () => {
  try {
    const response = await api.get('/api/resume/history', {
      timeout: REQUEST_TIMEOUTS.resumeHistory,
    });
    return response.data;
  } catch (error) {
    logApiError('/api/resume/history', error);
    try {
      if (!error?.response) notifyNetworkIssue({ endpoint: '/api/resume/history', message: error?.message });
    } catch (e) {
      // ignore
    }
    throw error;
  }
};

// Client-side master codes for offline activation. These mirror backend
// fallback master_coupons.json entries and allow the UI to enable unlimited
// subscription locally when the user provides a known master code while
// offline. Entries here must match the backend for security when online.
const MASTER_CODES = {
  'MASTER-BASIC-E8E588F630E6E93F': { grant_unlimited: true, grant_tier: 'basic' },
  'MASTER-PRO-16BAEA3245C7D44A': { grant_unlimited: true, grant_tier: 'pro' },
};

export function applyMasterCode(code) {
  if (typeof window === 'undefined' || !code) return false;
  const norm = String(code).trim().toUpperCase();
  const info = MASTER_CODES[norm];
  if (!info) return false;

  try {
    const accountEmail = window.localStorage.getItem('auth_email') || '__authenticated__';
    const subscription = {
      tier: info.grant_tier || 'basic',
      status: 'active',
      interviews_used_this_month: 0,
      interviews_remaining: 'unlimited',
      monthly_limit: 'unlimited',
      features: [],
      subscription_start_date: new Date().toISOString(),
      subscription_end_date: null,
      activated_via_master: true,
    };
    const payload = {
      accountEmail,
      data: subscription,
      timestamp: Date.now(),
    };
    window.localStorage.setItem('subscription_data', JSON.stringify(payload));
    // Notify other parts of the app to re-read subscription cache
    try { window.dispatchEvent(new CustomEvent('app:master-code-applied', { detail: { code: norm, info } })); } catch (e) { window.dispatchEvent(new Event('app:master-code-applied')); }
    return true;
  } catch (e) {
    return false;
  }
}


// Subscription API functions
export const getSubscriptionStatus = async () => {
  const cacheKey = getCacheKey('GET', '/api/subscription/status');
  const cached = getCachedData(cacheKey);

  // Stale-while-revalidate: return cached data immediately if present,
  // and refresh the cache in the background so subsequent calls get fresh data.
  if (cached) {
    // Kick off background revalidation but do not await it here.
    (async () => {
      try {
        const resp = await api.get('/api/subscription/status', { timeout: REQUEST_TIMEOUTS.subscriptionStatus });
        setCachedData(cacheKey, resp.data, CACHE_TTL.default);
      } catch (err) {
        // Only log; preserve current cached value for callers.
        logApiError('/api/subscription/status (revalidate)', err);
      }
    })();

    return cached;
  }

  // No cached value: fetch normally and cache result for a short duration
  try {
    const response = await api.get('/api/subscription/status', {
      timeout: REQUEST_TIMEOUTS.subscriptionStatus,
    });
    try { setCachedData(cacheKey, response.data, CACHE_TTL.default); } catch (e) { /* ignore cache write failures */ }
    return response.data;
  } catch (error) {
    logApiError('/api/subscription/status', error);
    throw error;
  }
};

export const createRazorpayOrder = async (data) => {
  try {
    const response = await api.post('/api/subscription/create-order', data, {
      timeout: REQUEST_TIMEOUTS.createOrder,
    });
    return response.data;
  } catch (error) {
    const status = error?.response?.status;
    const respData = error?.response?.data;

    // Provide specific context for Gateway errors
    if (status === 502) {
      console.error('?? 502 Bad Gateway Error: The upstream Python backend (Werkzeug) crashed or timed out.');
      console.error('Backend may have encountered an unhandled exception. Check backend logs and .env configuration.');
      console.error('Common causes: Missing Razorpay credentials, API key issues, or MongoDB connection problems.');
    }

    // Log structured error data for debugging
    logApiError('/api/subscription/create-order', error);

    const serverMsg = respData?.error || respData?.message || error?.message || 'Unknown error creating Razorpay order';
    const out = new Error(serverMsg);
    out.status = status;
    out.response = error?.response;
    throw out;
  }
};

export const verifyRazorpayPayment = async (data) => {
  const response = await api.post('/api/subscription/verify-payment', data);
  return response.data;
};

export const cancelSubscription = async () => {
  const response = await api.post('/api/subscription/cancel');
  return response.data;
};

export const reactivateSubscription = async () => {
  const response = await api.post('/api/subscription/reactivate');
  return response.data;
};

export const createCustomerPortal = async () => {
  const response = await api.post('/api/subscription/portal');
  return response.data;
};

// Enhanced subscription API functions
export const getUsageStats = async () => {
  const response = await api.get('/api/subscription/usage-stats');
  return response.data;
};

export const getBillingHistory = async (limit = 50) => {
  const response = await api.get(`/api/subscription/billing-history?limit=${limit}`);
  return response.data;
};

export const upgradeSubscription = async (data) => {
  const response = await api.post('/api/subscription/upgrade', data);
  return response.data;
};

export const startTrial = async (tier = 'pro', trialDays = 7) => {
  const response = await api.post('/api/subscription/trial/start', {
    tier,
    trial_days: trialDays,
  });
  return response.data;
};

export const getAvailableFeatures = async () => {
  const response = await api.get('/api/subscription/features');
  return response.data;
};

export const validateCoupon = async (coupon_code) => {
  try {
    const response = await api.post('/api/subscription/validate-coupon', { coupon_code });
    return response.data;
  } catch (error) {
    const status = error?.response?.status;
    const respData = error?.response?.data;
    const serverMsg = respData?.error || error?.message || 'Failed to validate coupon';
    const out = new Error(serverMsg);
    out.status = status;
    out.response = error?.response;
    throw out;
  }
};

export const hasFeatureAccess = async (featureName) => {
  const response = await api.get(`/api/subscription/has-feature/${featureName}`);
  return response.data.has_access;
};

// Interview API functions - use server-side LLM proxy at /api/interview
export const generateInterviewQuestions = async (role, category, difficulty, num_questions = 3) => {
  try {
    // Build a clear instruction prompt and pass structured params. The server-side proxy
    // will forward this to the configured LLM (DeepSeek) using server env vars.
    const prompt = `Generate ${num_questions} interview questions` +
      (category ? ` in the category '${category}'` : '') +
      (difficulty ? ` with difficulty '${difficulty}'` : '') +
      (role ? ` for the role '${role}'.` : '.') +
      ` For each question include a short expected answer sketch.`;

    const response = await api.post('/api/interview', {
      action: 'generate_questions',
      prompt,
      params: { role, category, difficulty, num_questions },
    }, { timeout: REQUEST_TIMEOUTS.interviewQuestions });

    return response.data;
  } catch (error) {
    logApiError('/api/interview (generate_questions)', error);
    const message = error.response?.data?.error || error.message || 'Failed to generate questions';
    throw new Error(message);
  }
};

export const generateFeedback = async (role, qaPairs) => {
  try {
    // Provide instruction plus structured data. Keep payload concise to avoid
    // very large JSON bodies � server proxy will forward params to the LLM.
    const prompt = `You are an expert interview coach. Provide concise feedback for each question-answer pair and an overall summary for the role '${role || 'candidate'}'.`;

    const response = await api.post('/api/interview', {
      action: 'analyze_qa_pairs',
      prompt,
      params: { role, qaPairs },
    }, { timeout: REQUEST_TIMEOUTS.interviewAnalysis });

    return response.data;
  } catch (error) {
    logApiError('/api/interview (analyze_qa_pairs)', error);
    const message = error.response?.data?.error || error.message || 'Failed to generate feedback';
    throw new Error(message);
  }
};

// New subscription features API
export const getQuestionCategories = async () => {
  const cacheKey = getCacheKey('GET', '/api/subscription/question-categories');
  const cached = getCachedData(cacheKey);
  if (cached) return cached;

  try {
    const response = await api.get('/api/subscription/question-categories', {
      timeout: REQUEST_TIMEOUTS.questionCategories,
    });
    setCachedData(cacheKey, response.data, CACHE_TTL.questionCategories);
    return response.data;
  } catch (error) {
    // Always return safe fallback for question categories to prevent app from crashing
    try {
      const status = error?.response?.status;
      const isNetworkError = !error?.response;
      console.warn(`[getQuestionCategories] API failed (network=${isNetworkError}, status=${status}), using fallback`);
      logApiError('/api/subscription/question-categories', error);
    } catch (logError) {
      console.debug('[getQuestionCategories] Could not log error details:', logError);
    }
    
    // Return the same safe defaults the backend returns on error
    return {
      available_categories: ['technical', 'behavioral'],
      tier: 'free',
      interviews_remaining: 0,
      monthly_limit: 3,
      all_categories_available: false,
      fallback: true
    };
  }
};

export const getAdvancedAnalytics = async () => {
  const cacheKey = getCacheKey('GET', '/api/subscription/analytics');
  const cached = getCachedData(cacheKey);
  if (cached) return cached;

  const response = await api.get('/api/subscription/analytics');
  setCachedData(cacheKey, response.data, CACHE_TTL.features);
  return response.data;
};

export const submitEmailSupport = async (subject, message) => {
  const response = await api.post('/api/subscription/email-support', {
    subject,
    message,
  });
  return response.data;
};

export const getPlanComparison = async () => {
  const cacheKey = getCacheKey('GET', '/api/subscription/plan-comparison');
  const cached = getCachedData(cacheKey);
  if (cached) return cached;

  const response = await api.get('/api/subscription/plan-comparison');
  setCachedData(cacheKey, response.data, CACHE_TTL.features);
  return response.data;
};

export const getFeedbackHistoryLimit = async () => {
  const cacheKey = getCacheKey('GET', '/api/subscription/feedback-history-limit');
  const cached = getCachedData(cacheKey);
  if (cached) return cached;

  const response = await api.get('/api/subscription/feedback-history-limit');
  setCachedData(cacheKey, response.data, CACHE_TTL.features);
  return response.data;
};


