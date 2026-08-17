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
  resumeAnalysis: 10_000,
  resumeHistory: 10_000,
  subscriptionStatus: 8_000,
  questionCategories: 8_000,
  createOrder: 15_000,
  // Allow longer AI generation time in environments with higher server limits.
  // Increase to 120s for question generation which can be expensive.
  interviewQuestions: 120_000,
  // Client-side timeout for answer analysis. Allow up to 120s for complex analysis.
  interviewAnalysis: 120_000,
};

function responseBodyForLog(error) {
  if (!error?.response) return 'No response received from the server';

  const body = error.response.data;
  if (body == null || (typeof body === 'object' && Object.keys(body).length === 0)) {
    return 'Empty server response body';
  }
  return body;
}

function logApiError(endpoint, error) {
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
    console.error(`API error at ${endpoint}: ${JSON.stringify(out, null, 2)}`);
    // Also emit a debug-level object for richer inspection when supported
    console.debug('API error (debug):', out);
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
async function createJobAndPoll(jobEndpoint, pollEndpointBase, payload, totalTimeout = REQUEST_TIMEOUTS.interviewQuestions) {
  // Allow 202 responses without throwing
  const createResp = await api.post(jobEndpoint, payload, {
    timeout: Math.min(10_000, totalTimeout),
    validateStatus: (status) => status < 500,
  });

  if (createResp.status === 202 && createResp.data?.job_id) {
    const jobId = createResp.data.job_id;
    const start = Date.now();
    let interval = 1000; // 1s initial
    while (Date.now() - start < totalTimeout) {
      try {
        const statusResp = await api.get(`${pollEndpointBase}/${jobId}`, { timeout: Math.min(10_000, totalTimeout), validateStatus: (s) => s < 500 });
        if (statusResp.data?.status === 'completed') {
          return statusResp.data.result;
        }
        if (statusResp.data?.status === 'failed') {
          throw new Error(statusResp.data?.error || 'Job failed');
        }
      } catch (pollErr) {
        // Ignore transient poll errors but log for visibility
        console.warn('Poll error for job', jobId, pollErr?.message || pollErr);
      }
      // Wait before next poll (exponential backoff)
      await new Promise((res) => setTimeout(res, interval));
      interval = Math.min(interval * 2, 10_000); // cap 10s
    }

    throw new Error('Job polling timed out');
  }

  // If server returned 200 with immediate result, return it
  if (createResp.status === 200) return createResp.data;

  throw new Error('Failed to create job');
}

export const getQuestions = async (params) => {
  try {
    // Prefer job-based generation to avoid HTTP timeouts for long LLM calls
    const result = await createJobAndPoll('/api/interview/generate-questions-job', '/api/interview/job', params, REQUEST_TIMEOUTS.interviewQuestions);
    // Normalize result shape if needed
    if (result && result.questions) return result;
    return result;
  } catch (error) {
    logApiError('/api/interview/generate-questions-job', error);

    // Fall back to the original synchronous endpoint with a retry policy
    const maxAttempts = 2;
    let attempt = 0;
    let lastError = null;
    let timeout = REQUEST_TIMEOUTS.interviewQuestions;

    while (attempt < maxAttempts) {
      try {
        const response = await api.post('/api/interview/generate-questions', params, { timeout });
        return response.data;
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

export const submitAnswer = async (data) => {
  const maxAttempts = 2;
  let attempt = 0;
  let lastError = null;
  let timeout = REQUEST_TIMEOUTS.interviewAnalysis;

  while (attempt < maxAttempts) {
    try {
      const response = await api.post('/api/interview/analyze-answer', data, { timeout });
      return response.data;
    } catch (error) {
      lastError = error;
      // If timeout, attempt an exponential backoff retry once with a longer timeout
      const isTimeout = error?.code === 'ECONNABORTED' || error?.message?.toLowerCase?.().includes('timeout');
      if (isTimeout) {
        attempt += 1;
        console.warn(`submitAnswer attempt ${attempt} timed out (timeout=${timeout}ms).`);
        if (attempt < maxAttempts) {
          // Wait with exponential backoff before retrying
          const backoffMs = 1000 * Math.pow(2, attempt - 1);
          await new Promise((res) => setTimeout(res, backoffMs));
          // Increase timeout for retry but cap at 120s
          timeout = Math.min(timeout * 2, 120_000);
          continue;
        }

        console.error('submitAnswer API timeout after retry:', error?.message || error);
        return {
          error: 'Analysis timed out',
          details: 'The analysis service is taking too long. Try again later or shorten the response.',
        };
      }

      // Non-timeout errors — break and handle below
      break;
    }
  }

  // If we reach here, handle the last non-timeout error similarly to previous behavior
  const error = lastError;
  let errorPayload = error?.response?.data;

  console.error('submitAnswer API error:', error);
  if (error?.response) {
    console.error('submitAnswer server response (raw):', errorPayload);
  }

  // If server returned a string payload, try to parse JSON out of it
  if (typeof errorPayload === 'string') {
    try {
      const parsed = JSON.parse(errorPayload);
      if (parsed && typeof parsed === 'object') {
        return parsed;
      }
    } catch (e) {
      // Not JSON — fall through and return a structured error
      return {
        error: 'Server error',
        details: errorPayload,
      };
    }
  }

  if (errorPayload && typeof errorPayload === 'object') {
    return errorPayload;
  }

  return {
    error: 'Failed to connect to analysis service',
    details: error?.message || 'Unable to reach the interview analysis service.',
  };
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
    const response = await api.get('/api/interview/dashboard-stats', {
      timeout: REQUEST_TIMEOUTS.questionCategories,
    });

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
    console.error('getDashboardStats error:', errorDetails);
    if (serializedError) {
      console.debug('getDashboardStats Axios error:', serializedError);
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
  try {
    const response = await api.get('/api/subscription/status', {
      timeout: REQUEST_TIMEOUTS.subscriptionStatus,
    });
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



