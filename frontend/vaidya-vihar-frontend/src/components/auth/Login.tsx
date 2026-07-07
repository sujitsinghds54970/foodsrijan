import React, { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'

interface LoginProps {
  onSwitchToRegistration: () => void;
}

export default function Login({ onSwitchToRegistration }: LoginProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()

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
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-950 via-indigo-900 to-slate-900" />
      <div className="absolute -top-24 -left-24 w-72 h-72 bg-cyan-400/25 rounded-full blur-3xl" />
      <div className="absolute -bottom-20 -right-20 w-80 h-80 bg-violet-500/30 rounded-full blur-3xl" />

      <div className="relative z-10 grid lg:grid-cols-2 gap-8 w-full max-w-6xl items-center">
        <div className="hidden lg:block text-white px-6">
          <p className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] bg-white/10 px-3 py-1 rounded-full border border-white/20">
            Premium Diagnostic ERP
          </p>
          <h1 className="mt-6 text-5xl font-black leading-tight">
            Beautiful.
            <span className="block text-cyan-300">Fast. Trusted.</span>
          </h1>
          <p className="mt-5 text-white/80 text-lg max-w-xl">
            Manage patients, doctors, lab operations, billing, and analytics from one elegant control center crafted for modern Indian diagnostics teams.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-4 max-w-xl">
            <div className="premium-glass rounded-2xl p-4 border-white/20 text-white">
              <p className="text-2xl font-bold">20+</p>
              <p className="text-xs text-white/80">Integrated modules</p>
            </div>
            <div className="premium-glass rounded-2xl p-4 border-white/20 text-white">
              <p className="text-2xl font-bold">99.9%</p>
              <p className="text-xs text-white/80">Operational visibility</p>
            </div>
          </div>
        </div>

        <div className="premium-glass rounded-3xl shadow-2xl p-8 md:p-10 w-full max-w-xl mx-auto border-white/40">
          <div className="text-center">
            <div className="mx-auto h-14 w-14 flex items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-cyan-500 shadow-lg">
              <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <h2 className="mt-6 text-3xl font-black text-slate-900">VaidyaVihar Diagnostic</h2>
            <p className="mt-2 text-sm text-slate-600">Sign in to your premium workspace</p>
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
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white/90 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
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
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white/90 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex justify-center items-center py-3 px-4 rounded-xl text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 via-violet-600 to-cyan-500 hover:brightness-110 transition-all shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in to Dashboard'}
            </button>

            <div className="rounded-2xl p-4 bg-slate-900 text-slate-200 text-sm">
              <p className="text-xs uppercase tracking-widest text-cyan-300 mb-2">Login Credentials</p>
              <p className="font-mono text-xs">Username: <span className="text-white">sujiterp</span></p>
              <p className="font-mono text-xs mt-1">Password: <span className="text-white">#sujiterp54970</span></p>
            </div>

            <div className="text-sm text-slate-600 text-center">
              Don&apos;t have an account?{' '}
              <button
                type="button"
                onClick={onSwitchToRegistration}
                className="font-semibold text-indigo-600 hover:text-indigo-700"
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
