import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Bar, BarChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { getApiErrorMessage, staffSelfApi } from './api'
import { StaffPerformance } from './types'

const monthToken = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`

export default function PerformanceTab() {
  const [month, setMonth] = useState(monthToken(new Date()))
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<StaffPerformance | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const result = await staffSelfApi.getMyPerformance(month)
      setData(result)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load performance metrics'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month])

  const attendanceSeries = useMemo(() => {
    const pct = data?.attendance_percentage || 0
    return [
      { name: 'Present %', value: pct },
      { name: 'Remaining %', value: Math.max(0, 100 - pct) },
    ]
  }, [data])

  const taskSeries = useMemo(() => {
    return [
      { name: 'Completed', value: data?.tasks_completed || 0 },
      { name: 'Pending', value: Math.max(0, (data?.tasks_total || 0) - (data?.tasks_completed || 0)) },
    ]
  }, [data])

  const completionRate = useMemo(() => {
    const total = data?.tasks_total || 0
    if (total <= 0) return 0
    return Math.round(((data?.tasks_completed || 0) / total) * 100)
  }, [data])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">My Performance</h2>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />
      </div>

      {loading ? (
        <div className="rounded-2xl bg-white/90 p-6 shadow dark:bg-slate-900">Loading performance...</div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl bg-indigo-50 p-4 dark:bg-indigo-900/30"><p className="text-xs font-semibold uppercase text-indigo-700 dark:text-indigo-200">Attendance %</p><p className="mt-2 text-3xl font-extrabold text-indigo-900 dark:text-indigo-100">{data?.attendance_percentage || 0}%</p></div>
            <div className="rounded-2xl bg-teal-50 p-4 dark:bg-teal-900/30"><p className="text-xs font-semibold uppercase text-teal-700 dark:text-teal-200">Tasks Completed</p><p className="mt-2 text-3xl font-extrabold text-teal-900 dark:text-teal-100">{data?.tasks_completed || 0}/{data?.tasks_total || 0}</p></div>
            <div className="rounded-2xl bg-amber-50 p-4 dark:bg-amber-900/30"><p className="text-xs font-semibold uppercase text-amber-700 dark:text-amber-200">Total Revenue Generated</p><p className="mt-2 text-3xl font-extrabold text-amber-900 dark:text-amber-100">{data?.revenue_generated || 0}</p></div>
          </div>

          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-900/30">
            <p className="text-xs font-semibold uppercase text-emerald-700 dark:text-emerald-200">Task Completion Rate (Current Month)</p>
            <p className="mt-2 text-3xl font-extrabold text-emerald-900 dark:text-emerald-100">{completionRate}%</p>
            <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-200">{data?.tasks_completed || 0} of {data?.tasks_total || 0} tasks completed.</p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
              <h3 className="mb-4 text-lg font-bold text-slate-900 dark:text-slate-100">Attendance Percentage</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={attendanceSeries} dataKey="value" nameKey="name" outerRadius={100} innerRadius={60} fill="#4f46e5" label />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
              <h3 className="mb-4 text-lg font-bold text-slate-900 dark:text-slate-100">Tasks Completed (Current Month)</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={taskSeries}>
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#0ea5e9" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
