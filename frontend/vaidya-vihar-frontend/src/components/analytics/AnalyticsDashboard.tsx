import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from 'recharts'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'
import { fetchAnalyticsDashboard, fetchAnalyticsTrends, fetchNextMonthForecast, fetchTopReferrers } from './api'
import { DashboardResponse, ForecastResponse, TopReferrersResponse, TrendsResponse } from './types'

const PIE_COLORS = ['#0ea5e9', '#22c55e', '#f59e0b', '#8b5cf6', '#ef4444']

function toIsoDate(d: Date) {
  return d.toISOString().slice(0, 10)
}

function formatInr(value: number) {
  return `Rs ${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}

export default function AnalyticsDashboard() {
  const { user, token } = useAuth()
  const [branchId, setBranchId] = useState<number>(Number(user?.branch_id || 1))
  const [loading, setLoading] = useState(false)

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [trends, setTrends] = useState<TrendsResponse | null>(null)
  const [topReferrers, setTopReferrers] = useState<TopReferrersResponse | null>(null)
  const [forecast, setForecast] = useState<ForecastResponse | null>(null)

  const [startDate, setStartDate] = useState<string>(toIsoDate(new Date(Date.now() - 29 * 24 * 3600 * 1000)))
  const [endDate, setEndDate] = useState<string>(toIsoDate(new Date()))

  useEffect(() => {
    if (user?.role !== 'super_admin' && user?.branch_id) {
      setBranchId(Number(user.branch_id))
    }
  }, [user?.role, user?.branch_id])

  const loadData = useCallback(async () => {
    if (!branchId) {
      toast.error('Please provide a valid branch ID')
      return
    }

    try {
      setLoading(true)
      const [dashboardData, trendsData, topDoctorsData, forecastData] = await Promise.all([
        fetchAnalyticsDashboard(branchId, token),
        fetchAnalyticsTrends(branchId, startDate, endDate, token),
        fetchTopReferrers(branchId, startDate, endDate, token),
        fetchNextMonthForecast(branchId, token),
      ])

      setDashboard(dashboardData)
      setTrends(trendsData)
      setTopReferrers(topDoctorsData)
      setForecast(forecastData)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to load analytics data')
    } finally {
      setLoading(false)
    }
  }, [branchId, token, startDate, endDate])

  useEffect(() => {
    loadData().catch(() => {
      toast.error('Failed to initialize analytics module')
    })
  }, [loadData])

  const anomaly = useMemo(() => {
    const daily = trends?.daily || []
    if (daily.length < 8) return null

    const todayPoint = daily[daily.length - 1]
    const prev7 = daily.slice(-8, -1)
    const avg7 = prev7.reduce((sum, item) => sum + item.revenue, 0) / prev7.length
    if (avg7 <= 0) return null

    if (todayPoint.revenue < avg7 * 0.7) {
      return {
        message: `Revenue drop detected in Branch ${branchId}.`,
        todayRevenue: todayPoint.revenue,
        avg7,
      }
    }
    return null
  }, [trends?.daily, branchId])

  const modalityChartData = useMemo(() => {
    if (!dashboard) return []
    return [
      { name: 'X-ray', value: dashboard.modality_split.xray },
      { name: 'Sonography', value: dashboard.modality_split.sonography },
      { name: 'Pathology', value: dashboard.modality_split.pathology },
      { name: 'CT/MRI', value: dashboard.modality_split.ct_mri },
      { name: 'Other', value: dashboard.modality_split.other },
    ]
  }, [dashboard])

  const topDoctorsChart = useMemo(() => {
    return (topReferrers?.items || []).slice(0, 5).map((row) => ({
      doctor: row.doctor_name,
      revenue: row.total_revenue,
      patients: row.patient_count,
    }))
  }, [topReferrers?.items])

  const tatRows = dashboard?.department_tat || []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3 rounded-2xl bg-white p-5 shadow-sm">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Founder Analytics</p>
          <h1 className="text-3xl font-black text-slate-900">Business 360 Dashboard</h1>
        </div>

        <div className="ml-auto grid grid-cols-1 gap-2 sm:grid-cols-4">
          <input
            type="number"
            value={branchId}
            onChange={(e) => setBranchId(Number(e.target.value || 0))}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Branch ID"
            disabled={user?.role !== 'super_admin'}
          />
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <button onClick={() => loadData()} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Refresh</button>
        </div>
      </div>

      {anomaly && (
        <div className="rounded-2xl border border-rose-300 bg-rose-50 p-4">
          <p className="text-sm font-bold text-rose-700">Revenue Alert</p>
          <p className="text-rose-800">Revenue drop detected in Branch {branchId}.</p>
          <p className="mt-1 text-xs text-rose-700">
            Today: {formatInr(anomaly.todayRevenue)} vs 7-day avg: {formatInr(anomaly.avg7)}
          </p>
        </div>
      )}

      {forecast && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm font-bold text-emerald-700">Next Month Forecast</p>
          <p className="text-emerald-900">
            Predicted Patients: {forecast.predicted_patients} (+/-{forecast.confidence_margin_percent}%)
          </p>
          <p className="mt-1 text-xs text-emerald-700">
            Range: {forecast.lower_bound} - {forecast.upper_bound}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <KpiCard title="Current Month Revenue" value={formatInr(dashboard?.kpis.total_revenue || 0)} />
        <KpiCard title="Current Month Net Profit" value={formatInr(dashboard?.kpis.net_profit || 0)} />
        <KpiCard title="Patient Count" value={String(dashboard?.kpis.patient_count || 0)} />
        <KpiCard title="Avg Bill Value" value={formatInr(dashboard?.kpis.avg_bill_value || 0)} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-lg font-semibold text-slate-900">Daily Revenue vs Expense</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends?.daily || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="revenue" stroke="#16a34a" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="expenses" stroke="#dc2626" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-lg font-semibold text-slate-900">Modality Distribution</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={modalityChartData} dataKey="value" nameKey="name" outerRadius={110} label>
                  {modalityChartData.map((entry, idx) => (
                    <Cell key={`${entry.name}-${idx}`} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-lg font-semibold text-slate-900">Top 5 Referring Doctors</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topDoctorsChart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="doctor" hide />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="revenue" fill="#0284c7" />
                <Bar dataKey="patients" fill="#a855f7" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h3 className="mb-3 text-lg font-semibold text-slate-900">Department-wise TAT</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b bg-slate-50 text-left text-slate-700">
                  <th className="px-3 py-2">Department</th>
                  <th className="px-3 py-2">Avg Minutes</th>
                  <th className="px-3 py-2">Avg Hours</th>
                  <th className="px-3 py-2">Samples</th>
                </tr>
              </thead>
              <tbody>
                {tatRows.map((row) => (
                  <tr key={row.department} className="border-b border-slate-100">
                    <td className="px-3 py-2 capitalize">{row.department.replace('_', '/')}</td>
                    <td className="px-3 py-2">{row.avg_minutes}</td>
                    <td className="px-3 py-2">{row.avg_hours}</td>
                    <td className="px-3 py-2">{row.sample_size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {loading && <div className="text-sm text-slate-500">Loading analytics...</div>}
    </div>
  )
}

function KpiCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-black text-slate-900">{value}</p>
    </div>
  )
}
