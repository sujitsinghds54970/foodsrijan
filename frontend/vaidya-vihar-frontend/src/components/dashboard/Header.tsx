import { useState } from 'react'

interface User {
  id: number
  username: string
  email: string
  role: string
  first_name: string
  last_name: string
}

interface HeaderProps {
  user: User | null
  onLogout: () => void
}

export default function Header({ user, onLogout }: HeaderProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [profileImageError, setProfileImageError] = useState(false)

  return (
    <header className="premium-glass border-b border-white/70 px-8 py-5 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-purple-300/20 to-pink-300/20 rounded-full blur-3xl -mr-32 -mt-32" />
      
      <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-3xl">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-blue-950">
            Sujit Rajput
          </h1>
          <p className="mt-4 text-base md:text-lg text-blue-700 font-semibold uppercase tracking-[0.14em]">
            Founder & CEO
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* User Profile Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="flex items-center space-x-2 text-slate-700 hover:text-slate-900 focus:outline-none bg-white border-2 border-slate-200 hover:border-purple-300 rounded-full px-2.5 py-2.5 shadow-lg hover:shadow-xl transition-all group"
            >
              <div className="w-9 h-9 rounded-full overflow-hidden shadow-lg shrink-0 bg-slate-100">
                {!profileImageError ? (
                  <img
                    src="/founder.jpg"
                    alt="Founder profile"
                    className="w-full h-full object-cover"
                    onError={() => setProfileImageError(true)}
                  />
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-purple-600 via-pink-600 to-red-600 flex items-center justify-center text-white font-black text-lg" aria-hidden="true">
                    {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
                  </div>
                )}
              </div>
              <svg className={`w-5 h-5 text-slate-400 transition-transform duration-300 ${showDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showDropdown && (
              <div className="absolute right-0 mt-3 w-72 bg-white rounded-2xl shadow-2xl py-3 z-50 border-2 border-slate-100 animate-fadeIn">
                {/* Profile Header */}
                <div className="px-5 py-4 border-b-2 border-slate-100 bg-gradient-to-r from-purple-50 to-pink-50">
                  <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 rounded-xl overflow-hidden shadow-lg bg-slate-100">
                      {!profileImageError ? (
                        <img
                          src="/founder.jpg"
                          alt="Founder profile"
                          className="w-full h-full object-cover"
                          onError={() => setProfileImageError(true)}
                        />
                      ) : (
                        <div className="w-full h-full bg-gradient-to-br from-purple-600 via-pink-600 to-red-600 flex items-center justify-center text-white font-black text-xl" aria-hidden="true">
                          {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-black text-slate-900 text-base truncate">Sujit Rajput</div>
                      <div className="text-xs text-slate-500 truncate font-semibold uppercase tracking-[0.25em]">Founder & CEO</div>
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
                    onClick={onLogout}
                    className="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-red-500 to-pink-500 text-white font-black text-sm hover:shadow-xl transition-all hover:-translate-y-0.5 flex items-center justify-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    <span>Sign Out</span>
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
