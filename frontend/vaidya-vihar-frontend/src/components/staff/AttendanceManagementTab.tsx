import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

import { getApiErrorMessage, staffSelfApi } from './api'
import { StaffSelfAttendanceRow } from './types'

const monthToken = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`

export default function AttendanceManagementTab() {
  const [month, setMonth] = useState(monthToken(new Date()))
  const [loading, setLoading] = useState(true)
  const [clocking, setClocking] = useState(false)
  const [rows, setRows] = useState<StaffSelfAttendanceRow[]>([])

  const loadRows = async () => {
    try {
      setLoading(true)
      const data = await staffSelfApi.getMyAttendance(month)
      setRows(data)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load attendance'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRows()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month])

  const byDay = useMemo(() => {
    const map = new Map<string, StaffSelfAttendanceRow>()
    rows.forEach((row) => {
      const key = new Date(row.attendance_date).toISOString().slice(0, 10)
      map.set(key, row)
    })
    return map
  }, [rows])

  const palette = (status: string) => {
    const s = status.toLowerCase()
    if (s === 'present') return 'bg-green-500 text-white'
    if (s === 'absent') return 'bg-red-500 text-white'
    if (s === 'leave') return 'bg-yellow-500 text-black'
    if (s === 'holiday') return 'bg-slate-400 text-white'
    return 'bg-slate-200 text-slate-700'
  }

  const runClock = async (action: 'in' | 'out') => {
    try {
      setClocking(true)
      const coords = await new Promise<{ latitude?: string; longitude?: string }>((resolve) => {
        if (!navigator.geolocation) return resolve({})
        navigator.geolocation.getCurrentPosition(
          (pos) => resolve({ latitude: String(pos.coords.latitude), longitude: String(pos.coords.longitude) }),
          () => resolve({}),
          { enableHighAccuracy: true, timeout: 6000 },
        )
      })
      await staffSelfApi.clockMyAttendance({ action, ...coords })
      toast.success(action === 'in' ? 'Clock-in saved' : 'Clock-out saved')
      await loadRows()
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to update attendance'))
    } finally {
      setClocking(false)
    }
  }

  const [year, m] = month.split('-').map(Number)
  const first = new Date(year, (m || 1) - 1, 1)
  const totalDays = new Date(year, m || 1, 0).getDate()

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <button disabled={clocking} onClick={() => void runClock('in')} className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-60">Clock In</button>
        <button disabled={clocking} onClick={() => void runClock('out')} className="rounded-xl bg-orange-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-orange-700 disabled:opacity-60">Clock Out</button>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
        <h2 className="mb-4 text-xl font-bold text-slate-900 dark:text-slate-100">Attendance Management System</h2>
        {loading ? (
          <p className="text-slate-600 dark:text-slate-300">Loading monthly attendance...</p>
        ) : (
          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: first.getDay() }).map((_, idx) => <div key={`pad-${idx}`} className="h-20 rounded-lg bg-transparent" />)}
            {Array.from({ length: totalDays }).map((_, idx) => {
              const day = idx + 1
              const dateKey = new Date(year, (m || 1) - 1, day).toISOString().slice(0, 10)
              const row = byDay.get(dateKey)
              const status = row?.status || 'No Data'
              return (
                <div key={day} className="h-20 rounded-xl border border-slate-100 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-800">
                  <p className="text-xs font-semibold text-slate-500 dark:text-slate-300">{day}</p>
                  <div className={`mt-2 inline-flex rounded-md px-2 py-1 text-[11px] font-bold ${palette(status)}`}>{status}</div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
