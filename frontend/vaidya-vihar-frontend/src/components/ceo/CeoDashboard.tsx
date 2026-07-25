import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import toast from 'react-hot-toast'
import CeoSecurityGuard from './CeoSecurityGuard'
import {
  askCeoAssistant,
  CeoApprovalItem,
  CeoAskNlpResponse,
  CeoDashboardResponse,
  CeoDailyBriefResponse,
  CeoExecutiveItem,
  CeoMasterDataBranch,
  CeoSimulationResponse,
  createCeoBranch,
  decideCeoApproval,
  getCeoApprovals,
  getCeoDashboard,
  getCeoDailyBrief,
  getCeoExecutives,
  getCeoMasterData,
  simulateCeo,
} from './api'

const CARD_CLASS = 'bg-white rounded-xl shadow-lg p-6 border border-gray-100 hover:shadow-xl transition-shadow'

const toCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

const toNumber = (value: number) => new Intl.NumberFormat('en-IN').format(Math.round(Number(value || 0)))

const toPercent = (value: number, digits = 2) => `${Number(value || 0).toFixed(digits)}%`

type CeoTab = 'dashboard' | 'master-data' | 'approvals' | 'executives' | 'simulator'

export default function CeoDashboard() {
  const [activeTab, setActiveTab] = useState<CeoTab>('dashboard')
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState<CeoDashboardResponse | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [asking, setAsking] = useState(false)
  const [assistantResult, setAssistantResult] = useState<CeoAskNlpResponse | null>(null)
  const [showFinancialDrillDown, setShowFinancialDrillDown] = useState(false)

  const [branches, setBranches] = useState<CeoMasterDataBranch[]>([])
  const [masterDataLoading, setMasterDataLoading] = useState(false)
  const [savingBranch, setSavingBranch] = useState(false)
  const [branchForm, setBranchForm] = useState({ name: '', city: '', state: '', phone: '' })

  const [approvals, setApprovals] = useState<CeoApprovalItem[]>([])
  const [approvalsLoading, setApprovalsLoading] = useState(false)
  const [approvalBusyId, setApprovalBusyId] = useState<number | null>(null)

  const [executives, setExecutives] = useState<CeoExecutiveItem[]>([])
  const [executivesLoading, setExecutivesLoading] = useState(false)

  const [dailyBrief, setDailyBrief] = useState<CeoDailyBriefResponse | null>(null)
  const [dailyBriefLoading, setDailyBriefLoading] = useState(false)

  const [simForm, setSimForm] = useState({ target_city: '', initial_investment: '', projected_staff_count: '' })
  const [simulating, setSimulating] = useState(false)
  const [simulationResult, setSimulationResult] = useState<CeoSimulationResponse | null>(null)

  const loadDashboard = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await getCeoDashboard()
      setDashboard(result)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to load CEO dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDashboard()
    void loadDailyBrief()
  }, [])

  useEffect(() => {
    if (activeTab === 'master-data') {
      void loadMasterData()
    }
    if (activeTab === 'approvals') {
      void loadApprovals()
    }
    if (activeTab === 'executives') {
      void loadExecutives()
    }
  }, [activeTab])

  const askAssistant = async () => {
    const trimmed = query.trim()
    if (!trimmed) return
    setAsking(true)
    try {
      const result = await askCeoAssistant(trimmed)
      setAssistantResult(result)
    } catch {
      setAssistantResult({
        query: trimmed,
        intent: 'error',
        answer: 'Unable to process this request right now.',
        data_points: [],
        suggestions: [],
        generated_at: new Date().toISOString(),
      })
    } finally {
      setAsking(false)
    }
  }

  const loadMasterData = async () => {
    setMasterDataLoading(true)
    try {
      const data = await getCeoMasterData()
      setBranches(data.branches || [])
    } catch {
      setBranches([])
    } finally {
      setMasterDataLoading(false)
    }
  }

  const submitNewBranch = async () => {
    const name = branchForm.name.trim()
    const city = branchForm.city.trim()
    const state = branchForm.state.trim()
    const phone = branchForm.phone.trim()
    if (!name || !city || !state || !phone) return

    setSavingBranch(true)
    try {
      await createCeoBranch({ name, city, state, phone })
      setBranchForm({ name: '', city: '', state: '', phone: '' })
      await loadMasterData()
      toast.success('Branch created successfully')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to create branch')
    } finally {
      setSavingBranch(false)
    }
  }

  const loadApprovals = async () => {
    setApprovalsLoading(true)
    try {
      const data = await getCeoApprovals()
      setApprovals(data.items || [])
    } catch {
      setApprovals([])
    } finally {
      setApprovalsLoading(false)
    }
  }

  const handleApprovalDecision = async (id: number, status: 'approved' | 'rejected') => {
    setApprovalBusyId(id)
    try {
      await decideCeoApproval(id, status)
      await loadApprovals()
      toast.success(status === 'approved' ? 'Request approved' : 'Request rejected')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to update approval')
    } finally {
      setApprovalBusyId(null)
    }
  }

  const loadExecutives = async () => {
    setExecutivesLoading(true)
    try {
      const data = await getCeoExecutives()
      setExecutives(data.items || [])
    } catch {
      setExecutives([])
    } finally {
      setExecutivesLoading(false)
    }
  }

  const executiveBadgeClass = (item: CeoExecutiveItem) => {
    if (item.staff_attrition_percent <= 8 && item.revenue >= 500000) return 'bg-green-100 text-green-800'
    if (item.staff_attrition_percent <= 15 && item.revenue >= 250000) return 'bg-amber-100 text-amber-800'
    return 'bg-red-100 text-red-800'
  }

  const loadDailyBrief = async () => {
    setDailyBriefLoading(true)
    try {
      const data = await getCeoDailyBrief()
      setDailyBrief(data)
    } catch {
      setDailyBrief(null)
      toast.error('Unable to load daily brief')
    } finally {
      setDailyBriefLoading(false)
    }
  }

  const runSimulation = async () => {
    const target_city = simForm.target_city.trim()
    const initial_investment = Number(simForm.initial_investment)
    const projected_staff_count = Number(simForm.projected_staff_count)
    if (!target_city || !initial_investment || !projected_staff_count) return

    setSimulating(true)
    try {
      const result = await simulateCeo({ target_city, initial_investment, projected_staff_count })
      setSimulationResult(result)
      toast.success('Simulation completed')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  const machineUtilizationSeries = useMemo(() => {
    if (!dashboard) return []
    const used = Number(dashboard.kpis.operational.machine_utilization_percent || 0)
    return [
      { label: 'Utilized', value: Math.max(0, Math.min(100, used)) },
      { label: 'Idle', value: Math.max(0, 100 - used) },
    ]
  }, [dashboard])

  const financialSparkline = useMemo(() => {
    if (!dashboard) return []
    if (dashboard.charts.financial_daily_revenue?.length > 0) {
      return dashboard.charts.financial_daily_revenue
    }
    if (dashboard.charts.revenue_trend?.length > 0) {
      return dashboard.charts.revenue_trend
    }

    const base = Number(dashboard.kpis.financial.revenue_month || 0) / 30
    return Array.from({ length: 7 }).map((_, index) => ({
      label: `D${index + 1}`,
      value: Math.max(0, Math.round(base * (0.8 + (index % 3) * 0.13))),
    }))
  }, [dashboard])

  const salesBranchBars = useMemo(() => {
    if (!dashboard) return []
    if (dashboard.sales_branch_breakdown.length === 0) {
      return [
        {
          branch: 'All Branches',
          referrals: Number(dashboard.kpis.sales.doctor_referrals_total || 0),
          visits: Number(dashboard.kpis.sales.patient_visits_total || 0),
        },
      ]
    }
    return dashboard.sales_branch_breakdown.map((row) => ({
      branch: row.branch_name,
      referrals: row.doctor_referrals,
      visits: row.patient_visits,
    }))
  }, [dashboard])

  return (
    <CeoSecurityGuard>
      <section className="space-y-5 rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-300">CEO Command Center</p>
            <h2 className="mt-2 text-2xl font-black text-slate-900 dark:text-slate-100">Big 5 Strategic Dashboard</h2>
            {dashboard?.generated_at && (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-300">Updated: {new Date(dashboard.generated_at).toLocaleString()}</p>
            )}
          </div>
          <button onClick={() => void loadDashboard()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black">
            Refresh
          </button>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-2 border border-gray-200 flex flex-wrap gap-2">
          {[
            { key: 'dashboard', label: 'Dashboard' },
            { key: 'master-data', label: 'Master Data' },
            { key: 'approvals', label: 'Approvals' },
            { key: 'executives', label: 'Executives' },
            { key: 'simulator', label: 'Simulator' },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key as CeoTab)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold ${
                activeTab === tab.key ? 'bg-blue-600 text-white' : 'bg-gray-100 text-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'dashboard' && (

        <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-800 dark:bg-indigo-900/30">
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Ask your CEO Assistant</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  void askAssistant()
                }
              }}
              placeholder="Ask: How is revenue trending this month?"
              className="min-w-[260px] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
            <button
              onClick={() => void askAssistant()}
              disabled={asking || !query.trim()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {asking ? 'Thinking...' : 'Ask'}
            </button>
          </div>
          {assistantResult && (
            <div className="mt-3 rounded-lg border border-indigo-200 bg-white p-3 text-sm dark:border-indigo-700 dark:bg-slate-900">
              <p className="font-semibold text-slate-900 dark:text-slate-100">{assistantResult.answer}</p>
              {assistantResult.data_points.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600 dark:text-slate-300">
                  {assistantResult.data_points.map((point) => (
                    <span key={point.label} className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">
                      {point.label}: {point.value}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
        )}

        {activeTab === 'dashboard' && (loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900">Loading CEO dashboard...</div>
        ) : error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-950/30">{error}</div>
        ) : dashboard ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className={CARD_CLASS}>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Financial Health</p>
                  <button type="button" onClick={() => setShowFinancialDrillDown(true)} className="rounded bg-emerald-600 px-2 py-1 text-[11px] font-semibold text-white hover:bg-emerald-700">View Branch Drill-Down</button>
                </div>
                <p className="text-2xl font-black text-slate-900">{toCurrency(dashboard.kpis.financial.revenue_month)}</p>
                <div className="mt-1 space-y-1 text-xs text-slate-500">
                  <p>Revenue: {toCurrency(dashboard.kpis.financial.revenue_month)}</p>
                  <p>Expense: {toCurrency(dashboard.kpis.financial.expense_month)}</p>
                  <p>Net: {toCurrency(dashboard.kpis.financial.net_month)}</p>
                </div>
                <div className="mt-4 h-28">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={financialSparkline}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" hide />
                      <YAxis hide />
                      <Tooltip formatter={(value) => toCurrency(Number(value || 0))} />
                      <Area type="monotone" dataKey="value" stroke="#2563eb" fill="#bfdbfe" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className={CARD_CLASS}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Operational Efficiency</p>
                <p className="text-2xl font-black text-slate-900">{toPercent(dashboard.kpis.operational.machine_utilization_percent)}</p>
                <p className="mt-1 text-xs text-slate-500">Avg TAT {dashboard.kpis.operational.average_tat_minutes.toFixed(2)} min</p>
                <div className="mt-4 h-28">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={machineUtilizationSeries} dataKey="value" nameKey="label" innerRadius={26} outerRadius={40}>
                        <Cell fill="#16a34a" />
                        <Cell fill="#e5e7eb" />
                      </Pie>
                      <Tooltip formatter={(value) => toPercent(Number(value || 0))} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className={CARD_CLASS}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sales & Marketing</p>
                <p className="text-2xl font-black text-slate-900">{toNumber(dashboard.kpis.sales.doctor_referrals_total + dashboard.kpis.sales.patient_visits_total)}</p>
                <p className="mt-1 text-xs text-slate-500">Referrals {toNumber(dashboard.kpis.sales.doctor_referrals_total)} | Visits {toNumber(dashboard.kpis.sales.patient_visits_total)}</p>
                <div className="mt-4 h-28">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={salesBranchBars}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="branch" hide />
                      <YAxis hide />
                      <Tooltip formatter={(value) => toNumber(Number(value || 0))} />
                      <Bar dataKey="referrals" fill="#7c3aed" />
                      <Bar dataKey="visits" fill="#f59e0b" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className={CARD_CLASS}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">People & Culture</p>
                <p className="text-2xl font-black text-slate-900">{toPercent(dashboard.kpis.people.attendance_rate, 1)}</p>
                <div className="mt-3 space-y-1 text-sm text-slate-700">
                  <p className="font-semibold">Attrition: {toPercent(dashboard.kpis.people.attrition_rate)}</p>
                  <p>Present: {toNumber(dashboard.kpis.people.present_today)} / {toNumber(dashboard.kpis.people.active_staff)}</p>
                  <p>Pending Leaves: {toNumber(dashboard.kpis.people.pending_leave_requests)}</p>
                </div>
              </div>

              <div className={CARD_CLASS}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Risk & Compliance</p>
                <p className="text-2xl font-black text-slate-900">{dashboard.kpis.risk.risk_score.toFixed(1)}</p>
                <div className="mt-3 space-y-1 text-sm text-slate-700">
                  <p className="font-semibold">License Renewals: {toNumber(dashboard.kpis.risk.pending_license_renewals)}</p>
                  <p>Statutory Pending: {toNumber(dashboard.kpis.risk.pending_statutory_compliance)}</p>
                  <p>Break-Glass 7d: {toNumber(dashboard.kpis.risk.break_glass_events_7d)}</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-indigo-600 text-lg font-semibold">📋 CEO Daily Brief - {new Date().toLocaleDateString('en-IN')}</h3>
                <button
                  type="button"
                  onClick={() => void loadDailyBrief()}
                  className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-semibold"
                >
                  Refresh
                </button>
              </div>
              <div className="mt-3 text-sm text-slate-700 whitespace-pre-line">
                {dailyBriefLoading ? 'Loading daily brief...' : dailyBrief?.brief || 'Daily brief is currently unavailable.'}
              </div>
            </div>

            {showFinancialDrillDown && (
              <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/60 p-4" onClick={() => setShowFinancialDrillDown(false)}>
                <div className="h-[88vh] w-[96vw] max-w-6xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl" onClick={(event) => event.stopPropagation()}>
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-black text-slate-900">Financial Health Drill-Down (Branch-wise)</h3>
                    <button className="rounded border px-3 py-1.5 text-sm" onClick={() => setShowFinancialDrillDown(false)}>Close</button>
                  </div>

                  <div className="mt-4 h-80 rounded-xl border border-slate-200 p-3">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dashboard.charts.financial_branch_revenue}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="branch_name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="revenue" fill="#2563eb" name="Revenue" />
                        <Bar dataKey="expense" fill="#f97316" name="Expense" />
                        <Bar dataKey="net" fill="#16a34a" name="Net" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
                    <table className="min-w-full text-sm">
                      <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
                        <tr>
                          <th className="px-3 py-2">Branch</th>
                          <th className="px-3 py-2">Revenue</th>
                          <th className="px-3 py-2">Expense</th>
                          <th className="px-3 py-2">Net</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dashboard.charts.financial_branch_revenue.map((row) => (
                          <tr key={row.branch_id || row.branch_name} className="border-t">
                            <td className="px-3 py-2">{row.branch_name}</td>
                            <td className="px-3 py-2">{toCurrency(row.revenue)}</td>
                            <td className="px-3 py-2">{toCurrency(row.expense)}</td>
                            <td className="px-3 py-2 font-semibold">{toCurrency(row.net)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : null)}

        {activeTab === 'master-data' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200 lg:col-span-1">
              <h3 className="text-indigo-600 text-lg font-semibold">Branch Management</h3>
              <div className="mt-4 space-y-3">
                <input
                  value={branchForm.name}
                  onChange={(event) => setBranchForm((prev) => ({ ...prev, name: event.target.value }))}
                  placeholder="Branch Name"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <input
                  value={branchForm.city}
                  onChange={(event) => setBranchForm((prev) => ({ ...prev, city: event.target.value }))}
                  placeholder="City"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <input
                  value={branchForm.state}
                  onChange={(event) => setBranchForm((prev) => ({ ...prev, state: event.target.value }))}
                  placeholder="State"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <input
                  value={branchForm.phone}
                  onChange={(event) => setBranchForm((prev) => ({ ...prev, phone: event.target.value }))}
                  placeholder="Phone"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <button
                  type="button"
                  onClick={() => void submitNewBranch()}
                  disabled={savingBranch}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold"
                >
                  {savingBranch ? 'Saving...' : 'Create Branch'}
                </button>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200 lg:col-span-2">
              <h3 className="text-indigo-600 text-lg font-semibold">Current Branches</h3>
              {masterDataLoading ? (
                <p className="mt-3 text-sm text-slate-500">Loading branches...</p>
              ) : (
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
                      <tr>
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">City</th>
                        <th className="px-3 py-2">State</th>
                        <th className="px-3 py-2">Phone</th>
                      </tr>
                    </thead>
                    <tbody>
                      {branches.map((row) => (
                        <tr key={`${row.id}-${row.name}`} className="border-t">
                          <td className="px-3 py-2">{row.name}</td>
                          <td className="px-3 py-2">{row.city}</td>
                          <td className="px-3 py-2">{row.state}</td>
                          <td className="px-3 py-2">{row.phone}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'approvals' && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-indigo-600 text-lg font-semibold">Strategic Approvals Hub</h3>
            {approvalsLoading ? (
              <p className="mt-3 text-sm text-slate-500">Loading approvals...</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Request ID</th>
                      <th className="px-3 py-2">Branch</th>
                      <th className="px-3 py-2">Amount</th>
                      <th className="px-3 py-2">Reason</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvals.map((row) => (
                      <tr key={row.request_id} className="border-t">
                        <td className="px-3 py-2">{row.request_id}</td>
                        <td className="px-3 py-2">{row.branch}</td>
                        <td className="px-3 py-2">{toCurrency(row.amount)}</td>
                        <td className="px-3 py-2">{row.reason}</td>
                        <td className="px-3 py-2 capitalize">{row.status}</td>
                        <td className="px-3 py-2">
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => void handleApprovalDecision(row.request_id, 'approved')}
                              disabled={approvalBusyId === row.request_id}
                              className="bg-green-600 text-white px-4 py-2 rounded-lg"
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleApprovalDecision(row.request_id, 'rejected')}
                              disabled={approvalBusyId === row.request_id}
                              className="bg-red-600 text-white px-4 py-2 rounded-lg"
                            >
                              Reject
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'executives' && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <h3 className="text-indigo-600 text-lg font-semibold">Talent & Leadership</h3>
            {executivesLoading ? (
              <p className="mt-3 text-sm text-slate-500">Loading executives...</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Name</th>
                      <th className="px-3 py-2">Branch</th>
                      <th className="px-3 py-2">Revenue</th>
                      <th className="px-3 py-2">Staff Attrition %</th>
                      <th className="px-3 py-2">Patient Count</th>
                      <th className="px-3 py-2">Performance</th>
                    </tr>
                  </thead>
                  <tbody>
                    {executives.map((row, index) => (
                      <tr key={`${row.name}-${index}`} className="border-t">
                        <td className="px-3 py-2 font-semibold">{row.name}</td>
                        <td className="px-3 py-2">{row.branch}</td>
                        <td className="px-3 py-2">{toCurrency(row.revenue)}</td>
                        <td className="px-3 py-2">{toPercent(row.staff_attrition_percent)}</td>
                        <td className="px-3 py-2">{toNumber(row.patient_count)}</td>
                        <td className="px-3 py-2">
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${executiveBadgeClass(row)}`}>
                            {executiveBadgeClass(row).includes('green') ? 'High Performer' : executiveBadgeClass(row).includes('amber') ? 'Stable' : 'Needs Attention'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'simulator' && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <h3 className="text-indigo-600 text-lg font-semibold">Digital Twin Business Simulator</h3>
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <input
                  value={simForm.target_city}
                  onChange={(event) => setSimForm((prev) => ({ ...prev, target_city: event.target.value }))}
                  placeholder="Target City"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <input
                  value={simForm.initial_investment}
                  onChange={(event) => setSimForm((prev) => ({ ...prev, initial_investment: event.target.value }))}
                  placeholder="Initial Investment (₹)"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
                <input
                  value={simForm.projected_staff_count}
                  onChange={(event) => setSimForm((prev) => ({ ...prev, projected_staff_count: event.target.value }))}
                  placeholder="Projected Staff Count"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                />
              </div>
              <button
                type="button"
                onClick={() => void runSimulation()}
                disabled={simulating}
                className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold"
              >
                {simulating ? 'Simulating...' : 'Simulate'}
              </button>
            </div>

            {simulationResult && (
              <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                <h4 className="text-indigo-600 text-lg font-semibold">Simulation Result</h4>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div>
                    <p className="text-xs text-slate-500">Breakeven Months</p>
                    <p className="text-2xl font-black text-slate-900">{simulationResult.breakeven_months}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Projected Annual Revenue</p>
                    <p className="text-2xl font-black text-slate-900">{toCurrency(simulationResult.projected_annual_revenue)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Risk Factor</p>
                    <p className="text-2xl font-black text-slate-900">{simulationResult.risk_factor}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </CeoSecurityGuard>
  )
}