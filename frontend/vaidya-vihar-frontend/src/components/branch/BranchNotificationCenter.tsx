import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'

const API_BASE =
  (process as any).env.REACT_APP_API_BASE_URL ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

type LeaveRequestSummary = {
  id: number
  staff_profile_id: number
  staff_name?: string | null
  staff_id?: string | null
  leave_type: string
  start_date: string
  end_date: string
  reason?: string | null
  status: string
  rejection_reason?: string | null
}

type BranchNotification = {
  id: number
  type: string
  title: string
  message: string
  related_entity_id?: number | null
  is_read: boolean
  created_at: string
  status?: string
  leave_request?: LeaveRequestSummary | null
}

const canManageBranchNotifications = (role?: string): boolean => {
  const normalizedRole = (role || '').trim().toLowerCase()
  return normalizedRole === 'branch_director' || normalizedRole === 'branch_admin'
}

export default function BranchNotificationCenter() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [notifications, setNotifications] = useState<BranchNotification[]>([])
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null)
  const [rejectModalNotification, setRejectModalNotification] = useState<BranchNotification | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const canUse = useMemo(() => canManageBranchNotifications(user?.role), [user?.role])

  const loadNotifications = useCallback(async () => {
    if (!canUse) return
    try {
      setLoading(true)
      const response = await axios.get(`${API_BASE}/api/branch/notifications`)
      setNotifications(Array.isArray(response.data) ? response.data : [])
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }, [canUse])

  useEffect(() => {
    void loadNotifications()
  }, [loadNotifications])

  const markRead = async (notificationId: number) => {
    try {
      setActionLoadingId(notificationId)
      await axios.put(`${API_BASE}/api/branch/notifications/${notificationId}/read`)
      setNotifications((prev) =>
        prev.map((item) => (item.id === notificationId ? { ...item, is_read: true } : item)),
      )
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to mark notification as read')
    } finally {
      setActionLoadingId(null)
    }
  }

  const applyLeaveAction = async (notification: BranchNotification, action: 'approve' | 'reject', reasonInput?: string) => {
    const leaveId = notification.leave_request?.id
    if (!leaveId) {
      toast.error('Leave request information is missing')
      return
    }

    const reason = (reasonInput || '').trim()
    if (action === 'reject' && !reason) {
      toast.error('Rejection reason is required')
      return
    }

    try {
      setActionLoadingId(notification.id)
      await axios.post(`${API_BASE}/api/branch/leaves/${leaveId}/action`, {
        action,
        reason: reason || undefined,
      })
      toast.success(`Leave request ${action}d successfully`)
      await loadNotifications()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || `Failed to ${action} leave request`)
    } finally {
      setActionLoadingId(null)
    }
  }

  const statusBadgeClass = (status?: string) => {
    const normalized = (status || '').toLowerCase()
    if (normalized === 'pending') return 'bg-yellow-100 text-yellow-800'
    if (normalized === 'approved') return 'bg-green-100 text-green-800'
    if (normalized === 'rejected') return 'bg-red-100 text-red-800'
    return 'bg-slate-100 text-slate-700'
  }

  if (!canUse) {
    return (
      <div className="rounded-2xl bg-white p-6 shadow-sm">
        This tab is available only for Branch Director/Admin.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-2xl font-black text-slate-900">Notification Center</h2>
        <p className="mt-1 text-sm text-slate-600">
          Leave approvals and branch workflow alerts scoped to your branch.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        {loading ? (
          <p className="text-sm text-slate-600">Loading notifications...</p>
        ) : notifications.length === 0 ? (
          <p className="text-sm text-slate-600">No notifications found.</p>
        ) : (
          <div className="space-y-4">
            {notifications.map((notification) => {
              const leave = notification.leave_request
              const leaveStatus = (leave?.status || '').toLowerCase()
              const canTakeLeaveAction = notification.type === 'LeaveRequest' && leave && leaveStatus === 'pending'
              const statusLabel = leave?.status || notification.status || (notification.is_read ? 'Read' : 'Unread')

              return (
                <div
                  key={notification.id}
                  className={`rounded-xl border p-4 ${notification.is_read ? 'border-slate-200 bg-slate-50' : 'border-indigo-200 bg-indigo-50/60'}`}
                >
                  <div className="grid gap-3 md:grid-cols-[1fr_1.4fr_2fr_auto_auto]">
                    <div>
                      <p className="text-[11px] font-semibold uppercase text-slate-500">Type</p>
                      <p className="text-sm font-bold text-indigo-700">{notification.type}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold uppercase text-slate-500">Title</p>
                      <p className="text-sm font-bold text-slate-900">{notification.title}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold uppercase text-slate-500">Message</p>
                      <p className="text-sm text-slate-700">{notification.message}</p>
                      <p className="mt-1 text-xs text-slate-500">{new Date(notification.created_at).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold uppercase text-slate-500">Status</p>
                      <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusBadgeClass(statusLabel)}`}>
                        {statusLabel}
                      </span>
                    </div>
                    <div className="flex items-start">
                      <button
                        type="button"
                        onClick={() => void markRead(notification.id)}
                        disabled={notification.is_read || actionLoadingId === notification.id}
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {notification.is_read ? 'Read' : 'Mark as Read'}
                      </button>
                    </div>
                  </div>

                  {leave && (
                    <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
                      <p><span className="font-semibold">Staff:</span> {leave.staff_name || leave.staff_id || '-'}</p>
                      <p><span className="font-semibold">Leave:</span> {leave.leave_type}</p>
                      <p>
                        <span className="font-semibold">Duration:</span>{' '}
                        {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                      </p>
                      <p><span className="font-semibold">Reason:</span> {leave.reason || '-'}</p>
                      <p><span className="font-semibold">Status:</span> {leave.status}</p>
                      {leave.rejection_reason && (
                        <p><span className="font-semibold">Rejection Reason:</span> {leave.rejection_reason}</p>
                      )}
                    </div>
                  )}

                  {canTakeLeaveAction && leave && (
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        onClick={() => void applyLeaveAction(notification, 'approve')}
                        disabled={actionLoadingId === notification.id}
                        className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
                      >
                        ✅ Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setRejectModalNotification(notification)
                          setRejectReason('')
                        }}
                        disabled={actionLoadingId === notification.id}
                        className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
                      >
                        ❌ Reject
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {rejectModalNotification && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setRejectModalNotification(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-900">Please provide a reason for rejection</h3>
            <textarea
              value={rejectReason}
              onChange={(event) => setRejectReason(event.target.value)}
              rows={4}
              className="mt-3 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-rose-500"
              placeholder="Reason for rejection"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                onClick={() => setRejectModalNotification(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-700"
                onClick={async () => {
                  const notification = rejectModalNotification
                  setRejectModalNotification(null)
                  if (notification) {
                    await applyLeaveAction(notification, 'reject', rejectReason)
                  }
                }}
              >
                Submit Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
