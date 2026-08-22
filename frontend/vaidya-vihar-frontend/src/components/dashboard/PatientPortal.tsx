import React, { useEffect, useState } from 'react'

import CustomerDashboard from '../customers/CustomerDashboard'
import CustomerB2CPhase1 from '../customers/CustomerB2CPhase1'
import CustomerPremiumPhase4 from '../customers/CustomerPremiumPhase4'

interface CustomerPortalProps {
  activeTab: string
}

const PATIENT_PORTAL_STORAGE_KEY = 'patient_portal_token'
const PATIENT_PORTAL_SESSION_EVENT = 'patient-portal-session-changed'

export default function CustomerPortal({ activeTab }: CustomerPortalProps) {
  const active = activeTab === 'patient-portal'
  const [hasCustomerSession, setHasCustomerSession] = useState(
    typeof window !== 'undefined' && Boolean(localStorage.getItem(PATIENT_PORTAL_STORAGE_KEY))
  )

  useEffect(() => {
    if (typeof window === 'undefined') return

    const syncSession = () => {
      setHasCustomerSession(Boolean(localStorage.getItem(PATIENT_PORTAL_STORAGE_KEY)))
    }

    syncSession()
    window.addEventListener('storage', syncSession)
    window.addEventListener(PATIENT_PORTAL_SESSION_EVENT, syncSession)

    return () => {
      window.removeEventListener('storage', syncSession)
      window.removeEventListener(PATIENT_PORTAL_SESSION_EVENT, syncSession)
    }
  }, [])

  if (!hasCustomerSession) {
    return <CustomerDashboard active={active} />
  }

  return (
    <div className="space-y-6">
      <CustomerDashboard active={active} />
      <CustomerB2CPhase1 active={active} />
      <CustomerPremiumPhase4 active={active} />
    </div>
  )
}

