import React from 'react'
import { useAuth } from '../../contexts/AuthContext'

interface SidebarProps {
  activeTab: string
  setActiveTab: (tab: any) => void
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const { user } = useAuth()

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: '📊', gradient: 'from-blue-500 to-cyan-500' },
    ...(user?.role === 'super_admin' ? [{ id: 'branch-management', label: 'Branch Management', icon: '🏢', gradient: 'from-red-500 to-orange-500' }] : []),
    { id: 'patients', label: 'Patients', icon: '👥', gradient: 'from-emerald-500 to-teal-500' },
    ...((user?.role === 'branch_admin' || user?.role === 'super_admin') ? [{ id: 'daily-operations', label: 'Daily Operations', icon: '📝', gradient: 'from-purple-500 to-pink-500' }] : []),
    { id: 'staff', label: 'Staff', icon: '👨‍⚕️', gradient: 'from-indigo-500 to-blue-500' },
    { id: 'inventory', label: 'Inventory', icon: '📦', gradient: 'from-amber-500 to-orange-500' },
    { id: 'analytics', label: 'Analytics', icon: '📈', gradient: 'from-pink-500 to-rose-500' },
    { id: 'reports', label: 'Reports', icon: '📋', gradient: 'from-violet-500 to-purple-500' },
    { id: 'lis', label: 'LIS Lab Tests', icon: '🧪', gradient: 'from-cyan-500 to-blue-500' },
    { id: 'payments', label: 'Payments', icon: '💳', gradient: 'from-green-500 to-emerald-500' },
    { id: 'accounting', label: 'Accounting', icon: '💰', gradient: 'from-yellow-500 to-amber-500' },
    { id: 'hr', label: 'HR & Leave', icon: '👔', gradient: 'from-slate-500 to-gray-500' },
    { id: 'doctor-portal', label: 'Doctor Portal', icon: '🩺', gradient: 'from-teal-500 to-cyan-500' },
    { id: 'patient-portal', label: 'Patient Portal', icon: '🏥', gradient: 'from-rose-500 to-pink-500' },
  ]

  return (
    <aside className="w-80 min-h-screen premium-glass border-r border-white/60 shadow-2xl relative overflow-hidden">
      {/* Animated Background Orbs */}
      <div className="absolute top-0 left-0 w-40 h-40 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-400/20 to-cyan-400/20 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      
      {/* Header */}
      <div className="relative p-6 border-b border-slate-200/70">
        <div className="flex items-center space-x-3">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-red-600 via-purple-600 to-pink-600 flex items-center justify-center shadow-2xl transform hover:scale-110 transition-transform duration-300 animate-gradient">
            <span className="text-white font-black text-2xl">V</span>
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight">VaidyaVihar</h1>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}

      {/* Navigation Menu */}
      <nav className="relative p-4 pb-24 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 280px)' }}>
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={`group w-full flex items-center space-x-3 px-4 py-3.5 text-left rounded-xl transition-all duration-300 relative overflow-hidden ${
                    isActive
                      ? 'bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 text-white shadow-2xl scale-[1.02] font-black'
                      : 'text-slate-700 hover:bg-white hover:text-slate-900 hover:shadow-lg font-semibold'
                  }`}
                >
                  {isActive && (
                    <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent animate-shimmer" />
                  )}
                  <div className={`relative w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 ${
                    isActive 
                      ? 'bg-white/20 shadow-lg' 
                      : `bg-gradient-to-br ${item.gradient} text-white shadow-md group-hover:scale-110 group-hover:rotate-3`
                  }`}>
                    <span className={`text-xl ${isActive ? 'text-white' : ''}`}>{item.icon}</span>
                  </div>
                  <span className="relative font-bold text-sm tracking-wide">{item.label}</span>
                  {isActive && (
                    <div className="absolute right-3 w-2 h-2 bg-white rounded-full animate-pulse" />
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

    </aside>
  )
}
