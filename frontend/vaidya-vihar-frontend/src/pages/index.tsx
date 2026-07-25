


import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import Login from '../components/auth/Login'
import Registration from '../components/auth/Registration'
import Dashboard from '../components/dashboard/Dashboard'
import PatientPortal from '../components/dashboard/PatientPortal'

export default function Home() {
  const { user, loading } = useAuth()
  const [showRegistration, setShowRegistration] = useState(false)
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '/'
  const hasPatientSession = typeof window !== 'undefined' && Boolean(localStorage.getItem('patient_portal_token'))
  const isPatientRoute = pathname.startsWith('/patient-portal')

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    if (isPatientRoute || hasPatientSession) {
      return <PatientPortal activeTab="patient-portal" />
    }

    return showRegistration ? (
      <Registration onSwitchToLogin={() => setShowRegistration(false)} />
    ) : (
      <Login onSwitchToRegistration={() => setShowRegistration(true)} />
    )
  }

  if ((user.role || '').trim().toLowerCase() === 'patient') {
    return <PatientPortal activeTab="patient-portal" />
  }

  return <Dashboard />
}
