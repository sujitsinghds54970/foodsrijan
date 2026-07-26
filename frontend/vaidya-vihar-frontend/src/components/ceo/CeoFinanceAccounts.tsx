import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
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
  CeoFinanceBranchProfitabilityHeatmapResponse,
  CeoFinanceCashLiquidityResponse,
  CeoFinanceCfoBriefingResponse,
  CeoFinanceComplianceTaxationResponse,
  CeoFinanceCostControlResponse,
  CeoFinanceDoctorReferralFinancialsResponse,
  CeoFinanceHealthScoreResponse,
  CeoFinanceLisOperationsOverviewResponse,
  CeoFinancePredictiveAnalyticsResponse,
  CeoFinanceProfitabilityRevenueResponse,
  CeoFinanceReceivablesCycleResponse,
  CeoFinanceWhatIfSimulatorResponse,
  getCeoFinanceBranchProfitabilityHeatmap,
  getCeoFinanceCashLiquidity,
  getCeoFinanceCfoBriefing,
  getCeoFinanceComplianceTaxation,
  getCeoFinanceCostControl,
  getCeoFinanceDoctorReferralFinancials,
  getCeoFinanceHealthScore,
  getCeoFinanceLisOperationsOverview,
  getCeoFinancePredictiveAnalytics,
  getCeoFinanceProfitabilityRevenue,
  getCeoFinanceReceivablesCycle,
  getCeoFinanceWhatIfSimulation,
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

const CeoFinanceAccounts = () => {
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<CeoFinanceHealthScoreResponse | null>(null)
  const [liquidity, setLiquidity] = useState<CeoFinanceCashLiquidityResponse | null>(null)
  const [profitability, setProfitability] = useState<CeoFinanceProfitabilityRevenueResponse | null>(null)
  const [receivables, setReceivables] = useState<CeoFinanceReceivablesCycleResponse | null>(null)
  const [costControl, setCostControl] = useState<CeoFinanceCostControlResponse | null>(null)
  const [compliance, setCompliance] = useState<CeoFinanceComplianceTaxationResponse | null>(null)
  const [predictive, setPredictive] = useState<CeoFinancePredictiveAnalyticsResponse | null>(null)
  const [doctorReferral, setDoctorReferral] = useState<CeoFinanceDoctorReferralFinancialsResponse | null>(null)
  const [cfoBriefing, setCfoBriefing] = useState<CeoFinanceCfoBriefingResponse | null>(null)
  const [branchHeatmap, setBranchHeatmap] = useState<CeoFinanceBranchProfitabilityHeatmapResponse | null>(null)
  const [lisOverview, setLisOverview] = useState<CeoFinanceLisOperationsOverviewResponse | null>(null)
  const [whatIfResult, setWhatIfResult] = useState<CeoFinanceWhatIfSimulatorResponse | null>(null)
  const [whatIfCity, setWhatIfCity] = useState('Pune')
  const [whatIfDiscount, setWhatIfDiscount] = useState(5)
  const [simulating, setSimulating] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [
          healthResp,
          liquidityResp,
          profitabilityResp,
          receivablesResp,
          costControlResp,
          complianceResp,
          predictiveResp,
          doctorReferralResp,
          cfoBriefingResp,
          branchHeatmapResp,
          lisOverviewResp,
        ] = await Promise.all([
          getCeoFinanceHealthScore(),
          getCeoFinanceCashLiquidity(),
          getCeoFinanceProfitabilityRevenue(),
          getCeoFinanceReceivablesCycle(),
          getCeoFinanceCostControl(),
          getCeoFinanceComplianceTaxation(),
          getCeoFinancePredictiveAnalytics(),
          getCeoFinanceDoctorReferralFinancials(),
          getCeoFinanceCfoBriefing(),
          getCeoFinanceBranchProfitabilityHeatmap(),
          getCeoFinanceLisOperationsOverview(),
        ])
        setHealth(healthResp)
        setLiquidity(liquidityResp)
        setProfitability(profitabilityResp)
        setReceivables(receivablesResp)
        setCostControl(costControlResp)
        setCompliance(complianceResp)
        setPredictive(predictiveResp)
        setDoctorReferral(doctorReferralResp)
        setCfoBriefing(cfoBriefingResp)
        setBranchHeatmap(branchHeatmapResp)
        setLisOverview(lisOverviewResp)
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Unable to load Finance & Accounts dashboard')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const runWhatIfScenario = async () => {
    setSimulating(true)
    try {
      const response = await getCeoFinanceWhatIfSimulation({ city: whatIfCity.trim() || 'Pune', discount_percent: whatIfDiscount })
      setWhatIfResult(response)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run what-if simulation')
    } finally {
      setSimulating(false)
    }
  }

  const healthGaugeData = useMemo(() => {
    const value = health?.score || 0
    return [{ name: 'Financial Health', value, fill: getScoreColor(value) }]
  }, [health])

  const operatingCashGauge = useMemo(() => {
    const value = liquidity?.operating_cash_flow.score || 0
    return [{ name: 'Operating Cash Flow Score', value, fill: getScoreColor(value) }]
  }, [liquidity])

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading Finance &amp; Accounts dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">Finance &amp; Accounts</h1>
        <p className="mt-1 text-sm text-slate-600">Financial pulse and liquidity monitoring for super admin decision-making.</p>
      </section>

      <section className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">{cfoBriefing?.title || 'Automated CFO Briefing'}</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-700">
              {cfoBriefing?.brief || 'CFO briefing is being generated.'}
            </p>
          </div>
          <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
            {(cfoBriefing?.highlights || []).map((item) => (
              <div key={item.label} className="rounded-md border border-indigo-100 bg-white px-3 py-2">
                <p className="text-[11px] uppercase text-slate-500">{item.label}</p>
                <p className="font-bold text-slate-800">{item.value}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">LIS Operations Analytics (Read-only Command Feed)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Today&apos;s Test Volume</p>
            <p className="mt-2 text-3xl font-black text-slate-900">{lisOverview?.network_summary.today_test_volume || 0}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Average TAT</p>
            <p className="mt-2 text-3xl font-black text-indigo-700">{Number(lisOverview?.network_summary.average_tat_minutes || 0).toFixed(1)} min</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Pending Tests</p>
            <p className="mt-2 text-3xl font-black text-amber-700">{lisOverview?.network_summary.pending_tests || 0}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Lab Readiness Score</p>
            <p className="mt-2 text-3xl font-black" style={{ color: getScoreColor(lisOverview?.network_summary.readiness_score || 0) }}>
              {lisOverview?.network_summary.readiness_score || 0}
            </p>
          </div>

          {(lisOverview?.smart_alerts || []).length > 0 && (
            <div className="col-span-12 rounded-xl border border-rose-200 bg-rose-50 p-4">
              <p className="text-sm font-semibold text-rose-700">Smart LIS Alerts</p>
              <div className="mt-2 space-y-2">
                {(lisOverview?.smart_alerts || []).slice(0, 4).map((alert, idx) => (
                  <div key={`${alert.title}-${idx}`} className="rounded-md border border-rose-100 bg-white px-3 py-2 text-sm">
                    <p className="font-semibold text-rose-700">{alert.title}</p>
                    <p className="text-slate-700">{alert.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Branch LIS Metrics (CEO Read-only View)</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Branch</th>
                    <th className="px-3 py-2">Volume</th>
                    <th className="px-3 py-2">Pending</th>
                    <th className="px-3 py-2">Avg TAT</th>
                    <th className="px-3 py-2">QC Status</th>
                    <th className="px-3 py-2">Rejection Rate</th>
                    <th className="px-3 py-2">Health</th>
                  </tr>
                </thead>
                <tbody>
                  {(lisOverview?.branch_metrics || []).map((row) => (
                    <tr key={row.branch_id} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-semibold text-slate-800">{row.branch_name}</td>
                      <td className="px-3 py-2">{row.today_test_volume}</td>
                      <td className="px-3 py-2">{row.pending_samples}</td>
                      <td className="px-3 py-2">{Number(row.average_tat_minutes || 0).toFixed(1)} min</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          row.qc_status === 'Good' ? 'bg-emerald-100 text-emerald-700' :
                            row.qc_status === 'Watch' ? 'bg-amber-100 text-amber-700' :
                              'bg-rose-100 text-rose-700'
                        }`}>
                          {row.qc_status}
                        </span>
                      </td>
                      <td className="px-3 py-2">{Number(row.sample_rejection_rate || 0).toFixed(1)}%</td>
                      <td className="px-3 py-2 font-bold" style={{ color: getScoreColor(row.health_score || 0) }}>{row.health_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Financial Health Scorecard (The Pulse)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Overall Financial Health Score</p>
            <div className="mt-2 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={healthGaugeData} innerRadius="68%" outerRadius="100%" barSize={22} startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-96px] text-center">
              <p className="text-4xl font-black" style={{ color: getScoreColor(health?.score || 0) }}>
                {health?.score || 0}
              </p>
              <p className="text-xs font-semibold uppercase text-slate-500">Status: {(health?.color || 'yellow').toUpperCase()}</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Key Driver Breakdown</p>
            <div className="mt-3 space-y-4">
              {[
                { label: 'Revenue Growth', value: health?.drivers.revenue_growth || 0 },
                { label: 'Cash Flow', value: health?.drivers.cash_flow || 0 },
                { label: 'Profitability', value: health?.drivers.profitability || 0 },
              ].map((item) => (
                <div key={item.label}>
                  <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-600">
                    <span>{item.label}</span>
                    <span>{item.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500" style={{ width: `${Math.min(Math.max(item.value, 0), 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Revenue vs Expense (MoM)</p>
            <div className="mt-3 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={health?.monthly_revenue_vs_expense || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Bar dataKey="revenue" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="expense" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">12-Month Financial Health Trend</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={health?.monthly_health_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis domain={[50, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Cash Flow &amp; Liquidity (The Lifeblood)</h2>

        {liquidity?.zero_balance_alert.enabled && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
            {liquidity.zero_balance_alert.message}
          </div>
        )}

        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Cash in Hand</p>
            <p className="mt-2 text-3xl font-black text-slate-900">{toCurrency(liquidity?.cash_position.cash_in_hand || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Cash in Bank</p>
            <p className="mt-2 text-3xl font-black text-slate-900">{toCurrency(liquidity?.cash_position.cash_in_bank || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Total Available Liquidity</p>
            <p className="mt-2 text-3xl font-black text-indigo-700">{toCurrency(liquidity?.cash_position.total_available_liquidity || 0)}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">Cash Flow Forecast (30/60/90 Days)</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={liquidity?.forecast_30_60_90 || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Line type="monotone" dataKey="inflow" stroke="#22c55e" strokeWidth={3} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="outflow" stroke="#ef4444" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Cash Burn Rate &amp; Runway</p>
            <div className="mt-3 space-y-3">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Burn Rate</p>
                <p className="text-2xl font-black text-rose-700">{toCurrency(liquidity?.cash_burn_rate_per_month || 0)}/month</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Runway</p>
                <p className="text-2xl font-black text-emerald-700">{Number(liquidity?.runway_months || 0).toFixed(1)} months</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs uppercase text-slate-500">Liquidity Alert Threshold</p>
                <p className="text-lg font-bold text-slate-800">{toCurrency(liquidity?.liquidity_threshold || 0)}</p>
              </div>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Operating Cash Flow</p>
            <div className="mt-3 grid grid-cols-12 gap-4">
              <div className="col-span-12 rounded-lg bg-slate-50 p-4 md:col-span-4">
                <p className="text-xs uppercase text-slate-500">Cash from Operations</p>
                <p className="mt-1 text-3xl font-black text-slate-900">{toCurrency(liquidity?.operating_cash_flow.value || 0)}</p>
              </div>
              <div className="col-span-12 h-44 md:col-span-8">
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart data={operatingCashGauge} innerRadius="65%" outerRadius="100%" barSize={18} startAngle={180} endAngle={0}>
                    <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                    <RadialBar background dataKey="value" cornerRadius={12} />
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Profitability &amp; Revenue Analytics (The Engine)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Consolidated P&amp;L</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Period</th>
                    <th className="px-3 py-2">Revenue</th>
                    <th className="px-3 py-2">Expenses</th>
                    <th className="px-3 py-2">Net Profit</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-slate-100">
                    <td className="px-3 py-2 font-semibold text-slate-800">Current Month</td>
                    <td className="px-3 py-2">{toCurrency(profitability?.consolidated_pnl.current_month.revenue || 0)}</td>
                    <td className="px-3 py-2">{toCurrency(profitability?.consolidated_pnl.current_month.expenses || 0)}</td>
                    <td className="px-3 py-2 font-bold text-emerald-700">{toCurrency(profitability?.consolidated_pnl.current_month.net_profit || 0)}</td>
                  </tr>
                  <tr className="border-t border-slate-100">
                    <td className="px-3 py-2 font-semibold text-slate-800">Year-to-Date</td>
                    <td className="px-3 py-2">{toCurrency(profitability?.consolidated_pnl.ytd.revenue || 0)}</td>
                    <td className="px-3 py-2">{toCurrency(profitability?.consolidated_pnl.ytd.expenses || 0)}</td>
                    <td className="px-3 py-2 font-bold text-emerald-700">{toCurrency(profitability?.consolidated_pnl.ytd.net_profit || 0)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">Branch-wise Profitability</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={profitability?.branch_profitability || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="branch" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Bar dataKey="revenue" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="expenses" fill="#ef4444" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="net_profit" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">EBITDA &amp; Margin</p>
            <div className="mt-3 rounded-lg bg-slate-50 p-4">
              <p className="text-xs uppercase text-slate-500">EBITDA</p>
              <p className="mt-1 text-3xl font-black text-indigo-700">{toCurrency(profitability?.ebitda.value || 0)}</p>
            </div>
            <div className="mt-3 rounded-lg bg-emerald-50 p-4">
              <p className="text-xs uppercase text-emerald-700">EBITDA Margin</p>
              <p className="mt-1 text-3xl font-black text-emerald-700">{Number(profitability?.ebitda.margin_percent || 0).toFixed(1)}%</p>
            </div>
            <div className="mt-3 rounded-lg border border-slate-200 p-4 text-sm">
              <p className="text-xs uppercase text-slate-500">Avg Revenue per Patient</p>
              <p className="text-xl font-bold text-slate-900">{toCurrency(profitability?.revenue_per_unit.avg_revenue_per_patient || 0)}</p>
              <p className="mt-2 text-xs uppercase text-slate-500">Avg Revenue per Test</p>
              <p className="text-xl font-bold text-slate-900">{toCurrency(profitability?.revenue_per_unit.avg_revenue_per_test || 0)}</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Test-wise Profitability</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={profitability?.test_profitability || []}
                    dataKey="profitability"
                    nameKey="test_type"
                    outerRadius={120}
                    label
                  >
                    {(profitability?.test_profitability || []).map((entry, index) => (
                      <Cell key={entry.test_type} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Accounts Receivable &amp; Revenue Cycle (The Collections Engine)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">AR Aging Report</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={receivables?.ar_aging || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Bar dataKey="amount" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Collections KPIs</p>
            <div className="mt-3 space-y-3">
              <div className="rounded-lg bg-blue-50 p-3">
                <p className="text-xs uppercase text-blue-600">Collection Effectiveness Index (CEI)</p>
                <p className="text-2xl font-black text-blue-700">{Number(receivables?.collection_effectiveness_index_percent || 0).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg bg-rose-50 p-3">
                <p className="text-xs uppercase text-rose-600">Bad Debt Ratio</p>
                <p className="text-2xl font-black text-rose-700">{Number(receivables?.bad_debt_ratio_percent || 0).toFixed(1)}%</p>
              </div>
              <div className="rounded-lg bg-emerald-50 p-3">
                <p className="text-xs uppercase text-emerald-600">Days in Accounts Receivable (DSO)</p>
                <p className="text-2xl font-black text-emerald-700">{receivables?.days_sales_outstanding || 0} days</p>
              </div>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Insurance vs Self-Pay Mix</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={receivables?.insurance_vs_self_pay_mix || []}
                    dataKey="value"
                    nameKey="payer_type"
                    outerRadius={110}
                    label
                  >
                    {(receivables?.insurance_vs_self_pay_mix || []).map((entry, index) => (
                      <Cell key={entry.payer_type} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Cost Control &amp; Expense Management</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Expense Breakdown</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={costControl?.expense_breakdown || []}
                    dataKey="amount"
                    nameKey="category"
                    outerRadius={120}
                    label
                  >
                    {(costControl?.expense_breakdown || []).map((entry, index) => (
                      <Cell key={entry.category} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Branch-wise Cost Comparison</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={costControl?.branch_cost_comparison || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="branch" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Bar dataKey="cost" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Cost per Test</p>
            <p className="mt-2 text-3xl font-black text-slate-900">{toCurrency(costControl?.cost_per_unit.avg_cost_per_test || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Cost per Patient</p>
            <p className="mt-2 text-3xl font-black text-slate-900">{toCurrency(costControl?.cost_per_unit.avg_cost_per_patient || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Cost-to-Income Ratio</p>
            <p className="mt-2 text-3xl font-black text-rose-700">{Number(costControl?.cost_to_income_ratio_percent || 0).toFixed(1)}%</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Vendor Spend Analysis</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Vendor</th>
                    <th className="px-3 py-2">Category</th>
                    <th className="px-3 py-2">Total Spend</th>
                  </tr>
                </thead>
                <tbody>
                  {(costControl?.vendor_spend_analysis || []).map((row) => (
                    <tr key={row.vendor} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.vendor}</td>
                      <td className="px-3 py-2">{row.category}</td>
                      <td className="px-3 py-2 font-semibold text-slate-800">{toCurrency(row.total_spend)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Compliance &amp; Taxation (The Risk Shield)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Tax Compliance Dashboard</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Tax Type</th>
                    <th className="px-3 py-2">Period</th>
                    <th className="px-3 py-2">Due Date</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(compliance?.tax_compliance || []).map((row) => (
                    <tr key={`${row.tax_type}-${row.period}`} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.tax_type}</td>
                      <td className="px-3 py-2">{row.period}</td>
                      <td className="px-3 py-2">{row.due_date}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                          row.status === 'Filled' ? 'bg-emerald-100 text-emerald-700' :
                            row.status === 'Pending' ? 'bg-amber-100 text-amber-700' :
                              'bg-rose-100 text-rose-700'
                        }`}>
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">PF / ESI Compliance</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Type</th>
                    <th className="px-3 py-2">Employee</th>
                    <th className="px-3 py-2">Employer</th>
                    <th className="px-3 py-2">Due</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(compliance?.pf_esi_compliance || []).map((row) => (
                    <tr key={row.compliance_type} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.compliance_type}</td>
                      <td className="px-3 py-2">{toCurrency(row.employee_contribution)}</td>
                      <td className="px-3 py-2">{toCurrency(row.employer_contribution)}</td>
                      <td className="px-3 py-2">{row.due_date}</td>
                      <td className="px-3 py-2">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">License &amp; Registration Tracker</p>
            <div className="mt-3 space-y-2">
              {(compliance?.license_tracker || []).map((row) => (
                <div key={row.license_name} className="rounded-md border border-slate-200 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-900">{row.license_name}</p>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      row.renewal_alert ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
                    }`}>
                      {row.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">Expiry: {row.expiry_date}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">AI-Powered Predictive Analytics &amp; Scenario Planning</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Revenue Forecast (Next 6-12 Months)</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={predictive?.revenue_forecast || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Line type="monotone" dataKey="projected_revenue" stroke="#22c55e" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Profitability Forecast</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={predictive?.profitability_forecast || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Line type="monotone" dataKey="projected_net_profit" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Risk Alerts</p>
            <div className="mt-3 space-y-2">
              {(predictive?.risk_alerts || []).map((alert, idx) => (
                <div
                  key={`${alert.title}-${idx}`}
                  className={`rounded-md border px-3 py-2 ${
                    alert.severity === 'high'
                      ? 'border-rose-200 bg-rose-50'
                      : alert.severity === 'medium'
                        ? 'border-amber-200 bg-amber-50'
                        : 'border-blue-200 bg-blue-50'
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-900">{alert.title}</p>
                  <p className="text-xs text-slate-600">{alert.message}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Automated Financial Commentary</p>
            <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50 p-4">
              <p className="text-sm leading-relaxed text-slate-700">{predictive?.automated_financial_commentary || 'No commentary available.'}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Doctor &amp; Referral Financials</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">Referral Revenue Breakdown</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={doctorReferral?.referral_revenue_breakdown || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="doctor_name" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Bar dataKey="revenue" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Referral Cost as % of Revenue</p>
            <p className="mt-2 text-4xl font-black text-rose-700">{Number(doctorReferral?.referral_cost_percent_of_revenue || 0).toFixed(1)}%</p>
            <p className="mt-2 text-xs text-slate-500">Tracks total referral payouts versus referral-attributed topline.</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Doctor Commission &amp; Incentive Tracking</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Doctor</th>
                    <th className="px-3 py-2">Referred Revenue</th>
                    <th className="px-3 py-2">Commission %</th>
                    <th className="px-3 py-2">Commission Earned</th>
                  </tr>
                </thead>
                <tbody>
                  {(doctorReferral?.doctor_commission_tracking || []).map((row) => (
                    <tr key={row.doctor_name} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.doctor_name}</td>
                      <td className="px-3 py-2">{toCurrency(row.referred_revenue)}</td>
                      <td className="px-3 py-2">{row.commission_percent}%</td>
                      <td className="px-3 py-2 font-semibold text-slate-800">{toCurrency(row.commission_earned)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Doctor-wise Profitability</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Doctor</th>
                    <th className="px-3 py-2">Revenue</th>
                    <th className="px-3 py-2">Referral Cost</th>
                    <th className="px-3 py-2">Service Cost</th>
                    <th className="px-3 py-2">Net Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {(doctorReferral?.doctor_wise_profitability || []).map((row) => (
                    <tr key={row.doctor_name} className="border-t border-slate-100">
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
        <h2 className="text-xl font-bold text-slate-900">Branch Profitability Heatmap</h2>
        <div className={`${CARD_CLASS}`}>
          <div className="mb-4 flex flex-wrap items-center gap-3 text-xs">
            <span className="rounded-full bg-emerald-100 px-2 py-1 font-semibold text-emerald-700">Green = Profitable</span>
            <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-700">Yellow = Break-even</span>
            <span className="rounded-full bg-rose-100 px-2 py-1 font-semibold text-rose-700">Red = Loss-making</span>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(branchHeatmap?.items || []).map((item) => (
              <div
                key={item.branch}
                className={`rounded-lg border p-4 ${
                  item.status === 'profitable'
                    ? 'border-emerald-200 bg-emerald-50'
                    : item.status === 'break_even'
                      ? 'border-amber-200 bg-amber-50'
                      : 'border-rose-200 bg-rose-50'
                }`}
              >
                <p className="text-sm font-semibold text-slate-900">{item.branch}</p>
                <p className="mt-1 text-xs uppercase text-slate-500">Profitability Score</p>
                <p className="text-2xl font-black text-slate-800">{item.profitability_score}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">What-If Scenario Simulator</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Scenario Input</p>
            <p className="mt-1 text-xs text-slate-500">What if we open a new branch in Pune and give a 5% discount?</p>
            <div className="mt-4 space-y-3">
              <label className="block text-xs font-semibold uppercase text-slate-500">
                City
                <input
                  value={whatIfCity}
                  onChange={(event) => setWhatIfCity(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  placeholder="Pune"
                />
              </label>
              <label className="block text-xs font-semibold uppercase text-slate-500">
                Discount Percent
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={whatIfDiscount}
                  onChange={(event) => setWhatIfDiscount(Number(event.target.value || 0))}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </label>
              <button
                type="button"
                onClick={() => void runWhatIfScenario()}
                disabled={simulating}
                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
              >
                {simulating ? 'Running Simulation...' : 'Run Simulation'}
              </button>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Projected Revenue &amp; Cost Implications</p>
            {whatIfResult ? (
              <div className="mt-3 space-y-3">
                <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">{whatIfResult.scenario}</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-md bg-emerald-50 p-3">
                    <p className="text-xs uppercase text-emerald-700">Revenue Impact</p>
                    <p className="text-2xl font-black text-emerald-700">{whatIfResult.projections.projected_revenue_impact_percent.toFixed(2)}%</p>
                  </div>
                  <div className="rounded-md bg-rose-50 p-3">
                    <p className="text-xs uppercase text-rose-700">Cost Impact</p>
                    <p className="text-2xl font-black text-rose-700">{whatIfResult.projections.projected_cost_impact_percent.toFixed(2)}%</p>
                  </div>
                  <div className="rounded-md bg-indigo-50 p-3">
                    <p className="text-xs uppercase text-indigo-700">Net Profit Impact</p>
                    <p className="text-2xl font-black text-indigo-700">{whatIfResult.projections.projected_net_profit_impact_percent.toFixed(2)}%</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div className="rounded-md border border-slate-200 p-3">
                    <p className="text-xs uppercase text-slate-500">Estimated Monthly Revenue Delta</p>
                    <p className="text-xl font-bold text-slate-900">{toCurrency(whatIfResult.projections.estimated_monthly_revenue_delta)}</p>
                  </div>
                  <div className="rounded-md border border-slate-200 p-3">
                    <p className="text-xs uppercase text-slate-500">Estimated Monthly Cost Delta</p>
                    <p className="text-xl font-bold text-slate-900">{toCurrency(whatIfResult.projections.estimated_monthly_cost_delta)}</p>
                  </div>
                </div>
                <p className="rounded-md border border-indigo-100 bg-indigo-50 px-3 py-2 text-sm text-slate-700">{whatIfResult.ai_summary}</p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-500">Run the simulation to view AI projected revenue and cost implications.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

export default CeoFinanceAccounts
