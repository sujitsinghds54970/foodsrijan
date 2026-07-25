/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'
import StaffManagementModule from '../staff/StaffManagementModule'


type DirectorProfile = {
  user_id: number
  branch_id: number
  full_name: string
  first_name: string
  last_name: string
  designation?: string
  mobile?: string
  email?: string
  address?: string
  date_of_joining?: string
  specialization?: string
  emergency_contact?: string
  photo_path?: string
  role: string
}

type DirectorCreateForm = {
  first_name: string
  last_name: string
  mobile: string
  email?: string
  designation?: string
  address?: string
  date_of_joining?: string
  specialization?: string
  emergency_contact?: string
}

type DirectorProfileForm = {
  first_name: string
  last_name: string
  mobile?: string
  email?: string
  designation?: string
  address?: string
  date_of_joining?: string
  specialization?: string
  emergency_contact?: string
}

export default function DirectorManagementModule() {
  const { user, token } = useAuth()

  const [activeTab, setActiveTab] = useState<'director-profile' | 'staff-management'>('director-profile')
  const [profile, setProfile] = useState<DirectorProfile | null>(null)
  const [summary, setSummary] = useState<{ total_staff: number; pending_leave_requests: number; approved_leave_requests: number } | null>(null)
  const [notifications, setNotifications] = useState<Array<{ id: number; title: string; message: string; is_read: boolean; created_at: string }>>([])

  const API_BASE =
    process.env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token])

  const createDirectorForm = useForm<DirectorCreateForm>()
  const profileForm = useForm<DirectorProfileForm>()

  const isAdminForCreate = user?.role === 'branch_admin' || user?.role === 'super_admin'
  const canSeeNotifications = user?.role === 'branch_director'
  const shouldLoadDirectorProfile = user?.role === 'branch_director'

  const loadProfile = async () => {
    if (!token) return

    try {
      const res = await axios.get(`${API_BASE}/api/director-v2/profile`, requestConfig)
      setProfile(res.data)
      profileForm.reset({
        first_name: res.data.first_name || '',
        last_name: res.data.last_name || '',
        mobile: res.data.mobile || '',
        email: res.data.email || '',
        designation: res.data.designation || '',
        address: res.data.address || '',
        date_of_joining: res.data.date_of_joining ? String(res.data.date_of_joining).slice(0, 10) : '',
        specialization: res.data.specialization || '',
        emergency_contact: res.data.emergency_contact || '',
      })
    } catch (err: any) {
      if (err?.response?.status !== 404) {
        toast.error(err?.response?.data?.detail || 'Failed to load director profile')
      }
      setProfile(null)
    }
  }

  const loadSummary = async () => {
    if (!token) return
    try {
      const res = await axios.get(`${API_BASE}/api/director-v2/dashboard/summary`, requestConfig)
      setSummary(res.data)
    } catch {
      setSummary(null)
    }
  }

  const loadNotifications = async () => {
    if (!token || !canSeeNotifications) return
    try {
      const res = await axios.get(`${API_BASE}/api/director-v2/notifications`, requestConfig)
      setNotifications(Array.isArray(res.data) ? res.data : [])
    } catch {
      setNotifications([])
    }
  }

  // Intentionally runs on auth context changes only.
  // Non-director users should not hit the profile endpoint on mount; they may
  // legitimately have no director profile yet.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (shouldLoadDirectorProfile) {
      void loadProfile()
    }
    void loadSummary()
    void loadNotifications()
  }, [token, user?.role, shouldLoadDirectorProfile])

  const createDirector = createDirectorForm.handleSubmit(async values => {
    try {
      const res = await axios.post(
        `${API_BASE}/api/director-v2/create`,
        {
          ...values,
          date_of_joining: values.date_of_joining ? new Date(values.date_of_joining).toISOString() : null,
        },
        requestConfig,
      )
      toast.success(`Director created. Username: ${res.data?.credentials?.username}, Password: ${res.data?.credentials?.password}`)
      createDirectorForm.reset()
      await loadProfile()
      await loadSummary()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to create director')
    }
  })

  const updateDirectorProfile = profileForm.handleSubmit(async values => {
    try {
      await axios.put(
        `${API_BASE}/api/director-v2/profile`,
        {
          ...values,
          date_of_joining: values.date_of_joining ? new Date(values.date_of_joining).toISOString() : null,
        },
        requestConfig,
      )
      toast.success('Director profile updated')
      await loadProfile()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to update director profile')
    }
  })

  const markNotificationRead = async (notificationId: number) => {
    try {
      await axios.put(`${API_BASE}/api/director-v2/notifications/${notificationId}/read`, {}, requestConfig)
      await loadNotifications()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to mark notification')
    }
  }

  if (!user || !['super_admin', 'branch_admin', 'branch_director'].includes(user.role)) {
    return <div className="premium-card p-6">Access denied</div>
  }

  return (
    <div className="space-y-6">
      <div className="premium-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-black text-slate-900">Director & Staff Management</h2>
            <p className="text-sm text-slate-500">Director profile intentionally excludes bank account, UPI ID, and soundbox fields.</p>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('director-profile')}
              className={`px-4 py-2 rounded-xl font-semibold ${activeTab === 'director-profile' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
            >
              Director Profile
            </button>
            <button
              onClick={() => setActiveTab('staff-management')}
              className={`px-4 py-2 rounded-xl font-semibold ${activeTab === 'staff-management' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
            >
              Staff Management
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'director-profile' && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="premium-card p-4 bg-gradient-to-br from-blue-50 to-cyan-50">
              <p className="text-xs uppercase tracking-wide text-blue-600 font-bold">Total Staff</p>
              <p className="text-3xl font-black text-slate-900 mt-2">{summary?.total_staff ?? 0}</p>
            </div>
            <div className="premium-card p-4 bg-gradient-to-br from-amber-50 to-orange-50">
              <p className="text-xs uppercase tracking-wide text-amber-700 font-bold">Pending Leave Requests</p>
              <p className="text-3xl font-black text-slate-900 mt-2">{summary?.pending_leave_requests ?? 0}</p>
            </div>
            <div className="premium-card p-4 bg-gradient-to-br from-emerald-50 to-teal-50">
              <p className="text-xs uppercase tracking-wide text-emerald-700 font-bold">Approved Leave Requests</p>
              <p className="text-3xl font-black text-slate-900 mt-2">{summary?.approved_leave_requests ?? 0}</p>
            </div>
          </div>

          {isAdminForCreate && !profile && (
            <div className="premium-card p-6">
              <h3 className="text-xl font-black text-slate-900 mb-3">Create Branch Director</h3>
              <form onSubmit={createDirector} className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input className="px-4 py-2 border rounded-xl" placeholder="First Name" {...createDirectorForm.register('first_name', { required: true })} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Last Name" {...createDirectorForm.register('last_name', { required: true })} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Mobile" {...createDirectorForm.register('mobile', { required: true })} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Email (optional)" {...createDirectorForm.register('email')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Designation" {...createDirectorForm.register('designation')} />
                <input type="date" className="px-4 py-2 border rounded-xl" {...createDirectorForm.register('date_of_joining')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Specialization" {...createDirectorForm.register('specialization')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Emergency Contact" {...createDirectorForm.register('emergency_contact')} />
                <textarea className="md:col-span-2 px-4 py-2 border rounded-xl" placeholder="Address" {...createDirectorForm.register('address')} />
                <button className="md:col-span-2 px-4 py-2 rounded-xl bg-emerald-600 text-white font-semibold">Create Director</button>
              </form>
            </div>
          )}

          {profile && (
            <div className="premium-card p-6">
              <h3 className="text-xl font-black text-slate-900 mb-3">Director Profile</h3>
              <form onSubmit={updateDirectorProfile} className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input className="px-4 py-2 border rounded-xl" placeholder="First Name" {...profileForm.register('first_name', { required: true })} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Last Name" {...profileForm.register('last_name', { required: true })} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Mobile" {...profileForm.register('mobile')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Email" {...profileForm.register('email')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Designation" {...profileForm.register('designation')} />
                <input type="date" className="px-4 py-2 border rounded-xl" {...profileForm.register('date_of_joining')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Specialization" {...profileForm.register('specialization')} />
                <input className="px-4 py-2 border rounded-xl" placeholder="Emergency Contact" {...profileForm.register('emergency_contact')} />
                <textarea className="md:col-span-2 px-4 py-2 border rounded-xl" placeholder="Address" {...profileForm.register('address')} />
                <button className="md:col-span-2 px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold">Save Director Profile</button>
              </form>
            </div>
          )}

          {canSeeNotifications && (
            <div className="premium-card p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-black text-slate-900">Notifications</h3>
                <button onClick={() => void loadNotifications()} className="px-3 py-2 rounded-xl bg-slate-900 text-white text-sm font-semibold">Refresh</button>
              </div>
              <div className="mt-3 space-y-2">
                {notifications.length === 0 ? (
                  <p className="text-sm text-slate-500">No notifications</p>
                ) : notifications.map(item => (
                  <div key={item.id} className="p-3 border rounded-xl bg-white flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                      <p className="text-sm text-slate-600">{item.message}</p>
                      <p className="text-xs text-slate-400 mt-1">{new Date(item.created_at).toLocaleString()}</p>
                    </div>
                    {!item.is_read && (
                      <button onClick={() => void markNotificationRead(item.id)} className="px-3 py-1 rounded-lg bg-blue-600 text-white text-xs">Mark Read</button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'staff-management' && <StaffManagementModule />}
    </div>
  )
}
