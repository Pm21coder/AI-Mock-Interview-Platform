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
  interviewQuestions: 45_000,
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
  console.error('API error:', {
    endpoint,
    status: error?.response?.status ?? null,
    statusText: error?.response?.statusText ?? null,
    data: responseBodyForLog(error),
    message: error?.message || 'Unknown request error',
  });
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
  timeout: 45_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = window.localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
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

export const getQuestions = async (params) => {
  const response = await api.post('/api/interview/generate-questions', params, {
    timeout: REQUEST_TIMEOUTS.interviewQuestions,
  });
  return response.data;
};

export const submitAnswer = async (data) => {
  try {
    const response = await api.post('/api/interview/analyze-answer', data);
    return response.data;
  } catch (error) {
    const errorPayload = error.response?.data;

    console.error('submitAnswer API error:', error);
    if (error.response) {
      console.error('submitAnswer server response:', errorPayload);
    }

    if (errorPayload && typeof errorPayload === 'object') {
      return errorPayload;
    }

    return {
      error: 'Failed to connect to analysis service',
      details: error.message || 'Unable to reach the interview analysis service.',
    };
  }
};

export const getFeedback = async (sessionId) => {
  const response = await api.get(`/api/interview/get-feedback/${sessionId}`);
  return response.data;
};

export const saveResponse = async (data) => {
  const response = await api.post('/api/interview/save-response', data);
  return response.data;
};

export const getDashboardStats = async () => {
  const timestamp = new Date().getTime(); // Cache-busting to ensure fresh data

  try {
    const response = await api.get(`/api/interview/dashboard-stats?t=${timestamp}`);
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
      console.error('ðŸ”´ 502 Bad Gateway Error: The upstream Python backend (Werkzeug) crashed or timed out.');
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

