import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext'
import Accounts from '../dashboard/Accounts'
import Analytics from '../dashboard/Analytics'
import DailyOperations from '../dashboard/DailyOperations'
import InventoryManagement from '../dashboard/InventoryManagement'
import Payments from '../dashboard/Payments'

type BranchDetailTab = 'daily-operations' | 'inventory' | 'analytics' | 'accounts' | 'payments'

const tabs: Array<{ id: BranchDetailTab; label: string }> = [
  { id: 'daily-operations', label: 'Daily Operations' },
  { id: 'inventory', label: 'Inventory' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'accounts', label: 'Accounts' },
  { id: 'payments', label: 'Payments' },
]

export default function BranchDetailsDashboard() {
  const { user } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<BranchDetailTab>('daily-operations')

  const parsedBranchId = useMemo(() => {
    const match = location.pathname.match(/^\/branch-details\/(\d+)$/)
    const id = Number(match?.[1] || '')
    return Number.isFinite(id) && id > 0 ? id : null
  }, [location.pathname])

  if ((user?.role || '').trim().toLowerCase() !== 'super_admin') {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        This page is only available for Super Admin.
      </div>
    )
  }

  if (!parsedBranchId) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-700">
        Invalid branch selected.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white p-5 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Branch Drill-Down</p>
          <h2 className="text-2xl font-black text-slate-900">Branch Details • #{parsedBranchId}</h2>
        </div>
        <button
          type="button"
          onClick={() => navigate('/branch/management')}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black"
        >
          Back to Branch Management
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab.id
                ? 'bg-indigo-600 text-white shadow'
                : 'bg-white text-slate-700 hover:bg-slate-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div>
        {activeTab === 'daily-operations' && <DailyOperations branchId={parsedBranchId} />}
        {activeTab === 'inventory' && <InventoryManagement branchId={parsedBranchId} />}
        {activeTab === 'analytics' && <Analytics branchId={parsedBranchId} />}
        {activeTab === 'accounts' && <Accounts branchId={parsedBranchId} />}
        {activeTab === 'payments' && <Payments activeTab="payments" branchId={parsedBranchId} />}
      </div>
    </div>
  )
}
