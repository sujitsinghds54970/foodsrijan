

import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Login from '../components/auth/Login'
import Registration from '../components/auth/Registration'
import Dashboard from '../components/dashboard/Dashboard'
import CustomerPortal from '../components/dashboard/PatientPortal'
import SuperCEOWorkspace from './SuperCEO/layout/SuperCEOWorkspace'
import SuperCEOAccessGuard from './SuperCEO/layout/SuperCEOAccessGuard'
import { isManagerRole } from '../services/managerApi'
import { isStaffRole } from '../services/staffApi'

const OverviewPage = React.lazy(() => import('./SuperCEO/command/OverviewPage'))
const StrategyPage = React.lazy(() => import('./SuperCEO/command/StrategyPage'))
const PerformancePage = React.lazy(() => import('./SuperCEO/command/PerformancePage'))
const ProfilePage = React.lazy(() => import('./SuperCEO/people/ProfilePage'))
const ParentCompanyPage = React.lazy(() => import('./SuperCEO/business/ParentCompanyPage'))
const DepartmentsPage = React.lazy(() => import('./SuperCEO/people/DepartmentsPage'))
const DepartmentHeadsPage = React.lazy(() => import('./SuperCEO/people/DepartmentHeadsPage'))
const TalentPage = React.lazy(() => import('./SuperCEO/people/TalentPage'))
const AttendancePortfolioPage = React.lazy(() => import('./SuperCEO/people/AttendancePortfolioPage'))
const CompaniesPage = React.lazy(() => import('./SuperCEO/business/CompaniesPage'))
const CompanyWizardPage = React.lazy(() => import('./SuperCEO/business/CompanyWizardPage'))
const CompanyDetailPage = React.lazy(() => import('./SuperCEO/business/CompanyDetailPage'))
const CustomersPage = React.lazy(() => import('./SuperCEO/business/CustomersPage'))
const InvestorsPage = React.lazy(() => import('./SuperCEO/business/InvestorsPage'))
const MarketIntelPage = React.lazy(() => import('./SuperCEO/business/MarketIntelPage'))
const FinancePage = React.lazy(() => import('./SuperCEO/operations/FinancePage'))
const SupplyChainPage = React.lazy(() => import('./SuperCEO/operations/SupplyChainPage'))
const InnovationPage = React.lazy(() => import('./SuperCEO/operations/InnovationPage'))
const BoardPage = React.lazy(() => import('./SuperCEO/governance/BoardPage'))
const LegalPage = React.lazy(() => import('./SuperCEO/governance/LegalPage'))
const RiskPage = React.lazy(() => import('./SuperCEO/governance/RiskPage'))
const SustainabilityPage = React.lazy(() => import('./SuperCEO/governance/SustainabilityPage'))
const AuditPage = React.lazy(() => import('./SuperCEO/governance/AuditPage'))
const SoftwareUIPage = React.lazy(() => import('./SuperCEO/system/SoftwareUIPage'))
const IconPreviewPage = React.lazy(() => import('./SuperCEO/system/IconPreviewPage'))
const CompanyCEOWorkspace = React.lazy(() => import('./CompanyCEO/layout/CompanyCEOWorkspace'))
const CompanyCEOCommand = React.lazy(() => import('./CompanyCEO/command'))
const CompanyCEOOperations = React.lazy(() => import('./CompanyCEO/operations'))
const CompanyCEOCommercial = React.lazy(() => import('./CompanyCEO/commercial'))
const CompanyCEOPeople = React.lazy(() => import('./CompanyCEO/people'))
const CompanyCEOFinanceLegal = React.lazy(() => import('./CompanyCEO/finance-legal'))
const CompanyCEOGrowth = React.lazy(() => import('./CompanyCEO/growth'))
const CompanyCEOIntelligence = React.lazy(() => import('./CompanyCEO/intelligence'))
const CompanyCEOGovernanceTech = React.lazy(() => import('./CompanyCEO/governance-tech'))
const ManagerWorkspace = React.lazy(() => import('./Manager/layout/ManagerWorkspace'))
const ManagerCommand = React.lazy(() => import('./Manager/command'))
const ManagerDailyOps = React.lazy(() => import('./Manager/daily-ops'))
const ManagerTeam = React.lazy(() => import('./Manager/team'))
const ManagerCommercial = React.lazy(() => import('./Manager/commercial'))
const ManagerFinance = React.lazy(() => import('./Manager/finance'))
const ManagerQuality = React.lazy(() => import('./Manager/quality'))
const ManagerIntelligence = React.lazy(() => import('./Manager/intelligence'))
const StaffWorkspace = React.lazy(() => import('./Staff/layout/StaffWorkspace'))
const StaffRoutes = React.lazy(() => import('./Staff'))

export default function Home() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showRegistration, setShowRegistration] = useState(false)
  const pathname = location.pathname
  const hasCustomerSession = typeof window !== 'undefined' && Boolean(localStorage.getItem('patient_portal_token'))
  const normalizedRole = (user?.role || '').trim().toLowerCase()
  const isCompanyCeoRole = normalizedRole === 'company_ceo'
  const isManagerRoleUser = isManagerRole(user?.role)
  const isSuperAdminRole = Boolean(user?.is_super_admin || normalizedRole === 'super_admin' || normalizedRole === 'super_ceo')
  const isCustomerRoute = pathname.startsWith('/patient-portal')
  const isSuperAdminRoute = pathname.startsWith('/super-admin') || pathname.startsWith('/super-ceo')
  const isCompanyCeoRoute = pathname.startsWith('/company-ceo')
  const isManagerRoute = pathname.startsWith('/manager')
  const isStaffRoute = pathname.startsWith('/staff')
  const isStaffRoleUser = isStaffRole(user?.role)
  const isDashboardRoute = pathname.startsWith('/branch') || pathname.startsWith('/staff') || pathname.startsWith('/ceo') || pathname.startsWith('/super-admin') || pathname.startsWith('/super-ceo') || pathname.startsWith('/company-ceo') || isManagerRoute || pathname === '/'

  // Role-based redirect on initial login
  useEffect(() => {
    if (loading || !user) return

    if (isCompanyCeoRole && !isCompanyCeoRoute) {
      navigate('/company-ceo/command/overview', { replace: true })
      return
    }
    if (isManagerRoleUser && !isManagerRoute) {
      navigate('/manager/dashboard', { replace: true })
      return
    }
    if (isStaffRoleUser && !isStaffRoute) {
      navigate('/staff/dashboard', { replace: true })
      return
    }
    
    // Only redirect if user is on root path or unspecified route
    if (isDashboardRoute && pathname !== '/') return // Allow navigation within dashboard
    
    if (isSuperAdminRole && !pathname.startsWith('/super-ceo') && !pathname.startsWith('/super-admin')) {
      navigate('/super-ceo/overview', { replace: true })
    } else if ((normalizedRole === 'branch_admin' || normalizedRole === 'branch_director') && !pathname.startsWith('/branch')) {
      navigate('/branch/dashboard', { replace: true })
    } else if (isStaffRoleUser && !pathname.startsWith('/staff')) {
      navigate('/staff/dashboard', { replace: true })
    }
  }, [loading, user, navigate, pathname, isDashboardRoute, isSuperAdminRole, isCompanyCeoRole, isCompanyCeoRoute, isManagerRoleUser, isManagerRoute, isStaffRoleUser, isStaffRoute, normalizedRole])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    if (isCustomerRoute || hasCustomerSession) {
      return <CustomerPortal activeTab="patient-portal" />
    }

    return showRegistration ? (
      <Registration onSwitchToLogin={() => setShowRegistration(false)} />
    ) : (
      <Login onSwitchToRegistration={() => setShowRegistration(true)} />
    )
  }

  if ((user.role || '').trim().toLowerCase() === 'patient') {
    return <CustomerPortal activeTab="patient-portal" />
  }

  if (isCompanyCeoRoute) {
    return isCompanyCeoRole ? (
      <React.Suspense fallback={<div className="company-ceo-route-state">Loading company command…</div>}>
        <Routes>
          <Route path="/company-ceo" element={<Navigate to="/company-ceo/command/overview" replace />} />
          <Route path="/company-ceo/*" element={<CompanyCEOWorkspace />}>
            <Route path="command/*" element={<CompanyCEOCommand />} />
            <Route path="operations/*" element={<CompanyCEOOperations />} />
            <Route path="commercial/*" element={<CompanyCEOCommercial />} />
            <Route path="people/*" element={<CompanyCEOPeople />} />
            <Route path="finance-legal/*" element={<CompanyCEOFinanceLegal />} />
            <Route path="growth/*" element={<CompanyCEOGrowth />} />
            <Route path="intelligence/*" element={<CompanyCEOIntelligence />} />
            <Route path="governance-tech/*" element={<CompanyCEOGovernanceTech />} />
            <Route path="*" element={<Navigate to="/company-ceo/command/overview" replace />} />
          </Route>
        </Routes>
      </React.Suspense>
    ) : <Navigate to="/" replace />
  }

  if (isCompanyCeoRole) {
    return <Navigate to="/company-ceo/command/overview" replace />
  }

  if (isManagerRoute) {
    return isManagerRoleUser ? (
      <React.Suspense fallback={<div className="manager-route-state">Loading outlet command…</div>}>
        <Routes>
          <Route path="/manager" element={<Navigate to="/manager/dashboard" replace />} />
          <Route path="/manager/*" element={<ManagerWorkspace />}>
            <Route index element={<Navigate to="/manager/dashboard" replace />} />
            <Route path="overview" element={<Navigate to="/manager/dashboard" replace />} />
            <Route path="profile" element={<Navigate to="/manager/profile/about" replace />} />
            <Route path="command/overview" element={<Navigate to="/manager/dashboard" replace />} />
            <Route path="command/profile" element={<Navigate to="/manager/profile/about" replace />} />
            <Route path="command/responsibilities" element={<Navigate to="/manager/intelligence/tasks" replace />} />
            <Route path="operations/daily-operations" element={<Navigate to="/manager/daily-ops/operations" replace />} />
            <Route path="operations/roster" element={<Navigate to="/manager/team/attendance" replace />} />
            <Route path="operations/production" element={<Navigate to="/manager/daily-ops/kitchen" replace />} />
            <Route path="operations/maintenance" element={<Navigate to="/manager/quality/maintenance" replace />} />
            <Route path="inventory/stock" element={<Navigate to="/manager/finance/inventory" replace />} />
            <Route path="inventory/indents" element={<Navigate to="/manager/finance/purchasing" replace />} />
            <Route path="inventory/wastage" element={<Navigate to="/manager/finance/recipes" replace />} />
            <Route path="people/team" element={<Navigate to="/manager/team/staff" replace />} />
            <Route path="people/attendance" element={<Navigate to="/manager/team/attendance" replace />} />
            <Route path="people/training" element={<Navigate to="/manager/team/staff" replace />} />
            <Route path="commercial/sales" element={<Navigate to="/manager/commercial/orders" replace />} />
            <Route path="compliance/food-safety" element={<Navigate to="/manager/quality/food-safety" replace />} />
            <Route path="compliance/audits" element={<Navigate to="/manager/quality/security" replace />} />
            <Route path="daily-ops/*" element={<ManagerDailyOps />} />
            <Route path="team/*" element={<ManagerTeam />} />
            <Route path="commercial/*" element={<ManagerCommercial />} />
            <Route path="finance/*" element={<ManagerFinance />} />
            <Route path="quality/*" element={<ManagerQuality />} />
            <Route path="intelligence/*" element={<ManagerIntelligence />} />
            <Route path="*" element={<ManagerCommand />} />
          </Route>
        </Routes>
      </React.Suspense>
    ) : <Navigate to="/" replace />
  }
  if (isManagerRoleUser) return <Navigate to="/manager/dashboard" replace />
  if (isStaffRoute) {
    return isStaffRoleUser ? (
      <React.Suspense fallback={<div className="manager-route-state">Loading staff workspace…</div>}>
        <Routes>
          <Route path="/staff" element={<Navigate to="/staff/dashboard" replace />} />
          <Route path="/staff/*" element={<StaffWorkspace />}>
            <Route path="*" element={<StaffRoutes />} />
          </Route>
        </Routes>
      </React.Suspense>
    ) : <Navigate to="/" replace />
  }
  if (isStaffRoleUser) return <Navigate to="/staff/dashboard" replace />

  if (isSuperAdminRole && !isSuperAdminRoute && pathname === '/') {
    return <Navigate to="/super-ceo/overview" replace />
  }

  if (isSuperAdminRoute) {
    return (
      <React.Suspense fallback={<div className="super-ceo-route-state">Loading executive workspace…</div>}>
        <Routes>
          <Route path="/super-admin/*" element={<Navigate to="/super-ceo/overview" replace />} />
          <Route path="/super-ceo" element={<Navigate to="/super-ceo/overview" replace />} />
          <Route path="/super-ceo/*" element={<SuperCEOWorkspace />}>
            <Route path="overview" element={<OverviewPage />} />
            <Route path="strategy" element={<StrategyPage />} />
            <Route path="performance" element={<PerformancePage />} />
            <Route path="people/profile/:profileTab?" element={<ProfilePage />} />
            <Route path="people/departments" element={<DepartmentsPage />} />
            <Route path="people/department-heads" element={<DepartmentHeadsPage />} />
            <Route path="people/talent" element={<TalentPage />} />
            <Route path="people/attendance" element={<AttendancePortfolioPage />} />
            <Route path="business/companies" element={<CompaniesPage />} />
            <Route path="business/companies/new" element={<CompanyWizardPage />} />
            <Route path="business/companies/:companyId" element={<CompanyDetailPage />} />
            <Route path="business/companies/:companyId/edit" element={<CompanyWizardPage />} />
            <Route path="business/companies/:companyId/:companyTab" element={<CompanyDetailPage />} />
            <Route path="business/customers" element={<CustomersPage />} />
            <Route path="business/investors" element={<InvestorsPage />} />
            <Route path="business/market-intelligence" element={<MarketIntelPage />} />
            <Route path="operations/finance" element={<FinancePage />} />
            <Route path="operations/supply-chain" element={<SupplyChainPage />} />
            <Route path="operations/innovation" element={<InnovationPage />} />
            <Route path="governance/board" element={<BoardPage />} />
            <Route path="governance/legal" element={<LegalPage />} />
            <Route path="governance/risk" element={<RiskPage />} />
            <Route path="governance/sustainability" element={<SustainabilityPage />} />
            <Route path="governance/audit" element={<AuditPage />} />
            <Route
              path="system/software-ui"
              element={(
                <SuperCEOAccessGuard requiredPermission="manage_system_settings">
                  <SoftwareUIPage />
                </SuperCEOAccessGuard>
              )}
            />
            <Route path="system/parent-company/:companyTab?" element={<ParentCompanyPage />} />
            {process.env.NODE_ENV === 'development' && <Route path="system/icon-preview" element={<IconPreviewPage />} />}
            <Route path="*" element={<Navigate to="/super-ceo/overview" replace />} />
          </Route>
        </Routes>
      </React.Suspense>
    )
  }

  return <Dashboard />
}
