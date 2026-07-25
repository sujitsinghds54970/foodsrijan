import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Overview from './Overview'
import PatientManagement from './PatientManagement'
import StaffManagement from '../staff/StaffManagementModule'
import InventoryManagement from './InventoryManagement'
import Analytics from './Analytics'
import Reports from './Reports'
import LIS from './LIS'
import Payments from './Payments'
import Accounting from './Accounting'
import Accounts from './Accounts'
import HR from './HR'
import PayrollDashboard from '../payroll/PayrollDashboard'
import PatientPortal from './PatientPortal'
import DoctorManagementCRMModule from '../doctors/DoctorManagementCRMModule'
import DoctorPortal from './DoctorPortal'
import BranchManagement from './BranchManagement'
import DailyOperations from './DailyOperations'
import MyProfileTab from '../staff/MyProfileTab'
import SalaryTab from '../staff/SalaryTab'
import AttendanceTab from '../staff/AttendanceTab'
import TasksTab from '../staff/TasksTab'
import NotificationsTab from '../staff/NotificationsTab'
import PerformanceTab from '../staff/PerformanceTab'
import CeoDashboard from '../ceo/CeoDashboard'

type ActiveTab = 'overview' | 'patients' | 'daily-operations' | 'staff' | 'payroll' | 'staff-profile' | 'staff-salary' | 'staff-attendance' | 'staff-tasks' | 'staff-notifications' | 'staff-performance' | 'inventory' | 'analytics' | 'reports' | 'lis' | 'payments' | 'accounting' | 'accounts' | 'hr' | 'doctor-portal' | 'patient-portal' | 'branch-management' | 'ceo'

const tabPathMap: Record<ActiveTab, string> = {
  overview: '/branch/dashboard',
  patients: '/branch/patients',
  'daily-operations': '/branch/daily-operations',
  staff: '/branch/staff',
  payroll: '/branch/payroll',
  'staff-profile': '/staff/profile',
  'staff-salary': '/staff/salary',
  'staff-attendance': '/staff/attendance',
  'staff-tasks': '/staff/tasks',
  'staff-notifications': '/staff/notifications',
  'staff-performance': '/staff/performance',
  inventory: '/branch/inventory',
  analytics: '/branch/analytics',
  reports: '/branch/reports',
  lis: '/branch/lis',
  payments: '/branch/payments',
  accounting: '/branch/accounting',
  accounts: '/branch/accounts',
  hr: '/branch/hr',
  'doctor-portal': '/branch/doctor-portal',
  'patient-portal': '/branch/patient-portal',
  'branch-management': '/branch/management',
  ceo: '/ceo',
}

function tabFromPath(pathname: string): ActiveTab {
  const path = normalizePath(pathname).toLowerCase()
  if (path === '/branch/dashboard' || path.startsWith('/branch/dashboard/')) return 'overview'
  if (path === '/branch/staff' || path.startsWith('/branch/staff/')) return 'staff'
  if (path === '/branch/payroll' || path.startsWith('/branch/payroll/')) return 'payroll'
  if (path === '/staff/profile' || path.startsWith('/staff/profile/')) return 'staff-profile'
  if (path === '/staff/salary' || path.startsWith('/staff/salary/')) return 'staff-salary'
  if (path === '/staff/attendance' || path.startsWith('/staff/attendance/')) return 'staff-attendance'
  if (path === '/staff/tasks' || path.startsWith('/staff/tasks/')) return 'staff-tasks'
  if (path === '/staff/notifications' || path.startsWith('/staff/notifications/')) return 'staff-notifications'
  if (path === '/staff/performance' || path.startsWith('/staff/performance/')) return 'staff-performance'
  if (path === '/branch/daily-operations' || path.startsWith('/branch/daily-operations/')) return 'daily-operations'
  if (path === '/branch/management' || path.startsWith('/branch/management/')) return 'branch-management'
  if (path === '/branch/inventory' || path.startsWith('/branch/inventory/')) return 'inventory'
  if (path === '/branch/analytics' || path.startsWith('/branch/analytics/')) return 'analytics'
  if (path === '/branch/reports' || path.startsWith('/branch/reports/')) return 'reports'
  if (path === '/branch/lis' || path.startsWith('/branch/lis/')) return 'lis'
  if (path === '/branch/payments' || path.startsWith('/branch/payments/')) return 'payments'
  if (path === '/branch/accounting' || path.startsWith('/branch/accounting/')) return 'accounting'
  if (path === '/branch/accounts' || path.startsWith('/branch/accounts/')) return 'accounts'
  if (path === '/branch/hr' || path.startsWith('/branch/hr/')) return 'hr'
  if (path === '/branch/doctor-portal' || path.startsWith('/branch/doctor-portal/')) return 'doctor-portal'
  if (path === '/branch/patient-portal' || path.startsWith('/branch/patient-portal/')) return 'patient-portal'
  if (path === '/ceo' || path.startsWith('/ceo/')) return 'ceo'
  if (path === '/branch/patients' || path.startsWith('/branch/patients/')) return 'patients'
  return 'overview'
}

function normalizePath(pathname: string): string {
  const trimmed = pathname.trim()
  if (!trimmed || trimmed === '/') return '/'
  const collapsed = trimmed.replace(/\/+/g, '/')
  return collapsed.endsWith('/') ? collapsed.slice(0, -1) : collapsed
}

export default function Dashboard() {
  const { user, logout, loading: isLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview')
  const normalizedLocationPath = useMemo(() => normalizePath(location.pathname), [location.pathname])

  // Log every location pathname change
  useEffect(() => {
    console.log('[DASHBOARD] Location pathname changed:', location.pathname)
  }, [location.pathname])

  // IMPORTANT: Sync activeTab with current route pathname (NO redirects here!)
  useEffect(() => {
    if (isLoading) return
    const newTab = tabFromPath(normalizedLocationPath)
    console.log('[DASHBOARD] Syncing activeTab:', { pathname: normalizedLocationPath, newTab })
    setActiveTab(newTab)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, normalizedLocationPath])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-slate-700 shadow-lg">
          Loading...
        </div>
      </div>
    )
  }

  if (activeTab === 'patient-portal') {
    return (
      <div className="min-h-screen overflow-hidden" style={{
        background: 'linear-gradient(135deg, #fafbff 0%, #f0f4ff 50%, #e8efff 100%)'
      }}>
        <PatientPortal activeTab={activeTab} />
      </div>
    )
  }

  const handleTabChange = (nextTab: ActiveTab) => {
    if (nextTab === activeTab) return

    console.log('[DASHBOARD] Tab change:', { from: activeTab, to: nextTab })
    const targetPath = normalizePath(tabPathMap[nextTab])
    console.log('[DASHBOARD] Navigate to:', { targetPath, currentPath: normalizedLocationPath })
    if (targetPath && normalizedLocationPath !== targetPath) {
      navigate(targetPath)
    }
  }

  const renderContent = () => {
    const normalizedRole = (user?.role || '').trim().toLowerCase()
    console.log('[DASHBOARD] renderContent:', { activeTab, normalizedRole })

    switch (activeTab) {
      case 'overview':
        if (normalizedRole === 'staff') return <MyProfileTab />
        return <Overview />
      case 'patients':
        return <PatientManagement />
      case 'daily-operations':
        return <DailyOperations />
      case 'staff':
        return <StaffManagement />
      case 'payroll':
        return <PayrollDashboard />
      case 'staff-profile':
        return <MyProfileTab />
      case 'staff-salary':
        return <SalaryTab />
      case 'staff-attendance':
        return <AttendanceTab />
      case 'staff-tasks':
        return <TasksTab />
      case 'staff-notifications':
        return <NotificationsTab />
      case 'staff-performance':
        return <PerformanceTab />
      case 'inventory':
        return <InventoryManagement />
      case 'analytics':
        return <Analytics />
      case 'reports':
        return <Reports />
      case 'lis':
        return <LIS activeTab={activeTab} />
      case 'payments':
        return <Payments activeTab={activeTab} />
      case 'accounting':
        return <Accounting activeTab={activeTab} />
      case 'accounts':
        return <Accounts />
      case 'hr':
        return <HR activeTab={activeTab} />
      case 'doctor-portal':
        return normalizedRole === 'doctor' ? <DoctorPortal /> : <DoctorManagementCRMModule />
      case 'branch-management':
        return <BranchManagement />
      case 'ceo':
        return normalizedRole === 'super_admin' ? <CeoDashboard /> : <Overview />
      default:
        if (normalizedRole === 'staff') return <MyProfileTab />
        return <Overview />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{
      background: 'linear-gradient(135deg, #fafbff 0%, #f0f4ff 50%, #e8efff 100%)'
    }}>
      <Sidebar activeTab={activeTab} setActiveTab={handleTabChange} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header user={user} onLogout={logout} />
        <main className="flex-1 overflow-x-hidden overflow-y-auto p-8">
          <div className="max-w-[1600px] mx-auto">
            {renderContent()}
          </div>
        </main>
      </div>
    </div>
  )
}
