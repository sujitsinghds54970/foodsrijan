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
  CeoPeopleDeiResponse,
  CeoPeopleEngagementCultureResponse,
  CeoPeopleHealthScoreResponse,
  CeoPeopleLeadershipDevelopmentResponse,
  CeoPeopleTalentRetentionResponse,
  CeoPeopleWhatIfResponse,
  CeoPeopleWorkforceProductivityResponse,
  getCeoPeopleDei,
  getCeoPeopleEngagementCulture,
  getCeoPeopleHealthScore,
  getCeoPeopleLeadershipDevelopment,
  getCeoPeopleTalentRetention,
  getCeoPeopleWhatIfSimulation,
  getCeoPeopleWorkforceProductivity,
  getCeoPeopleWowFeatures,
  CeoPeopleWowFeaturesResponse,
} from './api'

const CARD_CLASS = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm'
const PIE_COLORS = ['#4f46e5', '#0ea5e9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']

const getScoreColor = (score: number) => {
  if (score >= 80) return '#16a34a'
  if (score >= 65) return '#f59e0b'
  return '#ef4444'
}

const toPercent = (value: number) => `${Number(value || 0).toFixed(0)}%`
const signedNumber = (value: number) => `${value > 0 ? '+' : ''}${value}`
const toCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

const CeoPeopleCulture = () => {
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<CeoPeopleHealthScoreResponse | null>(null)
  const [talent, setTalent] = useState<CeoPeopleTalentRetentionResponse | null>(null)
  const [engagement, setEngagement] = useState<CeoPeopleEngagementCultureResponse | null>(null)
  const [leadership, setLeadership] = useState<CeoPeopleLeadershipDevelopmentResponse | null>(null)
  const [workforce, setWorkforce] = useState<CeoPeopleWorkforceProductivityResponse | null>(null)
  const [dei, setDei] = useState<CeoPeopleDeiResponse | null>(null)
  const [wow, setWow] = useState<CeoPeopleWowFeaturesResponse | null>(null)
  const [whatIfRole, setWhatIfRole] = useState('MRI Technologists')
  const [whatIfIncrease, setWhatIfIncrease] = useState('10')
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [whatIfResult, setWhatIfResult] = useState<CeoPeopleWhatIfResponse | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [healthResp, talentResp, engagementResp, leadershipResp, workforceResp, deiResp, wowResp] = await Promise.all([
          getCeoPeopleHealthScore(),
          getCeoPeopleTalentRetention(),
          getCeoPeopleEngagementCulture(),
          getCeoPeopleLeadershipDevelopment(),
          getCeoPeopleWorkforceProductivity(),
          getCeoPeopleDei(),
          getCeoPeopleWowFeatures(),
        ])
        setHealth(healthResp)
        setTalent(talentResp)
        setEngagement(engagementResp)
        setLeadership(leadershipResp)
        setWorkforce(workforceResp)
        setDei(deiResp)
        setWow(wowResp)
        setWhatIfResult({
          is_mock: true,
          input: wowResp.default_what_if.input,
          role_name: 'MRI Technologists',
          salary_increase_percent: 10,
          attrition_impact_percent: wowResp.default_what_if.attrition_impact_percent,
          workforce_cost_impact_percent: wowResp.default_what_if.workforce_cost_impact_percent,
          estimated_monthly_cost_increase: wowResp.default_what_if.estimated_monthly_cost_increase,
          summary: wowResp.default_what_if.summary,
          table_reference: wowResp.table_reference,
        })
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Unable to load People & Culture insights')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const gaugeData = useMemo(() => {
    const value = health?.score || 0
    return [{ name: 'Health', value, fill: getScoreColor(value) }]
  }, [health])

  const enpsGaugeData = useMemo(() => {
    const value = engagement?.enps.score || 0
    const normalized = Math.max(0, Math.min(100, ((value + 100) / 200) * 100))
    return [{ name: 'eNPS', value: normalized, fill: getScoreColor(normalized) }]
  }, [engagement])

  const handleWhatIfRun = async () => {
    const roleName = whatIfRole.trim()
    const increasePercent = Number(whatIfIncrease)
    if (!roleName || Number.isNaN(increasePercent) || increasePercent < 0 || increasePercent > 50) {
      toast.error('Enter a valid role and salary increase between 0% and 50%.')
      return
    }
    setWhatIfLoading(true)
    try {
      const response = await getCeoPeopleWhatIfSimulation({
        role_name: roleName,
        salary_increase_percent: increasePercent,
      })
      setWhatIfResult(response)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run What-If simulation')
    } finally {
      setWhatIfLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading People &amp; Culture dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">People &amp; Culture</h1>
        <p className="mt-1 text-sm text-slate-600">
          Organizational health and talent engine insights for super admin leadership decisions.
        </p>
      </section>

      <section className="rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50 to-cyan-50 p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase text-indigo-700">CEO Daily Pulse Briefing</p>
        <p className="mt-2 text-sm font-medium text-indigo-900">
          {wow?.ceo_daily_pulse || 'Good morning. Daily pulse summary is loading...'}
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Organizational Health Score (The Pulse)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Overall Health Score</p>
            <div className="mt-2 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  innerRadius="70%"
                  outerRadius="100%"
                  barSize={22}
                  data={gaugeData}
                  startAngle={180}
                  endAngle={0}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-96px] text-center">
              <p className="text-4xl font-black" style={{ color: getScoreColor(health?.score || 0) }}>
                {health?.score || 0}
              </p>
              <p className="text-xs font-semibold uppercase text-slate-500">Trend: {health?.trend || 'stable'}</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Driver Breakdown</p>
            <div className="mt-3 space-y-4">
              {[
                { label: 'Engagement', value: health?.drivers.engagement || 0 },
                { label: 'Attrition', value: health?.drivers.attrition || 0 },
                { label: 'Leadership Pipeline', value: health?.drivers.leadership || 0 },
              ].map((item) => (
                <div key={item.label}>
                  <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-600">
                    <span>{item.label}</span>
                    <span>{item.value}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500"
                      style={{ width: `${Math.min(Math.max(item.value, 0), 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Benchmark Comparison</p>
            <div className="mt-3 space-y-3 text-sm">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Industry Average</p>
                <p className="text-3xl font-black text-slate-700">{health?.benchmark.industry_average ?? 74}</p>
              </div>
              <div className="rounded-lg bg-emerald-50 p-3">
                <p className="text-xs uppercase text-emerald-700">Our Score</p>
                <p className="text-3xl font-black text-emerald-700">{health?.benchmark.our_score ?? 82}</p>
              </div>
              <p className="text-xs text-slate-500">Mock output powered by new read-only CEO People APIs.</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">12-Month Health Trajectory</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={health?.monthly_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis domain={[60, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Talent Acquisition &amp; Retention (The Engine of Growth)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 xl:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Total Headcount</p>
            <p className="mt-2 text-4xl font-black text-indigo-700">{talent?.headcount.total ?? 0}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-6 xl:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">YTD Attrition</p>
            <p className="mt-2 text-4xl font-black text-rose-600">{toPercent(talent?.attrition_retention.ytd_attrition_percent ?? 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-6 xl:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Retention Rate</p>
            <p className="mt-2 text-4xl font-black text-emerald-600">{toPercent(talent?.attrition_retention.retention_rate_percent ?? 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 xl:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Quality of Hire (6M)</p>
            <p className="mt-2 text-4xl font-black text-sky-700">{(talent?.quality_of_hire.six_month_avg_rating ?? 0).toFixed(1)}</p>
            <p className="mt-1 text-xs text-slate-500">Based on {talent?.quality_of_hire.new_hires_evaluated ?? 0} new hires</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Headcount by Branch</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={talent?.headcount.by_branch || []}
                    dataKey="count"
                    nameKey="name"
                    outerRadius={110}
                    label
                  >
                    {(talent?.headcount.by_branch || []).map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Headcount by Department</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={talent?.headcount.by_department || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#4f46e5" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Attrition vs Retention by Branch</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={talent?.attrition_retention.by_branch || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="attrition" fill="#ef4444" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="retention" fill="#22c55e" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Time-to-Hire &amp; Time-to-Fill</p>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Avg Time-to-Hire</p>
                <p className="text-3xl font-black text-slate-900">{talent?.hiring_velocity.avg_time_to_hire_days ?? 0} days</p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Avg Time-to-Fill</p>
                <p className="text-3xl font-black text-slate-900">{talent?.hiring_velocity.avg_time_to_fill_days ?? 0} days</p>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {(talent?.hiring_velocity.critical_roles || []).map((role) => (
                <div key={role.role} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <span className="font-medium text-slate-800">{role.role}</span>
                  <span className="font-bold text-amber-700">{role.days_to_fill} days</span>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Open Positions &amp; Critical Roles</p>
            <div className="mt-3 space-y-2">
              {(talent?.open_positions || []).map((position) => (
                <div key={`${position.role}-${position.branch}`} className="rounded-md border border-slate-200 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-900">{position.role}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        position.critical ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {position.critical ? 'Critical' : 'Normal'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{position.branch} • {position.department}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Employee Engagement &amp; Culture (The Soul)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Employee Net Promoter Score (eNPS)</p>
            <div className="mt-2 h-52">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  innerRadius="68%"
                  outerRadius="100%"
                  barSize={20}
                  data={enpsGaugeData}
                  startAngle={180}
                  endAngle={0}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-78px] text-center">
              <p className="text-4xl font-black text-indigo-700">{signedNumber(engagement?.enps.score || 0)}</p>
              <p className="mx-auto mt-1 max-w-xs text-xs text-slate-500">{engagement?.enps.description || 'No eNPS description available.'}</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Engagement Index</p>
            <div className="mt-3 rounded-lg bg-blue-50 p-4">
              <p className="text-xs uppercase text-blue-600">Composite Score</p>
              <p className="mt-1 text-4xl font-black text-blue-700">{engagement?.engagement_index.score ?? 0}</p>
              <p className="mt-2 text-xs text-slate-600">{engagement?.engagement_index.source || 'Pulse survey composite (mock).'}</p>
            </div>
            <p className="mt-3 text-xs text-slate-500">Includes pulse sentiment, recognition activity, and consistency indicators.</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Real-time Feedback &amp; Recognition Feed</p>
            <div className="mt-3 max-h-52 space-y-2 overflow-y-auto pr-1">
              {(engagement?.recognition_feed || []).map((feed) => (
                <div key={feed.id} className="rounded-md border border-slate-200 bg-slate-50 p-2">
                  <p className="text-xs font-semibold text-slate-800">{feed.actor}</p>
                  <p className="mt-1 text-xs text-slate-600">{feed.message}</p>
                  <p className="mt-1 text-[10px] uppercase text-slate-400">{feed.source}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Pulse Survey Results (Theme Sentiment)</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={engagement?.pulse_survey_results || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="theme" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="positive" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="negative" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Leadership &amp; Talent Development (The Future)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Leadership Pipeline Readiness</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={leadership?.leadership_pipeline || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="level" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Internal Promotion Rate</p>
            <div className="mt-3 rounded-lg bg-emerald-50 p-4">
              <p className="text-xs uppercase text-emerald-700">Open positions filled internally</p>
              <p className="mt-1 text-4xl font-black text-emerald-700">{toPercent(leadership?.internal_promotion_rate_percent ?? 0)}</p>
            </div>
            <p className="mt-3 text-xs text-slate-500">Higher internal fill rates indicate stronger succession and development continuity.</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Managerial Effectiveness Score by Branch</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={leadership?.manager_effectiveness || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="branch" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="engagement_score" fill="#3b82f6" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="retention_score" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="overall_score" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Skills Gap Analysis</p>
            <ul className="mt-3 space-y-2">
              {(leadership?.skills_gap_analysis || []).map((gap, index) => (
                <li key={`${gap}-${index}`} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  {gap}
                </li>
              ))}
            </ul>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">High-Potential (HiPo) Talent Pool</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Employee ID</th>
                    <th className="px-3 py-2">Name</th>
                    <th className="px-3 py-2">Branch</th>
                    <th className="px-3 py-2">Role</th>
                    <th className="px-3 py-2">Readiness</th>
                  </tr>
                </thead>
                <tbody>
                  {(leadership?.hipo_talent_pool || []).map((row) => (
                    <tr key={row.employee_id} className="border-t border-slate-100">
                      <td className="px-3 py-2 font-medium text-slate-800">{row.employee_id}</td>
                      <td className="px-3 py-2">{row.name}</td>
                      <td className="px-3 py-2">{row.branch}</td>
                      <td className="px-3 py-2">{row.role}</td>
                      <td className="px-3 py-2">{row.readiness}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Workforce Cost &amp; Productivity (The ROI of People)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Revenue Per Employee</p>
            <p className="mt-2 text-3xl font-black text-indigo-700">{toCurrency(workforce?.revenue_per_employee ?? 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Total Workforce Cost</p>
            <p className="mt-2 text-3xl font-black text-rose-700">{toCurrency(workforce?.total_workforce_cost ?? 0)}</p>
            <p className="mt-1 text-xs text-slate-500">{toPercent(workforce?.workforce_cost_percent_of_revenue ?? 0)} of revenue</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Labor Cost Forecast</p>
            <p className="mt-2 text-sm text-slate-700">{workforce?.forecast_notes || 'Forecast pending.'}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Branch-wise Cost vs Revenue</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={workforce?.branch_cost_comparison || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="branch" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Bar dataKey="revenue" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="workforce_cost" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">AI Labor Cost Forecast</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={workforce?.labor_cost_forecast || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Line type="monotone" dataKey="forecast_cost" stroke="#7c3aed" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Diversity, Equity &amp; Inclusion (DEI) – The Strength</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">DEI Score</p>
            <p className="mt-2 text-4xl font-black text-violet-700">{dei?.dei_scorecard.score ?? 0}</p>
            <div className="mt-2 space-y-1 text-xs text-slate-600">
              <p>Representation: {dei?.dei_scorecard.representation_score ?? 0}</p>
              <p>Pay Equity: {dei?.dei_scorecard.pay_equity_score ?? 0}</p>
              <p>Inclusion: {dei?.dei_scorecard.inclusion_score ?? 0}</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-sm font-semibold text-slate-700">Gender</p>
            <div className="mt-2 h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dei?.workforce_demographics.gender || []} dataKey="value" nameKey="name" outerRadius={80} label>
                    {(dei?.workforce_demographics.gender || []).map((entry, index) => (
                      <Cell key={`gender-${entry.name}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-sm font-semibold text-slate-700">Age</p>
            <div className="mt-2 h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dei?.workforce_demographics.age || []} dataKey="value" nameKey="name" outerRadius={80} label>
                    {(dei?.workforce_demographics.age || []).map((entry, index) => (
                      <Cell key={`age-${entry.name}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}>
            <p className="text-sm font-semibold text-slate-700">Ethnicity</p>
            <div className="mt-2 h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dei?.workforce_demographics.ethnicity || []} dataKey="value" nameKey="name" outerRadius={80} label>
                    {(dei?.workforce_demographics.ethnicity || []).map((entry, index) => (
                      <Cell key={`ethnicity-${entry.name}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Pay Equity Analysis</p>
            <div className="mt-3 overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Role</th>
                    <th className="px-3 py-2">Gender / Ethnicity</th>
                    <th className="px-3 py-2">Average Pay</th>
                  </tr>
                </thead>
                <tbody>
                  {(dei?.pay_equity_analysis || []).map((row, index) => (
                    <tr key={`${row.role}-${row.gender_or_ethnicity}-${index}`} className="border-t border-slate-100">
                      <td className="px-3 py-2">{row.role}</td>
                      <td className="px-3 py-2">{row.gender_or_ethnicity}</td>
                      <td className="px-3 py-2 font-semibold text-slate-800">{toCurrency(row.avg_pay)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Out-of-the-Box "Wow" Features</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">The "Flight Risk" AI</p>
            <div className="mt-3 space-y-2">
              {(wow?.flight_risk_employees || []).map((employee) => (
                <div key={employee.employee_id} className="rounded-md border border-slate-200 p-3">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-900">{employee.name}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        employee.risk_level === 'high' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {employee.risk_level.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{employee.role} • {employee.branch}</p>
                  <p className="mt-1 text-xs text-slate-600">
                    Tenure: {employee.tenure_months} months • Engagement: {employee.engagement_score}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">The "Culture Heatmap"</p>
            <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
              {(wow?.culture_heatmap || []).map((cell) => {
                const score = cell.engagement_score
                const shadeClass =
                  score >= 85 ? 'bg-emerald-100 text-emerald-900 border-emerald-200'
                    : score >= 75 ? 'bg-blue-100 text-blue-900 border-blue-200'
                      : 'bg-amber-100 text-amber-900 border-amber-200'
                return (
                  <div key={`${cell.branch}-${cell.department}`} className={`rounded-md border px-3 py-2 ${shadeClass}`}>
                    <p className="text-xs font-semibold">{cell.branch}</p>
                    <p className="text-xs">{cell.department}</p>
                    <p className="mt-1 text-sm font-black">{score}</p>
                  </div>
                )
              })}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">"What-If" Scenario Simulator</p>
            <div className="mt-3 grid grid-cols-12 gap-3">
              <input
                value={whatIfRole}
                onChange={(event) => setWhatIfRole(event.target.value)}
                className="col-span-12 rounded-lg border border-slate-300 px-3 py-2 text-sm lg:col-span-7"
                placeholder="Role (e.g., MRI Technologists)"
              />
              <input
                type="number"
                min={0}
                max={50}
                value={whatIfIncrease}
                onChange={(event) => setWhatIfIncrease(event.target.value)}
                className="col-span-12 rounded-lg border border-slate-300 px-3 py-2 text-sm lg:col-span-3"
                placeholder="Increase %"
              />
              <button
                type="button"
                onClick={() => void handleWhatIfRun()}
                disabled={whatIfLoading}
                className="col-span-12 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 lg:col-span-2"
              >
                {whatIfLoading ? 'Running...' : 'Run Scenario'}
              </button>
            </div>
            {whatIfResult && (
              <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
                <p className="font-semibold text-slate-800">{whatIfResult.input}</p>
                <div className="mt-2 grid grid-cols-12 gap-2">
                  <div className="col-span-12 rounded bg-white p-2 md:col-span-4">
                    <p className="text-xs text-slate-500">Attrition Impact</p>
                    <p className="text-lg font-black text-emerald-700">{whatIfResult.attrition_impact_percent}%</p>
                  </div>
                  <div className="col-span-12 rounded bg-white p-2 md:col-span-4">
                    <p className="text-xs text-slate-500">Workforce Cost Impact</p>
                    <p className="text-lg font-black text-rose-700">{whatIfResult.workforce_cost_impact_percent}%</p>
                  </div>
                  <div className="col-span-12 rounded bg-white p-2 md:col-span-4">
                    <p className="text-xs text-slate-500">Estimated Monthly Cost Increase</p>
                    <p className="text-lg font-black text-slate-900">{toCurrency(whatIfResult.estimated_monthly_cost_increase)}</p>
                  </div>
                </div>
                <p className="mt-2 text-xs text-slate-600">{whatIfResult.summary}</p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className={`${CARD_CLASS}`}>
        <h3 className="text-base font-semibold text-slate-900">Real Data Mapping (Current Mock Strategy)</h3>
        <p className="mt-1 text-sm text-slate-600">
          These widgets currently use mock values served by read-only APIs. The table snapshots below are live references for future aggregation wiring.
        </p>
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">StaffProfile rows</p><p className="font-bold text-slate-900">{talent?.table_reference.staff_profiles_count ?? 0}</p></div>
          <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">PayrollRun rows</p><p className="font-bold text-slate-900">{talent?.table_reference.payroll_runs_count ?? 0}</p></div>
          <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">AttendanceLog rows</p><p className="font-bold text-slate-900">{talent?.table_reference.attendance_logs_count ?? 0}</p></div>
          <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Branch rows</p><p className="font-bold text-slate-900">{talent?.table_reference.branches_count ?? 0}</p></div>
        </div>
      </section>
    </div>
  )
}

export default CeoPeopleCulture
