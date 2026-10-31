import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Overview from './Overview'
import CustomerManagement from './PatientManagement'
import StaffManagement from '../staff/StaffManagementModule'
import InventoryManagement from './InventoryManagement'
import Analytics from './Analytics'
import Orders from './Reports'
import BranchLISDashboard from '../branch/BranchLISDashboard'
import BranchPaymentsDashboard from '../branch/BranchPaymentsDashboard'
import Accounting from './Accounting'
import Accounts from './Accounts'
import HR from './HR'
import PayrollDashboard from '../payroll/PayrollDashboard'
import BranchDirectorSalaryDashboard from '../branch-director/BranchDirectorSalaryDashboard'
import CustomerPortal from './PatientPortal'
import StaffManagementCRMModule from '../doctors/DoctorManagementCRMModule'
import StaffPortal from './DoctorPortal'
import BranchManagement from './BranchManagement'
import DailyOperations from './DailyOperations'
import MyProfileTab from '../staff/MyProfileTab'
import SalaryTab from '../staff/SalaryTab'
import AttendanceTab from '../staff/AttendanceTab'
import TasksTab from '../staff/TasksTab'
import NotificationsTab from '../staff/NotificationsTab'
import PerformanceTab from '../staff/PerformanceTab'
import CeoDashboard from '../ceo/CeoDashboard'
import CeoOverview from '../ceo/CeoOverview'
import CeoComplianceLegal from '../ceo/CeoComplianceLegal'
import CeoStaffNetwork from '../ceo/CeoDoctorNetwork'
import CeoFinanceAccounts from '../ceo/CeoFinanceAccounts'
import CeoInventorySupply from '../ceo/CeoInventorySupply'
import CeoCustomerInsights from '../ceo/CeoPatientInsights'
import CeoPeopleCulture from '../ceo/CeoPeopleCulture'
import CeoSystemSettings from '../ceo/CeoSystemSettings'
import CeoProfile from '../ceo/CeoProfile'
import BranchDetailsDashboard from '../branch/BranchDetailsDashboard'
import BranchNotificationCenter from '../branch/BranchNotificationCenter'

type ActiveTab = 'overview' | 'ceo-overview' | 'ceo-profile' | 'ceo-people-culture' | 'ceo-finance-accounts' | 'ceo-doctor-network' | 'ceo-patient-insights' | 'ceo-inventory-supply' | 'ceo-compliance-legal' | 'ceo-system-settings' | 'customers' | 'daily-operations' | 'staff' | 'payroll' | 'branch-notifications' | 'staff-profile' | 'staff-salary' | 'staff-attendance' | 'staff-tasks' | 'staff-notifications' | 'staff-performance' | 'inventory' | 'analytics' | 'orders' | 'lis' | 'payments' | 'accounting' | 'accounts' | 'hr' | 'doctor-portal' | 'patient-portal' | 'branch-management' | 'ceo' | 'branch-details'

const tabPathMap: Record<ActiveTab, string> = {
  overview: '/branch/dashboard',
  'ceo-overview': '/ceo/overview',
  'ceo-profile': '/ceo/profile',
  'ceo-people-culture': '/ceo/people-and-culture',
  'ceo-finance-accounts': '/ceo/finance-accounts',
  'ceo-doctor-network': '/ceo/doctor-network',
  'ceo-patient-insights': '/ceo/patient-insights',
  'ceo-inventory-supply': '/ceo/inventory-supply',
  'ceo-compliance-legal': '/ceo/compliance-legal',
  'ceo-system-settings': '/ceo/system-settings',
  customers: '/branch/customers',
  'daily-operations': '/branch/daily-operations',
  staff: '/branch/staff',
  payroll: '/branch/payroll',
  'branch-notifications': '/branch/notifications',
  'staff-profile': '/staff/profile',
  'staff-salary': '/staff/salary',
  'staff-attendance': '/staff/attendance',
  'staff-tasks': '/staff/tasks',
  'staff-notifications': '/staff/notifications',
  'staff-performance': '/staff/performance',
  inventory: '/branch/inventory',
  analytics: '/branch/analytics',
  orders: '/branch/orders',
  lis: '/branch/lis',
  payments: '/branch/payments',
  accounting: '/branch/accounting',
  accounts: '/branch/accounts',
  hr: '/branch/hr',
  'doctor-portal': '/branch/doctor-portal',
  'patient-portal': '/branch/patient-portal',
  'branch-management': '/branch/management',
  ceo: '/ceo',
  'branch-details': '/branch-details',
}

function tabFromPath(pathname: string): ActiveTab {
  const path = normalizePath(pathname).toLowerCase()
  if (path === '/ceo/overview' || path.startsWith('/ceo/overview/')) return 'ceo-overview'
  if (path === '/ceo/profile' || path.startsWith('/ceo/profile/')) return 'ceo-profile'
  if (path === '/ceo/people-and-culture' || path.startsWith('/ceo/people-and-culture/')) return 'ceo-people-culture'
  if (path === '/ceo/finance-accounts' || path.startsWith('/ceo/finance-accounts/')) return 'ceo-finance-accounts'
  if (path === '/ceo/doctor-network' || path.startsWith('/ceo/doctor-network/')) return 'ceo-doctor-network'
  if (path === '/ceo/patient-insights' || path.startsWith('/ceo/patient-insights/')) return 'ceo-patient-insights'
  if (path === '/ceo/inventory-supply' || path.startsWith('/ceo/inventory-supply/')) return 'ceo-inventory-supply'
  if (path === '/ceo/compliance-legal' || path.startsWith('/ceo/compliance-legal/')) return 'ceo-compliance-legal'
  if (path === '/ceo/system-settings' || path.startsWith('/ceo/system-settings/')) return 'ceo-system-settings'
  if (path === '/branch/dashboard' || path.startsWith('/branch/dashboard/')) return 'overview'
  if (path === '/branch/staff' || path.startsWith('/branch/staff/')) return 'staff'
  if (path === '/branch/payroll' || path.startsWith('/branch/payroll/')) return 'payroll'
  if (path === '/branch/notifications' || path.startsWith('/branch/notifications/')) return 'branch-notifications'
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
  if (path === '/branch/orders' || path.startsWith('/branch/orders/')) return 'orders'
  if (path === '/branch/lis' || path.startsWith('/branch/lis/')) return 'lis'
  if (path === '/branch/payments' || path.startsWith('/branch/payments/')) return 'payments'
  if (path === '/branch/accounting' || path.startsWith('/branch/accounting/')) return 'accounting'
  if (path === '/branch/accounts' || path.startsWith('/branch/accounts/')) return 'accounts'
  if (path === '/branch/hr' || path.startsWith('/branch/hr/')) return 'hr'
  if (path === '/branch/doctor-portal' || path.startsWith('/branch/doctor-portal/')) return 'doctor-portal'
  if (path === '/branch/patient-portal' || path.startsWith('/branch/patient-portal/')) return 'patient-portal'
  if (path === '/branch-details' || path.startsWith('/branch-details/')) return 'branch-details'
  if (path === '/ceo' || path.startsWith('/ceo/')) return 'ceo'
  if (path === '/branch/customers' || path.startsWith('/branch/customers/')) return 'customers'
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

  // List of staff roles (not just 'staff', but also receptionist, technician, etc.)
  const isStaffRole = (role: string | undefined) => {
    const normalizedRole = (role || '').trim().toLowerCase()
    return normalizedRole !== 'super_admin' &&
      normalizedRole !== 'branch_admin' &&
      normalizedRole !== 'branch_director' &&
      normalizedRole !== 'doctor'
  }

  // Log every location pathname change
  useEffect(() => {
    console.log('[DASHBOARD] Location pathname changed:', location.pathname)
  }, [location.pathname])

  // Initial redirect based on user role
  useEffect(() => {
    if (isLoading || !user) return

    const userRole = (user.role || '').trim().toLowerCase()
    const isSystemAdmin = Boolean((user as any)?.is_super_admin || userRole === 'super_admin')
    const currentPath = normalizePath(window.location.pathname)
    console.log('[DASHBOARD] Checking role for redirect:', { role: userRole, isSystemAdmin, currentPath })

    // Redirect only from root/generic dashboard entry paths to prevent redirect loops on tab navigation.
    if (currentPath === '/' || currentPath === '/dashboard') {
      if (isSystemAdmin) {
        navigate('/super-admin/dashboard', { replace: true })
      } else if (userRole === 'branch_admin' || userRole === 'branch_director') {
        navigate('/branch/dashboard', { replace: true })
      } else if (isStaffRole(userRole)) {
        navigate('/staff/profile', { replace: true })
      }
    }
  }, [isLoading, user, navigate]) // REMOVED location.pathname to prevent re-redirect on tab change

  // IMPORTANT: Sync activeTab with current route pathname (NO redirects here!)
  useEffect(() => {
    if (isLoading) return
    const normalizedRole = (user?.role || '').trim().toLowerCase()
    const isSystemAdmin = Boolean((user as any)?.is_super_admin || normalizedRole === 'super_admin')
    if (
      isSystemAdmin &&
      (normalizedLocationPath === '/branch/daily-operations' ||
        normalizedLocationPath === '/branch/inventory' ||
        normalizedLocationPath === '/branch/analytics' ||
        normalizedLocationPath === '/branch/lis' ||
        normalizedLocationPath === '/branch/payments' ||
        normalizedLocationPath === '/branch/accounts' ||
        normalizedLocationPath === '/branch/doctor-portal' ||
        normalizedLocationPath === '/branch/patient-portal')
    ) {
      navigate('/branch/management', { replace: true })
      return
    }

    const newTab = tabFromPath(normalizedLocationPath)
    console.log('[DASHBOARD] Syncing activeTab:', { pathname: normalizedLocationPath, newTab })
    setActiveTab(newTab)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, navigate, normalizedLocationPath, user?.role])

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
        <CustomerPortal activeTab={activeTab} />
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
    const isSystemAdmin = Boolean((user as any)?.is_super_admin || normalizedRole === 'super_admin')
    console.log('[DASHBOARD] renderContent:', { activeTab, normalizedRole, isSystemAdmin })

    switch (activeTab) {
      case 'overview':
        if (isStaffRole(normalizedRole)) return <MyProfileTab />
        return <Overview />
      case 'ceo-overview':
        return isSystemAdmin ? <CeoOverview /> : <Overview />
      case 'ceo-profile':
        return isSystemAdmin ? <CeoProfile /> : <Overview />
      case 'ceo-people-culture':
        return isSystemAdmin ? <CeoPeopleCulture /> : <Overview />
      case 'ceo-finance-accounts':
        return isSystemAdmin ? <CeoFinanceAccounts /> : <Overview />
      case 'ceo-doctor-network':
        return isSystemAdmin ? <CeoStaffNetwork /> : <Overview />
      case 'ceo-patient-insights':
        return isSystemAdmin ? <CeoCustomerInsights /> : <Overview />
      case 'ceo-inventory-supply':
        return isSystemAdmin ? <CeoInventorySupply /> : <Overview />
      case 'ceo-compliance-legal':
        return isSystemAdmin ? <CeoComplianceLegal /> : <Overview />
      case 'ceo-system-settings':
        return isSystemAdmin ? <CeoSystemSettings /> : <Overview />
      case 'customers':
        return <CustomerManagement />
      case 'daily-operations':
        return <DailyOperations />
      case 'staff':
        return <StaffManagement />
      case 'payroll':
        return (normalizedRole === 'branch_director' || normalizedRole === 'branch_admin')
          ? <BranchDirectorSalaryDashboard />
          : <PayrollDashboard />
      case 'branch-notifications':
        return (normalizedRole === 'branch_director' || normalizedRole === 'branch_admin')
          ? <BranchNotificationCenter />
          : <NotificationsTab />
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
      case 'orders':
        return <Orders />
      case 'lis':
        return <BranchLISDashboard />
      case 'payments':
        return <BranchPaymentsDashboard />
      case 'accounting':
        return <Accounting activeTab={activeTab} />
      case 'accounts':
        return <Accounts />
      case 'hr':
        return <HR activeTab={activeTab} />
      case 'doctor-portal':
        return normalizedRole === 'doctor' ? <StaffPortal /> : <StaffManagementCRMModule />
      case 'branch-management':
        return <BranchManagement />
      case 'ceo':
        return isSystemAdmin ? <CeoDashboard /> : <Overview />
      case 'branch-details':
        return isSystemAdmin ? <BranchDetailsDashboard /> : <Overview />
      default:
        if (isStaffRole(normalizedRole)) return <MyProfileTab />
        return <Overview />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{
      background: 'linear-gradient(135deg, #fffaf6 0%, #f8f9fa 55%, #eef8f5 100%)'
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
