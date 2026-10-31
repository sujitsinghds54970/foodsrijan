import axios, { AxiosHeaders } from 'axios';
import toast from 'react-hot-toast';

const API_BASE = 'http://127.0.0.1:8000';

export const api = axios.create({ baseURL: API_BASE });

const AUTH_STORAGE_KEYS = [
  'token',
  'user',
  'workspace.companyId',
  'workspace.brandId',
  'workspace.companies',
  'workspace.brands',
];

let sessionExpiryHandled = false;

/**
 * Every API module in the app shares this `api` instance, but it is a
 * separate axios instance from the global `axios` object that
 * AuthContext attaches its own 401 interceptor to. Without this,
 * a revoked/expired token surfaces here as a raw error (e.g. "Session
 * has been signed out") instead of redirecting the user to a fresh
 * login - guard against that once per session.
 */
const handleSessionExpired = () => {
  if (sessionExpiryHandled || typeof window === 'undefined') return;
  sessionExpiryHandled = true;

  AUTH_STORAGE_KEYS.forEach((key) => window.localStorage.removeItem(key));
  delete axios.defaults.headers.common['Authorization'];
  window.dispatchEvent(new CustomEvent('workspace:user-updated', { detail: null }));
  toast.error('Session expired. Please login again.', { id: 'session-expired' });

  if (window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
};

const readWorkspaceHeaders = () => {
  const workspaceHeaders: Record<string, string> = {};

  if (typeof window === 'undefined') return workspaceHeaders;

  const companyId = window.localStorage.getItem('workspace.companyId');
  const brandId = window.localStorage.getItem('workspace.brandId');

  if (companyId) workspaceHeaders['X-Company-ID'] = companyId;
  if (brandId) workspaceHeaders['X-Brand-ID'] = brandId;

  return workspaceHeaders;
};

api.interceptors.request.use((config) => {
  const headers = AxiosHeaders.from(config.headers ?? {});
  const workspaceHeaders = readWorkspaceHeaders();

  Object.entries(workspaceHeaders).forEach(([key, value]) => {
    if (value) {
      headers.set(key, value);
    }
  });

  const authToken = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;
  if (authToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }

  config.headers = headers;
  return config;
});

api.interceptors.response.use(
  (response) => {
    sessionExpiryHandled = false;
    return response;
  },
  (error) => {
    if (process.env.NODE_ENV === 'development') {
      const config = error.config;
      console.error('[API RESPONSE ERROR]', {
        status: error.response?.status ?? null,
        method: config?.method?.toUpperCase(),
        url: config?.url ?? null,
        fullUrl: config ? `${config.baseURL || ''}${config.url || ''}` : null,
        data: error.response?.data ?? null,
        message: error.message,
      });
    }

    const isLoginEndpoint = error.config?.url?.includes('/api/auth/login');
    if (error.response?.status === 401 && !isLoginEndpoint) {
      handleSessionExpired();
    }

    return Promise.reject(error);
  },
);

export default api;
