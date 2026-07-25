import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { getApiErrorMessage, staffApi } from './api'
import { LeaveEntry } from './types'

interface LeaveRequestsProps {
  staffProfileId: number
  canReview: boolean
}

export default function LeaveRequests({ staffProfileId, canReview }: LeaveRequestsProps) {
  const [items, setItems] = useState<LeaveEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    leave_type: 'casual',
    start_date: '',
    end_date: '',
    reason: '',
  })

  const load = async () => {
    setLoading(true)
    try {
      const rows = await staffApi.listLeave(staffProfileId)
      setItems(rows)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to load leaves'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staffProfileId])

  const submit = async () => {
    if (!form.start_date || !form.end_date) {
      toast.error('Start and end dates are required')
      return
    }
    try {
      await staffApi.applyLeave(staffProfileId, form)
      toast.success('Leave request submitted')
      setForm({ leave_type: 'casual', start_date: '', end_date: '', reason: '' })
      load()
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to submit leave'))
    }
  }

  const decide = async (leaveId: number, status: 'approved' | 'rejected') => {
    try {
      await staffApi.decideLeave(leaveId, { status })
      toast.success(`Leave ${status}`)
      load()
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to update leave status'))
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-bold text-slate-900">Leave Requests</h3>

      <div className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <select className="rounded border px-2 py-1.5 text-sm" value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}>
          <option value="casual">Casual</option>
          <option value="sick">Sick</option>
          <option value="privileged">Privileged</option>
          <option value="other">Other</option>
        </select>
        <input type="date" className="rounded border px-2 py-1.5 text-sm" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        <input type="date" className="rounded border px-2 py-1.5 text-sm" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        <input className="rounded border px-2 py-1.5 text-sm" placeholder="Reason" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
      </div>

      <button onClick={submit} className="mb-3 rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">Apply Leave</button>

      {loading ? (
        <p className="text-sm text-slate-500">Loading leave records...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-500">No leave records.</p>
      ) : (
        <div className="max-h-52 overflow-auto rounded border">
          <table className="min-w-full text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-2 py-1 text-left">Type</th>
                <th className="px-2 py-1 text-left">From</th>
                <th className="px-2 py-1 text-left">To</th>
                <th className="px-2 py-1 text-left">Days</th>
                <th className="px-2 py-1 text-left">Status</th>
                <th className="px-2 py-1 text-left">Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-t">
                  <td className="px-2 py-1 capitalize">{row.leave_type}</td>
                  <td className="px-2 py-1">{new Date(row.start_date).toLocaleDateString()}</td>
                  <td className="px-2 py-1">{new Date(row.end_date).toLocaleDateString()}</td>
                  <td className="px-2 py-1">{row.total_days}</td>
                  <td className="px-2 py-1 capitalize">{row.status}</td>
                  <td className="px-2 py-1">
                    {canReview && row.status === 'pending' ? (
                      <div className="flex gap-1">
                        <button onClick={() => decide(row.id, 'approved')} className="rounded bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white">Approve</button>
                        <button onClick={() => decide(row.id, 'rejected')} className="rounded bg-red-600 px-2 py-1 text-[10px] font-semibold text-white">Reject</button>
                      </div>
                    ) : (
                      '-'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
