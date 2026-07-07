import { useEffect, useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Overview from './Overview'
import PatientManagement from './PatientManagement'
import StaffManagement from './StaffManagement'
import InventoryManagement from './InventoryManagement'
import Analytics from './Analytics'
import Reports from './Reports'
import LIS from './LIS'
import Payments from './Payments'
import Accounting from './Accounting'
import HR from './HR'
import PatientPortal from './PatientPortal'
import DoctorDashboard from './DoctorDashboard'
import BranchManagement from './BranchManagement'
import DailyOperations from './DailyOperations'

type ActiveTab = 'overview' | 'patients' | 'daily-operations' | 'staff' | 'inventory' | 'analytics' | 'reports' | 'lis' | 'payments' | 'accounting' | 'hr' | 'doctor-portal' | 'patient-portal' | 'branch-management'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview')

  useEffect(() => {
    if (!user?.role) return

    if (user.role === 'super_admin') {
      setActiveTab('branch-management')
      return
    }

    if (user.role === 'patient') {
      setActiveTab('patient-portal')
      return
    }

    if (user.role === 'doctor') {
      setActiveTab('doctor-portal')
      return
    }

    // staff, branch_admin and others
    setActiveTab('overview')
  }, [user?.role])

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <Overview />
      case 'patients':
        return <PatientManagement />
      case 'daily-operations':
        return <DailyOperations />
      case 'staff':
        return <StaffManagement />
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
      case 'hr':
        return <HR activeTab={activeTab} />
      case 'doctor-portal':
        return <DoctorDashboard doctorId={1} />
      case 'patient-portal':
        return <PatientPortal activeTab={activeTab} />
      case 'branch-management':
        return <BranchManagement />
      default:
        return <Overview />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{
      background: 'linear-gradient(135deg, #fafbff 0%, #f0f4ff 50%, #e8efff 100%)'
    }}>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
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
