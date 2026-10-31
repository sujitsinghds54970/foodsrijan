import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { FaUtensils, FaPuzzlePiece, FaShieldAlt } from 'react-icons/fa'
import { useAuth } from '../../contexts/AuthContext'

interface LoginProps {
  onSwitchToRegistration: () => void;
}

export default function Login({ onSwitchToRegistration }: LoginProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [branding, setBranding] = useState<{ logo: string | null; name: string; tagline: string }>({ logo: null, name: 'FoodSrijan Group', tagline: 'One Platform. Infinite Possibilities.' })
  const [stats, setStats] = useState({
    modules: 0,
    visibility: 0,
    customers: 0,
  })
  const { login } = useAuth()
  const API_BASE =
    (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  useEffect(() => {
    const loadBranding = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/public/branding`)
        setBranding({
          logo: response.data?.primary_logo_url || null,
          name: 'FoodSrijan Group',
          tagline: 'One Platform. Infinite Possibilities.',
        })
      } catch {
        setBranding({ logo: null, name: 'FoodSrijan Group', tagline: 'One Platform. Infinite Possibilities.' })
      }
    }
    void loadBranding()
  }, [API_BASE])

  useEffect(() => {
    const intervals: number[] = []
    const counters = [
      { key: 'modules' as const, target: 20, duration: 900 },
      { key: 'visibility' as const, target: 999, duration: 1100 },
      { key: 'customers' as const, target: 1000, duration: 1300 },
    ]
    counters.forEach(({ key, target, duration }) => {
      const steps = Math.max(1, Math.floor(duration / 30))
      const increment = Math.max(1, Math.ceil(target / steps))
      const intervalId = window.setInterval(() => {
        setStats((prev) => {
          const nextValue = Math.min(target, prev[key] + increment)
          if (nextValue === target) {
            window.clearInterval(intervalId)
          }
          return { ...prev, [key]: nextValue }
        })
      }, 30)
      intervals.push(intervalId)
    })
    return () => {
      intervals.forEach((id) => window.clearInterval(id))
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const ok = await login(username, password)
      if (!ok) {
        // Error toast is already handled in AuthContext.login
        return
      }
    } catch (err: any) {
      console.error('Login failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden flex items-center justify-center px-4 py-10">
      <div className="absolute inset-0 bg-[linear-gradient(135deg,#2D3436_0%,#3e4748_55%,#E85D3A_150%)]" />

      <div className="relative z-10 grid lg:grid-cols-2 gap-8 w-full max-w-6xl items-center">
        <div className="hidden lg:block text-white px-6">
          <p className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] bg-white/10 px-3 py-1 rounded-full border border-white/20">
            FOOD BUSINESS OPERATIONS
          </p>
          <h1 className="mt-6 text-5xl font-black leading-tight">
            {branding.name || 'FoodSrijan Group'}
          </h1>
          <p className="mt-5 text-amber-200 text-3xl font-black leading-tight">
            {branding.tagline || 'One Platform. Infinite Possibilities.'}
          </p>
          <p className="mt-5 text-white/80 text-lg max-w-xl">
            Manage branches, menus, recipes, inventory, teams, and orders from one elegant control center for modern food businesses.
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
              {FaUtensils({ className: 'mx-auto mb-3 h-8 w-8 text-amber-200' })}
              <p className="text-3xl font-extrabold text-white">{stats.customers}+</p>
              <p className="text-sm font-semibold text-white/90 mt-1">Happy Customers</p>
            </div>
          </div>
        </div>

        <div className="premium-glass rounded-3xl shadow-2xl p-8 md:p-10 w-full max-w-xl mx-auto border-white/40">
          <div className="text-center">
            {branding.logo ? (
              <img src={branding.logo} alt="Company Logo" className="w-16 h-16 rounded-2xl object-cover mx-auto mb-4 shadow-sm border border-gray-100 bg-white" />
            ) : (
              <div className="mx-auto h-16 w-16 flex items-center justify-center rounded-2xl bg-[#E85D3A] shadow-lg mb-4">
                <svg className="h-9 w-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
            )}
            <h2 className="mt-6 text-3xl font-black text-slate-900">{branding.name || 'FoodSrijan Group'}</h2>
            <p className="mt-2 text-sm text-slate-600">Sign in to your food business workspace</p>
          </div>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label htmlFor="username" className="text-sm font-medium text-slate-700 block mb-1.5">Username</label>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white/90 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 shadow-sm"
                  placeholder="Enter username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="password" className="text-sm font-medium text-slate-700 block mb-1.5">Password</label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white/90 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 shadow-sm"
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex justify-center items-center py-3 px-4 rounded-xl text-sm font-semibold text-white bg-[#E85D3A] hover:bg-[#d94e2d] transition-all shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in to Dashboard'}
            </button>

            <div className="rounded-2xl p-4 bg-slate-900 text-slate-200 text-sm">
              <p className="text-xs uppercase tracking-widest text-cyan-300 mb-2">Login Help</p>
              <p className="text-xs">Use your assigned username or email and password.</p>
              <p className="text-xs mt-1">If login fails, verify credentials with your administrator.</p>
            </div>

            <div className="text-sm text-slate-600 text-center">
              Don&apos;t have an account?{' '}
              <button
                type="button"
                onClick={onSwitchToRegistration}
                className="font-semibold text-[#E85D3A] hover:text-[#d94e2d]"
              >
                Register here
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
