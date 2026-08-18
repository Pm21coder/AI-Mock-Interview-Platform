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
  // Keep browser requests same-origin. Next.js rewrites /api/* to the backend
  // using NEXT_PUBLIC_API_URL, so this works for local development and
  // deployments without exposing the browser to CORS origin differences.
  baseURL: '',
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

// Helper to create a job and poll for completion
// Detect Redis-required 503 responses and provide a typed error
function isRedisRequiredError(err) {
  try {
    if (!err || !err.response) return false;
    if (err.response.status !== 503) return false;
    const msg = err.response.data?.error || err.response.data?.message || '';
    return /redis/i.test(msg) || /required in production/i.test(msg) || /set REDIS_URL/i.test(msg);
  } catch (e) {
    return false;
  }
}

function parseRedisRequiredMessage(err) {
  if (!err || !err.response) return null;
  return err.response.data?.error || err.response.data?.message || null;
}

async function createJobAndPoll(jobEndpoint, pollEndpointBase, payload, totalTimeout = REQUEST_TIMEOUTS.interviewQuestions, options = {}) {
  // Deduplicate identical concurrent job requests to avoid duplicate work
  // keying by endpoint + payload JSON. Return the existing promise if one exists.
  if (!createJobAndPoll._activeRequests) createJobAndPoll._activeRequests = new Map();
  const dedupeKey = `${jobEndpoint}:${JSON.stringify(payload || {})}`;
  if (createJobAndPoll._activeRequests.has(dedupeKey)) {
    return createJobAndPoll._activeRequests.get(dedupeKey);
  }

  const controller = options.signal ? null : new AbortController();
  const signal = options.signal || (controller ? controller.signal : undefined);

  const promise = (async () => {
    // Allow 202 responses without throwing. Wrap create in try/catch so 503 responses
    // can be detected and surfaced to the UI as a special actionable error.
    let createResp;

    // Storage key to persist last job for this endpoint (helps resume after reload)
    const storageKey = `last_job:${jobEndpoint}`;
    const shouldPersist = options.persist !== false;
    const resumeFromStorage = options.resumeFromStorage !== false; // default true

    // Nested helper: poll loop encapsulated so it can be reused for resumes
    const pollLoop = async (jobId) => {
      const start = Date.now();
      let interval = typeof options.pollIntervalBase === 'number' ? options.pollIntervalBase : 1000;
      const maxInterval = typeof options.pollIntervalMax === 'number' ? options.pollIntervalMax : 2000;
      const maxDuration = Math.min(totalTimeout, options.maxPollDuration || 180_000);

      while (Date.now() - start < maxDuration) {
        try {
          if (signal && signal.aborted) {
            const cancelErr = new Error('Request canceled');
            cancelErr.name = 'AbortError';
            throw cancelErr;
          }

          const remaining = Math.max(1000, maxDuration - (Date.now() - start));
          const statusResp = await api.get(`${pollEndpointBase}/${jobId}`, { timeout: Math.min(10_000, remaining), validateStatus: (s) => s < 500, signal });
          const data = statusResp.data || {};
          const status = data.status;
          if (status === 'completed') {
            // Remove persisted marker
            try { if (shouldPersist && typeof window !== 'undefined') window.localStorage.removeItem(storageKey); } catch (e) {}
            return data.result || data;
          }
          if (status === 'failed') {
            try { if (shouldPersist && typeof window !== 'undefined') window.localStorage.removeItem(storageKey); } catch (e) {}
            throw new Error(data.error || 'Job failed');
          }
        } catch (pollErr) {
          if (pollErr && (pollErr.name === 'AbortError' || pollErr.code === 'ERR_CANCELED')) {
            throw pollErr;
          }

          // Detect socket-level resets / proxy hangups during polling and escalate
          try {
            const pm = String(pollErr?.message || '').toLowerCase();
            if (pollErr && (pollErr.code === 'ECONNRESET' || pm.includes('socket hang up') || pm.includes('connection reset'))) {
              const out = new Error(`Socket hang up / connection reset while polling job ${jobId}`);
              out.isSocketHangUp = true;
              out.jobId = jobId;
              out.original = pollErr;
              logApiError(`${pollEndpointBase}/${jobId}`, out);
              throw out;
            }
          } catch (e) {
            // ignore detection errors
          }

          console.warn('Poll error for job', jobId, pollErr?.message || pollErr);
        }
        await new Promise((res) => setTimeout(res, interval));
        interval = Math.min(interval * 2, maxInterval);
      }
      throw new Error(`Job polling timed out for job ${jobId}`);
    };

    // If a previous job for this endpoint was persisted, attempt to resume polling it
    try {
      if (resumeFromStorage && typeof window !== 'undefined' && shouldPersist) {
        const raw = window.localStorage.getItem(storageKey);
        if (raw) {
          try {
            const saved = JSON.parse(raw);
            if (saved && saved.jobId) {
              // Try to poll the saved job id before creating a new job
              try {
                const resumed = await pollLoop(saved.jobId);
                return resumed;
              } catch (resumeErr) {
                // If resume fails, remove persisted marker and continue to create a new job
                try { window.localStorage.removeItem(storageKey); } catch (e) {}
                console.warn('Resuming persisted job failed, creating a new job', resumeErr);
              }
            }
          } catch (e) {
            // malformed storage; remove it
            try { window.localStorage.removeItem(storageKey); } catch (e2) {}
          }
        }
      }
    } catch (e) {
      // Non-fatal; continue to create a new job
    }

    try {
      createResp = await api.post(jobEndpoint, payload, {
        timeout: Math.min(10_000, totalTimeout),
        validateStatus: (status) => status < 500,
        signal,
      });
    } catch (err) {
      // If aborted by caller, propagate cancellation
      if (err && (err.name === 'CanceledError' || err.code === 'ERR_CANCELED' || err.message === 'canceled')) {
        const cancelErr = new Error('Request canceled');
        cancelErr.name = 'AbortError';
        throw cancelErr;
      }

      // Detect socket-level resets / proxy hangups and mark them so callers
      // can choose an immediate fallback flow instead of retrying the job.
      try {
        const msg = String(err?.message || '').toLowerCase();
        if (err && (err.code === 'ECONNRESET' || msg.includes('socket hang up') || msg.includes('connection reset'))) {
          const out = new Error('Socket hang up / connection reset when contacting job endpoint');
          out.isSocketHangUp = true;
          out.original = err;
          logApiError(jobEndpoint, out);
          throw out;
        }
      } catch (e) {
        // ignore detection errors
      }

      // If the backend explicitly returned 503 with a Redis-required message,
      // attach a flag so the UI can show an actionable admin banner.
      if (isRedisRequiredError(err)) {
        logApiError(jobEndpoint, err);
        const msg = parseRedisRequiredMessage(err) || 'Server requires Redis to process jobs. Set REDIS_URL and run a worker.';
        const out = new Error(msg);
        out.isRedisRequired = true;
        out.status = 503;
        throw out;
      }

      // Re-throw other errors so callers can handle timeouts / network issues
      throw err;
    }

    if (createResp.status === 202 && createResp.data?.job_id) {
      const jobId = createResp.data.job_id;

      // Persist job id so polling can resume after reloads/crashes
      try {
        if (shouldPersist && typeof window !== 'undefined') {
          const payloadToStore = { jobId, endpoint: pollEndpointBase, createdAt: Date.now() };
          window.localStorage.setItem(storageKey, JSON.stringify(payloadToStore));
        }
      } catch (e) {
        // ignore storage errors
      }

      // Poll the job using shared loop
      return await pollLoop(jobId);
    }

    // If server returned 200 with immediate result, return it
    if (createResp.status === 200) return createResp.data;

    throw new Error('Failed to create job');
  })();

  // Store the promise to dedupe identical concurrent requests
  createJobAndPoll._activeRequests.set(dedupeKey, promise);

  // Ensure cleanup when promise settles
  const cleanup = () => createJobAndPoll._activeRequests.delete(dedupeKey);
  promise.then(cleanup).catch(cleanup);

  return promise;
}

export const getQuestions = async (params, options = {}) => {
  try {
    // Prefer job-based generation to avoid HTTP timeouts for long LLM calls
    const result = await createJobAndPoll('/api/interview/generate-questions-job', '/api/interview/job', params, REQUEST_TIMEOUTS.interviewQuestions, { signal: options.signal });
    // Normalize result shape if needed
    if (result && result.questions) return result;
    return result;
  } catch (error) {
    logApiError('/api/interview/generate-questions-job', error);

    // Fall back to the original synchronous endpoint with a retry policy.
    // Also support the endpoint returning a 202 + job_id (async) by polling it.
    const maxAttempts = 2;
    let attempt = 0;
    let lastError = null;
    let timeout = REQUEST_TIMEOUTS.interviewQuestions;

    while (attempt < maxAttempts) {
      // Create per-attempt forwarding so a previously-aborted controller
      // doesn't cancel subsequent fallback attempts immediately.
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

        const response = await api.post('/api/interview/generate-questions', params, { timeout, validateStatus: (s) => s < 500, signal: signalForAttempt });

        // If server accepted as an async job, delegate to the job poller
        if (response.status === 202 && response.data?.job_id) {
          const jobId = response.data.job_id;
          // Poll the existing job id until completion
          const start = Date.now();
          let interval = 1000;
          const maxInterval = 2000;
          const maxDuration = Math.min(REQUEST_TIMEOUTS.interviewQuestions, 60_000);
          while (Date.now() - start < maxDuration) {
            try {
              const statusResp = await api.get(`/api/interview/job/${jobId}`, { timeout: Math.min(10_000, maxDuration), validateStatus: (s) => s < 500, signal: options.signal });
              const d = statusResp.data || {};
              if (d.status === 'completed') return d.result;
              if (d.status === 'failed') throw new Error(d.error || 'Job failed');
            } catch (pollErr) {
              console.warn('Poll error for job', jobId, pollErr?.message || pollErr);
            }
            await new Promise((res) => setTimeout(res, interval));
            interval = Math.min(interval * 2, maxInterval);
          }
          throw new Error('Job polling timed out');
        }
        // Otherwise, expect synchronous result
        if (response.status === 200) return response.data;
        lastError = new Error('Unexpected response from generate-questions');
        break;
      } catch (err) {
        lastError = err;
        const isTimeout = err?.code === 'ECONNABORTED' || err?.message?.toLowerCase?.().includes('timeout');
        if (isTimeout) {
          attempt += 1;
          console.warn(`getQuestions attempt ${attempt} timed out (timeout=${timeout}ms).`);
          if (attempt < maxAttempts) {
            const backoffMs = 1000 * Math.pow(2, attempt - 1);
            await new Promise((res) => setTimeout(res, backoffMs));
            timeout = Math.min(timeout * 2, 180_000); // cap at 3 minutes
            continue;
          }
          console.error('getQuestions API timeout after retry:', err?.message || err);
        } else {
          logApiError('/api/interview/generate-questions', err);
          break;
        }
      } finally {
        // Cleanup the forwarded abort listener to avoid leaking handlers across attempts.
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
    logApiError('/api/interview/generate-questions', err || new Error('Unknown error'));

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
      const count = Math.min(Math.max(1, requested), 10); // clamp between 1 and 10
      return {
        session_id: `local_fallback_${Date.now()}`,
        questions: fallbackQuestions.slice(0, count),
        fallback: true,
      };
    }

    throw err;
  }
};

export const submitAnswer = async (data, options = {}) => {
  // Use synchronous analysis endpoint directly (no Redis/RQ or polling).
  // Implement small retry/backoff to handle transient provider/backend issues.
  const maxAttempts = 2;
  let attempt = 0;
  let lastError = null;
  let timeout = REQUEST_TIMEOUTS.interviewAnalysis * 2; // generous timeout for provider calls

  while (attempt < maxAttempts) {
    attempt += 1;
    try {
      const response = await api.post('/api/interview/analyze-answer', data, {
        timeout,
        validateStatus: (s) => s < 500,
        signal: options.signal,
      });

      // Expect 200 with analysis result. If server returns 202 with job_id, the
      // backend still intends async processing; treat that as an error because
      // we're removing job/polling from the client. Surface a clear message.
      if (response.status === 200) return response.data;
      if (response.status === 202 && response.data?.job_id) {
        // Server is returning job-based flow; log it and return a helpful error
        const out = new Error('Server returned job-based response but client is configured for synchronous analysis. Configure server for direct analysis or enable background workers.');
        out.status = 202;
        out.job_id = response.data.job_id;
        throw out;
      }

      lastError = new Error('Unexpected response from analyze-answer');
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
      logApiError('/api/interview/analyze-answer', err);

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
  logApiError('/api/interview/analyze-answer', lastError || new Error('Unknown error'));
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

// In-memory cache for dashboard stats to avoid rapid-fire requests (429)
let _cachedDashboardStats = null;
let _cachedDashboardTs = 0;
const DASHBOARD_CACHE_TTL = 30_000; // 30 seconds

export const getDashboardStats = async (options = { forceRefresh: false }) => {
  try {
    const now = Date.now();
    if (!options?.forceRefresh && _cachedDashboardStats && (now - _cachedDashboardTs) < DASHBOARD_CACHE_TTL) {
      // Return cached payload to avoid hammering the backend (helps avoid 429)
      return _cachedDashboardStats;
    }

    // Fetch fresh data from the backend (no automatic timestamp param)
    // Retry once with a short timeout to avoid long blocking delays in the UI.
    const attemptTimeouts = [8000, REQUEST_TIMEOUTS.dashboardStats];
    let lastFetchError = null;
    let response = null;
    for (let i = 0; i < attemptTimeouts.length; i++) {
      try {
        response = await api.get('/api/interview/dashboard-stats', { timeout: attemptTimeouts[i] });
        break; // success
      } catch (err) {
        lastFetchError = err;
        const isTimeout = err?.code === 'ECONNABORTED' || (err?.message || '').toLowerCase().includes('timeout');
        console.warn(`getDashboardStats attempt ${i + 1} failed (timeout=${attemptTimeouts[i]}ms):`, isTimeout ? 'timeout' : err?.message || err);
        // brief backoff before retrying
        if (i < attemptTimeouts.length - 1) await new Promise((res) => setTimeout(res, 500 * Math.pow(2, i)));
      }
    }

    if (!response) {
      // No successful response after retries — surface the last error into the existing catch handling
      throw lastFetchError || new Error('Failed to fetch dashboard stats');
    }

    _cachedDashboardStats = response.data;
    _cachedDashboardTs = Date.now();
    return response.data;
  } catch (error) {
    // The backend may be temporarily offline during local startup or if the
    // API container is unavailable. Fall back to the same guest dashboard data
    // used by the server so the dashboard continues to render instead of
    // surfacing a raw Axios "Network Error" in the browser console.
    // Axios Error properties are non-enumerable, which TurboPack can render
    // as `{}`. Build a plain object and preserve Axios' diagnostic payload so
    // response and network failures remain distinguishable in DevTools.
    const serializedError = typeof error?.toJSON === 'function'
      ? error.toJSON()
      : null;
    const serializedHeaders = serializedError?.config?.headers;
    if (serializedHeaders && typeof serializedHeaders === 'object') {
      const safeHeaders = Object.fromEntries(
        Object.entries(serializedHeaders).map(([name, value]) => [
          name,
          ['authorization', 'cookie', 'proxy-authorization', 'x-api-key'].includes(name.toLowerCase())
            ? '[REDACTED]'
            : value,
        ]),
      );
      serializedError.config = {
        ...serializedError.config,
        headers: safeHeaders,
      };
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

    // TurboPack and some devtools may show Error objects as "{}" because
    // properties are non-enumerable. Stringify the plain object so the
    // diagnostic is visible in all consoles (and avoid leaking auth headers).
    try {
      console.error('getDashboardStats error:', JSON.stringify(errorDetails, null, 2));
    } catch (e) {
      // Fallback to raw object if stringification fails for any reason.
      console.error('getDashboardStats error (unserializable):', errorDetails);
    }

    if (serializedError) {
      try {
        console.debug('getDashboardStats Axios error:', JSON.stringify(serializedError, null, 2));
      } catch (e) {
        console.debug('getDashboardStats Axios error (unserializable):', serializedError);
      }
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
    
    // If we get a 5xx error, also return fallback to prevent dashboard from breaking
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
    throw error;
  }
};

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
      console.error('🔴 502 Bad Gateway Error: The upstream Python backend (Werkzeug) crashed or timed out.');
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

export const hasFeatureAccess = async (featureName) => {
  const response = await api.get(`/api/subscription/has-feature/${featureName}`);
  return response.data.has_access;
};

// Gemini-powered interview API functions (via Next.js API routes)
export const generateInterviewQuestions = async (role, category, difficulty) => {
  try {
    const response = await axios.post('/api/interview/questions', {
      role,
      category,
      difficulty,
    });
    return response.data;
  } catch (error) {
    const message = error.response?.data?.error || error.message || 'Failed to generate questions';
    throw new Error(message);
  }
};

export const generateFeedback = async (role, qaPairs) => {
  try {
    const response = await axios.post('/api/interview/feedback', {
      role,
      qaPairs,
    });
    return response.data;
  } catch (error) {
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

export { isRedisRequiredError, parseRedisRequiredMessage };

