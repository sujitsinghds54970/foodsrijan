import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useDropzone } from 'react-dropzone'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import QRCode from 'react-qr-code'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { useAuth } from '../../contexts/AuthContext'

type BranchDirectorOverviewDashboardProps = {
  branchId?: number
  showBackButton?: boolean
  onBack?: () => void
}

type OverviewDashboardPayload = {
  branch: {
    id: number
    name: string
    address: string
    city: string
    state: string
    phone: string
    email?: string
    branch_code: string
  }
  director: {
    full_name: string
    mobile: string
    email: string
    age: string
    address: string
    photo_url: string
  }
  attendance_summary: {
    present_today: number
    total_staff: number
    label: string
  }
  bank_details: {
    account_number: string
    ifsc_code: string
  }
  credentials: {
    username: string
    password: string
  }
}

type TrendPayload = {
  monthly: Array<{
    month: string
    revenue: number
    expenses: number
    patients: number
  }>
}

const maskValue = (value: string, keep: number = 4) => {
  if (!value) return ''
  if (value.length <= keep) return value
  return `${'*'.repeat(Math.max(0, value.length - keep))}${value.slice(-keep)}`
}

const formatMonth = (value: string) => {
  const [year, month] = value.split('-')
  const date = new Date(Number(year), Number(month) - 1, 1)
  return date.toLocaleDateString(undefined, { month: 'short' })
}

const getBranchLogoStorageKey = (branchId?: number) => `overview-branch-logo-${branchId || 'default'}`
const CR80_CARD_WIDTH_MM = 85.6
const CR80_CARD_HEIGHT_MM = 54
const CR80_SAFE_MARGIN_MM = 3

export default function BranchDirectorOverviewDashboard({
  branchId,
  showBackButton = false,
  onBack,
}: BranchDirectorOverviewDashboardProps) {
  const { user, token } = useAuth()

  const [loading, setLoading] = useState(true)
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingCredentials, setSavingCredentials] = useState(false)

  const [overview, setOverview] = useState<OverviewDashboardPayload | null>(null)
  const [trends, setTrends] = useState<TrendPayload['monthly']>([])

  const [fullName, setFullName] = useState('')
  const [mobile, setMobile] = useState('')
  const [email, setEmail] = useState('')
  const [age, setAge] = useState('')
  const [address, setAddress] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [ifscCode, setIfscCode] = useState('')
  const [photoUrl, setPhotoUrl] = useState('')
  const [branchLogoUrl, setBranchLogoUrl] = useState('')

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showAccountNumber, setShowAccountNumber] = useState(false)
  const [showIfscCode, setShowIfscCode] = useState(false)
  const [showUsername, setShowUsername] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const branchLogoInputRef = useRef<HTMLInputElement>(null)
  const directorIdFrontRef = useRef<HTMLDivElement | null>(null)
  const directorIdBackRef = useRef<HTMLDivElement | null>(null)
  const [overviewLoadError, setOverviewLoadError] = useState(false)

  const rawApiBase =
    process.env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)
  const API_BASE =
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? String(rawApiBase).replace('://localhost', '://127.0.0.1')
      : rawApiBase

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token])

  const selectedBranchId = branchId || user?.branch_id || undefined

  const loadOverview = useCallback(async () => {
    if (!token) return

    setLoading(true)
    setOverviewLoadError(false)
    try {
      const params = new URLSearchParams()
      if (selectedBranchId) {
        params.append('branch_id', String(selectedBranchId))
      }

      const overviewRes = await axios.get<OverviewDashboardPayload>(
        `${API_BASE}/api/overview/dashboard${params.toString() ? `?${params.toString()}` : ''}`,
        requestConfig,
      )

      const data = overviewRes.data
      setOverview(data)
      setFullName(data.director.full_name || '')
      setMobile(data.director.mobile || '')
      setEmail(data.director.email || '')
      setAge(data.director.age || '')
      setAddress(data.director.address || '')
      setAccountNumber(data.bank_details.account_number || '')
      setIfscCode(data.bank_details.ifsc_code || '')
      setPhotoUrl(data.director.photo_url || '')
      setUsername(data.credentials.username || '')
      setPassword(data.credentials.password || '')

      try {
        const storedLogo = window.localStorage.getItem(getBranchLogoStorageKey(data.branch?.id)) || ''
        setBranchLogoUrl(storedLogo)
      } catch {
        setBranchLogoUrl('')
      }

      if (data.branch?.id) {
        try {
          const trendsRes = await axios.get<TrendPayload>(
            `${API_BASE}/api/analytics/trends?branch_id=${data.branch.id}`,
            requestConfig,
          )
          setTrends(trendsRes.data?.monthly || [])
        } catch {
          setTrends([])
        }
      }
    } catch {
      setOverviewLoadError(true)
    } finally {
      setLoading(false)
    }
  }, [token, selectedBranchId, API_BASE, requestConfig])

  useEffect(() => {
    void loadOverview()
  }, [loadOverview])

  const onDropPhoto = useCallback((acceptedFiles: File[]) => {
    const first = acceptedFiles[0]
    if (!first) return

    const reader = new FileReader()
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : ''
      if (result) {
        setPhotoUrl(result)
        toast.success('Profile image ready. Save profile to persist it.')
      }
    }
    reader.readAsDataURL(first)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: onDropPhoto,
    multiple: false,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
    },
  })

  const onSelectBranchLogo = useCallback((file?: File) => {
    if (!file || !overview?.branch?.id) return

    const reader = new FileReader()
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : ''
      if (!result) return
      setBranchLogoUrl(result)
      try {
        window.localStorage.setItem(getBranchLogoStorageKey(overview.branch.id), result)
        toast.success('Branch logo updated for invoices and overview')
      } catch {
        toast.error('Unable to persist branch logo locally')
      }
    }
    reader.readAsDataURL(file)
  }, [overview?.branch?.id])

  const saveProfile = async () => {
    if (!overview) return

    setSavingProfile(true)
    try {
      await axios.put(
        `${API_BASE}/api/overview/profile`,
        {
          branch_id: branchId,
          full_name: fullName,
          mobile,
          email,
          age,
          address,
          account_number: accountNumber,
          ifsc_code: ifscCode,
          director_photo_url: photoUrl,
        },
        requestConfig,
      )

      toast.success('Profile updated successfully')
      await loadOverview()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Unable to update profile')
    } finally {
      setSavingProfile(false)
    }
  }

  const saveCredentials = async () => {
    if (!overview) return

    if (!username.trim() || !password.trim()) {
      toast.error('Username and password are required')
      return
    }

    setSavingCredentials(true)
    try {
      await axios.put(
        `${API_BASE}/api/overview/credentials`,
        {
          branch_id: branchId,
          username: username.trim(),
          password: password.trim(),
        },
        requestConfig,
      )

      toast.success('Credentials updated successfully')
      await loadOverview()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Unable to update credentials')
    } finally {
      setSavingCredentials(false)
    }
  }

  const downloadDirectorIdCardPdf = async () => {
    if (!directorIdFrontRef.current || !directorIdBackRef.current) {
      toast.error('Director ID card preview is not ready')
      return
    }

    try {
      const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: [CR80_CARD_WIDTH_MM, CR80_CARD_HEIGHT_MM],
      })
      const cardRefs = [directorIdFrontRef.current, directorIdBackRef.current]

      for (let i = 0; i < cardRefs.length; i += 1) {
        const canvas = await html2canvas(cardRefs[i], { scale: 3, useCORS: true, backgroundColor: '#ffffff' })
        const imgData = canvas.toDataURL('image/png')

        if (i > 0) pdf.addPage()
        pdf.addImage(imgData, 'PNG', 0, 0, CR80_CARD_WIDTH_MM, CR80_CARD_HEIGHT_MM)
      }

      const safeBranchName = (overview?.branch?.name || 'branch').replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, '')
      pdf.save(`director-id-card-${safeBranchName || 'branch'}.pdf`)
      toast.success('Director ID card PDF downloaded')
    } catch {
      toast.error('Failed to generate Director ID card PDF')
    }
  }

  const attendancePie = useMemo(() => {
    const present = overview?.attendance_summary?.present_today || 0
    const total = overview?.attendance_summary?.total_staff || 0
    const absent = Math.max(0, total - present)

    return [
      { name: 'Present', value: present },
      { name: 'Absent', value: absent },
    ]
  }, [overview])

  const analyticsSummary = useMemo(() => {
    if (!trends.length) {
      return { revenue: 0, expenses: 0, patients: 0 }
    }

    return trends.reduce((acc, item) => {
      acc.revenue += Number(item.revenue || 0)
      acc.expenses += Number(item.expenses || 0)
      acc.patients += Number(item.patients || 0)
      return acc
    }, { revenue: 0, expenses: 0, patients: 0 })
  }, [trends])

  const aboutText = useMemo(() => {
    const location = [overview?.branch.city, overview?.branch.state].filter(Boolean).join(', ')
    return `${fullName || 'Branch Director'} leads operations at ${overview?.branch.name || 'this branch'} in ${location || 'the branch network'}, overseeing staff attendance, patient coordination, banking workflow, and branch-level credential management.`
  }, [fullName, overview?.branch.city, overview?.branch.name, overview?.branch.state])

  if (loading) {
    return (
      <div className="premium-card p-8">
        <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
        <p className="mt-3 text-sm font-semibold text-slate-600">Loading branch dashboard...</p>
      </div>
    )
  }

  if (!overview) {
    return (
      <div className="premium-card p-8">
        <p className="text-slate-600 font-semibold">Overview data is currently unavailable.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {overviewLoadError && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">Overview dashboard is temporarily unavailable</p>
          <p className="mt-1 text-xs text-amber-700">Live branch summary widgets are using fallback data while services recover.</p>
        </div>
      )}
      <div className="premium-card p-8 relative overflow-hidden">
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-gradient-to-br from-cyan-300/30 to-blue-300/30 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-gradient-to-br from-emerald-300/30 to-teal-300/30 blur-3xl" />

        <div className="absolute top-4 left-4 z-20 w-16 h-16 rounded-full object-cover border-2 border-white shadow-lg cursor-pointer hover:opacity-80">
          <label className="relative block h-full w-full overflow-hidden rounded-full" aria-label="Upload branch logo">
            {branchLogoUrl ? (
              <img
                src={branchLogoUrl}
                alt="Branch logo"
                className="h-full w-full rounded-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center rounded-full bg-white text-sm font-black text-blue-600">
                VV
              </div>
            )}
            <span className="absolute bottom-0 right-0 flex h-4 w-4 items-center justify-center rounded-full border border-white bg-slate-900 text-[9px] text-white shadow-sm">
              +
            </span>
            <input
              ref={branchLogoInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => onSelectBranchLogo(e.target.files?.[0])}
            />
          </label>
        </div>

        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="pl-24 text-blue-600 font-extrabold text-3xl">{overview.branch.name}</h2>
            <p className="mt-3 text-xs uppercase tracking-[0.2em] font-bold text-slate-500">Branch Operations Command Center</p>
            <p className="mt-1 text-sm font-semibold text-slate-600">{overview.branch.city}, {overview.branch.state} · Code {overview.branch.branch_code}</p>
          </div>
          <div className="flex items-center gap-3">
            {showBackButton && (
              <button
                type="button"
                onClick={onBack}
                className="rounded-xl bg-slate-100 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-200"
              >
                Back
              </button>
            )}
            <button
              type="button"
              onClick={() => void loadOverview()}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-8 items-start">
        <div className="col-span-12 xl:col-span-4 space-y-6">
          <div className="rounded-[28px] border border-slate-200 bg-white p-7 shadow-sm">
            <div className="flex flex-col items-start gap-2">
              <div
                className="h-16 w-16 overflow-hidden rounded-full bg-slate-100 shrink-0"
                style={{ minWidth: '64px', maxWidth: '64px', minHeight: '64px', maxHeight: '64px' }}
              >
                {photoUrl ? (
                  <img
                    src={photoUrl}
                    alt="Director profile"
                    className="h-16 w-16 rounded-full object-cover border-2 border-gray-200 shadow-sm"
                    style={{ minWidth: '64px', maxWidth: '64px', minHeight: '64px', maxHeight: '64px' }}
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center text-base font-black text-slate-400">{(fullName || 'D').slice(0, 1)}</div>
                )}
              </div>

              <div className="min-w-0 flex-1 text-left">
                <h3 className="text-2xl font-black text-slate-900">{fullName || 'Director Name'}</h3>
                <p className="mt-1 text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">Branch Director</p>
                <div className="mt-4 space-y-2 text-sm text-slate-600">
                  <p>{mobile || 'Mobile not set'}</p>
                  <p className="break-all">{email || 'Email not set'}</p>
                  <p>{overview.branch.city}, {overview.branch.state}</p>
                </div>
              </div>
            </div>

            <div className="mt-6" {...getRootProps()}>
              <input {...getInputProps()} />
              <div className={`rounded-2xl border-2 border-dashed p-4 transition ${isDragActive ? 'border-cyan-500 bg-cyan-50' : 'border-slate-300 bg-slate-50'}`}>
                <p className="text-sm font-semibold text-slate-700">Update director avatar</p>
                <p className="mt-1 text-xs text-slate-500">Drag and drop photo here, or click to select</p>
              </div>
            </div>

            <div className="mt-6 rounded-2xl bg-slate-50 p-5">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">About</p>
              <p className="mt-3 text-sm leading-6 text-slate-700">{aboutText}</p>
            </div>
          </div>

          <div className="rounded-[28px] bg-gradient-to-br from-slate-950 to-slate-800 p-6 text-white shadow-xl">
            <p className="text-xs uppercase tracking-wider font-bold text-slate-300">Attendance Today</p>
            <p className="mt-3 text-3xl font-black">{overview.attendance_summary.present_today}/{overview.attendance_summary.total_staff}</p>
            <p className="mt-2 text-sm text-slate-300">{overview.attendance_summary.label}</p>
            <div className="mt-4 h-[180px] w-full rounded-2xl bg-white/5 p-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={attendancePie}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={42}
                    outerRadius={68}
                    fill="#22c55e"
                    stroke="#fff"
                    strokeWidth={2}
                  />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="col-span-12 xl:col-span-8 space-y-6">
          <div className="premium-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-xl font-black text-slate-900">Revenue and Expense Trend</h3>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Monthly Analytics</p>
            </div>

            <div className="mb-5 grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wider font-bold text-slate-400">Revenue</p>
                <p className="mt-2 text-2xl font-black text-slate-900">INR {analyticsSummary.revenue.toLocaleString()}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wider font-bold text-slate-400">Expenses</p>
                <p className="mt-2 text-2xl font-black text-slate-900">INR {analyticsSummary.expenses.toLocaleString()}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wider font-bold text-slate-400">Patients</p>
                <p className="mt-2 text-2xl font-black text-slate-900">{analyticsSummary.patients.toLocaleString()}</p>
              </div>
            </div>

            <div className="h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trends} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0.05} />
                    </linearGradient>
                    <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="month" tickFormatter={formatMonth} stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Area type="monotone" dataKey="revenue" stroke="#0284c7" fillOpacity={1} fill="url(#colorRevenue)" />
                  <Area type="monotone" dataKey="expenses" stroke="#dc2626" fillOpacity={1} fill="url(#colorExpense)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="premium-card p-6">
            <h3 className="text-xl font-black text-slate-900">Director and Branch Profile</h3>
            <p className="mt-1 text-sm text-slate-500">Update contact, address, bank details, logo, and profile identity without changing backend save logic.</p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <Field label="Director Full Name">
                <input value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-4 py-3" />
              </Field>
              <Field label="Age">
                <input value={age} onChange={(e) => setAge(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-4 py-3" />
              </Field>
              <Field label="Mobile">
                <input value={mobile} onChange={(e) => setMobile(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-4 py-3" />
              </Field>
              <Field label="Email">
                <input value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-4 py-3" />
              </Field>
              <Field label="Bank Account Number">
                <SensitiveInput value={accountNumber} visible={showAccountNumber} onToggle={() => setShowAccountNumber(prev => !prev)} onChange={setAccountNumber} />
              </Field>
              <Field label="IFSC Code">
                <SensitiveInput value={ifscCode} visible={showIfscCode} onToggle={() => setShowIfscCode(prev => !prev)} onChange={(value) => setIfscCode(value.toUpperCase())} keep={2} />
              </Field>
              <div className="md:col-span-2">
                <Field label="Address">
                  <textarea value={address} onChange={(e) => setAddress(e.target.value)} className="w-full rounded-xl border-2 border-slate-200 px-4 py-3" rows={4} />
                </Field>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="grid gap-4 md:grid-cols-1">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Branch Contact</p>
                  <div className="mt-3 space-y-2 text-sm text-slate-700">
                    <p>{overview.branch.phone || 'Phone not set'}</p>
                    <p>{overview.branch.email || 'Email not set'}</p>
                    <p>{overview.branch.address || 'Address not set'}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => void downloadDirectorIdCardPdf()}
                  className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white hover:bg-slate-800"
                >
                  Download PDF
                </button>
              </div>

              <div
                aria-hidden="true"
                className="pointer-events-none fixed"
                style={{ position: 'fixed', left: '-10000px', top: '0', pointerEvents: 'none', zIndex: -1 }}
              >
                <div
                  ref={directorIdFrontRef}
                  className="font-sans"
                  style={{
                    width: `${CR80_CARD_WIDTH_MM}mm`,
                    height: `${CR80_CARD_HEIGHT_MM}mm`,
                    padding: `${CR80_SAFE_MARGIN_MM}mm`,
                    boxSizing: 'border-box',
                    background: 'linear-gradient(145deg, #e7f1ff 0%, #ffffff 45%, #dbeafe 100%)',
                    border: '1px solid #bfdbfe',
                    borderTop: '5px solid #2563eb',
                    borderRadius: '4mm',
                    boxShadow: '0 3mm 7mm rgba(37, 99, 235, 0.18)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      textAlign: 'center',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      color: '#1d4ed8',
                      fontSize: '8.2pt',
                      lineHeight: 1.1,
                      paddingBottom: '1.2mm',
                    }}
                  >
                    {overview.branch.name}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '2.2mm', flex: 1 }}>
                    <div style={{ width: '34%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '1.6mm' }}>
                      <div
                        style={{
                          width: '20mm',
                          height: '20mm',
                          overflow: 'hidden',
                          borderRadius: '2.4mm',
                          border: '1px solid #93c5fd',
                          background: '#ffffff',
                          boxShadow: '0 1mm 2.2mm rgba(15, 23, 42, 0.18)',
                        }}
                      >
                        {photoUrl ? (
                          <img
                            src={photoUrl}
                            alt="Director avatar"
                            style={{ width: '20mm', height: '20mm', objectFit: 'cover', display: 'block' }}
                          />
                        ) : (
                          <div
                            style={{
                              width: '100%',
                              height: '100%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '16pt',
                              color: '#1d4ed8',
                            }}
                          >
                            👤
                          </div>
                        )}
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '1.3mm',
                          padding: '0.9mm 1.7mm',
                          borderRadius: '999px',
                          border: '1px solid #67e8f9',
                          background: 'linear-gradient(90deg, #0284c7 0%, #0891b2 52%, #0f766e 100%)',
                          boxShadow: '0 1mm 2mm rgba(14, 116, 144, 0.35)',
                        }}
                      >
                        <span
                          style={{
                            width: '3.6mm',
                            height: '3.6mm',
                            borderRadius: '1.2mm',
                            background: 'linear-gradient(180deg, #ffffff 0%, #dbeafe 100%)',
                            color: '#0369a1',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '8pt',
                            fontWeight: 900,
                            lineHeight: 1,
                            boxShadow: 'inset 0 0 0 0.3mm #93c5fd',
                          }}
                        >
                          +
                        </span>
                        <span style={{ color: '#ffffff', fontSize: '6.5pt', fontWeight: 800, letterSpacing: '0.04em' }}>MEDICAL STAFF</span>
                      </div>
                    </div>

                    <div
                      style={{
                        width: '66%',
                        minWidth: 0,
                        borderRadius: '2mm',
                        border: '1px solid #dbeafe',
                        background: 'rgba(255, 255, 255, 0.92)',
                        padding: '1.5mm 1.8mm',
                      }}
                    >
                      <p
                        style={{
                          margin: 0,
                          fontWeight: 800,
                          color: '#0f172a',
                          fontSize: '9.5pt',
                          lineHeight: 1.12,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {fullName || 'Director Name'}
                      </p>
                      <p style={{ margin: '0.8mm 0 0', fontWeight: 700, color: '#2563eb', fontSize: '7.3pt', lineHeight: 1.15 }}>Role: Branch Director</p>
                      <p style={{ margin: '0.7mm 0 0', color: '#334155', fontSize: '7pt', lineHeight: 1.15 }}>Phone: {mobile || '-'}</p>
                      <p style={{ margin: '0.6mm 0 0', color: '#334155', fontSize: '6.9pt', lineHeight: 1.15 }}>Employee ID: DIR-{overview.branch.id}</p>
                      <div style={{ marginTop: '0.8mm', display: 'flex', gap: '1.8mm', flexWrap: 'wrap', color: '#64748b', fontSize: '6.2pt', lineHeight: 1.1 }}>
                        <span>Issue: {new Date().toLocaleDateString()}</span>
                        <span>Valid: 2027</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  ref={directorIdBackRef}
                  className="mt-3 font-sans"
                  style={{
                    width: `${CR80_CARD_WIDTH_MM}mm`,
                    height: `${CR80_CARD_HEIGHT_MM}mm`,
                    padding: `${CR80_SAFE_MARGIN_MM}mm`,
                    boxSizing: 'border-box',
                    background: 'linear-gradient(145deg, #eaf3ff 0%, #ffffff 45%, #dbeafe 100%)',
                    border: '1px solid #bfdbfe',
                    borderTop: '5px solid #2563eb',
                    borderRadius: '4mm',
                    boxShadow: '0 3mm 7mm rgba(37, 99, 235, 0.18)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      textAlign: 'center',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                      color: '#1d4ed8',
                      fontSize: '8.2pt',
                      lineHeight: 1.1,
                      paddingBottom: '1.2mm',
                    }}
                  >
                    {overview.branch.name}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'stretch', gap: '2.2mm', flex: 1 }}>
                    <div
                      style={{
                        width: '72%',
                        minWidth: 0,
                        borderRadius: '2mm',
                        border: '1px solid #dbeafe',
                        background: 'rgba(255, 255, 255, 0.92)',
                        padding: '1.8mm 2mm',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                      }}
                    >
                      <p style={{ margin: 0, fontWeight: 800, color: '#0f172a', fontSize: '8pt', lineHeight: 1.2 }}>Contact Details</p>
                      <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2, wordBreak: 'break-word' }}><span style={{ fontWeight: 700 }}>Address:</span> {address || '-'}</p>
                      <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2 }}><span style={{ fontWeight: 700 }}>Phone:</span> {mobile || '-'}</p>
                      <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2, wordBreak: 'break-word' }}><span style={{ fontWeight: 700 }}>Email:</span> {email || '-'}</p>
                      <div style={{ marginTop: '1.1mm', display: 'flex', gap: '2mm', flexWrap: 'wrap', color: '#475569', fontSize: '6.6pt', lineHeight: 1.15, fontWeight: 600 }}>
                        <span>Issue: {new Date().toLocaleDateString()}</span>
                        <span>Valid: 2027</span>
                      </div>
                    </div>

                    <div style={{ width: '28%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                      <div
                        style={{
                          width: '18mm',
                          height: '18mm',
                          lineHeight: 0,
                          borderRadius: '2mm',
                          border: '1px solid #93c5fd',
                          background: '#ffffff',
                          padding: '1.3mm',
                          boxShadow: '0 1mm 2.2mm rgba(15, 23, 42, 0.18)',
                        }}
                      >
                        <QRCode
                          value={`DIRECTOR_BACK|${overview.branch.id}|${address}|${overview.branch.phone}|${overview.branch.email || ''}`}
                          size={160}
                          style={{ width: '100%', height: '100%', display: 'block' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={() => void saveProfile()}
              disabled={savingProfile}
              className="mt-6 rounded-xl bg-cyan-600 px-5 py-3 text-sm font-bold text-white hover:bg-cyan-700 disabled:opacity-60"
            >
              {savingProfile ? 'Saving...' : 'Save Profile'}
            </button>
          </div>

          <div className="premium-card p-6">
            <h3 className="text-xl font-black text-slate-900">Admin Credentials</h3>
            <p className="mt-1 text-sm text-slate-500">Manage branch login credentials with reveal toggles for sensitive values.</p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <Field label="Portal Username">
                <SensitiveInput value={username} visible={showUsername} onToggle={() => setShowUsername(prev => !prev)} onChange={setUsername} keep={2} />
              </Field>
              <Field label="Portal Password">
                <SensitiveInput value={password} visible={showPassword} onToggle={() => setShowPassword(prev => !prev)} onChange={setPassword} keep={2} />
              </Field>
            </div>

            <button
              type="button"
              onClick={() => void saveCredentials()}
              disabled={savingCredentials}
              className="mt-6 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {savingCredentials ? 'Updating...' : 'Update Credentials'}
            </button>

            <div className="mt-6 rounded-2xl bg-slate-900 p-5 text-slate-100">
              <p className="text-xs uppercase tracking-wider font-bold text-slate-400">Security Note</p>
              <p className="mt-2 text-sm">Changing credentials immediately updates branch login access. Share the new password only with authorized operations leads.</p>
            </div>

          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-bold uppercase tracking-[0.2em] text-slate-500">{label}</label>
      {children}
    </div>
  )
}

function SensitiveInput({
  value,
  visible,
  onToggle,
  onChange,
  keep = 4,
}: {
  value: string
  visible: boolean
  onToggle: () => void
  onChange: (value: string) => void
  keep?: number
}) {
  return (
    <div className="relative">
      <input
        value={value}
        type={visible ? 'text' : 'password'}
        placeholder={visible ? '' : maskValue(value, keep)}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 pr-12"
      />
      <button
        type="button"
        onClick={onToggle}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-lg text-slate-500 hover:text-slate-800"
        aria-label={visible ? 'Hide value' : 'Show value'}
      >
        👁️
      </button>
    </div>
  )
}
