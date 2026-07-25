import { useEffect, useMemo, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'
import StaffIDCard from './StaffIDCard'
import { getApiErrorMessage, resolveStaffMediaUrl, staffSelfApi } from './api'
import { LeaveBalance, StaffNotification, StaffSelfAttendanceRow, StaffSelfProfile } from './types'

const formatDateTime = (value?: string | null): string => {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '-'
  return parsed.toLocaleString()
}

const isStaffRole = (role?: string): boolean => {
  if (!role) return false
  const staffRoles = ['staff', 'receptionist', 'technician', 'doctor', 'nurse']
  return staffRoles.includes(role.toLowerCase())
}

const currentMonthToken = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export default function StaffDashboard() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [savingContact, setSavingContact] = useState(false)
  const [savingBank, setSavingBank] = useState(false)
  const [applyingLeave, setApplyingLeave] = useState(false)

  const [profile, setProfile] = useState<StaffSelfProfile | null>(null)
  const [attendance, setAttendance] = useState<StaffSelfAttendanceRow[]>([])
  const [leaveBalance, setLeaveBalance] = useState<LeaveBalance | null>(null)
  const [notifications, setNotifications] = useState<StaffNotification[]>([])

  const [mobile, setMobile] = useState('')
  const [email, setEmail] = useState('')

  const [bankName, setBankName] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [ifscCode, setIfscCode] = useState('')
  const [upiId, setUpiId] = useState('')

  const [showLeaveModal, setShowLeaveModal] = useState(false)
  const [leaveType, setLeaveType] = useState('casual')
  const [leaveStart, setLeaveStart] = useState('')
  const [leaveEnd, setLeaveEnd] = useState('')
  const [leaveReason, setLeaveReason] = useState('')

  const hasShownNotificationsRef = useRef(false)

  const loadAll = async () => {
    try {
      setLoading(true)
      const me = await staffSelfApi.getMe()
      setProfile(me)
      setMobile(me.mobile || '')
      setEmail(me.email || '')
      setBankName(me.bank_name || '')
      setAccountNumber(me.bank_account_number || '')
      setIfscCode(me.ifsc_code || '')
      setUpiId(me.upi_id || '')

      const [attendanceRows, leaves, notices] = await Promise.all([
        staffSelfApi.getMyAttendance(currentMonthToken()),
        staffSelfApi.getLeaveBalance(),
        staffSelfApi.getNotifications(),
      ])
      setAttendance(attendanceRows)
      setLeaveBalance(leaves)
      setNotifications(notices)

      if (notices.length > 0 && !hasShownNotificationsRef.current) {
        hasShownNotificationsRef.current = true
        toast.success(`You have ${notices.length} update(s) from director workflows`)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load staff dashboard'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isStaffRole(user?.role)) return
    loadAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.role])

  const persistContactField = async (payload: Partial<StaffSelfProfile>) => {
    if (!profile) return
    try {
      setSavingContact(true)
      const updated = await staffSelfApi.updateMe(payload)
      setProfile(updated)
      setMobile(updated.mobile || '')
      setEmail(updated.email || '')
      toast.success('Profile updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to update profile'))
    } finally {
      setSavingContact(false)
    }
  }

  const saveBankDetails = async () => {
    if (!profile) return
    try {
      setSavingBank(true)
      const updated = await staffSelfApi.updateMe({
        bank_name: bankName,
        bank_account_number: accountNumber,
        ifsc_code: ifscCode,
        upi_id: upiId,
      } as any)
      setProfile(updated)
      toast.success('Bank details saved successfully')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to save bank details'))
    } finally {
      setSavingBank(false)
    }
  }

  const onDrop = async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return
    try {
      const updated = await staffSelfApi.uploadMyPhoto(acceptedFiles[0])
      setProfile(updated)
      toast.success('Photo updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to upload photo'))
    }
  }

  const dropzone = useDropzone({
    onDrop,
    accept: { 'image/*': [] },
    maxFiles: 1,
  })

  const staffCardData = useMemo(() => {
    if (!profile) return null
    return {
      staff_profile_id: profile.staff_profile_id,
      staff_id: `ST-${profile.staff_profile_id}`,
      username: user?.username || 'staff',
      first_name: profile.full_name.split(' ')[0] || profile.full_name,
      last_name: profile.full_name.split(' ').slice(1).join(' '),
      full_name: profile.full_name,
      email: profile.email || '',
      mobile: profile.mobile || '',
      department: profile.department || '',
      designation: profile.role,
      status: 'active',
      user_id: profile.id,
      branch_id: profile.branch_id || 0,
      address: profile.address || '',
      photo_url: profile.photo_url || '',
      salary: {
        basic: 0,
        hra: 0,
        allowances: 0,
        deductions: 0,
        net_pay: 0,
        bank_name: profile.bank_name,
        account_number: profile.bank_account_number,
        ifsc_code: profile.ifsc_code,
        upi_id: profile.upi_id,
      },
    }
  }, [profile, user?.username])

  const applyLeave = async () => {
    if (!leaveStart || !leaveEnd) {
      toast.error('Select start and end date')
      return
    }

    try {
      setApplyingLeave(true)
      await staffSelfApi.applyLeave({
        leave_type: leaveType,
        start_date: new Date(leaveStart).toISOString(),
        end_date: new Date(leaveEnd).toISOString(),
        reason: leaveReason || undefined,
      })
      toast.success('Leave request submitted')
      setShowLeaveModal(false)
      setLeaveReason('')
      const [leaves, notices] = await Promise.all([
        staffSelfApi.getLeaveBalance(),
        staffSelfApi.getNotifications(),
      ])
      setLeaveBalance(leaves)
      setNotifications(notices)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to apply leave'))
    } finally {
      setApplyingLeave(false)
    }
  }

  if (!isStaffRole(user?.role)) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900">Staff Self-Service</h2>
        <p className="mt-2 text-slate-600">This dashboard is only available for staff accounts.</p>
      </div>
    )
  }

  if (loading || !profile || !staffCardData) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-sm">
        <p className="text-slate-600">Loading your dashboard...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 to-purple-600 p-8 shadow-2xl">
        <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full bg-white/20 blur-2xl" />
        <div className="absolute -bottom-14 left-1/3 h-40 w-40 rounded-full bg-cyan-300/20 blur-3xl" />
        <div className="relative flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="h-20 w-20 overflow-hidden rounded-2xl border-2 border-white/70 bg-white/20">
              {profile.branch_logo_url ? (
                <img src={resolveStaffMediaUrl(profile.branch_logo_url)} alt="Branch logo" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-3xl text-white">🏥</div>
              )}
            </div>
            <div>
              <h1 className="text-4xl font-extrabold text-white drop-shadow-md">{profile.branch_name || 'Vaidya Vihar Diagnostic'}</h1>
              <p className="mt-2 text-2xl font-semibold text-white/90">{profile.full_name}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/30 bg-white/15 px-5 py-3 text-white backdrop-blur">
            <div className="text-sm font-medium text-white/80">Role</div>
            <div className="text-lg font-bold uppercase tracking-wide">{profile.role}</div>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
          <div>
            <div
              {...dropzone.getRootProps()}
              className="group cursor-pointer rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-4 text-center transition hover:border-blue-500 hover:bg-blue-50"
            >
              <input {...dropzone.getInputProps()} />
              <div className="mx-auto h-52 w-52 overflow-hidden rounded-full border-4 border-white bg-slate-200 shadow-xl">
                {profile.photo_url ? (
                  <img src={resolveStaffMediaUrl(profile.photo_url)} alt="Staff" className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-6xl text-slate-500">👤</div>
                )}
              </div>
              <p className="mt-4 text-sm font-semibold text-slate-700">Drop a photo here, or click to upload</p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Full Name</label>
                <p className="mt-1 text-lg font-bold text-slate-900">{profile.full_name}</p>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Department</label>
                <p className="mt-1 text-base font-semibold text-slate-800">{profile.department || '-'}</p>
              </div>
              <div className="md:col-span-2">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Address</label>
                <p className="mt-1 rounded-xl bg-slate-50 px-3 py-2 text-slate-700">{profile.address || '-'}</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Mobile Number</label>
                <input
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  onBlur={() => mobile !== (profile.mobile || '') && persistContactField({ mobile })}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500"
                  placeholder="Enter mobile number"
                  disabled={savingContact}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Email ID</label>
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={() => email !== (profile.email || '') && persistContactField({ email })}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500"
                  placeholder="Enter email"
                  disabled={savingContact}
                />
              </div>
            </div>

            <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900">ID Card Section</h3>
                <span className="rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white">Preview + Download</span>
              </div>
              <div className="scale-[0.82] origin-top-left overflow-hidden rounded-xl">
                <StaffIDCard staff={staffCardData as any} branchName={profile.branch_name || undefined} />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Bank Details For Salary</h2>
          <button
            onClick={saveBankDetails}
            disabled={savingBank}
            className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-emerald-700 disabled:opacity-60"
          >
            {savingBank ? 'Saving...' : 'Save Bank Details'}
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Bank Name</label>
            <input value={bankName} onChange={(e) => setBankName(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Account Number</label>
            <input value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">IFSC Code</label>
            <input value={ifscCode} onChange={(e) => setIfscCode(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">UPI ID</label>
            <input value={upiId} onChange={(e) => setUpiId(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" />
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900">This Month Attendance</h2>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{currentMonthToken()}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">Clock-in</th>
                  <th className="py-2 pr-4">Clock-out</th>
                  <th className="py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {attendance.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-5 text-center text-slate-500">No attendance records found for current month.</td>
                  </tr>
                ) : (
                  attendance.map((row) => {
                    const isPresent = row.status.toLowerCase() === 'present'
                    return (
                      <tr key={row.id} className="border-b border-slate-100">
                        <td className="py-2 pr-4">{formatDateTime(row.attendance_date)}</td>
                        <td className="py-2 pr-4">{formatDateTime(row.clock_in_time)}</td>
                        <td className="py-2 pr-4">{formatDateTime(row.clock_out_time)}</td>
                        <td className="py-2">
                          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${isPresent ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900">Leave Balance</h2>
              <button
                onClick={() => setShowLeaveModal(true)}
                className="rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700"
              >
                Apply for Leave
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase text-slate-500">Casual Leave</p>
                <p className="mt-1 text-2xl font-extrabold text-slate-900">{leaveBalance?.casual_remaining ?? 0}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase text-slate-500">Sick Leave</p>
                <p className="mt-1 text-2xl font-extrabold text-slate-900">{leaveBalance?.sick_remaining ?? 0}</p>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-900">Director Notifications</h2>
              {notifications.length > 0 && (
                <span className="rounded-full bg-red-500 px-2.5 py-1 text-xs font-bold text-white">{notifications.length}</span>
              )}
            </div>

            <div className="space-y-3">
              {notifications.length === 0 ? (
                <p className="text-sm text-slate-500">No new updates.</p>
              ) : (
                notifications.slice(0, 4).map((item) => (
                  <div key={item.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                    <p className="mt-1 text-sm text-slate-600">{item.message}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>

      {showLeaveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <h3 className="text-xl font-bold text-slate-900">Quick Leave Apply</h3>

            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Leave Type</label>
                <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2">
                  <option value="casual">Casual</option>
                  <option value="sick">Sick</option>
                  <option value="privileged">Privileged</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Start Date</label>
                <input type="date" value={leaveStart} onChange={(e) => setLeaveStart(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">End Date</label>
                <input type="date" value={leaveEnd} onChange={(e) => setLeaveEnd(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Reason</label>
                <textarea value={leaveReason} onChange={(e) => setLeaveReason(e.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2" rows={3} />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-3">
              <button onClick={() => setShowLeaveModal(false)} className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">
                Cancel
              </button>
              <button onClick={applyLeave} disabled={applyingLeave} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
                {applyingLeave ? 'Submitting...' : 'Submit Leave'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
