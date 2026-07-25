import React, { useEffect, useState } from 'react'
import GroupsIcon from '@mui/icons-material/Groups'
import { FaWallet } from 'react-icons/fa'
import { useAuth } from '../../contexts/AuthContext'
import { staffSelfApi } from '../staff/api'

interface SidebarProps {
  activeTab: string
  setActiveTab: (tab: any) => void
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const { user } = useAuth()
  const role = (user?.role || '').trim().toLowerCase()
  const [unreadNotifications, setUnreadNotifications] = useState(0)

  // Helper to detect staff roles (not super_admin, branch_admin, branch_director, or doctor)
  const isStaffRole = () => {
    return role !== 'super_admin' && 
           role !== 'branch_admin' && 
           role !== 'branch_director' &&
           role !== 'doctor'
  }

  const canAccessDailyOps = isStaffRole() ? Boolean((user as any)?.can_access_daily_ops) : false

  useEffect(() => {
    if (!isStaffRole()) {
      setUnreadNotifications(0)
      return
    }

    const loadUnread = async () => {
      try {
        const notifications = await staffSelfApi.getNotifications()
        setUnreadNotifications(notifications.filter((item) => !item.is_read).length)
      } catch {
        setUnreadNotifications(0)
      }
    }

    void loadUnread()
  }, [activeTab])

  const staffMenuItems = [
    { id: 'staff-profile', label: 'My Profile', icon: '🪪', gradient: 'from-blue-600 to-purple-600' },
    { id: 'staff-attendance', label: 'Attendance Management System', icon: '🕒', gradient: 'from-orange-500 to-amber-500' },
    ...(canAccessDailyOps ? [{ id: 'daily-operations', label: 'Daily Operations', icon: '📝', gradient: 'from-fuchsia-600 to-pink-600' }] : []),
    { id: 'staff-tasks', label: 'Tasks Allotted', icon: '📋', gradient: 'from-sky-600 to-cyan-600' },
    { id: 'staff-notifications', label: 'Important Notification', icon: '🔔', gradient: 'from-rose-600 to-red-600', badge: unreadNotifications },
    { id: 'staff-performance', label: 'My Performance', icon: '📈', gradient: 'from-indigo-600 to-violet-600' },
  ]

  const doctorMenuItems = [
    { id: 'doctor-portal', label: 'Doctor Portal', icon: '🩺', gradient: 'from-teal-500 to-cyan-500' },
  ]

  const defaultMenuItems = [
    { id: 'overview', label: 'Overview', icon: '📊', gradient: 'from-blue-500 to-cyan-500' },
    ...(role === 'super_admin' ? [{ id: 'ceo', label: 'CEO Command Center', icon: '🛡️', gradient: 'from-slate-700 to-indigo-700' }] : []),
    ...(role === 'super_admin' ? [{ id: 'branch-management', label: 'Branch Management', icon: '🏢', gradient: 'from-red-500 to-orange-500' }] : []),
    ...((role === 'branch_director' || role === 'branch_admin') ? [{ id: 'staff', label: 'Staff Management', icon: GroupsIcon, gradient: 'from-emerald-500 to-teal-500' }] : []),
    ...((role === 'branch_director' || role === 'branch_admin') ? [{ id: 'payroll', label: 'Salary Management', icon: FaWallet, gradient: 'from-emerald-600 to-lime-600' }] : []),
    ...((role === 'branch_admin' || role === 'super_admin') ? [{ id: 'daily-operations', label: 'Daily Operations', icon: '📝', gradient: 'from-purple-500 to-pink-500' }] : []),
    { id: 'inventory', label: 'Inventory', icon: '📦', gradient: 'from-amber-500 to-orange-500' },
    { id: 'analytics', label: 'Analytics', icon: '📈', gradient: 'from-pink-500 to-rose-500' },
    { id: 'lis', label: 'LIS Lab Tests', icon: '🧪', gradient: 'from-cyan-500 to-blue-500' },
    { id: 'payments', label: 'Payments', icon: '💳', gradient: 'from-green-500 to-emerald-500' },
    { id: 'accounts', label: 'Accounts', icon: '📚', gradient: 'from-indigo-500 to-sky-500' },
    ...((role === 'branch_director' || role === 'branch_admin' || role === 'super_admin') ? [{ id: 'doctor-portal', label: 'Doctor Portal', icon: '🩺', gradient: 'from-teal-500 to-cyan-500' }] : []),
    { id: 'patient-portal', label: 'Patient Portal', icon: '🏥', gradient: 'from-rose-500 to-pink-500' },
  ]

  // Determine which menu to show: prioritize based on role
  const menuItems = isStaffRole() ? staffMenuItems : role === 'doctor' ? doctorMenuItems : defaultMenuItems

  const handleMenuClick = (tabId: string) => {
    if (tabId === activeTab) return
    setActiveTab(tabId)
  }

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
            <h1 className="text-2xl font-black tracking-tight">Staff Desk</h1>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}

      {/* Navigation Menu */}
      <nav className="relative p-4 pb-24 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 280px)' }}>
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const isActive = activeTab === item.id
            const isIconComponent = typeof item.icon !== 'string'
            return (
              <li key={item.id}>
                <button
                  onClick={() => handleMenuClick(item.id)}
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
                    {isIconComponent ? (
                      React.createElement(item.icon as any, { className: `text-base ${isActive ? 'text-white' : ''}` })
                    ) : (
                      <span className={`text-xl ${isActive ? 'text-white' : ''}`}>{item.icon as string}</span>
                    )}
                  </div>
                  <span className="relative font-bold text-sm tracking-wide">{item.label}</span>
                  {typeof (item as any).badge === 'number' && (item as any).badge > 0 && (
                    <div className="absolute right-3 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">{(item as any).badge}</div>
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
