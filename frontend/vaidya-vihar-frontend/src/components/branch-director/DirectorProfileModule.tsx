import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import { useForm } from 'react-hook-form'
import { useDropzone } from 'react-dropzone'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import toast from 'react-hot-toast'
import QRCode from 'react-qr-code'

import { useAuth } from '../../contexts/AuthContext'
import BranchPaymentsDashboard from './BranchPaymentsDashboard'

type DirectorTab = 'profile' | 'staff' | 'attendance' | 'leave' | 'reports' | 'payments'

type DirectorProfile = {
  user_id: number
  full_name: string
  designation?: string
  mobile?: string
  email?: string
  address?: string
  date_of_joining?: string
  specialization?: string
  emergency_contact?: string
  role: string
  photo_path?: string
}

type StaffRow = {
  id: number
  staff_id: string
  name: string
  email: string
  mobile: string
  role: string
  department?: string
  specialization?: string
  date_of_joining?: string
  shift_timings?: string
  status: string
}

type LeaveRequest = {
  id: number
  staff_profile_id: number
  staff_id: string
  leave_type: string
  start_date: string
  end_date: string
  total_days: number
  reason?: string
  status: string
}

type NotificationItem = {
  id: number
  title: string
  message: string
  is_read: boolean
  created_at: string
}

type MonthlyAttendanceRow = {
  date: string
  status: string
  clock_in_time?: string | null
  clock_out_time?: string | null
  task?: string | null
  staff_note?: string | null
  clock_in_selfie_url?: string | null
  clock_out_selfie_url?: string | null
}

type SalaryForm = {
  basic: number
  allowances: number
  deductions: number
  bank_name?: string
  account_number?: string
  ifsc_code?: string
  upi_id?: string
}

type DirectorProfileForm = {
  first_name: string
  last_name: string
  designation?: string
  mobile?: string
  email?: string
  address?: string
  date_of_joining?: string
  specialization?: string
  emergency_contact?: string
}

type StaffForm = {
  first_name: string
  last_name: string
  email: string
  mobile: string
  address?: string
  emergency_contact?: string
  role: string
  department?: string
  specialization?: string
  date_of_joining?: string
  shift_timings?: string
  temporary_password?: string
  auto_generate_password: boolean
}

const staffColumnHelper = createColumnHelper<StaffRow>()
const ID_CARD_WIDTH_MM = 85.6
const ID_CARD_HEIGHT_MM = 54
const ID_CARD_SAFE_MARGIN_MM = 3

export default function DirectorProfileModule() {
  const { user, token } = useAuth()
  const [activeTab, setActiveTab] = useState<DirectorTab>('profile')
  const [profile, setProfile] = useState<DirectorProfile | null>(null)
  const [staffRows, setStaffRows] = useState<StaffRow[]>([])
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [selectedStaff, setSelectedStaff] = useState<any>(null)
  const [monthlyAttendance, setMonthlyAttendance] = useState<MonthlyAttendanceRow[]>([])
  const [attendanceTargetId, setAttendanceTargetId] = useState<number | null>(null)
  const [geoCoords, setGeoCoords] = useState<{ lat: string; lng: string } | null>(null)
  const [selfieFile, setSelfieFile] = useState<File | null>(null)
  const [staffPhotoFile, setStaffPhotoFile] = useState<File | null>(null)
  const [directorPhotoFile, setDirectorPhotoFile] = useState<File | null>(null)
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const [performanceNote, setPerformanceNote] = useState('')
  const [leaveApplyStaffId, setLeaveApplyStaffId] = useState<number | null>(null)
  const [leaveType, setLeaveType] = useState('casual')
  const [leaveReason, setLeaveReason] = useState('')
  const [leaveStart, setLeaveStart] = useState('')
  const [leaveEnd, setLeaveEnd] = useState('')
  const [salary, setSalary] = useState<SalaryForm>({ basic: 0, allowances: 0, deductions: 0 })
  const [staffFilter, setStaffFilter] = useState({ role: '', department: '', status: '' })
  const [staffSearch, setStaffSearch] = useState('')
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1)
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear())

  const idCardRef = useRef<HTMLDivElement | null>(null)
  const staffIdBackRef = useRef<HTMLDivElement | null>(null)
  const payslipRef = useRef<HTMLDivElement | null>(null)
  const directorIdFrontRef = useRef<HTMLDivElement | null>(null)
  const directorIdBackRef = useRef<HTMLDivElement | null>(null)

  const API_BASE =
    process.env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const resolveAttendanceMediaUrl = (value?: string | null) => {
    const raw = (value || '').trim()
    if (!raw) return ''
    if (/^https?:\/\//i.test(raw)) return raw
    if (raw.startsWith('/api/files/')) return `${API_BASE}${raw}`
    if (raw.startsWith('/')) return `${API_BASE}/api/files/${raw.slice(1)}`
    return `${API_BASE}/api/files/${raw}`
  }

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token])

  const profileForm = useForm<DirectorProfileForm>()
  const staffForm = useForm<StaffForm>({
    defaultValues: {
      role: 'staff',
      auto_generate_password: true,
    },
  })

  // Column config is intentionally stable; row action handlers read latest closures.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const staffColumns = useMemo(() => [
    staffColumnHelper.accessor('staff_id', {
      header: 'Staff ID',
      cell: info => <span className="font-bold text-slate-800">{info.getValue()}</span>,
    }),
    staffColumnHelper.accessor('name', { header: 'Name' }),
    staffColumnHelper.accessor('role', { header: 'Role' }),
    staffColumnHelper.accessor('department', { header: 'Department' }),
    staffColumnHelper.accessor('status', {
      header: 'Status',
      cell: info => (
        <span className={`px-2 py-1 rounded-full text-xs font-bold ${info.getValue() === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
          {info.getValue()}
        </span>
      ),
    }),
    staffColumnHelper.display({
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex gap-2">
          <button
            className="px-3 py-1 rounded-lg bg-blue-600 text-white text-xs font-semibold"
            onClick={() => void openStaffProfile(row.original.id)}
          >
            View/Edit
          </button>
          <button
            className="px-3 py-1 rounded-lg bg-amber-600 text-white text-xs font-semibold"
            onClick={() => void deactivateStaff(row.original.id)}
          >
            Deactivate
          </button>
        </div>
      ),
    }),
  ], [])

  const staffTable = useReactTable({
    data: staffRows,
    columns: staffColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  const loadProfile = useCallback(async () => {
    if (!token) return
    const res = await axios.get(`${API_BASE}/api/director/profile`, requestConfig)
    setProfile(res.data)

    const nameParts = String(res.data.full_name || '').split(' ')
    profileForm.reset({
      first_name: nameParts[0] || '',
      last_name: nameParts.slice(1).join(' ') || '',
      designation: res.data.designation || '',
      mobile: res.data.mobile || '',
      email: res.data.email || '',
      address: res.data.address || '',
      date_of_joining: res.data.date_of_joining ? String(res.data.date_of_joining).slice(0, 10) : '',
      specialization: res.data.specialization || '',
      emergency_contact: res.data.emergency_contact || '',
    })
  }, [API_BASE, requestConfig, token, profileForm])

  const loadStaff = useCallback(async () => {
    if (!token) return
    const params = new URLSearchParams()
    if (staffFilter.role) params.set('role', staffFilter.role)
    if (staffFilter.department) params.set('department', staffFilter.department)
    if (staffFilter.status) params.set('status', staffFilter.status)
    if (staffSearch.trim()) params.set('search', staffSearch.trim())

    const res = await axios.get(`${API_BASE}/api/director/staff?${params.toString()}`, requestConfig)
    setStaffRows(Array.isArray(res.data) ? res.data : [])
  }, [API_BASE, requestConfig, token, staffFilter, staffSearch])

  const loadLeaveRequests = useCallback(async () => {
    if (!token) return
    const res = await axios.get(`${API_BASE}/api/director/leave/requests`, requestConfig)
    setLeaveRequests(Array.isArray(res.data) ? res.data : [])
  }, [API_BASE, requestConfig, token])

  const loadSummary = useCallback(async () => {
    if (!token) return
    const res = await axios.get(`${API_BASE}/api/director/dashboard/summary`, requestConfig)
    setSummary(res.data)
  }, [API_BASE, requestConfig, token])

  const loadNotifications = useCallback(async () => {
    if (!token || user?.role !== 'branch_director') return
    const res = await axios.get(`${API_BASE}/api/director/notifications`, requestConfig)
    setNotifications(Array.isArray(res.data) ? res.data : [])
  }, [API_BASE, requestConfig, token, user?.role])

  useEffect(() => {
    void loadProfile()
    void loadStaff()
    void loadLeaveRequests()
    void loadSummary()
    void loadNotifications()
  }, [loadProfile, loadStaff, loadLeaveRequests, loadSummary, loadNotifications])

  const directorPhotoDrop = useDropzone({
    multiple: false,
    accept: { 'image/*': [] },
    onDrop: files => setDirectorPhotoFile(files[0] || null),
  })

  const staffPhotoDrop = useDropzone({
    multiple: false,
    accept: { 'image/*': [] },
    onDrop: files => setStaffPhotoFile(files[0] || null),
  })

  const documentDrop = useDropzone({
    multiple: false,
    onDrop: files => setDocumentFile(files[0] || null),
  })

  const saveDirectorProfile = profileForm.handleSubmit(async values => {
    try {
      await axios.put(`${API_BASE}/api/director/profile`, {
        ...values,
        date_of_joining: values.date_of_joining ? new Date(values.date_of_joining).toISOString() : null,
      }, requestConfig)

      if (directorPhotoFile) {
        const fd = new FormData()
        fd.append('file', directorPhotoFile)
        await axios.post(`${API_BASE}/api/director/profile/photo`, fd, {
          ...requestConfig,
          headers: {
            ...requestConfig.headers,
            'Content-Type': 'multipart/form-data',
          },
        })
      }

      toast.success('Director profile updated')
      setDirectorPhotoFile(null)
      void loadProfile()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to update profile')
    }
  })

  const createStaff = staffForm.handleSubmit(async values => {
    try {
      const response = await axios.post(`${API_BASE}/api/director/staff`, {
        ...values,
        date_of_joining: values.date_of_joining ? new Date(values.date_of_joining).toISOString() : null,
      }, requestConfig)

      if (staffPhotoFile && response.data?.staff?.staff_profile_id) {
        const fd = new FormData()
        fd.append('file', staffPhotoFile)
        await axios.post(`${API_BASE}/api/director/staff/${response.data.staff.staff_profile_id}/photo`, fd, {
          ...requestConfig,
          headers: {
            ...requestConfig.headers,
            'Content-Type': 'multipart/form-data',
          },
        })
      }

      toast.success(`Staff created. Username: ${response.data?.credentials?.username}, Password: ${response.data?.credentials?.password}`)
      staffForm.reset({ role: 'staff', auto_generate_password: true } as any)
      setStaffPhotoFile(null)
      void loadStaff()
      void loadSummary()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to create staff')
    }
  })

  const openStaffProfile = async (staffProfileId: number) => {
    try {
      const res = await axios.get(`${API_BASE}/api/director/staff/${staffProfileId}`, requestConfig)
      setSelectedStaff(res.data)
      setAttendanceTargetId(staffProfileId)
      setLeaveApplyStaffId(staffProfileId)
      setSalary({
        basic: res.data.salary?.basic || 0,
        allowances: res.data.salary?.allowances || 0,
        deductions: res.data.salary?.deductions || 0,
        bank_name: res.data.salary?.bank_name || '',
        account_number: res.data.salary?.account_number || '',
        ifsc_code: res.data.salary?.ifsc_code || '',
        upi_id: res.data.salary?.upi_id || '',
      })
      await loadMonthlyAttendance(staffProfileId)
      setActiveTab('staff')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to load staff profile')
    }
  }

  const updateStaff = async () => {
    if (!selectedStaff) return
    try {
      await axios.put(`${API_BASE}/api/director/staff/${selectedStaff.id}`, {
        first_name: selectedStaff.first_name,
        last_name: selectedStaff.last_name,
        email: selectedStaff.email,
        mobile: selectedStaff.mobile,
        address: selectedStaff.address,
        emergency_contact: selectedStaff.emergency_contact,
        department: selectedStaff.department,
        specialization: selectedStaff.specialization,
        shift_timings: selectedStaff.shift_timings,
      }, requestConfig)
      toast.success('Staff profile updated')
      void loadStaff()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to update staff profile')
    }
  }

  const deactivateStaff = async (staffProfileId: number) => {
    try {
      await axios.delete(`${API_BASE}/api/director/staff/${staffProfileId}`, requestConfig)
      toast.success('Staff deactivated')
      if (selectedStaff?.id === staffProfileId) setSelectedStaff(null)
      void loadStaff()
      void loadSummary()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to deactivate staff')
    }
  }

  const saveSalary = async () => {
    if (!selectedStaff) return
    try {
      const payload = {
        ...salary,
        basic: Number(salary.basic || 0),
        allowances: Number(salary.allowances || 0),
        deductions: Number(salary.deductions || 0),
      }
      await axios.put(`${API_BASE}/api/director/staff/${selectedStaff.id}/salary`, payload, requestConfig)
      toast.success('Salary details saved')
      await openStaffProfile(selectedStaff.id)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save salary details')
    }
  }

  const loadMonthlyAttendance = async (staffProfileId: number) => {
    try {
      const res = await axios.get(`${API_BASE}/api/director/staff/${staffProfileId}/attendance/monthly?month=${selectedMonth}&year=${selectedYear}`, requestConfig)
      setMonthlyAttendance(Array.isArray(res.data) ? res.data : [])
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to load monthly attendance')
    }
  }

  const captureGeo = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported by this browser')
      return
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        setGeoCoords({ lat: String(pos.coords.latitude), lng: String(pos.coords.longitude) })
        toast.success('Location captured')
      },
      () => toast.error('Unable to capture location')
    )
  }

  const doClock = async (action: 'in' | 'out') => {
    if (!attendanceTargetId) {
      toast.error('Select a staff profile first')
      return
    }
    if (!selfieFile) {
      toast.error('Selfie photo is required for clock in and clock out')
      return
    }
    try {
      const fd = new FormData()
      fd.append('action', action)
      if (geoCoords?.lat) fd.append('latitude', geoCoords.lat)
      if (geoCoords?.lng) fd.append('longitude', geoCoords.lng)
      if (selfieFile) fd.append('photo', selfieFile)

      await axios.post(`${API_BASE}/api/director/staff/${attendanceTargetId}/attendance/clock`, fd, {
        ...requestConfig,
        headers: {
          ...requestConfig.headers,
          'Content-Type': 'multipart/form-data',
        },
      })
      toast.success(`Clock ${action} successful`)
      await loadMonthlyAttendance(attendanceTargetId)
      setSelfieFile(null)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || `Failed to clock ${action}`)
    }
  }

  const applyLeave = async () => {
    if (!leaveApplyStaffId || !leaveStart || !leaveEnd) {
      toast.error('Select staff and leave dates')
      return
    }
    try {
      await axios.post(`${API_BASE}/api/director/leave/apply`, {
        staff_profile_id: leaveApplyStaffId,
        leave_type: leaveType,
        start_date: new Date(leaveStart).toISOString(),
        end_date: new Date(leaveEnd).toISOString(),
        reason: leaveReason,
      }, requestConfig)
      toast.success('Leave request submitted')
      setLeaveReason('')
      void loadLeaveRequests()
      void loadNotifications()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to apply leave')
    }
  }

  const decideLeave = async (leaveRequestId: number, status: 'approved' | 'rejected') => {
    try {
      await axios.put(`${API_BASE}/api/director/leave/requests/${leaveRequestId}/decision`, { status }, requestConfig)
      toast.success(`Leave ${status}`)
      void loadLeaveRequests()
      if (attendanceTargetId) void loadMonthlyAttendance(attendanceTargetId)
      void loadSummary()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to update leave request')
    }
  }

  const addPerformanceNote = async () => {
    if (!selectedStaff || !performanceNote.trim()) return
    try {
      await axios.post(`${API_BASE}/api/director/staff/${selectedStaff.id}/performance-notes`, { note: performanceNote.trim() }, requestConfig)
      toast.success('Performance note added')
      setPerformanceNote('')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to add performance note')
    }
  }

  const uploadDocument = async () => {
    if (!selectedStaff || !documentFile) return
    try {
      const fd = new FormData()
      fd.append('file', documentFile)
      fd.append('document_type', 'staff_document')
      await axios.post(`${API_BASE}/api/director/staff/${selectedStaff.id}/documents`, fd, {
        ...requestConfig,
        headers: {
          ...requestConfig.headers,
          'Content-Type': 'multipart/form-data',
        },
      })
      toast.success('Document uploaded')
      setDocumentFile(null)
      await openStaffProfile(selectedStaff.id)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to upload document')
    }
  }

  const downloadElementPdf = async (element: HTMLElement | null, filename: string) => {
    if (!element) return
    const canvas = await html2canvas(element, { scale: 2 })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const width = 190
    const height = (canvas.height * width) / canvas.width
    pdf.addImage(imgData, 'PNG', 10, 10, width, height)
    pdf.save(filename)
  }

  const downloadStaffIdCardPdf = async () => {
    if (!idCardRef.current || !staffIdBackRef.current || !selectedStaff) {
      toast.error('Staff ID card preview is not ready')
      return
    }

    try {
      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: [ID_CARD_WIDTH_MM, ID_CARD_HEIGHT_MM] })
      const cardRefs = [idCardRef.current, staffIdBackRef.current]

      for (let i = 0; i < cardRefs.length; i += 1) {
        const canvas = await html2canvas(cardRefs[i], { scale: 3, useCORS: true, backgroundColor: '#ffffff' })
        const imgData = canvas.toDataURL('image/png')

        if (i > 0) pdf.addPage()
        pdf.addImage(imgData, 'PNG', 0, 0, ID_CARD_WIDTH_MM, ID_CARD_HEIGHT_MM)
      }

      pdf.save(`id-card-${selectedStaff.staff_id}.pdf`)
      toast.success('Staff ID card PDF downloaded')
    } catch {
      toast.error('Failed to generate staff ID card PDF')
    }
  }

  const downloadDirectorIdCardPdf = async () => {
    if (!directorIdFrontRef.current || !directorIdBackRef.current) {
      toast.error('Director ID card preview is not ready')
      return
    }

    try {
      const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: [ID_CARD_WIDTH_MM, ID_CARD_HEIGHT_MM] })
      const cardRefs = [directorIdFrontRef.current, directorIdBackRef.current]

      for (let i = 0; i < cardRefs.length; i += 1) {
        const canvas = await html2canvas(cardRefs[i], { scale: 3, useCORS: true, backgroundColor: '#ffffff' })
        const imgData = canvas.toDataURL('image/png')

        if (i > 0) pdf.addPage()
        pdf.addImage(imgData, 'PNG', 0, 0, ID_CARD_WIDTH_MM, ID_CARD_HEIGHT_MM)
      }

      pdf.save(`director-id-card-${profile?.user_id || 'profile'}.pdf`)
      toast.success('Director ID card PDF downloaded')
    } catch {
      toast.error('Failed to generate Director ID card PDF')
    }
  }

  const unreadCount = notifications.filter(n => !n.is_read).length

  if (!user || (user.role !== 'branch_director' && user.role !== 'branch_admin' && user.role !== 'super_admin')) {
    return <div className="premium-card p-8">Access denied.</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <aside className="premium-card p-6 xl:col-span-1">
          <div className="flex flex-col items-center text-center">
            <div className="w-24 h-24 rounded-full bg-slate-100 border-4 border-white shadow mb-3 overflow-hidden">
              {profile?.photo_path ? (
                <img src={`${API_BASE}/api/files/${profile.photo_path}`} alt="Director" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-2xl">👤</div>
              )}
            </div>
            <h2 className="text-xl font-black text-slate-900">{profile?.full_name || 'Director'}</h2>
            <p className="text-sm text-slate-500">{profile?.role || 'branch_director'}</p>
            <p className="text-xs text-slate-400 mt-1">{profile?.designation || 'Branch Director'}</p>
          </div>

          <div className="mt-6 space-y-2">
            {[
              { key: 'profile', label: 'My Profile' },
              { key: 'staff', label: 'Staff Management' },
              { key: 'attendance', label: 'Attendance' },
              { key: 'leave', label: 'Leave Requests' },
              { key: 'payments', label: 'Payments' },
              { key: 'reports', label: 'Reports' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as DirectorTab)}
                className={`w-full text-left px-4 py-2 rounded-xl font-semibold ${activeTab === tab.key ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-6 rounded-xl bg-slate-900 text-white p-4">
            <p className="text-xs uppercase tracking-wider text-slate-300">Quick Stats</p>
            <p className="text-sm mt-2">Total Staff: <span className="font-bold">{summary?.total_staff ?? 0}</span></p>
            <p className="text-sm">Present Today: <span className="font-bold">{summary?.present_today ?? 0}</span></p>
            <p className="text-sm">On Leave: <span className="font-bold">{summary?.on_leave ?? 0}</span></p>
            <p className="text-sm">Pending Leaves: <span className="font-bold">{summary?.pending_leave_requests ?? 0}</span></p>
            {user.role === 'branch_director' && (
              <p className="text-sm mt-2">Notifications: <span className="font-bold">{unreadCount}</span></p>
            )}
          </div>
        </aside>

        <section className="xl:col-span-3 space-y-6">
          {activeTab === 'profile' && (
            <div className="premium-card p-6">
              <h3 className="text-2xl font-black text-slate-900 mb-4">Director Profile</h3>
              <p className="text-sm text-slate-500 mb-4">HR-focused profile only. Bank/UPI/soundbox settings are intentionally excluded.</p>

              <div className="mb-4 p-4 border rounded-xl bg-slate-50">
                <p className="font-semibold text-sm mb-2">Profile Photo Upload</p>
                <div {...directorPhotoDrop.getRootProps()} className="p-4 border-2 border-dashed rounded-xl cursor-pointer bg-white">
                  <input {...directorPhotoDrop.getInputProps()} />
                  <p className="text-sm text-slate-600">Drag and drop photo, or click to choose</p>
                  {directorPhotoFile && <p className="text-xs text-slate-500 mt-2">Selected: {directorPhotoFile.name}</p>}
                </div>
              </div>

              <form onSubmit={saveDirectorProfile} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input placeholder="First Name" className="px-4 py-3 border rounded-xl" {...profileForm.register('first_name', { required: true })} />
                <input placeholder="Last Name" className="px-4 py-3 border rounded-xl" {...profileForm.register('last_name', { required: true })} />
                <input placeholder="Designation" className="px-4 py-3 border rounded-xl" {...profileForm.register('designation')} />
                <input placeholder="Mobile" className="px-4 py-3 border rounded-xl" {...profileForm.register('mobile')} />
                <input placeholder="Email" className="px-4 py-3 border rounded-xl" {...profileForm.register('email')} />
                <input type="date" className="px-4 py-3 border rounded-xl" {...profileForm.register('date_of_joining')} />
                <input placeholder="Specialization" className="px-4 py-3 border rounded-xl" {...profileForm.register('specialization')} />
                <input placeholder="Emergency Contact" className="px-4 py-3 border rounded-xl" {...profileForm.register('emergency_contact')} />
                <textarea placeholder="Address" className="md:col-span-2 px-4 py-3 border rounded-xl" {...profileForm.register('address')} />
                <button className="md:col-span-2 px-4 py-3 rounded-xl bg-blue-600 text-white font-bold">Save Profile</button>
              </form>

              <div className="mt-8 border rounded-2xl p-5 bg-slate-50">
                <h4 className="text-xl font-black text-slate-900">Director ID Card (Front & Back)</h4>
                <p className="text-sm text-slate-600 mt-1">Auto-generated card with QR, photo, and address details.</p>

                <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div
                    ref={directorIdFrontRef}
                    className="rounded-2xl border bg-white"
                    style={{
                      width: `${ID_CARD_WIDTH_MM}mm`,
                      height: `${ID_CARD_HEIGHT_MM}mm`,
                      padding: `${ID_CARD_SAFE_MARGIN_MM}mm`,
                      boxSizing: 'border-box',
                    }}
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">VaidyaVihar Diagnostic</p>
                    <div className="mt-2 flex items-start justify-between gap-3">
                      <div>
                        <p className="text-lg font-black text-slate-900">{profile?.full_name || 'Director'}</p>
                        <p className="text-sm text-slate-600">{profile?.designation || 'Branch Director'}</p>
                        <p className="text-xs text-slate-500 mt-1">ID: DIR-{profile?.user_id || '0000'}</p>
                        <p className="text-xs text-slate-500">Mobile: {profile?.mobile || '-'}</p>
                      </div>
                      <div className="rounded-full overflow-hidden border border-slate-200 bg-slate-100 shrink-0" style={{ width: '16mm', height: '16mm' }}>
                        {profile?.photo_path ? (
                          <img src={`${API_BASE}/api/files/${profile.photo_path}`} alt="Director" className="h-full w-full object-cover" style={{ width: '16mm', height: '16mm' }} />
                        ) : (
                          <div className="h-full w-full flex items-center justify-center text-xs">👤</div>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 flex items-center gap-3">
                      <div className="rounded-md border border-slate-200 bg-white p-1" style={{ width: '16mm', height: '16mm' }}>
                        <QRCode
                          value={`DIRECTOR_FRONT|${profile?.user_id || ''}|${profile?.full_name || ''}|${profile?.mobile || ''}|${profile?.email || ''}`}
                          size={120}
                          style={{ height: '100%', width: '100%' }}
                        />
                      </div>
                      <p className="text-xs text-slate-600">Scan to verify Director profile details</p>
                    </div>
                  </div>

                  <div
                    ref={directorIdBackRef}
                    className="rounded-2xl border bg-white"
                    style={{
                      width: `${ID_CARD_WIDTH_MM}mm`,
                      height: `${ID_CARD_HEIGHT_MM}mm`,
                      padding: `${ID_CARD_SAFE_MARGIN_MM}mm`,
                      boxSizing: 'border-box',
                    }}
                  >
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Director ID Card - Back</p>
                    <div className="mt-2 space-y-1 text-sm text-slate-700">
                      <p><span className="font-semibold">Address:</span> {profile?.address || '-'}</p>
                      <p><span className="font-semibold">Email:</span> {profile?.email || '-'}</p>
                      <p><span className="font-semibold">Emergency Contact:</span> {profile?.emergency_contact || '-'}</p>
                      <p><span className="font-semibold">Date of Joining:</span> {profile?.date_of_joining ? String(profile.date_of_joining).slice(0, 10) : '-'}</p>
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-3">
                      <p className="text-xs text-slate-500">If found, contact branch administration immediately.</p>
                      <div className="rounded-md border border-slate-200 bg-white p-1 shrink-0" style={{ width: '16mm', height: '16mm' }}>
                        <QRCode
                          value={`DIRECTOR_BACK|${profile?.user_id || ''}|${profile?.address || ''}|${profile?.emergency_contact || ''}`}
                          size={120}
                          style={{ height: '100%', width: '100%' }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => void downloadDirectorIdCardPdf()}
                  className="mt-4 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-semibold"
                >
                  Download Director ID Card PDF
                </button>
              </div>
            </div>
          )}

          {activeTab === 'staff' && (
            <>
              <div className="premium-card p-6">
                <h3 className="text-2xl font-black text-slate-900 mb-4">Staff List</h3>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
                  <input
                    value={staffSearch}
                    onChange={e => setStaffSearch(e.target.value)}
                    placeholder="Search name/staff ID"
                    className="px-4 py-2 border rounded-xl"
                  />
                  <input
                    value={staffFilter.role}
                    onChange={e => setStaffFilter(prev => ({ ...prev, role: e.target.value }))}
                    placeholder="Filter Role"
                    className="px-4 py-2 border rounded-xl"
                  />
                  <input
                    value={staffFilter.department}
                    onChange={e => setStaffFilter(prev => ({ ...prev, department: e.target.value }))}
                    placeholder="Filter Department"
                    className="px-4 py-2 border rounded-xl"
                  />
                  <select
                    value={staffFilter.status}
                    onChange={e => setStaffFilter(prev => ({ ...prev, status: e.target.value }))}
                    className="px-4 py-2 border rounded-xl"
                  >
                    <option value="">All Status</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
                <button onClick={() => void loadStaff()} className="mb-4 px-4 py-2 rounded-xl bg-slate-800 text-white font-semibold">Apply Filters</button>

                <div className="overflow-x-auto border rounded-xl">
                  <table className="min-w-full">
                    <thead className="bg-slate-100">
                      {staffTable.getHeaderGroups().map(hg => (
                        <tr key={hg.id}>
                          {hg.headers.map(header => (
                            <th key={header.id} className="px-3 py-2 text-left text-xs font-bold uppercase text-slate-600">
                              {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                            </th>
                          ))}
                        </tr>
                      ))}
                    </thead>
                    <tbody>
                      {staffTable.getRowModel().rows.map(row => (
                        <tr key={row.id} className="border-t">
                          {row.getVisibleCells().map(cell => (
                            <td key={cell.id} className="px-3 py-3 text-sm text-slate-700">
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {user.role === 'branch_director' && (
                <div className="premium-card p-6">
                  <h4 className="text-xl font-black mb-4">Add Staff</h4>

                  <div className="mb-4 p-4 border rounded-xl bg-slate-50">
                    <p className="font-semibold text-sm mb-2">Staff Photo Upload</p>
                    <div {...staffPhotoDrop.getRootProps()} className="p-4 border-2 border-dashed rounded-xl cursor-pointer bg-white">
                      <input {...staffPhotoDrop.getInputProps()} />
                      <p className="text-sm text-slate-600">Drag and drop photo, or click to choose</p>
                      {staffPhotoFile && <p className="text-xs text-slate-500 mt-2">Selected: {staffPhotoFile.name}</p>}
                    </div>
                  </div>

                  <form onSubmit={createStaff} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input placeholder="First Name" className="px-4 py-3 border rounded-xl" {...staffForm.register('first_name', { required: true })} />
                    <input placeholder="Last Name" className="px-4 py-3 border rounded-xl" {...staffForm.register('last_name', { required: true })} />
                    <input placeholder="Email" className="px-4 py-3 border rounded-xl" {...staffForm.register('email', { required: true })} />
                    <input placeholder="Mobile" className="px-4 py-3 border rounded-xl" {...staffForm.register('mobile', { required: true })} />
                    <input placeholder="Role" className="px-4 py-3 border rounded-xl" {...staffForm.register('role')} />
                    <input placeholder="Department" className="px-4 py-3 border rounded-xl" {...staffForm.register('department')} />
                    <input placeholder="Specialization" className="px-4 py-3 border rounded-xl" {...staffForm.register('specialization')} />
                    <input placeholder="Shift timings (9AM-6PM)" className="px-4 py-3 border rounded-xl" {...staffForm.register('shift_timings')} />
                    <input type="date" className="px-4 py-3 border rounded-xl" {...staffForm.register('date_of_joining')} />
                    <input placeholder="Temporary Password (optional)" className="px-4 py-3 border rounded-xl" {...staffForm.register('temporary_password')} />
                    <textarea placeholder="Address" className="md:col-span-2 px-4 py-3 border rounded-xl" {...staffForm.register('address')} />
                    <input placeholder="Emergency Contact" className="md:col-span-2 px-4 py-3 border rounded-xl" {...staffForm.register('emergency_contact')} />
                    <label className="md:col-span-2 flex items-center gap-2 text-sm">
                      <input type="checkbox" {...staffForm.register('auto_generate_password')} />
                      Auto-generate password if temporary password is not provided
                    </label>
                    <button className="md:col-span-2 px-4 py-3 rounded-xl bg-emerald-600 text-white font-bold">Create Staff</button>
                  </form>
                </div>
              )}

              {selectedStaff && (
                <div className="premium-card p-6 space-y-6">
                  <h4 className="text-xl font-black">Staff Profile: {selectedStaff.first_name} {selectedStaff.last_name}</h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <input value={selectedStaff.first_name || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, first_name: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.last_name || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, last_name: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.email || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, email: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.mobile || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, mobile: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.department || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, department: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.specialization || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, specialization: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.shift_timings || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, shift_timings: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <input value={selectedStaff.emergency_contact || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, emergency_contact: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                    <textarea value={selectedStaff.address || ''} onChange={e => setSelectedStaff((p: any) => ({ ...p, address: e.target.value }))} className="md:col-span-2 px-4 py-2 border rounded-xl" />
                  </div>
                  <button onClick={() => void updateStaff()} className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold">Save Staff Profile</button>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border rounded-2xl p-4 bg-slate-50">
                      <h5 className="font-black text-slate-900 mb-3">ID Card Preview</h5>
                      <div
                        ref={idCardRef}
                        className="bg-gradient-to-br from-blue-50 to-white rounded-xl border border-slate-300 p-5 shadow-sm"
                        style={{
                          width: `${ID_CARD_WIDTH_MM}mm`,
                          height: `${ID_CARD_HEIGHT_MM}mm`,
                          minWidth: `${ID_CARD_WIDTH_MM}mm`,
                          maxWidth: `${ID_CARD_WIDTH_MM}mm`,
                          minHeight: `${ID_CARD_HEIGHT_MM}mm`,
                          maxHeight: `${ID_CARD_HEIGHT_MM}mm`,
                          padding: `${ID_CARD_SAFE_MARGIN_MM}mm`,
                        }}
                      >
                        <div className="flex h-full items-center gap-5">
                          <div
                            className="overflow-hidden rounded-lg border border-slate-300 bg-slate-100 shrink-0"
                            style={{ width: '16mm', height: '16mm', minWidth: '16mm', minHeight: '16mm', maxWidth: '16mm', maxHeight: '16mm' }}
                          >
                            {selectedStaff.photo_path ? (
                              <img
                                src={`${API_BASE}/api/files/${selectedStaff.photo_path}`}
                                alt="Staff avatar"
                                style={{ width: '16mm', height: '16mm', minWidth: '16mm', minHeight: '16mm', maxWidth: '16mm', maxHeight: '16mm', objectFit: 'cover', display: 'block' }}
                              />
                            ) : (
                              <div className="h-full w-full flex items-center justify-center text-2xl">👤</div>
                            )}
                          </div>

                          <div className="flex h-full min-w-0 flex-1 flex-col justify-center">
                            <p className="font-black text-slate-900" style={{ fontSize: '20px', lineHeight: '24px' }}>{selectedStaff.first_name} {selectedStaff.last_name}</p>
                            <p className="mt-2 font-semibold text-slate-800" style={{ fontSize: '16px', lineHeight: '20px' }}>Role: {selectedStaff.role}</p>
                            <p className="mt-1 text-slate-500" style={{ fontSize: '14px', lineHeight: '18px' }}>{selectedStaff.department || 'Branch Staff'}</p>
                            <p className="mt-2 font-bold text-slate-800" style={{ fontSize: '16px', lineHeight: '20px' }}>Phone: {selectedStaff.mobile || '-'}</p>
                            <p className="mt-auto text-slate-600" style={{ fontSize: '12px', lineHeight: '16px' }}>Employee ID: {selectedStaff.staff_id}</p>
                          </div>
                        </div>

                        <div className="mt-3 flex items-center justify-between">
                          <p className="text-[11px] text-slate-500">Issue Date: {new Date().toLocaleDateString()}</p>
                          <p className="text-[11px] font-semibold text-slate-700">Valid till: 2027</p>
                        </div>
                      </div>

                      <div
                        ref={staffIdBackRef}
                        className="mt-3 bg-gradient-to-br from-blue-50 to-white rounded-xl border border-slate-300 p-5 shadow-sm"
                        style={{
                          width: `${ID_CARD_WIDTH_MM}mm`,
                          height: `${ID_CARD_HEIGHT_MM}mm`,
                          minWidth: `${ID_CARD_WIDTH_MM}mm`,
                          maxWidth: `${ID_CARD_WIDTH_MM}mm`,
                          minHeight: `${ID_CARD_HEIGHT_MM}mm`,
                          maxHeight: `${ID_CARD_HEIGHT_MM}mm`,
                          padding: `${ID_CARD_SAFE_MARGIN_MM}mm`,
                        }}
                      >
                        <div className="flex h-full items-center justify-between gap-5">
                          <div className="min-w-0 flex-1">
                            <p className="font-black text-slate-900" style={{ fontSize: '16px' }}>Contact Details</p>
                            <div className="mt-3 space-y-2 text-slate-700" style={{ fontSize: '14px', lineHeight: '18px' }}>
                              <p><span className="font-black">Address:</span> <span className="font-semibold">{selectedStaff.address || '-'}</span></p>
                              <p><span className="font-black">Phone:</span> <span className="font-semibold">{selectedStaff.mobile || '-'}</span></p>
                              <p><span className="font-black">Email:</span> <span className="font-semibold">{selectedStaff.email || '-'}</span></p>
                              <p><span className="font-black">Department:</span> <span className="font-semibold">{selectedStaff.department || '-'}</span></p>
                            </div>
                          </div>

                          <div
                            className="rounded border border-slate-300 bg-white p-2 shrink-0"
                            style={{ width: '18mm', height: '18mm', minWidth: '18mm', minHeight: '18mm', maxWidth: '18mm', maxHeight: '18mm', lineHeight: 0, padding: '2mm' }}
                          >
                            <QRCode
                              value={`STAFF_BACK|${selectedStaff.staff_id}|${selectedStaff.first_name}|${selectedStaff.last_name}|${selectedStaff.mobile}|${selectedStaff.email}`}
                              size={120}
                              style={{ width: '14mm', height: '14mm', display: 'block' }}
                            />
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => void downloadStaffIdCardPdf()}
                        className="mt-3 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-semibold"
                      >
                        Download PDF
                      </button>
                    </div>

                    <div className="border rounded-2xl p-4 bg-slate-50">
                      <h5 className="font-black text-slate-900 mb-3">Payslip Preview</h5>
                      <div ref={payslipRef} className="bg-white rounded-xl border p-4">
                        <div className="font-black text-slate-900 mb-2">Payslip - {selectedStaff.first_name} {selectedStaff.last_name}</div>
                        <div className="text-sm text-slate-600">Basic: INR {Number(salary.basic || 0).toLocaleString()}</div>
                        <div className="text-sm text-slate-600">Allowances: INR {Number(salary.allowances || 0).toLocaleString()}</div>
                        <div className="text-sm text-slate-600">Deductions: INR {Number(salary.deductions || 0).toLocaleString()}</div>
                        <div className="mt-2 font-bold text-slate-900">Net: INR {(Number(salary.basic || 0) + Number(salary.allowances || 0) - Number(salary.deductions || 0)).toLocaleString()}</div>
                      </div>
                      <button
                        onClick={() => void downloadElementPdf(payslipRef.current, `payslip-${selectedStaff.staff_id}.pdf`)}
                        className="mt-3 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-semibold"
                      >
                        Download PDF
                      </button>
                    </div>
                  </div>

                  {user.role === 'branch_director' && (
                    <div className="border rounded-2xl p-4 bg-slate-50 space-y-3">
                      <h5 className="font-black text-slate-900">Salary Management (Director Only)</h5>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <input type="number" placeholder="Basic" value={salary.basic} onChange={e => setSalary(prev => ({ ...prev, basic: Number(e.target.value || 0) }))} className="px-4 py-2 border rounded-xl" />
                        <input type="number" placeholder="Allowances" value={salary.allowances} onChange={e => setSalary(prev => ({ ...prev, allowances: Number(e.target.value || 0) }))} className="px-4 py-2 border rounded-xl" />
                        <input type="number" placeholder="Deductions" value={salary.deductions} onChange={e => setSalary(prev => ({ ...prev, deductions: Number(e.target.value || 0) }))} className="px-4 py-2 border rounded-xl" />
                        <input placeholder="Bank Name" value={salary.bank_name || ''} onChange={e => setSalary(prev => ({ ...prev, bank_name: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                        <input placeholder="Account Number" value={salary.account_number || ''} onChange={e => setSalary(prev => ({ ...prev, account_number: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                        <input placeholder="IFSC" value={salary.ifsc_code || ''} onChange={e => setSalary(prev => ({ ...prev, ifsc_code: e.target.value }))} className="px-4 py-2 border rounded-xl" />
                      </div>
                      <button onClick={() => void saveSalary()} className="px-4 py-2 rounded-xl bg-violet-600 text-white font-semibold">Save Salary Details</button>
                    </div>
                  )}

                  <div className="border rounded-2xl p-4 bg-slate-50">
                    <h5 className="font-black text-slate-900 mb-2">Performance Notes (Director Private)</h5>
                    <div className="flex gap-2">
                      <textarea value={performanceNote} onChange={e => setPerformanceNote(e.target.value)} className="flex-1 px-4 py-2 border rounded-xl" placeholder="Add feedback or notes..." />
                      <button onClick={() => void addPerformanceNote()} className="px-4 py-2 rounded-xl bg-amber-600 text-white text-sm font-semibold">Add</button>
                    </div>
                  </div>

                  <div className="border rounded-2xl p-4 bg-slate-50">
                    <h5 className="font-black text-slate-900 mb-2">Document Management</h5>
                    <div {...documentDrop.getRootProps()} className="p-4 border-2 border-dashed rounded-xl cursor-pointer bg-white">
                      <input {...documentDrop.getInputProps()} />
                      <p className="text-sm text-slate-600">Drag and drop a document, or click to choose</p>
                      {documentFile && <p className="text-xs text-slate-500 mt-2">Selected: {documentFile.name}</p>}
                    </div>
                    <button onClick={() => void uploadDocument()} className="mt-3 px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-semibold">Upload Document</button>
                    <div className="mt-3 space-y-2">
                      {(selectedStaff.documents || []).map((doc: any) => (
                        <a key={doc.id} href={`${API_BASE}/api/files/${doc.file_path}`} target="_blank" rel="noreferrer" className="block text-sm text-blue-700 underline">
                          {doc.file_name}
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {activeTab === 'attendance' && (
            <div className="premium-card p-6 space-y-4">
              <h3 className="text-2xl font-black text-slate-900">Attendance & Geo-tag Selfie</h3>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <select
                  className="px-4 py-2 border rounded-xl"
                  value={attendanceTargetId || ''}
                  onChange={e => {
                    const value = Number(e.target.value)
                    setAttendanceTargetId(value || null)
                    if (value) void loadMonthlyAttendance(value)
                  }}
                >
                  <option value="">Select staff</option>
                  {staffRows.map(st => <option key={st.id} value={st.id}>{st.staff_id} - {st.name}</option>)}
                </select>
                <input type="number" className="px-4 py-2 border rounded-xl" value={selectedMonth} onChange={e => setSelectedMonth(Number(e.target.value))} min={1} max={12} />
                <input type="number" className="px-4 py-2 border rounded-xl" value={selectedYear} onChange={e => setSelectedYear(Number(e.target.value))} min={2020} />
                <button onClick={() => attendanceTargetId && void loadMonthlyAttendance(attendanceTargetId)} className="px-4 py-2 rounded-xl bg-slate-800 text-white font-semibold">Load Month</button>
              </div>

              <div className="flex flex-wrap gap-3">
                <button onClick={captureGeo} className="px-4 py-2 rounded-xl bg-cyan-600 text-white font-semibold">Capture Location</button>
                <input type="file" accept="image/*" onChange={e => setSelfieFile(e.target.files?.[0] || null)} className="px-2 py-2 border rounded-xl bg-white" />
                <button onClick={() => void doClock('in')} className="px-4 py-2 rounded-xl bg-emerald-600 text-white font-semibold">Clock In</button>
                <button onClick={() => void doClock('out')} className="px-4 py-2 rounded-xl bg-amber-600 text-white font-semibold">Clock Out</button>
              </div>
              {geoCoords && <p className="text-xs text-slate-500">Location: {geoCoords.lat}, {geoCoords.lng}</p>}

              <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
                {monthlyAttendance.map((row) => {
                  const normalizedStatus = (row.status || '').toLowerCase()
                  return (
                  <div key={row.date} className={`p-2 rounded-xl text-center border ${
                    normalizedStatus === 'present' ? 'bg-emerald-50 border-emerald-200' :
                    normalizedStatus === 'leave' ? 'bg-blue-50 border-blue-200' :
                    normalizedStatus === 'holiday' ? 'bg-yellow-50 border-yellow-200' :
                    'bg-rose-50 border-rose-200'
                  }`}>
                    <div className="text-xs text-slate-500">{row.date.slice(8, 10)}</div>
                    <div className="text-xs font-bold capitalize">{row.status}</div>
                  </div>
                )})}
              </div>

              <div className="overflow-x-auto border rounded-xl bg-white">
                <table className="min-w-full">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs uppercase">Date</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Status</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Clock In</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Clock Out</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">In Photo</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Out Photo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyAttendance.map((row) => {
                      const inUrl = resolveAttendanceMediaUrl(row.clock_in_selfie_url)
                      const outUrl = resolveAttendanceMediaUrl(row.clock_out_selfie_url)

                      return (
                        <tr key={`detail-${row.date}`} className="border-t">
                          <td className="px-3 py-2 text-sm">{row.date}</td>
                          <td className="px-3 py-2 text-sm font-semibold">{row.status || '-'}</td>
                          <td className="px-3 py-2 text-sm">{row.clock_in_time ? new Date(row.clock_in_time).toLocaleTimeString() : '-'}</td>
                          <td className="px-3 py-2 text-sm">{row.clock_out_time ? new Date(row.clock_out_time).toLocaleTimeString() : '-'}</td>
                          <td className="px-3 py-2 text-sm">
                            {inUrl ? (
                              <a href={inUrl} target="_blank" rel="noreferrer">
                                <img src={inUrl} alt="Clock in" className="h-12 w-12 rounded-lg border object-cover" />
                              </a>
                            ) : '-'}
                          </td>
                          <td className="px-3 py-2 text-sm">
                            {outUrl ? (
                              <a href={outUrl} target="_blank" rel="noreferrer">
                                <img src={outUrl} alt="Clock out" className="h-12 w-12 rounded-lg border object-cover" />
                              </a>
                            ) : '-'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'leave' && (
            <div className="premium-card p-6 space-y-4">
              <h3 className="text-2xl font-black text-slate-900">Leave Management</h3>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <select value={leaveApplyStaffId || ''} onChange={e => setLeaveApplyStaffId(Number(e.target.value))} className="px-4 py-2 border rounded-xl">
                  <option value="">Select Staff</option>
                  {staffRows.map(st => <option key={st.id} value={st.id}>{st.staff_id} - {st.name}</option>)}
                </select>
                <select value={leaveType} onChange={e => setLeaveType(e.target.value)} className="px-4 py-2 border rounded-xl">
                  <option value="casual">Casual</option>
                  <option value="sick">Sick</option>
                  <option value="earned">Earned</option>
                  <option value="unpaid">Unpaid</option>
                </select>
                <input type="date" value={leaveStart} onChange={e => setLeaveStart(e.target.value)} className="px-4 py-2 border rounded-xl" />
                <input type="date" value={leaveEnd} onChange={e => setLeaveEnd(e.target.value)} className="px-4 py-2 border rounded-xl" />
                <button onClick={() => void applyLeave()} className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold">Apply Leave</button>
              </div>
              <textarea value={leaveReason} onChange={e => setLeaveReason(e.target.value)} placeholder="Reason" className="w-full px-4 py-2 border rounded-xl" />

              <div className="overflow-x-auto border rounded-xl">
                <table className="min-w-full">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs uppercase">Staff</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Type</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Dates</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Reason</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Status</th>
                      <th className="px-3 py-2 text-left text-xs uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaveRequests.map(req => (
                      <tr key={req.id} className="border-t">
                        <td className="px-3 py-2 text-sm">{req.staff_id}</td>
                        <td className="px-3 py-2 text-sm capitalize">{req.leave_type}</td>
                        <td className="px-3 py-2 text-sm">{String(req.start_date).slice(0, 10)} to {String(req.end_date).slice(0, 10)}</td>
                        <td className="px-3 py-2 text-sm">{req.reason || '-'}</td>
                        <td className="px-3 py-2 text-sm capitalize">{req.status}</td>
                        <td className="px-3 py-2 text-sm">
                          {req.status === 'pending' ? (
                            <div className="flex gap-2">
                              <button onClick={() => void decideLeave(req.id, 'approved')} className="px-3 py-1 rounded-lg bg-emerald-600 text-white text-xs">Approve</button>
                              <button onClick={() => void decideLeave(req.id, 'rejected')} className="px-3 py-1 rounded-lg bg-rose-600 text-white text-xs">Reject</button>
                            </div>
                          ) : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'reports' && (
            <div className="premium-card p-6 space-y-4">
              <h3 className="text-2xl font-black text-slate-900">Reports & Notifications</h3>

              <div className="flex flex-wrap gap-3">
                <p className="rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-700">
                  Attendance exports are available as PDF from Detailed History.
                </p>
              </div>

              {user.role === 'branch_director' && (
                <div className="border rounded-xl p-4 bg-slate-50">
                  <p className="font-bold mb-2">In-app Notifications</p>
                  <div className="space-y-2">
                    {notifications.length === 0 ? (
                      <p className="text-sm text-slate-500">No notifications</p>
                    ) : notifications.map(n => (
                      <div key={n.id} className="p-3 rounded-xl bg-white border flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold">{n.title}</p>
                          <p className="text-xs text-slate-500">{n.message}</p>
                        </div>
                        {!n.is_read && (
                          <button
                            onClick={async () => {
                              await axios.put(`${API_BASE}/api/director/notifications/${n.id}/read`, {}, requestConfig)
                              void loadNotifications()
                            }}
                            className="px-3 py-1 rounded-lg bg-slate-900 text-white text-xs"
                          >
                            Mark Read
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'payments' && (
            <div className="premium-card p-6">
              <BranchPaymentsDashboard />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
