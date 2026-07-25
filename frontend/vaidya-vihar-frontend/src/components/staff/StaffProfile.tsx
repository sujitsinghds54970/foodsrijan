import { useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { getApiErrorMessage, staffApi, resolveStaffMediaUrl } from './api'
import SalarySection from './SalarySection'
import StaffIDCard from './StaffIDCard'
import DirectorAttendancePanel from './attendance/DirectorAttendancePanel'
import { StaffDetail } from './types'

interface StaffProfileProps {
  staff: StaffDetail
  canReviewLeave: boolean
  onChanged: (next: StaffDetail) => void
}

export default function StaffProfile({ staff, canReviewLeave, onChanged }: StaffProfileProps) {
  void canReviewLeave
  const { user } = useAuth()
  const [profileForm, setProfileForm] = useState({
    first_name: staff.first_name || '',
    last_name: staff.last_name || '',
    email: staff.email || '',
    mobile: staff.mobile || '',
    department: staff.department || '',
    designation: staff.designation || '',
    specialization: staff.specialization || '',
    shift_timings: staff.shift_timings || '',
    date_of_joining: staff.date_of_joining ? staff.date_of_joining.slice(0, 10) : '',
    address: staff.address || '',
    emergency_contact: staff.emergency_contact || '',
    can_access_daily_ops: Boolean(staff.can_access_daily_ops),
    status: staff.status || 'active',
  })
  const [credentialsForm, setCredentialsForm] = useState({ username: staff.username || '', password: '' })
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingCreds, setSavingCreds] = useState(false)
  const [uploadingPhoto, setUploadingPhoto] = useState(false)

  const formattedJoinDate = useMemo(() => {
    if (!staff.date_of_joining) return 'N/A'
    return new Date(staff.date_of_joining).toLocaleDateString()
  }, [staff.date_of_joining])

  const branchName = useMemo(() => {
    const storedBranchName =
      localStorage.getItem('selectedBranchName') ||
      localStorage.getItem('branchName') ||
      ''

    return (staff as any)?.branch_name || (user as any)?.branch_name || storedBranchName || 'VaidyaVihar Diagnostic'
  }, [staff, user])

  // Resolve photo URL with version cache-busting parameter
  const photoUrl = useMemo(() => {
    const basePhotoUrl = staff.photo_url || (staff as any).photo_path
    if (!basePhotoUrl) return ''
    const resolved = resolveStaffMediaUrl(basePhotoUrl)
    if (!resolved) return ''
    // Add version parameter to force browser to reload cached image
    const version = encodeURIComponent(staff.updated_at || staff.created_at || Date.now())
    return `${resolved}${resolved.includes('?') ? '&' : '?'}v=${version}`
  }, [staff])

  const saveProfile = async () => {
    setSavingProfile(true)
    try {
      const updated = await staffApi.update(staff.staff_profile_id, profileForm)
      onChanged({ ...staff, ...updated })
      toast.success('Profile updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to update profile'))
    } finally {
      setSavingProfile(false)
    }
  }

  const saveCredentials = async () => {
    setSavingCreds(true)
    try {
      const username = await staffApi.updateCredentials(staff.staff_profile_id, {
        username: credentialsForm.username,
        password: credentialsForm.password || undefined,
      })
      onChanged({ ...staff, username })
      setCredentialsForm((prev) => ({ ...prev, password: '' }))
      toast.success('Credentials updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to update credentials'))
    } finally {
      setSavingCreds(false)
    }
  }

  const uploadPhoto = async (file?: File | null) => {
    if (!file) return
    setUploadingPhoto(true)
    try {
      const photoUrl = await staffApi.uploadPhoto(staff.staff_profile_id, file)
      // Update staff object with both photo_url and photo_path for compatibility
      const updatedStaff: StaffDetail = {
        ...staff,
        photo_url: photoUrl,
        // Also extract photo_path from the response URL if needed
        photo_path: photoUrl?.includes('/api/files/') 
          ? photoUrl.replace(/^.*\/api\/files\//, '')
          : undefined,
        updated_at: new Date().toISOString(),
      }
      onChanged(updatedStaff)
      toast.success('Photo updated successfully')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to upload photo'))
    } finally {
      setUploadingPhoto(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900">{staff.full_name}</h2>
            <p className="text-xs text-slate-500">{staff.staff_id} • Joined: {formattedJoinDate}</p>
          </div>
          <label className="ml-auto cursor-pointer rounded-lg border bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
            {uploadingPhoto ? 'Uploading...' : 'Upload Photo'}
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => uploadPhoto(e.target.files?.[0])}
            />
          </label>
        </div>

        {/* Photo Preview */}
        {photoUrl && (
          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="mb-2 text-xs font-semibold text-slate-600">Current Photo</p>
            <div className="flex justify-center">
              <img
                key={photoUrl}
                src={photoUrl}
                alt={`${staff.full_name} profile`}
                crossOrigin="anonymous"
                className="h-32 w-32 rounded-lg border-2 border-slate-300 object-cover shadow-sm"
              />
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.first_name} onChange={(e) => setProfileForm({ ...profileForm, first_name: e.target.value })} placeholder="First name" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.last_name} onChange={(e) => setProfileForm({ ...profileForm, last_name: e.target.value })} placeholder="Last name" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.email} onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })} placeholder="Email" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.mobile} onChange={(e) => setProfileForm({ ...profileForm, mobile: e.target.value })} placeholder="Mobile" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.department} onChange={(e) => setProfileForm({ ...profileForm, department: e.target.value })} placeholder="Department" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.designation} onChange={(e) => setProfileForm({ ...profileForm, designation: e.target.value })} placeholder="Designation" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.specialization} onChange={(e) => setProfileForm({ ...profileForm, specialization: e.target.value })} placeholder="Specialization" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.shift_timings} onChange={(e) => setProfileForm({ ...profileForm, shift_timings: e.target.value })} placeholder="Shift timings" />
          <input type="date" className="rounded border px-2 py-1.5 text-sm" value={profileForm.date_of_joining} onChange={(e) => setProfileForm({ ...profileForm, date_of_joining: e.target.value })} />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.address} onChange={(e) => setProfileForm({ ...profileForm, address: e.target.value })} placeholder="Address" />
          <input className="rounded border px-2 py-1.5 text-sm" value={profileForm.emergency_contact} onChange={(e) => setProfileForm({ ...profileForm, emergency_contact: e.target.value })} placeholder="Emergency contact" />
          <select className="rounded border px-2 py-1.5 text-sm" value={profileForm.status} onChange={(e) => setProfileForm({ ...profileForm, status: e.target.value })}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>

        <div className="mt-3 rounded-xl border border-cyan-200 bg-cyan-50 p-3">
          <label className="flex items-center justify-between gap-3 text-sm font-semibold text-slate-800">
            <span>Allow Access To Daily Operations</span>
            <input
              type="checkbox"
              checked={profileForm.can_access_daily_ops}
              onChange={(e) => setProfileForm({ ...profileForm, can_access_daily_ops: e.target.checked })}
              className="h-4 w-4"
            />
          </label>
          <p className="mt-1 text-xs text-slate-600">When off, this staff member cannot open Daily Operations.</p>
        </div>

        <button onClick={saveProfile} disabled={savingProfile} className="mt-3 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
          {savingProfile ? 'Saving...' : 'Save Profile'}
        </button>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-bold text-slate-900">Credentials</h3>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          <input className="rounded border px-2 py-1.5 text-sm" value={credentialsForm.username} onChange={(e) => setCredentialsForm({ ...credentialsForm, username: e.target.value })} placeholder="Username" />
          <input className="rounded border px-2 py-1.5 text-sm" type="password" value={credentialsForm.password} onChange={(e) => setCredentialsForm({ ...credentialsForm, password: e.target.value })} placeholder="New Password" />
          <button onClick={saveCredentials} disabled={savingCreds} className="rounded bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-black disabled:opacity-60">
            {savingCreds ? 'Saving...' : 'Update Credentials'}
          </button>
        </div>
      </div>

      <SalarySection
        staffProfileId={staff.staff_profile_id}
        salary={staff.salary}
        onUpdated={(nextSalary) => onChanged({ ...staff, salary: nextSalary })}
      />

      <DirectorAttendancePanel staffProfileId={staff.staff_profile_id} />
      <StaffIDCard staff={staff} branchName={branchName} />
    </div>
  )
}
