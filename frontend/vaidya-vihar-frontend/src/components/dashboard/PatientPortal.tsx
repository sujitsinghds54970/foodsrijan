import React, { useEffect, useState } from 'react'

import PatientDashboard from '../patient/PatientDashboard'
import PatientB2CPhase1 from '../patient/PatientB2CPhase1'
import PatientPremiumPhase4 from '../patient/PatientPremiumPhase4'

interface PatientPortalProps {
  activeTab: string
}

const PATIENT_PORTAL_STORAGE_KEY = 'patient_portal_token'
const PATIENT_PORTAL_SESSION_EVENT = 'patient-portal-session-changed'

export default function PatientPortal({ activeTab }: PatientPortalProps) {
  const active = activeTab === 'patient-portal'
  const [hasPatientSession, setHasPatientSession] = useState(
    typeof window !== 'undefined' && Boolean(localStorage.getItem(PATIENT_PORTAL_STORAGE_KEY))
  )

  useEffect(() => {
    if (typeof window === 'undefined') return

    const syncSession = () => {
      setHasPatientSession(Boolean(localStorage.getItem(PATIENT_PORTAL_STORAGE_KEY)))
    }

    syncSession()
    window.addEventListener('storage', syncSession)
    window.addEventListener(PATIENT_PORTAL_SESSION_EVENT, syncSession)

    return () => {
      window.removeEventListener('storage', syncSession)
      window.removeEventListener(PATIENT_PORTAL_SESSION_EVENT, syncSession)
    }
  }, [])

  if (!hasPatientSession) {
    return <PatientDashboard active={active} />
  }

  return (
    <div className="space-y-6">
      <PatientDashboard active={active} />
      <PatientB2CPhase1 active={active} />
      <PatientPremiumPhase4 active={active} />
    </div>
  )
}

