import axios from 'axios';

const api = axios.create({
  baseURL: '', // Use relative path for Next.js proxy
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
  const response = await api.get('/api/resume/history');
  return response.data;
};

// Subscription API functions
export const getSubscriptionStatus = async () => {
  const response = await api.get('/api/subscription/status');
  return response.data;
};

export const createCheckoutSession = async (data) => {
  const response = await api.post('/api/subscription/create-checkout-session', data);
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
