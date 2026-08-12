import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '',
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
  const response = await api.post('/api/interview/generate-questions', params);
  return response.data;
};

export const submitAnswer = async (data) => {
  const response = await api.post('/api/interview/analyze-answer', data);
  return response.data;
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
  const response = await api.get(`/api/interview/dashboard-stats?t=${timestamp}`);
  return response.data;
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
  const response = await api.get(`/api/resume/analysis/${resumeId}`);
  return response.data;
};

export const getResumeHistory = async () => {
  try {
    const response = await api.get('/api/resume/history');
    return response.data;
  } catch (error) {
    if (error.response) {
      console.error('Resume history API error:', {
        status: error.response.status,
        data: error.response.data,
      });
    } else if (error.request) {
      console.error('No response received for resume history request:', error.request);
    } else {
      console.error('Resume history request setup failed:', error.message);
    }
    throw error;
  }
};

// Subscription API functions
export const getSubscriptionStatus = async () => {
  const response = await api.get('/api/subscription/status');
  return response.data;
};

export const createRazorpayOrder = async (data) => {
  try {
    const response = await api.post('/api/subscription/create-order', data);
    return response.data;
  } catch (error) {
    try {
      console.error('createRazorpayOrder full error:', error);
    } catch (logErr) {
      // Swallow logging errors
    }

    const status = error?.response?.status;
    const respData = error?.response?.data;

    console.error('createRazorpayOrder API error summary:', { status, data: respData });

    const serverMsg = respData?.error || respData?.message || error?.message || 'Unknown error creating Razorpay order';
    const out = new Error(serverMsg);
    out.status = status;
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
