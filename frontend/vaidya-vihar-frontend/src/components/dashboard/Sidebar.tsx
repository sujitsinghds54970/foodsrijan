import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import GroupsIcon from '@mui/icons-material/Groups'
import { FaBell, FaBoxes, FaCogs, FaGavel, FaMoneyBillWave, FaStethoscope, FaUserCircle, FaUserInjured, FaUsers, FaWallet } from 'react-icons/fa'
import { useAuth } from '../../contexts/AuthContext'
import { staffSelfApi } from '../staff/api'

interface SidebarProps {
  activeTab: string
  setActiveTab: (tab: any) => void
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const auth = useAuth()
  const { user } = auth
  const role = (user?.role || '').trim().toLowerCase()
  const [unreadNotifications, setUnreadNotifications] = useState(0)
  const [branchUnreadNotifications, setBranchUnreadNotifications] = useState(0)
  const API_BASE =
    (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const isStaff = role !== 'super_admin' &&
    role !== 'branch_admin' &&
    role !== 'branch_director' &&
    role !== 'doctor'
  const staffProfilePhoto = auth.user?.profilePhoto
  const sidebarLogoSrc =
    auth.user?.role === 'super_admin'
      ? auth.user?.companyLogo || auth.user?.profilePhoto || '/default-company-logo.png'
      : auth.user?.branch?.logo_url || '/default-logo.png'
  const sidebarFallbackLogo = auth.user?.role === 'super_admin' ? '/default-company-logo.png' : '/default-logo.png'

  const canAccessDailyOps = isStaff ? Boolean((user as any)?.can_access_daily_ops) : false
  const deskTitle = useMemo(() => {
    if (role === 'super_admin') return 'CEO - Mr. Sujit Singh'
    if (role === 'branch_admin' || role === 'branch_director') return 'Director Desk'
    if (role === 'doctor') return 'Doctor Desk'
    if (role === 'staff') return 'Staff Desk'
    if (isStaff) return 'Staff Desk'
    return 'Staff Desk'
  }, [isStaff, role])

  useEffect(() => {
    const loadUnread = async () => {
      if (isStaff) {
        try {
          const notifications = await staffSelfApi.getNotifications()
          setUnreadNotifications(notifications.filter((item) => !item.is_read).length)
        } catch {
          setUnreadNotifications(0)
        }
        setBranchUnreadNotifications(0)
        return
      }

      if (role === 'branch_director' || role === 'branch_admin') {
        try {
          const response = await axios.get(`${API_BASE}/api/branch/notifications`)
          const items = Array.isArray(response.data) ? response.data : []
          setBranchUnreadNotifications(items.filter((item: any) => !item?.is_read).length)
        } catch {
          setBranchUnreadNotifications(0)
        }
        setUnreadNotifications(0)
        return
      }

      setUnreadNotifications(0)
      setBranchUnreadNotifications(0)
    }

    void loadUnread()
  }, [API_BASE, activeTab, isStaff, role])

  useEffect(() => {
    console.log('BRANCH LOGO URL:', auth.user?.branch?.logo_url)
    console.log('STAFF PHOTO URL:', staffProfilePhoto)
  }, [auth.user?.branch?.logo_url, staffProfilePhoto])

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

  const superAdminMenuItems = [
    { id: 'ceo-overview', label: 'Overview', icon: '📊', gradient: 'from-blue-500 to-cyan-500' },
    { id: 'ceo', label: 'CEO Command Center', icon: '🛡️', gradient: 'from-slate-700 to-indigo-700' },
    { id: 'ceo-profile', label: 'CEO Profile', icon: FaUserCircle, gradient: 'from-indigo-600 to-violet-600' },
    { id: 'branch-management', label: 'Branch Management', icon: '🏢', gradient: 'from-red-500 to-orange-500' },
    { id: 'ceo-people-culture', label: 'People & Culture', icon: FaUsers, gradient: 'from-indigo-600 to-violet-600' },
    { id: 'ceo-finance-accounts', label: 'Finance & Accounts', icon: FaMoneyBillWave, gradient: 'from-emerald-600 to-green-600' },
    { id: 'ceo-doctor-network', label: 'Doctor Network', icon: FaStethoscope, gradient: 'from-cyan-600 to-sky-600' },
    { id: 'ceo-patient-insights', label: 'Patient Insights', icon: FaUserInjured, gradient: 'from-rose-600 to-pink-600' },
    { id: 'ceo-inventory-supply', label: 'Inventory & Supply Chain', icon: FaBoxes, gradient: 'from-amber-600 to-orange-600' },
    { id: 'ceo-compliance-legal', label: 'Compliance & Legal', icon: FaGavel, gradient: 'from-slate-600 to-gray-700' },
    { id: 'ceo-system-settings', label: 'System Settings', icon: FaCogs, gradient: 'from-blue-600 to-indigo-700' },
  ]

  const defaultMenuItems = [
    { id: 'overview', label: 'Overview', icon: '📊', gradient: 'from-blue-500 to-cyan-500' },
    ...((role === 'branch_director' || role === 'branch_admin') ? [{ id: 'staff', label: 'Staff Management', icon: GroupsIcon, gradient: 'from-emerald-500 to-teal-500' }] : []),
    ...((role === 'branch_director' || role === 'branch_admin') ? [{ id: 'payroll', label: 'Salary Management', icon: FaWallet, gradient: 'from-emerald-600 to-lime-600' }] : []),
    ...((role === 'branch_director' || role === 'branch_admin')
      ? [{ id: 'branch-notifications', label: 'Notification Center', icon: FaBell, gradient: 'from-indigo-600 to-blue-600', badge: branchUnreadNotifications }]
      : []),
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
  const menuItems = isStaff
    ? staffMenuItems
    : role === 'doctor'
      ? doctorMenuItems
      : role === 'super_admin'
        ? superAdminMenuItems
        : defaultMenuItems

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
            {(() => {
              console.log('BRANCH DATA IN HEADER/SIDEBAR:', auth.user?.branch)
              return null
            })()}
            <img
              src={sidebarLogoSrc}
              alt="Branch logo"
              className="w-10 h-10 rounded-full object-cover"
              onError={(event) => {
                event.currentTarget.onerror = null
                event.currentTarget.src = sidebarFallbackLogo
              }}
            />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight">{deskTitle}</h1>
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
                    <div className="absolute right-3 bg-red-500 text-white rounded-full px-2 py-0.5 text-[10px] font-bold">{(item as any).badge}</div>
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
