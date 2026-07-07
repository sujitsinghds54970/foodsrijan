import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  branch_id?: number | null;
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

const API_BASE = 'http://localhost:8000';
console.log('[AUTH_DEBUG] API_BASE_FIXED', API_BASE);

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Configure axios defaults and restore auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('token');

      if (storedToken) {
        setToken(storedToken);
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;

        try {
          const response = await axios.get(`${API_BASE}/api/auth/me`);
          setUser(response.data);
          localStorage.setItem('user', JSON.stringify(response.data));
        } catch (err) {
          logout();
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
      (response) => response,
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
          toast.error('Network Error: Unable to reach backend API');
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
      // FIX: Clear any stale/expired tokens BEFORE login attempt
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);

      // Log exact payload being sent (Step 3 debugging)
      console.log('LOGIN_PAYLOAD:', { username, password });
      console.log('LOGIN_PAYLOAD_LENGTHS:', { 
        usernameLength: username.length, 
        passwordLength: password.length,
        usernameHasSpaces: username !== username.trim(),
        passwordHasSpaces: password !== password.trim()
      });

      const formData = new FormData();
      formData.append('username', username);
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

      console.log('[AUTH_DEBUG] LOGIN_RESPONSE', {
        hasToken: !!access_token,
        tokenPreview: access_token ? `${access_token.slice(0, 20)}...` : null,
      });

      // Persist token first for subsequent protected calls
      setToken(access_token);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;

      // Mandatory verification call to prevent half-logged-in state
      try {
        const meUrl = `${API_BASE}/api/auth/me`;
        console.log('[AUTH_DEBUG] ME_REQUEST', {
          url: meUrl,
          headers: {
            Authorization: axios.defaults.headers.common['Authorization'],
          },
        });

        const meResponse = await axios.get(meUrl);
        const verifiedUser = meResponse.data;

        console.log('[AUTH_DEBUG] ME_RESPONSE', {
          status: meResponse.status,
          data: verifiedUser,
        });

        if (!verifiedUser?.role) {
          throw new Error('User role missing in profile response');
        }

        setUser(verifiedUser);
        localStorage.setItem('user', JSON.stringify(verifiedUser));
      } catch (meError: any) {
        // Hard reset auth state if verification fails
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
    delete axios.defaults.headers.common['Authorization'];
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
