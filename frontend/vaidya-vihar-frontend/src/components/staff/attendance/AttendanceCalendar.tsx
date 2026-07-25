import Calendar from 'react-calendar'
import { AttendanceLogItem } from '../types'

interface AttendanceCalendarProps {
  value: Date
  logs: AttendanceLogItem[]
  onChange: (date: Date) => void
  onSelectLog: (log?: AttendanceLogItem) => void
}

const toDateKey = (value: Date | string) => {
  const d = typeof value === 'string' ? new Date(value) : value
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tz).toISOString().slice(0, 10)
}

const statusClass = (status?: string) => {
  const normalized = (status || '').toLowerCase()
  if (normalized === 'present' || normalized === 'workfromhome') return 'bg-emerald-500 text-white'
  if (normalized === 'late') return 'bg-amber-400 text-slate-900'
  if (normalized === 'absent') return 'bg-rose-500 text-white'
  if (normalized === 'approvedleave') return 'bg-sky-500 text-white'
  return 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100'
}

export default function AttendanceCalendar({ value, logs, onChange, onSelectLog }: AttendanceCalendarProps) {
  const byDate = new Map(logs.map((item) => [item.date, item]))

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-4 flex flex-wrap gap-2 text-xs font-semibold">
        <span className="rounded-full bg-emerald-500 px-2.5 py-1 text-white">Present</span>
        <span className="rounded-full bg-amber-400 px-2.5 py-1 text-slate-900">Late</span>
        <span className="rounded-full bg-rose-500 px-2.5 py-1 text-white">Absent</span>
        <span className="rounded-full bg-sky-500 px-2.5 py-1 text-white">Approved Leave</span>
      </div>

      <Calendar
        value={value}
        onChange={(next) => {
          const selected = Array.isArray(next) ? next[0] : next
          onChange(selected as Date)
          const selectedKey = toDateKey(selected as Date)
          onSelectLog(byDate.get(selectedKey))
        }}
        tileClassName={({ date, view }) => {
          if (view !== 'month') return ''
          const row = byDate.get(toDateKey(date))
          if (!row) return 'rounded-lg border border-slate-100 dark:border-slate-700'
          return `rounded-lg ${statusClass(row.status)}`
        }}
      />
    </div>
  )
}
