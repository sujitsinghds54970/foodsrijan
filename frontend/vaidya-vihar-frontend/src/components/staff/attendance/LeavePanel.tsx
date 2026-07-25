import { LeaveRequestItem } from '../types'

interface LeavePanelProps {
  upcoming: LeaveRequestItem[]
  leaves: LeaveRequestItem[]
  onCancel: (leaveId: number) => void
  onOpenApply: () => void
}

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleDateString()
}

const badgeClass = (status: string) => {
  const normalized = status.toLowerCase()
  if (normalized === 'approved') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200'
  if (normalized === 'rejected') return 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-200'
  if (normalized === 'cancelled') return 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100'
  return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200'
}

export default function LeavePanel({ upcoming, leaves, onCancel, onOpenApply }: LeavePanelProps) {
  const nextLeave = upcoming[0]

  return (
    <div className="space-y-4">
      <div className="sticky top-0 z-10 rounded-2xl border border-sky-200 bg-sky-50 p-4 dark:border-sky-700 dark:bg-sky-900/20">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-300">Upcoming Leave</p>
            <p className="text-base font-bold text-slate-900 dark:text-slate-100">
              {nextLeave
                ? `Next leave: ${formatDate(nextLeave.start_date)} (${(nextLeave.leave_type || 'Leave').toString()})`
                : 'No approved upcoming leave this month'}
            </p>
          </div>
          <button onClick={onOpenApply} className="rounded-lg bg-sky-600 px-3 py-2 text-xs font-semibold text-white hover:bg-sky-700">
            Apply Leave
          </button>
        </div>
        {upcoming.length > 1 && (
          <div className="mt-3 text-xs text-slate-600 dark:text-slate-300">
            {upcoming.slice(1).map((item) => (
              <p key={item.id}>{`${formatDate(item.start_date)} - ${(item.leave_type || '').toString()}`}</p>
            ))}
          </div>
        )}
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-200">
            <tr>
              <th className="px-3 py-2 text-left">Leave Type</th>
              <th className="px-3 py-2 text-left">Duration (Days/Hours)</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Attachment</th>
              <th className="px-3 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {leaves.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-slate-500 dark:text-slate-300" colSpan={5}>No leave requests yet.</td>
              </tr>
            ) : (
              leaves.map((leave) => (
                <tr key={leave.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-3 py-2 capitalize">{leave.leave_type}</td>
                  <td className="px-3 py-2">{`${leave.duration_days || 0} d / ${leave.duration_hours || 0} h`}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeClass(leave.status || '')}`}>{leave.status}</span>
                  </td>
                  <td className="px-3 py-2">
                    {leave.attachments ? (
                      <a href={leave.attachments} target="_blank" rel="noreferrer" className="text-sky-600 underline dark:text-sky-300">File</a>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {(leave.status || '').toLowerCase() === 'pending' ? (
                      <button
                        onClick={() => onCancel(leave.id)}
                        className="rounded-md bg-rose-600 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                      >
                        Cancel Leave
                      </button>
                    ) : (
                      '-'
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
