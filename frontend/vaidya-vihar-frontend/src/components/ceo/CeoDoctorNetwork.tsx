import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import {
  ColumnDef,
  SortingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  CeoStaffCommissionSimulatorResponse,
  CeoStaffEngagementRelationshipResponse,
  CeoStaffFinancialCommissionResponse,
  CeoStaffGrowthAcquisitionResponse,
  CeoStaffGrowthWhatIfResponse,
  CeoStaffNetworkHealthResponse,
  CeoStaffOperationalExcellenceResponse,
  CeoStaffPayoutAutomationResponse,
  CeoStaffPerformanceAnalyticsResponse,
  CeoStaffWowFeaturesResponse,
  getCeoStaffCommissionSimulation,
  getCeoStaffEngagementRelationship,
  getCeoStaffFinancialCommission,
  getCeoStaffGrowthAcquisition,
  getCeoStaffGrowthWhatIfSimulation,
  getCeoStaffNetworkHealth,
  getCeoStaffOperationalExcellence,
  getCeoStaffPerformanceAnalytics,
  getCeoStaffWowFeatures,
  triggerCeoStaffPayoutAutomation,
} from './api'

const CARD_CLASS = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm'
const PIE_COLORS = ['#4f46e5', '#0ea5e9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']

const toCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

const getScoreColor = (score: number) => {
  if (score >= 80) return '#16a34a'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}

type LeaderboardRow = CeoStaffPerformanceAnalyticsResponse['leaderboard'][number]

const CeoStaffNetwork = () => {
  const [loading, setLoading] = useState(true)
  const [networkHealth, setNetworkHealth] = useState<CeoStaffNetworkHealthResponse | null>(null)
  const [performance, setPerformance] = useState<CeoStaffPerformanceAnalyticsResponse | null>(null)
  const [financial, setFinancial] = useState<CeoStaffFinancialCommissionResponse | null>(null)
  const [engagement, setEngagement] = useState<CeoStaffEngagementRelationshipResponse | null>(null)
  const [growth, setGrowth] = useState<CeoStaffGrowthAcquisitionResponse | null>(null)
  const [operational, setOperational] = useState<CeoStaffOperationalExcellenceResponse | null>(null)
  const [wow, setWow] = useState<CeoStaffWowFeaturesResponse | null>(null)
  const [sorting, setSorting] = useState<SortingState>([{ id: 'total_referrals', desc: true }])
  const [branchFilter, setBranchFilter] = useState('all')
  const [specialtyFilter, setSpecialtyFilter] = useState('all')
  const [timePeriodFilter, setTimePeriodFilter] = useState('all')
  const [selectedTrendStaffId, setSelectedTrendStaffId] = useState<number | null>(null)
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null)

  const [commissionStructure, setCommissionStructure] = useState('tiered')
  const [baseCommission, setBaseCommission] = useState(7)
  const [commissionSimulation, setCommissionSimulation] = useState<CeoStaffCommissionSimulatorResponse | null>(null)
  const [simulationLoading, setSimulationLoading] = useState(false)
  const [payoutLoading, setPayoutLoading] = useState(false)
  const [payoutResult, setPayoutResult] = useState<CeoStaffPayoutAutomationResponse | null>(null)

  const [growthSpecialty, setGrowthSpecialty] = useState('Cardiology')
  const [growthCommissionIncrease, setGrowthCommissionIncrease] = useState(5)
  const [growthWhatIf, setGrowthWhatIf] = useState<CeoStaffGrowthWhatIfResponse | null>(null)
  const [growthSimLoading, setGrowthSimLoading] = useState(false)
  const [doctorLoadError, setStaffLoadError] = useState(false)

  const [onboardingDraft, setOnboardingDraft] = useState({ doctor_name: '', city: '', specialty: '' })
  const [onboardingQueue, setOnboardingQueue] = useState<Array<{ doctor_name: string; city: string; specialty: string }>>([])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setStaffLoadError(false)
      try {
        const results = await Promise.allSettled([
          getCeoStaffNetworkHealth(),
          getCeoStaffPerformanceAnalytics(),
          getCeoStaffFinancialCommission(),
          getCeoStaffEngagementRelationship(),
          getCeoStaffGrowthAcquisition(),
          getCeoStaffOperationalExcellence(),
          getCeoStaffWowFeatures(),
        ])
        const networkResp = results[0].status === 'fulfilled' ? results[0].value : null
        const performanceResp = results[1].status === 'fulfilled' ? results[1].value : null
        const financialResp = results[2].status === 'fulfilled' ? results[2].value : null
        const engagementResp = results[3].status === 'fulfilled' ? results[3].value : null
        const growthResp = results[4].status === 'fulfilled' ? results[4].value : null
        const operationalResp = results[5].status === 'fulfilled' ? results[5].value : null
        const wowResp = results[6].status === 'fulfilled' ? results[6].value : null

        if (networkResp) setNetworkHealth(networkResp)
        if (performanceResp) {
          setPerformance(performanceResp)
          setSelectedTrendStaffId(performanceResp.referral_trend.by_doctor[0]?.doctor_id ?? null)
        }
        if (financialResp) setFinancial(financialResp)
        if (engagementResp) setEngagement(engagementResp)
        if (growthResp) setGrowth(growthResp)
        if (operationalResp) setOperational(operationalResp)
        if (wowResp) setWow(wowResp)
        setStaffLoadError(results.some((item) => item.status === 'rejected'))
      } catch {
        setStaffLoadError(true)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const runCommissionSimulation = async () => {
    setSimulationLoading(true)
    try {
      const response = await getCeoStaffCommissionSimulation({
        structure: commissionStructure,
        base_commission_percent: baseCommission,
      })
      setCommissionSimulation(response)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run commission simulation')
    } finally {
      setSimulationLoading(false)
    }
  }

  const runPayoutAutomation = async () => {
    setPayoutLoading(true)
    try {
      const response = await triggerCeoStaffPayoutAutomation()
      setPayoutResult(response)
      toast.success('Mock payout automation completed')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to trigger payout automation')
    } finally {
      setPayoutLoading(false)
    }
  }

  const runGrowthWhatIf = async () => {
    setGrowthSimLoading(true)
    try {
      const response = await getCeoStaffGrowthWhatIfSimulation({
        specialty: growthSpecialty,
        commission_increase_percent: growthCommissionIncrease,
      })
      setGrowthWhatIf(response)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run growth scenario simulation')
    } finally {
      setGrowthSimLoading(false)
    }
  }

  const submitOnboarding = () => {
    if (!onboardingDraft.doctor_name.trim() || !onboardingDraft.city.trim() || !onboardingDraft.specialty.trim()) {
      toast.error('Please fill doctor name, city, and specialty')
      return
    }
    setOnboardingQueue((prev) => [...prev, { ...onboardingDraft }])
    setOnboardingDraft({ doctor_name: '', city: '', specialty: '' })
    toast.success('Staff added to mock onboarding queue')
  }

  const filteredLeaderboard = useMemo(() => {
    const rows = performance?.leaderboard || []
    return rows.filter((row) => {
      if (branchFilter !== 'all' && row.branch !== branchFilter) return false
      if (specialtyFilter !== 'all' && row.specialty !== specialtyFilter) return false
      if (timePeriodFilter !== 'all' && row.time_period !== timePeriodFilter) return false
      return true
    })
  }, [performance, branchFilter, specialtyFilter, timePeriodFilter])

  const columns = useMemo<ColumnDef<LeaderboardRow>[]>(
    () => [
      { id: 'rank', header: '#', cell: ({ row }) => <span className="font-semibold text-slate-700">{row.index + 1}</span> },
      { accessorKey: 'doctor_name', header: 'Staff' },
      { accessorKey: 'branch', header: 'Branch' },
      { accessorKey: 'specialty', header: 'Specialty' },
      { accessorKey: 'total_referrals', header: 'Referrals' },
      { accessorKey: 'revenue_generated', header: 'Revenue', cell: ({ row }) => toCurrency(row.original.revenue_generated) },
      { accessorKey: 'commission_earned', header: 'Commission', cell: ({ row }) => toCurrency(row.original.commission_earned) },
      { accessorKey: 'conversion_rate_percent', header: 'Conversion', cell: ({ row }) => `${row.original.conversion_rate_percent}%` },
      {
        id: 'actions',
        header: 'Summary',
        cell: ({ row }) => (
          <button
            type="button"
            onClick={() => setSelectedStaffId(row.original.doctor_id)}
            className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-700"
          >
            View
          </button>
        ),
      },
    ],
    []
  )

  const table = useReactTable({
    data: filteredLeaderboard,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const healthGaugeData = useMemo(() => {
    const value = networkHealth?.score || 0
    return [{ name: 'Network Health', value, fill: getScoreColor(value) }]
  }, [networkHealth])

  const selectedStaffTrend = useMemo(
    () => performance?.referral_trend.by_doctor.find((row) => row.doctor_id === selectedTrendStaffId) || null,
    [performance, selectedTrendStaffId]
  )

  const selectedStaffSummary = useMemo(
    () => performance?.doctor_summaries.find((doctor) => doctor.doctor_id === selectedStaffId) || null,
    [performance, selectedStaffId]
  )

  const selectedStaffProfile = useMemo(
    () => engagement?.doctor_profiles.find((doctor) => doctor.doctor_id === selectedStaffId) || null,
    [engagement, selectedStaffId]
  )

  const branchOptions = useMemo(
    () => ['all', ...Array.from(new Set((performance?.leaderboard || []).map((row) => row.branch)))],
    [performance]
  )
  const specialtyOptions = useMemo(
    () => ['all', ...Array.from(new Set((performance?.leaderboard || []).map((row) => row.specialty)))],
    [performance]
  )
  const timePeriodOptions = useMemo(
    () => ['all', ...Array.from(new Set((performance?.leaderboard || []).map((row) => row.time_period)))],
    [performance]
  )

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading Staff Network dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {doctorLoadError && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">Staff network data is partially unavailable</p>
          <p className="mt-1 text-xs text-amber-700">Some widgets are showing fallback values while data services recover.</p>
        </section>
      )}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">Staff Network</h1>
        <p className="mt-1 text-sm text-slate-600">Referral ecosystem command center for super admin strategy and network growth.</p>
      </section>

      <section className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6 shadow-sm">
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12 lg:col-span-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">{wow?.doctor_360_briefing.title || 'Staff 360 AI Briefing'}</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-700">{wow?.doctor_360_briefing.message || 'Briefing is loading.'}</p>
          </div>
          <div className="col-span-12 lg:col-span-3">
            <p className="text-sm font-semibold text-slate-700">Smart Referral Alerts</p>
            <div className="mt-2 space-y-2">
              {(wow?.smart_referral_alerts || []).map((alert, idx) => (
                <div
                  key={`${alert.title}-${idx}`}
                  className={`rounded-md border px-3 py-2 text-xs ${
                    alert.severity === 'high'
                      ? 'border-rose-200 bg-rose-50 text-rose-700'
                      : 'border-amber-200 bg-amber-50 text-amber-700'
                  }`}
                >
                  <p className="font-semibold">{alert.title}</p>
                  <p className="text-slate-600">{alert.message}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="col-span-12 lg:col-span-3">
            <p className="text-sm font-semibold text-slate-700">Staff Loyalty Program</p>
            <div className="mt-2 space-y-2">
              {(wow?.doctor_loyalty_program.tiers || []).map((tier) => (
                <div key={tier.name} className="rounded-md border border-indigo-100 bg-white px-3 py-2 text-xs text-slate-700">
                  <p className="font-semibold text-indigo-700">{tier.name}</p>
                  <p>{tier.criteria}</p>
                  <p className="mt-1 text-slate-500">Qualified: {tier.qualifies.join(', ')}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Staff Network Command Center (The Pulse)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Network Health Score</p>
            <div className="mt-2 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={healthGaugeData} innerRadius="68%" outerRadius="100%" barSize={22} startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-96px] text-center">
              <p className="text-4xl font-black" style={{ color: getScoreColor(networkHealth?.score || 0) }}>
                {networkHealth?.score || 0}
              </p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-6 lg:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Total Active Staffs</p>
            <p className="mt-1 text-3xl font-black text-slate-900">{networkHealth?.total_staff || 0}</p>
            <p className="mt-2 text-xs font-semibold text-emerald-700">MoM Growth: +{Number(networkHealth?.growth_mom_percent || 0).toFixed(1)}%</p>
            <div className="mt-5 rounded-lg bg-indigo-50 p-3">
              <p className="text-xs uppercase text-indigo-700">Revenue Contribution</p>
              <p className="text-2xl font-black text-indigo-800">{networkHealth?.revenue_contribution_percent || 0}%</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-6 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Staff Engagement Score</p>
            <div className="mt-4">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-600">
                <span>Engagement</span>
                <span>{networkHealth?.engagement_score || 0}/100</span>
              </div>
              <div className="h-3 rounded-full bg-slate-100">
                <div className="h-3 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500" style={{ width: `${networkHealth?.engagement_score || 0}%` }} />
              </div>
            </div>
            <div className="mt-5 rounded-lg bg-rose-50 p-3">
              <p className="text-xs uppercase text-rose-700">Attrition Risk</p>
              <p className="text-2xl font-black text-rose-700">{networkHealth?.attrition_risk_percent || 0}%</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="mb-3 text-sm font-semibold text-slate-700">Network Heatmap (Referring Staffs by Region)</p>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
              {(networkHealth?.regional_density || []).map((item) => (
                <div
                  key={item.region}
                  className="rounded-lg border border-slate-200 p-3 text-center"
                  style={{ backgroundColor: `rgba(79, 70, 229, ${Math.max(0.18, Math.min(item.doctor_count / 30, 0.9))})` }}
                >
                  <p className="text-xs font-semibold text-slate-100">{item.region}</p>
                  <p className="mt-1 text-2xl font-black text-white">{item.doctor_count}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Staff Performance &amp; Referral Analytics</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <p className="text-sm font-semibold text-slate-700">Staff Leaderboard</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <select value={branchFilter} onChange={(event) => setBranchFilter(event.target.value)} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm">
                  {branchOptions.map((branch) => <option key={branch} value={branch}>{branch === 'all' ? 'All Branches' : branch}</option>)}
                </select>
                <select value={specialtyFilter} onChange={(event) => setSpecialtyFilter(event.target.value)} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm">
                  {specialtyOptions.map((specialty) => <option key={specialty} value={specialty}>{specialty === 'all' ? 'All Specialties' : specialty}</option>)}
                </select>
                <select value={timePeriodFilter} onChange={(event) => setTimePeriodFilter(event.target.value)} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm">
                  {timePeriodOptions.map((period) => <option key={period} value={period}>{period === 'all' ? 'All Periods' : period.toUpperCase()}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <th
                          key={header.id}
                          onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                          className={`px-3 py-2 ${header.column.getCanSort() ? 'cursor-pointer select-none' : ''}`}
                        >
                          <span className="inline-flex items-center gap-1">
                            {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                            {header.column.getIsSorted() === 'asc' ? '↑' : header.column.getIsSorted() === 'desc' ? '↓' : ''}
                          </span>
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      {row.getVisibleCells().map((cell) => <td key={cell.id} className="px-3 py-2">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-slate-700">Referral Trend Analysis</p>
              <select
                value={selectedTrendStaffId ?? ''}
                onChange={(event) => setSelectedTrendStaffId(Number(event.target.value))}
                className="rounded-md border border-slate-300 px-3 py-1 text-sm"
              >
                {(performance?.referral_trend.by_doctor || []).map((doctor) => <option key={doctor.doctor_id} value={doctor.doctor_id}>{doctor.doctor_name}</option>)}
              </select>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={performance?.referral_trend.network || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="referrals" name="Network Referrals" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
                  <Line type="monotone" data={selectedStaffTrend?.points || []} dataKey="referrals" name={`${selectedStaffTrend?.doctor_name || 'Staff'} Referrals`} stroke="#0ea5e9" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Referral Leakage Alerts</p>
            <div className="mt-3 space-y-2">
              {(performance?.referral_leakage_alerts || []).map((item) => (
                <div key={item.doctor_id} className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{item.doctor_name}</p>
                  <p className="text-xs text-slate-600">{item.branch} · Down {item.decline_percent}%</p>
                  <p className="mt-1 text-xs text-rose-700">{item.message}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-md bg-emerald-50 p-3">
              <p className="text-xs uppercase text-emerald-700">Customer Conversion Rate</p>
              <p className="text-2xl font-black text-emerald-700">{performance?.patient_conversion_rate_percent || 0}%</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">MenuItem Mix Analysis</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={performance?.test_mix || []} dataKey="value" nameKey="test_type" outerRadius={120} label>
                    {(performance?.test_mix || []).map((entry, index) => <Cell key={entry.test_type} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Top Staff Revenue &amp; Commission</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={filteredLeaderboard}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="doctor_name" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Bar dataKey="revenue_generated" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="commission_earned" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Staff Financials &amp; Commission Management</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Commission Dashboard</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Staff</th>
                    <th className="px-3 py-2">Earned</th>
                    <th className="px-3 py-2">Paid</th>
                    <th className="px-3 py-2">Pending</th>
                  </tr>
                </thead>
                <tbody>
                  {(financial?.commission_dashboard || []).map((row) => (
                    <tr key={row.doctor_id} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.doctor_name}</td>
                      <td className="px-3 py-2">{toCurrency(row.earned)}</td>
                      <td className="px-3 py-2 text-emerald-700">{toCurrency(row.paid)}</td>
                      <td className="px-3 py-2 text-amber-700">{toCurrency(row.pending)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Commission Calculator</p>
            <div className="mt-3 space-y-3">
              <label className="block text-xs font-semibold uppercase text-slate-500">
                Structure
                <select value={commissionStructure} onChange={(event) => setCommissionStructure(event.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                  <option value="tiered">Tiered</option>
                  <option value="flat">Flat</option>
                  <option value="performance_linked">Performance Linked</option>
                </select>
              </label>
              <label className="block text-xs font-semibold uppercase text-slate-500">
                Base Commission (%)
                <input
                  type="number"
                  min={0}
                  max={30}
                  value={baseCommission}
                  onChange={(event) => setBaseCommission(Number(event.target.value || 0))}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
              <button
                type="button"
                onClick={() => void runCommissionSimulation()}
                disabled={simulationLoading}
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
              >
                {simulationLoading ? 'Simulating...' : 'Simulate Structure'}
              </button>
              {commissionSimulation && (
                <div className="rounded-md border border-indigo-100 bg-indigo-50 p-3 text-sm text-slate-700">
                  <p className="font-semibold text-indigo-800">Projected Referral Growth: {commissionSimulation.projections.projected_referral_growth_percent.toFixed(2)}%</p>
                  <p>Commission Cost Growth: {commissionSimulation.projections.projected_commission_cost_growth_percent.toFixed(2)}%</p>
                  <p>Profitability Impact: {commissionSimulation.projections.projected_profitability_impact_percent.toFixed(2)}%</p>
                  <p className="mt-2 text-xs">{commissionSimulation.ai_summary}</p>
                </div>
              )}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-700">Commission Payout Automation</p>
              <button
                type="button"
                onClick={() => void runPayoutAutomation()}
                disabled={payoutLoading}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
              >
                {payoutLoading ? 'Running...' : 'Generate Statements & Payouts'}
              </button>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-md bg-amber-50 p-3">
                <p className="text-xs uppercase text-amber-700">Referral Cost as % of Revenue</p>
                <p className="text-3xl font-black text-amber-700">{Number(financial?.referral_cost_percent_of_revenue || 0).toFixed(1)}%</p>
              </div>
              {payoutResult && (
                <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-slate-700">
                  <p className="font-semibold text-emerald-800">Run: {payoutResult.run_id}</p>
                  <p>Status: {payoutResult.status}</p>
                  <p>Statements: {payoutResult.statements_generated}</p>
                  <p>Payouts Queued: {payoutResult.payouts_queued}</p>
                  <p>Total Payout: {toCurrency(payoutResult.total_payout_amount)}</p>
                </div>
              )}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Staff-wise Profitability</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Staff</th>
                    <th className="px-3 py-2">Revenue</th>
                    <th className="px-3 py-2">Referral Cost</th>
                    <th className="px-3 py-2">Service Cost</th>
                    <th className="px-3 py-2">Net Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {(financial?.doctor_profitability || []).map((row) => (
                    <tr key={row.doctor_id} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.doctor_name}</td>
                      <td className="px-3 py-2">{toCurrency(row.revenue)}</td>
                      <td className="px-3 py-2">{toCurrency(row.referral_cost)}</td>
                      <td className="px-3 py-2">{toCurrency(row.service_cost)}</td>
                      <td className="px-3 py-2 font-semibold text-emerald-700">{toCurrency(row.net_profit)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Staff Engagement &amp; Relationship Management</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Staff Profile &amp; Insights</p>
            {selectedStaffProfile ? (
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                <p><span className="font-semibold">Staff:</span> {selectedStaffProfile.doctor_name}</p>
                <p><span className="font-semibold">Branch:</span> {selectedStaffProfile.branch}</p>
                <p><span className="font-semibold">Specialty:</span> {selectedStaffProfile.specialty}</p>
                <p><span className="font-semibold">Engagement Score:</span> {selectedStaffProfile.engagement_score}/100</p>
                <p><span className="font-semibold">Preferred Channel:</span> {selectedStaffProfile.preferred_channel}</p>
                <p><span className="font-semibold">Last Interaction:</span> {selectedStaffProfile.last_interaction}</p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-500">Select a doctor from the leaderboard and click “View” to see profile insights.</p>
            )}
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Engagement Calendar</p>
            <div className="mt-3 space-y-2">
              {(engagement?.engagement_calendar || []).map((event, idx) => (
                <div key={`${event.date}-${idx}`} className="rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{event.date} · {event.event_type}</p>
                  <p className="text-slate-600">{event.doctor_name}</p>
                  <p className="text-xs text-slate-500">{event.notes}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Flight Risk AI Predictor</p>
            <div className="mt-3 space-y-2">
              {(engagement?.flight_risk_staff || []).map((doctor) => (
                <div key={doctor.doctor_id} className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{doctor.doctor_name}</p>
                  <p className="text-xs uppercase text-rose-700">Risk: {doctor.risk_level}</p>
                  <p className="text-xs text-slate-600">{doctor.reason}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Staff NPS &amp; Feedback</p>
            <div className="mt-3 rounded-md bg-indigo-50 p-3">
              <p className="text-xs uppercase text-indigo-700">NPS Score</p>
              <p className="text-3xl font-black text-indigo-800">{engagement?.doctor_nps_feedback.nps_score || 0}</p>
            </div>
            <div className="mt-3 text-sm text-slate-700">
              <p className="font-semibold">Positive Themes</p>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-600">
                {(engagement?.doctor_nps_feedback.positive_themes || []).map((item) => <li key={item}>{item}</li>)}
              </ul>
              <p className="mt-2 font-semibold">Improvement Themes</p>
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-600">
                {(engagement?.doctor_nps_feedback.improvement_themes || []).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Staff Communication Hub</p>
            <p className="mt-3 text-sm text-slate-600">{engagement?.communication_hub.message || 'Communication workflows will be shown here.'}</p>
            <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
              Segment-based campaigns (specialty/branch/engagement tier) are available as a placeholder.
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">White-Label Staff Portal</p>
            <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 p-4">
              <p className="text-sm font-semibold text-emerald-800">{engagement?.white_label_portal.available ? 'Available' : 'Not Available'}</p>
              <p className="text-xs text-slate-600">{engagement?.white_label_portal.message || 'Portal status will be shown here.'}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Growth &amp; Acquisition</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Market Opportunity Dashboard</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Staff</th>
                    <th className="px-3 py-2">City</th>
                    <th className="px-3 py-2">Specialty</th>
                    <th className="px-3 py-2">Estimated Monthly Referrals</th>
                  </tr>
                </thead>
                <tbody>
                  {(growth?.market_opportunities || []).map((row, idx) => (
                    <tr key={`${row.doctor_name}-${idx}`} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.doctor_name}</td>
                      <td className="px-3 py-2">{row.city}</td>
                      <td className="px-3 py-2">{row.specialty}</td>
                      <td className="px-3 py-2 font-semibold text-slate-800">{row.estimated_monthly_referrals}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">New Staff Onboarding</p>
            <div className="mt-3 space-y-2">
              <input
                value={onboardingDraft.doctor_name}
                onChange={(event) => setOnboardingDraft((prev) => ({ ...prev, doctor_name: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Staff Name"
              />
              <input
                value={onboardingDraft.city}
                onChange={(event) => setOnboardingDraft((prev) => ({ ...prev, city: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="City"
              />
              <input
                value={onboardingDraft.specialty}
                onChange={(event) => setOnboardingDraft((prev) => ({ ...prev, specialty: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Specialty"
              />
              <button
                type="button"
                onClick={submitOnboarding}
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Add to Network (Mock)
              </button>
            </div>
            {onboardingQueue.length > 0 && (
              <div className="mt-3 rounded-md border border-slate-200 p-3 text-xs text-slate-600">
                <p className="mb-1 font-semibold text-slate-700">Queued Onboarding ({onboardingQueue.length})</p>
                <ul className="space-y-1">
                  {onboardingQueue.map((item, idx) => <li key={`${item.doctor_name}-${idx}`}>{item.doctor_name} · {item.city} · {item.specialty}</li>)}
                </ul>
              </div>
            )}
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Campaign Performance Tracking</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={growth?.campaign_performance || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="campaign" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Bar dataKey="investment" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="revenue_generated" fill="#22c55e" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">What-If Scenario Simulator</p>
            <div className="mt-3 space-y-3">
              <p className="text-xs text-slate-500">What if we increase commission rate for Cardiologists by 5%?</p>
              <input
                value={growthSpecialty}
                onChange={(event) => setGrowthSpecialty(event.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Specialty"
              />
              <input
                type="number"
                min={0}
                max={30}
                value={growthCommissionIncrease}
                onChange={(event) => setGrowthCommissionIncrease(Number(event.target.value || 0))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                type="button"
                onClick={() => void runGrowthWhatIf()}
                disabled={growthSimLoading}
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
              >
                {growthSimLoading ? 'Running...' : 'Run Scenario'}
              </button>
              {growthWhatIf && (
                <div className="rounded-md border border-indigo-100 bg-indigo-50 p-3 text-sm text-slate-700">
                  <p className="font-semibold text-indigo-800">{growthWhatIf.scenario}</p>
                  <p>Projected Referral Volume Growth: {growthWhatIf.projections.projected_referral_volume_growth_percent.toFixed(2)}%</p>
                  <p>Projected Profitability Impact: {growthWhatIf.projections.projected_profitability_impact_percent.toFixed(2)}%</p>
                  <p>Revenue Delta: {toCurrency(growthWhatIf.projections.estimated_monthly_revenue_delta)}</p>
                  <p>Commission Delta: {toCurrency(growthWhatIf.projections.estimated_monthly_commission_delta)}</p>
                </div>
              )}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Competitor Staff Leakage Order</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Staff</th>
                    <th className="px-3 py-2">City</th>
                    <th className="px-3 py-2">Estimated Leakage</th>
                    <th className="px-3 py-2">Competitor Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {(growth?.competitor_leakage_report || []).map((row, idx) => (
                    <tr key={`${row.doctor_name}-${idx}`} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.doctor_name}</td>
                      <td className="px-3 py-2">{row.city}</td>
                      <td className="px-3 py-2 text-rose-700">{row.estimated_leakage_percent}%</td>
                      <td className="px-3 py-2">{row.competitor_hint}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Operational Excellence</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Service Level Dashboard</p>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-md bg-indigo-50 p-3">
                <p className="text-xs uppercase text-indigo-700">Average TAT</p>
                <p className="text-2xl font-black text-indigo-800">{Number(operational?.service_level_dashboard.average_tat_hours || 0).toFixed(1)} hrs</p>
              </div>
              <div className="rounded-md bg-rose-50 p-3">
                <p className="text-xs uppercase text-rose-700">Sample Rejection</p>
                <p className="text-2xl font-black text-rose-700">{Number(operational?.service_level_dashboard.sample_rejection_rate_percent || 0).toFixed(1)}%</p>
              </div>
              <div className="rounded-md bg-emerald-50 p-3">
                <p className="text-xs uppercase text-emerald-700">Order Quality Score</p>
                <p className="text-2xl font-black text-emerald-700">{operational?.service_level_dashboard.report_quality_score || 0}/100</p>
              </div>
            </div>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={operational?.service_level_dashboard.tat_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="tat_hours" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Customer Journey Completion Rate</p>
            <div className="mt-4">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-600">
                <span>Completion</span>
                <span>{operational?.patient_journey_completion_rate_percent || 0}%</span>
              </div>
              <div className="h-4 rounded-full bg-slate-100">
                <div
                  className="h-4 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                  style={{ width: `${Math.min(Math.max(operational?.patient_journey_completion_rate_percent || 0, 0), 100)}%` }}
                />
              </div>
            </div>
            <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              Tracks referred customers who complete full diagnostic journey and report closure.
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Staff Issue Tracker</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Issue ID</th>
                    <th className="px-3 py-2">Staff</th>
                    <th className="px-3 py-2">Issue Type</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {(operational?.doctor_issue_tracker || []).map((issue) => (
                    <tr key={issue.issue_id} className="border-t border-slate-100">
                      <td className="px-3 py-2">{issue.issue_id}</td>
                      <td className="px-3 py-2">{issue.doctor_name}</td>
                      <td className="px-3 py-2">{issue.issue_type}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          issue.status === 'Resolved'
                            ? 'bg-emerald-100 text-emerald-700'
                            : issue.status === 'In Progress'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-rose-100 text-rose-700'
                        }`}>
                          {issue.status}
                        </span>
                      </td>
                      <td className="px-3 py-2">{issue.updated_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {selectedStaffSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-xl font-bold text-slate-900">{selectedStaffSummary.doctor_name}</h3>
                <p className="text-xs uppercase text-slate-500">Staff Performance Summary</p>
              </div>
              <button type="button" onClick={() => setSelectedStaffId(null)} className="rounded-md bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
                Close
              </button>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-md bg-indigo-50 p-3">
                <p className="text-xs uppercase text-indigo-700">Total Referrals</p>
                <p className="text-2xl font-black text-indigo-800">{selectedStaffSummary.total_referrals}</p>
              </div>
              <div className="rounded-md bg-emerald-50 p-3">
                <p className="text-xs uppercase text-emerald-700">Revenue Generated</p>
                <p className="text-xl font-black text-emerald-800">{toCurrency(selectedStaffSummary.revenue_generated)}</p>
              </div>
              <div className="rounded-md bg-amber-50 p-3">
                <p className="text-xs uppercase text-amber-700">Commission Earned</p>
                <p className="text-xl font-black text-amber-800">{toCurrency(selectedStaffSummary.commission_earned)}</p>
              </div>
            </div>
            <div className="mt-4">
              <p className="text-sm font-semibold text-slate-700">Interaction History</p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
                {selectedStaffSummary.interaction_history.map((item, idx) => <li key={`${selectedStaffSummary.doctor_id}-${idx}`}>{item}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CeoStaffNetwork
