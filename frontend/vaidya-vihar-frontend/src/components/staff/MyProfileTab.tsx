import { useEffect, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../../contexts/AuthContext'
import PayslipsTab from '../payroll/PayslipsTab'
import StaffIDCard from './StaffIDCard'
import { getApiErrorMessage, resolveStaffMediaUrl, staffSelfApi } from './api'
import { StaffSelfProfile } from './types'

const isStaffRole = (role?: string): boolean => {
  if (!role) return false
  const staffRoles = ['staff', 'receptionist', 'technician', 'doctor', 'nurse']
  return staffRoles.includes(role.toLowerCase())
}

export default function MyProfileTab() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [savingContact, setSavingContact] = useState(false)
  const [savingBank, setSavingBank] = useState(false)
  const [profile, setProfile] = useState<StaffSelfProfile | null>(null)
  const [showPhotoPreview, setShowPhotoPreview] = useState(false)
  const [showIdCardModal, setShowIdCardModal] = useState(false)

  const [mobile, setMobile] = useState('')
  const [email, setEmail] = useState('')
  const [bankName, setBankName] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [ifscCode, setIfscCode] = useState('')
  const [upiId, setUpiId] = useState('')

  const loadProfile = async () => {
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
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load profile'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if ((user?.role || '').toLowerCase() !== 'staff') return
    void loadProfile()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.role])

  const persistContact = async (payload: Partial<StaffSelfProfile>) => {
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

  const saveBank = async () => {
    try {
      setSavingBank(true)
      const updated = await staffSelfApi.updateMe({
        bank_name: bankName,
        bank_account_number: accountNumber,
        ifsc_code: ifscCode,
        upi_id: upiId,
      } as any)
      setProfile(updated)
      toast.success('Bank details saved')
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

  const dropzone = useDropzone({ onDrop, accept: { 'image/*': [] }, maxFiles: 1 })

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

  if (!isStaffRole(user?.role)) {
    return <div className="rounded-2xl bg-white p-8 shadow-sm dark:bg-slate-900 dark:text-slate-100">This page is only available for staff users.</div>
  }

  if (loading || !profile || !staffCardData) {
    return <div className="rounded-2xl bg-white p-8 shadow-sm dark:bg-slate-900 dark:text-slate-100">Loading profile...</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[340px_1fr]">
        <aside className="rounded-3xl border-t-4 border-indigo-500 bg-white/80 p-5 shadow-2xl backdrop-blur dark:border-indigo-400 dark:bg-slate-900/80">
          <div
            {...dropzone.getRootProps()}
            className="group cursor-pointer rounded-2xl border-2 border-dashed border-indigo-200 bg-indigo-50/70 p-4 text-center transition hover:border-indigo-500 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-indigo-950/40"
          >
            <input {...dropzone.getInputProps()} />
            <div
              className="mx-auto h-16 w-16 overflow-hidden rounded-full border-2 border-white bg-slate-200 shadow-md dark:border-slate-800"
              style={{ width: '64px', height: '64px', overflow: 'hidden', borderRadius: '9999px' }}
            >
              {profile.photo_url ? (
                <img
                  key={profile.photo_url}
                  src={resolveStaffMediaUrl(profile.photo_url)}
                  alt="Staff"
                  className="h-full w-full cursor-pointer object-cover hover:opacity-80"
                  style={{ width: '64px', height: '64px', objectFit: 'cover', display: 'block' }}
                  onClick={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    setShowPhotoPreview(true)
                  }}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-6xl text-slate-500" style={{ width: '64px', height: '64px', fontSize: '24px' }}>👤</div>
              )}
            </div>
            <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-300">Click photo to preview</p>
            <p className="mt-4 text-sm font-semibold text-indigo-700 dark:text-indigo-200">Drop a photo here, or click to upload</p>
          </div>

          <div className="mt-5 rounded-2xl bg-gradient-to-r from-indigo-600 to-fuchsia-600 p-4 text-white">
            <p className="text-xs uppercase tracking-widest text-indigo-100">Staff Name</p>
            <p className="text-blue-100 mt-1 text-2xl font-bold">{profile.full_name}</p>
            <p className="mt-1 text-sm text-indigo-100">{profile.role} • {profile.department || 'General'}</p>
          </div>
        </aside>

        <section className="space-y-6">
          <div className="rounded-3xl border-t-4 border-indigo-500 bg-white/80 p-6 shadow-2xl backdrop-blur dark:border-indigo-400 dark:bg-slate-900/80">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">My Profile</h2>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <button onClick={() => navigate('/staff/attendance')} className="rounded-lg bg-emerald-600 px-3 py-2 font-semibold text-white hover:bg-emerald-700">Mark Attendance</button>
                <button onClick={() => navigate('/staff/profile')} className="rounded-lg bg-indigo-600 px-3 py-2 font-semibold text-white hover:bg-indigo-700">Apply for Leave</button>
                <button type="button" onClick={() => setShowIdCardModal(true)} className="rounded-lg bg-slate-900 px-3 py-2 font-semibold text-white hover:bg-black">View ID Card</button>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">Mobile Number</label>
                <input
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  onBlur={() => mobile !== (profile.mobile || '') && void persistContact({ mobile })}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  disabled={savingContact}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">Email ID</label>
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={() => email !== (profile.email || '') && void persistContact({ email })}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  disabled={savingContact}
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">Address</label>
                <textarea
                  value={profile.address || ''}
                  onChange={(e) => setProfile((prev) => (prev ? { ...prev, address: e.target.value } : prev))}
                  onBlur={() => void persistContact({ address: profile.address || '' })}
                  className="w-full rounded-xl border border-slate-300 px-3 py-2 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                  rows={3}
                />
              </div>
            </div>
          </div>

          <div className="rounded-3xl border-t-4 border-fuchsia-500 bg-white/80 p-6 shadow-2xl backdrop-blur dark:border-fuchsia-400 dark:bg-slate-900/80">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Bank Details</h3>
              <button onClick={() => void saveBank()} disabled={savingBank} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">{savingBank ? 'Saving...' : 'Save Bank Details'}</button>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <input placeholder="Bank Name" value={bankName} onChange={(e) => setBankName(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" />
              <input placeholder="Account Number" value={accountNumber} onChange={(e) => setAccountNumber(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" />
              <input placeholder="IFSC Code" value={ifscCode} onChange={(e) => setIfscCode(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" />
              <input placeholder="UPI ID" value={upiId} onChange={(e) => setUpiId(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100" />
            </div>
          </div>

        </section>
      </div>

      <PayslipsTab />

      {showPhotoPreview && profile.photo_url && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', padding: '16px' }}
          onClick={() => setShowPhotoPreview(false)}
        >
          <div
            className="w-full max-w-3xl rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900"
            style={{ width: '100%', maxWidth: '960px', background: '#ffffff', borderRadius: '16px', padding: '20px' }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">Profile Photo Preview</h4>
              <button
                className="rounded border px-2 py-1 text-xs"
                onClick={() => setShowPhotoPreview(false)}
              >
                Close
              </button>
            </div>
            <div className="flex justify-center">
              <img
                key={profile.photo_url}
                src={resolveStaffMediaUrl(profile.photo_url)}
                alt="Profile preview"
                className="w-full rounded-xl border border-slate-200 object-contain"
                style={{ width: '100%', maxHeight: '70vh', objectFit: 'contain', border: '1px solid #e2e8f0', borderRadius: '12px', display: 'block' }}
              />
            </div>
          </div>
        </div>
      )}

      {showIdCardModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setShowIdCardModal(false)}
        >
          <div
            className="w-full max-w-6xl rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-3 flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">Professional ID Card</h4>
              <button
                type="button"
                className="rounded border px-2 py-1 text-xs"
                onClick={() => setShowIdCardModal(false)}
              >
                Close
              </button>
            </div>
            <StaffIDCard
              staff={staffCardData as any}
              branchName={profile.branch_name || undefined}
              downloadButtonLabel="Download ID Card"
            />
          </div>
        </div>
      )}
    </div>
  )
}
