import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { FaHeartbeat, FaPuzzlePiece, FaShieldAlt } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';

interface Branch {
  id: number;
  name: string;
}

interface RegistrationProps {
  onSwitchToLogin: () => void;
}

export default function Registration({ onSwitchToLogin }: RegistrationProps) {
  const navigate = useNavigate();
  const API_BASE =
    (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    phone: '',
    role: 'patient',
    branchId: ''
  });
  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [branding, setBranding] = useState<{ logo: string | null; name: string; tagline: string }>({
    logo: null,
    name: '',
    tagline: '',
  });
  const [stats, setStats] = useState({
    modules: 0,
    visibility: 0,
    customers: 0,
  });

  const loadBranches = useCallback(async () => {
    try {
      setLoadingBranches(true);
      const response = await axios.get(`${API_BASE}/api/public/branches`);
      setBranches(response.data);
    } catch (error) {
      console.error('Failed to load public branches:', error);
      setBranches([]);
    } finally {
      setLoadingBranches(false);
    }
  }, [API_BASE]);

  const loadBranding = useCallback(async () => {
    try {
      const response = await axios.get('/api/public/branding');
      setBranding({
        logo: response.data?.primary_logo_url || null,
        name: response.data?.company_name || '',
        tagline: response.data?.tagline || '',
      });
    } catch {
      try {
        const response = await axios.get(`${API_BASE}/api/public/branding`);
        setBranding({
          logo: response.data?.primary_logo_url || null,
          name: response.data?.company_name || '',
          tagline: response.data?.tagline || '',
        });
      } catch (error) {
        console.error('Failed to load branding:', error);
        setBranding({ logo: null, name: '', tagline: '' });
      }
    }
  }, [API_BASE]);

  useEffect(() => {
    void loadBranches();
    void loadBranding();
  }, [loadBranches, loadBranding]);

  useEffect(() => {
    const intervals: number[] = [];
    const counters = [
      { key: 'modules' as const, target: 20, duration: 900 },
      { key: 'visibility' as const, target: 999, duration: 1100 },
      { key: 'customers' as const, target: 1000, duration: 1300 },
    ];
    counters.forEach(({ key, target, duration }) => {
      const steps = Math.max(1, Math.floor(duration / 30));
      const increment = Math.max(1, Math.ceil(target / steps));
      const intervalId = window.setInterval(() => {
        setStats((prev) => {
          const nextValue = Math.min(target, prev[key] + increment);
          if (nextValue === target) {
            window.clearInterval(intervalId);
          }
          return { ...prev, [key]: nextValue };
        });
      }, 30);
      intervals.push(intervalId);
    });
    return () => {
      intervals.forEach((id) => window.clearInterval(id));
    };
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === 'role') {
      setFormData((prev) => ({
        ...prev,
        role: value,
        branchId: value === 'doctor' ? prev.branchId : '',
      }));
      if (value !== 'doctor') {
        setSelectedBranchId('');
      }
      return;
    }
    if (name === 'branchId') {
      setSelectedBranchId(value);
    }
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = () => {
    if (!formData.username || !formData.email || !formData.password || !formData.firstName || !formData.lastName) {
      toast.error('Please fill in all required fields');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return false;
    }

    if (formData.password.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      toast.error('Please enter a valid email address');
      return false;
    }

    if (formData.role === 'doctor' && !formData.branchId) {
      toast.error('Branch selection is required for Staff registration');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setLoading(true);
    
    try {
      const registrationData = {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        first_name: formData.firstName,
        last_name: formData.lastName,
        phone: formData.phone,
        role: formData.role,
        branch_id: formData.branchId ? parseInt(formData.branchId) : null
      };

      const response = await axios.post(`${API_BASE}/api/auth/public-register`, registrationData);
      
      // Extract token and user data from response
      const { access_token, user } = response.data;
      
      // Save token and user to localStorage
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(user));
      
      // Set axios default header
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Show success message
      toast.success(`Welcome ${user.first_name}! Account created successfully.`);
      
      // Wait a moment for toast to show
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Redirect based on role
      const dashboardRoutes: Record<string, string> = {
        'patient': '/patient-portal',
        'doctor': '/dashboard',
      };
      
      const redirectPath = dashboardRoutes[user.role] || '/dashboard';
      navigate(redirectPath);
      
      // Reload to ensure auth context updates
      window.location.href = redirectPath;
      
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Registration failed. Please try again.';
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const roleOptions = [
    { value: 'patient', label: 'Customer' },
    { value: 'doctor', label: 'Staff' },
  ];

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center px-4 py-10">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-950 via-indigo-900 to-slate-900" />
      <div className="absolute -top-24 -left-24 w-72 h-72 bg-cyan-400/25 rounded-full blur-3xl" />
      <div className="absolute -bottom-20 -right-20 w-80 h-80 bg-violet-500/30 rounded-full blur-3xl" />

      <div className="relative z-10 grid lg:grid-cols-2 gap-8 w-full max-w-7xl items-start lg:items-center">
        <div className="text-white px-2 lg:px-6">
          <p className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] bg-white/10 px-3 py-1 rounded-full border border-white/20">
            FOOD BUSINESS OPERATIONS
          </p>
          <div className="mt-6 flex items-center gap-4">
            {branding.logo ? (
              <img src={branding.logo} alt="Company Logo" className="w-16 h-16 rounded-2xl object-cover shadow-sm border border-white/20 bg-white" />
            ) : (
              <div className="w-16 h-16 rounded-2xl bg-white/15 border border-white/20 flex items-center justify-center">
                {FaHeartbeat({ className: 'w-8 h-8 text-cyan-300' })}
              </div>
            )}
            <h1 className="text-3xl md:text-4xl font-black leading-tight">
              {branding.name || 'FoodSrijan Group'}
            </h1>
          </div>
          <p className="mt-5 text-cyan-100 text-lg max-w-2xl font-semibold">
            {branding.tagline || 'One Platform. Infinite Possibilities.'}
          </p>
          <p className="mt-3 text-white/80 max-w-2xl">
            Register to access patient services and doctor workflows on a single secure platform.
          </p>

          <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mx-auto max-w-5xl">
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 text-center shadow-xl hover:scale-105 transition-transform duration-300">
              {FaPuzzlePiece({ className: 'mx-auto mb-3 h-8 w-8 text-cyan-200' })}
              <p className="text-3xl font-extrabold text-white">{stats.modules}+</p>
              <p className="text-sm font-semibold text-white/90 mt-1">Integrated Modules</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 text-center shadow-xl hover:scale-105 transition-transform duration-300">
              {FaShieldAlt({ className: 'mx-auto mb-3 h-8 w-8 text-emerald-200' })}
              <p className="text-3xl font-extrabold text-white">{(stats.visibility / 10).toFixed(1)}%</p>
              <p className="text-sm font-semibold text-white/90 mt-1">Operational Visibility</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-8 text-center shadow-xl hover:scale-105 transition-transform duration-300">
              {FaHeartbeat({ className: 'mx-auto mb-3 h-8 w-8 text-rose-200' })}
              <p className="text-3xl font-extrabold text-white">{stats.customers}+</p>
              <p className="text-sm font-semibold text-white/90 mt-1">Happy Customers</p>
            </div>
          </div>
        </div>

        <div className="premium-glass rounded-3xl shadow-2xl p-8 md:p-10 w-full max-w-xl mx-auto border-white/40">
          <div className="text-center">
            <h2 className="text-3xl font-black text-slate-900">
              Create Account
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Join {branding.name || 'FoodSrijan Group'} System
            </p>
          </div>

          <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1">
                  I am a:
                </label>
                <select
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  required
                >
                  {roleOptions.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {formData.role === 'doctor' && (
                <div>
                  <label htmlFor="branchId" className="block text-sm font-medium text-gray-700 mb-1">
                    Branch:
                  </label>
                  {loadingBranches ? (
                    <div className="animate-pulse h-10 bg-gray-200 rounded-md"></div>
                  ) : (
                    <select
                      id="branchId"
                      name="branchId"
                      value={selectedBranchId}
                      onChange={handleChange}
                      className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      required={formData.role === 'doctor'}
                    >
                      <option value="">Select Branch</option>
                      {branches.map(branch => (
                        <option key={branch.id} value={branch.id}>
                          {branch.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 mb-1">
                    First Name *
                  </label>
                  <input
                    id="firstName"
                    name="firstName"
                    type="text"
                    required
                    className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="First Name"
                    value={formData.firstName}
                    onChange={handleChange}
                  />
                </div>
                <div>
                  <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 mb-1">
                    Last Name *
                  </label>
                  <input
                    id="lastName"
                    name="lastName"
                    type="text"
                    required
                    className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Last Name"
                    value={formData.lastName}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                  Username *
                </label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Choose a username"
                  value={formData.username}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address *
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={handleChange}
                />
              </div>

              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number
                </label>
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Enter your phone number"
                  value={formData.phone}
                  onChange={handleChange}
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password *
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Create a password"
                  value={formData.password}
                  onChange={handleChange}
                />
                <p className="text-xs text-gray-500 mt-1">Must be at least 8 characters long</p>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm Password *
                </label>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  className="appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="Confirm your password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : null}
                {loading ? 'Creating Account...' : 'Create Account'}
              </button>
            </div>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={onSwitchToLogin}
                  className="font-medium text-blue-600 hover:text-blue-500"
                >
                  Sign in here
                </button>
              </p>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
