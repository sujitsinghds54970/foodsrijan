import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useWorkspace } from '../../context/WorkspaceContext'
import { resolveStaffMediaUrl, staffSelfApi } from '../staff/api'

interface User {
  id: number
  username: string
  email: string
  role: string
  first_name: string
  last_name: string
  branch_id?: number | null
  branch_name?: string
  branch_logo_url?: string
  logo_url?: string
  branch?: {
    name?: string
    logo_url?: string
  }
}

interface HeaderProps {
  user: User | null
  onLogout: () => void
}

export default function Header({ user, onLogout }: HeaderProps) {
  const auth = useAuth()
  const { user: authUser } = auth
  const location = useLocation()
  const [showDropdown, setShowDropdown] = useState(false)
  const [showCompanyMenu, setShowCompanyMenu] = useState(false)
  const [branchName, setBranchName] = useState<string>('FoodSrijan Group')
  const [branchLogoSrc, setBranchLogoSrc] = useState<string>('/default-branch-logo.png')
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  const companyMenuRef = useRef<HTMLDivElement | null>(null)
  const { companies, company, setCurrentWorkspace, companyId } = useWorkspace()
  const API_BASE =
    (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const normalizeHeaderTitle = (value?: string | null) => {
    const normalized = (value || '').trim()
    if (!normalized) return 'FoodSrijan Group'
    return normalized === 'Vaidya Vihar Diagnostic' || normalized === 'VaidyaVihar Diagnostic'
      ? 'FoodSrijan Group'
      : normalized
  }

  const role = (authUser?.role || user?.role || '').toLowerCase()
  const isSystemAdmin = Boolean((authUser as any)?.is_super_admin || (user as any)?.is_super_admin || role === 'super_admin' || role === 'super_ceo')
  const isStaffRoute = location.pathname.toLowerCase().startsWith('/staff/')
  const isStaffLikeRole = !isSystemAdmin &&
    role !== 'branch_admin' &&
    role !== 'branch_director' &&
    role !== 'doctor'

  useEffect(() => {
    const init = async () => {
      const authPayload = (authUser as any) || (user as any) || {}
      let nextBranchName = (authPayload?.branch?.name || authPayload?.branch_name || '').trim()
      let nextBranchLogoRaw = (
        authPayload?.branch?.logo_url ||
        authPayload?.branch_logo_url ||
        authPayload?.logo_url ||
        ''
      ).trim()

      if (isStaffRoute && isStaffLikeRole) {
        try {
          const me = await staffSelfApi.getMe()
          nextBranchName = (me.branch_name || nextBranchName || '').trim()
          nextBranchLogoRaw = (me.branch_logo_url || nextBranchLogoRaw || '').trim()
        } catch {
          // Use auth payload fallback if staff profile call fails.
        }
      }

      if (!nextBranchName && authPayload?.branch_id) {
        try {
          const response = await axios.get(`${API_BASE}/api/branches/${authPayload.branch_id}`)
          nextBranchName = (response.data?.name || nextBranchName || '').trim()
          nextBranchLogoRaw = (response.data?.logo_url || response.data?.branch_logo_url || nextBranchLogoRaw || '').trim()
        } catch {
          // Keep fallback branch title.
        }
      }
      setBranchName(normalizeHeaderTitle(nextBranchName))
      setBranchLogoSrc(resolveStaffMediaUrl(nextBranchLogoRaw) || '/default-branch-logo.png')
    }
    void init()
  }, [API_BASE, authUser, isStaffLikeRole, isStaffRoute, user])

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
      if (companyMenuRef.current && !companyMenuRef.current.contains(event.target as Node)) {
        setShowCompanyMenu(false)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [])

  useEffect(() => {
    setShowDropdown(false)
    setShowCompanyMenu(false)
  }, [location.pathname])

  useEffect(() => {
    console.log('BRANCH LOGO URL:', auth.user?.branch?.logo_url)
    console.log('STAFF PHOTO URL:', auth.user?.profilePhoto)
  }, [auth.user?.branch?.logo_url, auth.user?.profilePhoto])

  const displayName = `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username || 'User'
  const roleLabel = role ? role.replace('_', ' ') : 'Staff'

  return (
    <header className="relative z-50 overflow-visible border-b border-white/30 bg-[#2D3436] px-8 py-5 shadow-xl backdrop-blur-xl dark:border-slate-700">
      {/* Animated Background */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-purple-300/20 to-pink-300/20 rounded-full blur-3xl -mr-32 -mt-32" />

      <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-3xl">
          <h1 className="text-center text-4xl font-extrabold tracking-wide text-white drop-shadow-md md:text-5xl lg:text-left">
            {branchName}
          </h1>
          <p className="mt-3 text-center text-sm font-semibold tracking-wide text-white/80 lg:text-left">
            {displayName} • {roleLabel}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {(companies.length > 1 || authUser?.is_super_admin || isSystemAdmin) && (
            <div className="relative z-40" ref={companyMenuRef}>
              <button
                type="button"
                onClick={() => setShowCompanyMenu((current) => !current)}
                className="flex items-center gap-2 rounded-full border border-white/40 bg-white/10 px-4 py-2 text-sm font-bold text-white shadow-lg backdrop-blur-sm transition hover:bg-white/20"
              >
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="max-w-[160px] truncate">{company?.name || 'Company'}</span>
                <svg className={`h-4 w-4 transition-transform ${showCompanyMenu ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showCompanyMenu && (
                <div className="absolute right-0 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
                  <div className="border-b border-slate-100 px-4 py-3 text-xs font-black uppercase tracking-[0.22em] text-slate-500">
                    Company Switcher
                  </div>
                  <div className="max-h-72 overflow-y-auto py-2">
                    {companies.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => {
                          setCurrentWorkspace(option.id, null)
                          setShowCompanyMenu(false)
                        }}
                        className={`flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold transition ${
                          Number(companyId) === Number(option.id) ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-50'
                        }`}
                      >
                        <span className="truncate">{option.name}</span>
                        {Number(companyId) === Number(option.id) && (
                          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-indigo-600" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* User Profile Dropdown */}
          <div className="relative z-50" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center space-x-2 text-slate-700 hover:text-slate-900 focus:outline-none bg-white border-2 border-slate-200 hover:border-purple-300 rounded-full px-2.5 py-2.5 shadow-lg hover:shadow-xl transition-all group"
            >
              <div className="w-10 h-10 rounded-full overflow-hidden shadow-lg shrink-0 bg-slate-100">
                {(() => {
                  console.log('BRANCH DATA IN HEADER/SIDEBAR:', auth.user?.branch)
                  return null
                })()}
                <img
                  src={auth.user?.profilePhoto || auth.user?.photo || "/default-avatar.png"}
                  alt="User avatar"
                  className="w-10 h-10 rounded-full object-cover border-2 border-white"
                  onError={(event) => {
                    event.currentTarget.onerror = null
                    event.currentTarget.src = '/default-avatar.png'
                  }}
                />
              </div>
              <svg className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${showDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showDropdown && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-xl border border-gray-100 z-50 overflow-hidden">
                {/* Profile Header */}
                <div className="px-5 py-4 border-b-2 border-slate-100 bg-gradient-to-r from-purple-50 to-pink-50">
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 rounded-xl overflow-hidden shadow-lg bg-slate-100">
                      <img
                        src={branchLogoSrc}
                        alt="Branch logo"
                        className="w-full h-full object-cover"
                        onError={(event) => {
                          event.currentTarget.onerror = null
                          event.currentTarget.src = '/default-branch-logo.png'
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-black text-slate-900 text-base truncate">{displayName}</div>
                      <div className="text-xs text-slate-500 truncate font-semibold uppercase tracking-[0.25em]">{roleLabel}</div>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="py-2">
                  <button className="w-full text-left px-5 py-3 text-sm font-semibold text-slate-700 opacity-60 pointer-events-none transition-all flex items-center space-x-3 group">
                    <svg className="w-5 h-5 text-slate-400 group-hover:text-purple-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span>My Profile</span>
                  </button>

                  <button className="w-full text-left px-5 py-3 text-sm font-semibold text-slate-700 opacity-60 pointer-events-none transition-all flex items-center space-x-3 group">
                    <svg className="w-5 h-5 text-slate-400 group-hover:text-purple-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <span>Settings</span>
                  </button>

                  <button className="w-full text-left px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-gradient-to-r hover:from-purple-50 hover:to-pink-50 transition-all flex items-center space-x-3 group">
                    <svg className="w-5 h-5 text-slate-400 group-hover:text-purple-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Help & Support</span>
                  </button>
                </div>

                {/* Logout Button */}
                <div className="px-3 pt-2 pb-3 border-t-2 border-slate-100">
                  <button
                    type="button"
                    onClick={() => {
                      setShowDropdown(false)
                      onLogout()
                    }}
                    className="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-red-500 to-pink-500 text-white font-black text-sm hover:shadow-xl transition-all hover:-translate-y-0.5 flex items-center justify-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
