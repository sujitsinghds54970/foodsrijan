import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import axios, { AxiosHeaders } from 'axios';
import toast from 'react-hot-toast';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  company_id?: number | null;
  current_company_id?: number | null;
  is_super_admin?: boolean;
  is_company_ceo?: boolean;
  companies?: Array<{
    id?: number;
    company_id?: number | null;
    name?: string;
    company_name?: string;
    slug?: string;
    is_active?: boolean;
  }>;
  companyLogo?: string | null;
  profilePhoto?: string | null;
  photo?: string | null;
  profile_photo?: string | null;
  photo_url?: string | null;
  branch_id?: number | null;
  branch?: {
    id?: number;
    name?: string;
    logo_url?: string | null;
  } | null;
  can_access_daily_ops?: boolean | null;
  first_name: string;
  last_name: string;
  phone?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  token: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

const API_BASE = 'http://127.0.0.1:8000';
console.log('[AUTH_DEBUG] API_BASE_FIXED', API_BASE);

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const lastNetworkToastAtRef = useRef(0);

  // Configure axios defaults and restore auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');
      let parsedStoredUser: User | null = null;

      if (storedUser) {
        try {
          parsedStoredUser = JSON.parse(storedUser);
          setUser(parsedStoredUser);
        } catch {
          localStorage.removeItem('user');
        }
      }

      if (storedToken) {
        setToken(storedToken);
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;

        if (!storedUser) {
          // Avoid replaying stale token-only sessions into a logout loop.
          localStorage.removeItem('token');
          delete axios.defaults.headers.common['Authorization'];
          setToken(null);
        } else {
          const needsHydration = !parsedStoredUser?.branch?.logo_url;
          if (needsHydration) {
            try {
              const meResponse = await axios.get(`${API_BASE}/api/auth/me`);
              const verifiedUser = meResponse.data;
              if (verifiedUser?.role) {
                const hydratedUser = { ...(parsedStoredUser || {}), ...verifiedUser };
                setUser(hydratedUser);
                localStorage.setItem('user', JSON.stringify(hydratedUser));
              }
            } catch (error) {
              console.error('[AUTH_DEBUG] Failed to hydrate stored user from /api/auth/me', error);
            }
          }
        }
      }

      setLoading(false);
    };

    initializeAuth();
  }, []);

  // Request/response interceptors for auth + network diagnostics
  useEffect(() => {
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        const fullUrl = `${config.baseURL || ''}${config.url || ''}`;

        try {
          const workspaceCompanyId = localStorage.getItem('workspace.companyId');
          const workspaceBrandId = localStorage.getItem('workspace.brandId');
          const headers = AxiosHeaders.from(config.headers ?? {});

          if (workspaceCompanyId) {
            headers.set('X-Company-ID', workspaceCompanyId);
          }
          if (workspaceBrandId) {
            headers.set('X-Brand-ID', workspaceBrandId);
          }
          config.headers = headers;
        } catch {
          // Ignore storage access issues during server-side or stale contexts.
        }

        console.info('[API REQUEST]', {
          method: config.method,
          baseURL: config.baseURL || API_BASE,
          url: config.url,
          fullUrl,
        });
        return config;
      },
      (error) => Promise.reject(error)
    );

    const responseInterceptor = axios.interceptors.response.use(
      (response) => {
        lastNetworkToastAtRef.current = 0;
        return response;
      },
      (error) => {
        const config = error?.config || {};
        const fullUrl = `${config.baseURL || ''}${config.url || ''}`;

        if (!error.response) {
          console.error('[API NETWORK ERROR]', {
            baseURL: config.baseURL || API_BASE,
            url: config.url,
            fullUrl,
            message: error?.message,
            stack: error?.stack,
          });
          const now = Date.now();
          const COOLDOWN_MS = 5000;
          const isConnectionRefused =
            String(error?.message || '').toLowerCase().includes('network error') &&
            String(error?.stack || '').toLowerCase().includes('err_connection_refused');
          if (now - lastNetworkToastAtRef.current > COOLDOWN_MS) {
            lastNetworkToastAtRef.current = now;
            toast.error(
              isConnectionRefused
                ? 'Backend is not running on 127.0.0.1:8000. Start it using ./start_backend.sh'
                : 'Network Error: Unable to reach backend API', {
              id: 'backend-network-error',
            });
          }
          return Promise.reject(error);
        }

        // FIX: Don't auto-logout on 401 if it's the login endpoint itself
        if (error.response?.status === 401) {
          const isLoginEndpoint = config.url?.includes('/api/auth/login');
          if (!isLoginEndpoint) {
            logout();
            toast.error('Session expired. Please login again.');
          }
        }

        console.error('[API RESPONSE ERROR]', {
          status: error.response?.status,
          baseURL: config.baseURL || API_BASE,
          url: config.url,
          fullUrl,
          data: error.response?.data,
        });

        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const normalizedUsername = (username || '').trim();

      // FIX: Clear any stale/expired tokens BEFORE login attempt
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);

      const formData = new FormData();
      formData.append('username', normalizedUsername);
      formData.append('password', password);

      const loginUrl = `${API_BASE}/api/auth/login`;
      console.log('[AUTH_DEBUG] LOGIN_REQUEST', {
        apiBase: API_BASE,
        url: loginUrl,
      });

      const response = await axios.post(loginUrl, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        // Explicitly prevent Authorization header on login request
        transformRequest: [(data, headers) => {
          delete headers['Authorization'];
          return data;
        }],
      });

      const { access_token } = response.data;

      if (!access_token) {
        throw new Error('Missing access token in login response');
      }

      // Persist token first for subsequent protected calls
      setToken(access_token);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Mandatory verification call to prevent half-logged-in state
      try {
        const meUrl = `${API_BASE}/api/auth/me`;
        const loginUser = response.data?.user;

        console.log('[AUTH_DEBUG] LOGIN_USER', {
          hasUser: !!loginUser,
          role: loginUser?.role,
        });

        const meResponse = await axios.get(meUrl);
        const verifiedUser = meResponse.data;
        if (!verifiedUser?.role) {
          throw new Error('User role missing in profile response');
        }
        const mergedUser = { ...(loginUser || {}), ...verifiedUser };
        const activeCompanyId = Number(mergedUser.current_company_id ?? mergedUser.company_id ?? 0) || null;
        const primaryCompanies = Array.isArray(mergedUser.companies) && mergedUser.companies.length
          ? mergedUser.companies
          : [];

        if (primaryCompanies.length) {
          const normalizedCompanies = primaryCompanies.map((company: any) => ({
            id: Number(company.company_id ?? company.id ?? 0),
            name: company.name || company.company_name || 'Company',
            slug: company.slug || (company.name || company.company_name || 'company').toLowerCase().replace(/\s+/g, '-'),
            is_active: company.is_active ?? true,
          })).filter((company: any) => company.id);

          if (normalizedCompanies.length) {
            localStorage.setItem('workspace.companies', JSON.stringify(normalizedCompanies));
            const selectedCompany = normalizedCompanies.find((company: any) => Number(company.id) === Number(activeCompanyId)) || normalizedCompanies[0];
            if (selectedCompany) {
              localStorage.setItem('workspace.companyId', String(selectedCompany.id));
            }
          }
        }

        setUser(mergedUser);
        localStorage.setItem('user', JSON.stringify(mergedUser));
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('workspace:user-updated', { detail: mergedUser }));
        }
      } catch (meError: any) {
        setUser(null);
        setToken(null);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        delete axios.defaults.headers.common['Authorization'];

        const meErrorMessage =
          meError?.response?.data?.detail ||
          meError?.message ||
          'Unable to verify user session after login';
        throw new Error(meErrorMessage);
      }

      toast.success('Login successful!');
      return true;
    } catch (error: any) {
      const errorMessage = error?.message || error.response?.data?.detail || 'Login failed';
      toast.error(errorMessage);
      return false;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('workspace.companyId');
    localStorage.removeItem('workspace.brandId');
    localStorage.removeItem('workspace.companies');
    localStorage.removeItem('workspace.brands');
    delete axios.defaults.headers.common['Authorization'];
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('workspace:user-updated', { detail: null }));
    }
    toast.success('Logged out successfully');
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    loading,
    login,
    logout,
    token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
