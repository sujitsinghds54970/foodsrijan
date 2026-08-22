import { ChangeEvent, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'

export default function CeoProfile() {
  const { user } = useAuth()
  const API_BASE =
    (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const [fullName, setFullName] = useState(
    `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || user?.username || '',
  )
  const [mobile, setMobile] = useState(user?.phone || '')
  const [email, setEmail] = useState(user?.email || '')
  const [bio, setBio] = useState('')
  const [saving, setSaving] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [serverPhotoUrl, setServerPhotoUrl] = useState<string | null>(null)

  const profileImage = useMemo(() => {
    if (previewUrl) return previewUrl
    if (serverPhotoUrl) return serverPhotoUrl
    return user?.companyLogo || user?.profilePhoto || '/default-company-logo.png'
  }, [previewUrl, serverPhotoUrl, user?.companyLogo, user?.profilePhoto])

  const initials = useMemo(() => {
    const source = (fullName || user?.username || 'CEO').trim()
    const parts = source.split(/\s+/).filter(Boolean)
    if (parts.length === 0) return 'C'
    if (parts.length === 1) return parts[0][0]?.toUpperCase() || 'C'
    return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
  }, [fullName, user?.username])

  const onFileSelect = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    setSelectedFile(file)
    setPreviewUrl(URL.createObjectURL(file))
  }

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/ceo/profile`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
          },
        })
        const data = response.data || {}
        if (typeof data.full_name === 'string') setFullName(data.full_name)
        if (typeof data.mobile === 'string') setMobile(data.mobile)
        if (typeof data.email === 'string') setEmail(data.email)
        if (typeof data.bio === 'string') setBio(data.bio)
        if (typeof data.profile_photo === 'string' && data.profile_photo.trim()) {
          setServerPhotoUrl(data.profile_photo)
        }
      } catch (error) {
        console.error('Failed to load CEO profile:', error)
      }
    }
    void loadProfile()
  }, [API_BASE])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = new FormData()
      payload.append('full_name', fullName)
      payload.append('mobile', mobile)
      payload.append('email', email)
      payload.append('bio', bio)
      if (selectedFile) {
        payload.append('profile_photo', selectedFile)
      }

      await axios.put(`${API_BASE}/api/ceo/profile`, payload, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })

      const meResponse = await axios.get(`${API_BASE}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      localStorage.setItem('user', JSON.stringify(meResponse.data))

      toast.success('Profile updated successfully')
      window.location.reload()
    } catch (error) {
      console.error('Failed to update CEO profile:', error)
      toast.error('Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="bg-white rounded-xl shadow-lg p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Company Settings</p>
      <h2 className="mt-2 text-2xl font-black text-slate-900">FoodSrijan Group</h2>
      <p className="mt-1 text-sm text-slate-500">Company Profile, Branding, Team, and Compliance</p>

      <div className="mt-6 flex flex-col items-center">
        {profileImage ? (
          <img
            src={profileImage}
            alt="CEO profile"
            className="w-32 h-32 rounded-full object-cover border border-slate-200 bg-white"
            onError={(event) => {
              event.currentTarget.onerror = null
              event.currentTarget.src = '/default-company-logo.png'
            }}
          />
        ) : (
          <div className="w-32 h-32 rounded-full bg-indigo-600 text-white flex items-center justify-center text-4xl font-bold">
            {initials}
          </div>
        )}

        <label className="mt-4 inline-flex cursor-pointer items-center rounded-md bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200">
          Upload Photo
          <input type="file" accept="image/*" className="hidden" onChange={onFileSelect} />
        </label>
      </div>

      <div className="mt-8 grid gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Full Name</label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Mobile Number</label>
          <input
            type="text"
            value={mobile}
            onChange={(e) => setMobile(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Email ID</label>
          <input
            type="text"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Bio / About</label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={4}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
        </div>
      </div>

      <div className="mt-6">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded-md bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </div>
    </section>
  )
}
