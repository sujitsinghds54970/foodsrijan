import { useMemo, useState, useEffect, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import {
  ColumnDef,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import axios from 'axios'
import toast from 'react-hot-toast'
import { MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

import { useAuth } from '../../contexts/AuthContext'
import DoctorFormModal, { DoctorFormValues } from './DoctorFormModal'
import BulkPdfModal from './BulkPdfModal'
import { DoctorItem, PerformanceResponse, ShareResultItem } from './types'

const columnHelper = createColumnHelper<DoctorItem>()

type BroadcastValues = {
  message: string
  specialization?: string
  city?: string
  to_all: boolean
}

type PortalLoginValues = {
  username: string
  password: string
}

const mapCenter: [number, number] = [25.5941, 85.1376]

export default function DoctorManagementCRMModule() {
  const { user, token } = useAuth()
  const [doctors, setDoctors] = useState<DoctorItem[]>([])
  const [loading, setLoading] = useState(false)
  const [specializationFilter, setSpecializationFilter] = useState('')
  const [cityFilter, setCityFilter] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [editingDoctor, setEditingDoctor] = useState<DoctorItem | null>(null)
  const [showBulkModal, setShowBulkModal] = useState(false)

  const [performance, setPerformance] = useState<PerformanceResponse | null>(null)
  const [activeTab, setActiveTab] = useState<'list' | 'performance' | 'broadcast' | 'dashboard' | 'portal' | 'map'>('list')
  const [selectedIds, setSelectedIds] = useState<Record<number, boolean>>({})

  const [broadcastResults, setBroadcastResults] = useState<Array<{ doctor_name: string; email_link?: string; whatsapp_link?: string }>>([])

  const [portalToken, setPortalToken] = useState('')
  const [portalDoctor, setPortalDoctor] = useState<any>(null)
  const [portalReferrals, setPortalReferrals] = useState<any[]>([])

  const API_BASE =
    process.env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token])

  const broadcastForm = useForm<BroadcastValues>({
    defaultValues: {
      message: '',
      specialization: '',
      city: '',
      to_all: true,
    },
  })

  const portalLoginForm = useForm<PortalLoginValues>({
    defaultValues: { username: '', password: '' },
  })

  const selectedDoctors = useMemo(
    () => doctors.filter(d => selectedIds[d.id]),
    [doctors, selectedIds],
  )

  const loadDoctors = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (specializationFilter.trim()) params.append('specialization', specializationFilter.trim())
      if (cityFilter.trim()) params.append('city', cityFilter.trim())

      const res = await axios.get(`${API_BASE}/api/doctors?${params.toString()}`, requestConfig)
      setDoctors(Array.isArray(res.data) ? res.data : [])
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to load doctors')
    } finally {
      setLoading(false)
    }
  }, [token, specializationFilter, cityFilter, API_BASE, requestConfig])

  const loadPerformance = useCallback(async () => {
    if (!token) return
    try {
      const res = await axios.get(`${API_BASE}/api/doctors/performance`, requestConfig)
      setPerformance(res.data)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to load performance')
    }
  }, [token, API_BASE, requestConfig])

  useEffect(() => {
    void loadDoctors()
    void loadPerformance()
  }, [token, loadDoctors, loadPerformance])

  const submitDoctor = async (values: DoctorFormValues) => {
    const payload = {
      ...values,
      years_of_experience: values.years_of_experience ?? null,
      latitude: values.latitude ?? null,
      longitude: values.longitude ?? null,
    }

    try {
      if (editingDoctor) {
        await axios.put(`${API_BASE}/api/doctors/${editingDoctor.id}`, payload, requestConfig)
        toast.success('Doctor updated')
      } else {
        await axios.post(`${API_BASE}/api/doctors`, payload, requestConfig)
        toast.success('Doctor created')
      }
      setEditingDoctor(null)
      await loadDoctors()
      await loadPerformance()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save doctor')
      throw err
    }
  }

  const removeDoctor = useCallback(async (id: number) => {
    try {
      await axios.delete(`${API_BASE}/api/doctors/${id}`, requestConfig)
      toast.success('Doctor deleted')
      await loadDoctors()
      await loadPerformance()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to delete doctor')
    }
  }, [API_BASE, requestConfig, loadDoctors, loadPerformance])

  const handleBulkSend = async (files: File[]): Promise<ShareResultItem[]> => {
    const fd = new FormData()
    fd.append('doctor_ids', JSON.stringify(selectedDoctors.map(d => d.id)))
    files.forEach(file => fd.append('files', file))

    const res = await axios.post(`${API_BASE}/api/doctors/send-pdfs`, fd, {
      headers: {
        ...requestConfig.headers,
        'Content-Type': 'multipart/form-data',
      },
    })

    const items: ShareResultItem[] = res.data?.items || []
    if (items.length > 0) {
      toast.success('Bulk links generated')
    }
    return items
  }

  const submitBroadcast = broadcastForm.handleSubmit(async values => {
    try {
      const payload = {
        message: values.message,
        specialization: values.specialization || null,
        city: values.city || null,
        doctor_ids: values.to_all ? null : selectedDoctors.map(d => d.id),
        channels: ['email', 'whatsapp'],
      }

      const res = await axios.post(`${API_BASE}/api/doctors/broadcast`, payload, requestConfig)
      setBroadcastResults(res.data?.items || [])
      toast.success(`Broadcast ready for ${res.data?.total_recipients || 0} doctors`)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to build broadcast links')
    }
  })

  const handlePortalLogin = portalLoginForm.handleSubmit(async values => {
    try {
      const loginRes = await axios.post(`${API_BASE}/api/doctors/portal/login`, values)
      const tokenValue: string = loginRes.data?.token
      setPortalToken(tokenValue)

      const [meRes, referralsRes] = await Promise.all([
        axios.get(`${API_BASE}/api/doctors/portal/me?token=${encodeURIComponent(tokenValue)}`),
        axios.get(`${API_BASE}/api/doctors/portal/referrals?token=${encodeURIComponent(tokenValue)}`),
      ])

      setPortalDoctor(meRes.data)
      setPortalReferrals(Array.isArray(referralsRes.data) ? referralsRes.data : [])
      toast.success('Doctor portal session started')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Portal login failed')
    }
  })

  const columns = useMemo<ColumnDef<DoctorItem, any>[]>(() => [
    columnHelper.display({
      id: 'select',
      header: () => (
        <input
          type="checkbox"
          checked={doctors.length > 0 && doctors.every(d => !!selectedIds[d.id])}
          onChange={e => {
            const checked = e.target.checked
            const next: Record<number, boolean> = {}
            doctors.forEach(d => {
              next[d.id] = checked
            })
            setSelectedIds(next)
          }}
        />
      ),
      cell: info => (
        <input
          type="checkbox"
          checked={!!selectedIds[info.row.original.id]}
          onChange={e => {
            const checked = e.target.checked
            setSelectedIds(prev => ({ ...prev, [info.row.original.id]: checked }))
          }}
        />
      ),
      size: 36,
      minSize: 36,
    }),
    columnHelper.accessor('full_name', { header: 'Doctor Name', size: 220 }),
    columnHelper.accessor('specialization', { header: 'Specialization', size: 150 }),
    columnHelper.accessor('city', { header: 'City', size: 110 }),
    columnHelper.accessor('mobile', { header: 'Mobile', size: 120 }),
    columnHelper.accessor('email', { header: 'Email', size: 180 }),
    columnHelper.accessor('monthly_referrals', { header: 'Referrals', size: 85 }),
    columnHelper.accessor('monthly_revenue', {
      header: 'Revenue',
      size: 115,
      cell: info => <span>INR {Number(info.getValue() || 0).toLocaleString()}</span>,
    }),
    columnHelper.accessor('monthly_commission', {
      header: 'Commission',
      size: 130,
      cell: info => <span>INR {Number(info.getValue() || 0).toLocaleString()}</span>,
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Actions',
      size: 180,
      cell: info => (
        <div className="flex gap-2">
          <button
            className="px-2 py-1 rounded bg-blue-600 text-white text-xs"
            onClick={() => {
              setEditingDoctor(info.row.original)
              setShowForm(true)
            }}
          >
            Edit
          </button>
          <button
            className="px-2 py-1 rounded bg-rose-600 text-white text-xs"
            onClick={() => void removeDoctor(info.row.original.id)}
          >
            Delete
          </button>
        </div>
      ),
    }),
  ], [doctors, selectedIds, removeDoctor])

  const table = useReactTable({
    data: doctors,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!user || !['branch_director', 'branch_admin', 'super_admin'].includes(user.role)) {
    return <div className="premium-card p-6">Access denied</div>
  }

  return (
    <div className="space-y-6">
      <div className="premium-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-black text-slate-900">Doctor Management & CRM</h2>
            <p className="text-slate-500 text-sm">Branch leadership CRM for referring doctors, marketing, reports, and growth insights.</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-bold" onClick={() => { setEditingDoctor(null); setShowForm(true) }}>
              Add Doctor
            </button>
            <button
              className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-bold disabled:opacity-50"
              disabled={selectedDoctors.length === 0}
              onClick={() => setShowBulkModal(true)}
            >
              Send Bulk PDF
            </button>
          </div>
        </div>
      </div>

      <div className="premium-card p-4">
        <div className="flex flex-wrap gap-2">
          {[
            ['list', 'Doctor List'],
            ['performance', 'Performance'],
            ['dashboard', 'Director Dashboard'],
            ['broadcast', 'Marketing Broadcast'],
            ['map', 'Geo Mapping'],
            ['portal', 'Doctor Self-Service'],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key as any)}
              className={`px-3 py-2 rounded-lg text-sm font-bold ${activeTab === key ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'list' && (
        <div className="premium-card p-6 space-y-4">
          <div className="flex flex-wrap gap-3">
            <input
              value={specializationFilter}
              onChange={e => setSpecializationFilter(e.target.value)}
              placeholder="Filter by Specialization"
              className="px-3 py-2 border rounded-lg"
            />
            <input
              value={cityFilter}
              onChange={e => setCityFilter(e.target.value)}
              placeholder="Filter by City"
              className="px-3 py-2 border rounded-lg"
            />
            <button className="px-3 py-2 bg-slate-700 text-white rounded-lg" onClick={() => void loadDoctors()}>Apply</button>
          </div>

          <div className="overflow-x-auto border rounded-xl">
            <table className="w-full min-w-[1100px]">
              <thead className="bg-slate-100">
                {table.getHeaderGroups().map(hg => (
                  <tr key={hg.id}>
                    {hg.headers.map(header => (
                      <th key={header.id} className="text-left text-xs font-black text-slate-700 p-2 border-b">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {loading ? (
                  <tr><td className="p-3 text-sm text-slate-500" colSpan={10}>Loading...</td></tr>
                ) : (
                  table.getRowModel().rows.map(row => (
                    <tr key={row.id} className="hover:bg-slate-50">
                      {row.getVisibleCells().map(cell => (
                        <td key={cell.id} className="p-2 border-b text-xs text-slate-700 align-top">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'performance' && (
        <div className="premium-card p-6 space-y-4">
          <h3 className="text-xl font-black text-slate-900">Referral & Commission Tracking</h3>
          <div className="overflow-x-auto border rounded-xl">
            <table className="w-full min-w-[760px]">
              <thead className="bg-slate-100">
                <tr>
                  <th className="text-left p-2 text-xs font-black">Doctor</th>
                  <th className="text-left p-2 text-xs font-black">Specialization</th>
                  <th className="text-left p-2 text-xs font-black">Referrals</th>
                  <th className="text-left p-2 text-xs font-black">Revenue</th>
                  <th className="text-left p-2 text-xs font-black">Commission %</th>
                  <th className="text-left p-2 text-xs font-black">Commission</th>
                </tr>
              </thead>
              <tbody>
                {(performance?.doctor_performance || []).map(item => (
                  <tr key={item.doctor_id} className="border-b">
                    <td className="p-2 text-sm">{item.doctor_name}</td>
                    <td className="p-2 text-sm">{item.specialization || '-'}</td>
                    <td className="p-2 text-sm">{item.referrals}</td>
                    <td className="p-2 text-sm">INR {item.revenue.toLocaleString()}</td>
                    <td className="p-2 text-sm">{item.commission_percentage}%</td>
                    <td className="p-2 text-sm">INR {item.commission.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'dashboard' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="premium-card p-4 bg-gradient-to-br from-blue-50 to-cyan-50">
            <p className="text-xs uppercase tracking-wide text-blue-700 font-black">Total Revenue from Doctor Referrals</p>
            <p className="text-2xl font-black text-slate-900 mt-2">INR {Number(performance?.total_revenue_from_referrals || 0).toLocaleString()}</p>
          </div>
          <div className="premium-card p-4 bg-gradient-to-br from-amber-50 to-orange-50">
            <p className="text-xs uppercase tracking-wide text-amber-700 font-black">Pending Reports to Send</p>
            <p className="text-2xl font-black text-slate-900 mt-2">{performance?.pending_reports_to_send || 0}</p>
          </div>
          <div className="premium-card p-4 bg-gradient-to-br from-emerald-50 to-teal-50">
            <p className="text-xs uppercase tracking-wide text-emerald-700 font-black">Top 5 Referring Doctors</p>
            <div className="mt-2 space-y-1 text-sm text-slate-700">
              {(performance?.top_5_referring_doctors || []).map(item => (
                <p key={item.doctor_id}>{item.doctor_name} - INR {item.revenue.toLocaleString()}</p>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'broadcast' && (
        <div className="premium-card p-6 space-y-4">
          <h3 className="text-xl font-black text-slate-900">Marketing Broadcasts</h3>
          <form onSubmit={submitBroadcast} className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <textarea
              className="px-3 py-2 border rounded-lg md:col-span-2"
              placeholder="Write marketing message..."
              {...broadcastForm.register('message', { required: true })}
            />
            <input className="px-3 py-2 border rounded-lg" placeholder="Specialization filter (optional)" {...broadcastForm.register('specialization')} />
            <input className="px-3 py-2 border rounded-lg" placeholder="City filter (optional)" {...broadcastForm.register('city')} />
            <label className="inline-flex items-center gap-2 text-sm text-slate-700 md:col-span-2">
              <input type="checkbox" {...broadcastForm.register('to_all')} /> Send to all doctors (ignore selected rows)
            </label>
            <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-bold w-max">Generate Broadcast Links</button>
          </form>

          {broadcastResults.length > 0 && (
            <div className="space-y-2 pt-2">
              {broadcastResults.map((row, idx) => (
                <div key={`${row.doctor_name}-${idx}`} className="border rounded-lg p-3">
                  <p className="font-semibold text-slate-800">{row.doctor_name}</p>
                  <div className="flex gap-2 mt-2">
                    {row.email_link && <a href={row.email_link} target="_blank" rel="noreferrer" className="px-3 py-1 rounded bg-indigo-600 text-white text-xs">Open Email</a>}
                    {row.whatsapp_link && <a href={row.whatsapp_link} target="_blank" rel="noreferrer" className="px-3 py-1 rounded bg-emerald-600 text-white text-xs">Open WhatsApp</a>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'map' && (
        <div className="premium-card p-6">
          <h3 className="text-xl font-black text-slate-900 mb-4">Doctor Geo Mapping</h3>
          <div className="h-[500px] rounded-xl overflow-hidden border">
            <MapContainer center={mapCenter} zoom={11} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {doctors
                .filter(d => typeof d.latitude === 'number' && typeof d.longitude === 'number')
                .map(d => (
                  <Marker key={d.id} position={[Number(d.latitude), Number(d.longitude)]}>
                    <Popup>
                      <div className="text-sm">
                        <p className="font-bold">{d.full_name}</p>
                        <p>{d.specialization || 'General'}</p>
                        <p>{d.city || '-'}</p>
                      </div>
                    </Popup>
                  </Marker>
                ))}
            </MapContainer>
          </div>
          <p className="text-xs text-slate-500 mt-2">Add latitude/longitude in doctor profile to display markers.</p>
        </div>
      )}

      {activeTab === 'portal' && (
        <div className="premium-card p-6 space-y-4">
          <h3 className="text-xl font-black text-slate-900">Doctor Self-Service Portal (Extension)</h3>
          <form onSubmit={handlePortalLogin} className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input className="px-3 py-2 border rounded-lg" placeholder="Portal Username" {...portalLoginForm.register('username', { required: true })} />
            <input type="password" className="px-3 py-2 border rounded-lg" placeholder="Portal Password" {...portalLoginForm.register('password', { required: true })} />
            <button className="px-4 py-2 rounded-lg bg-blue-600 text-white font-bold">Login</button>
          </form>

          {portalToken && portalDoctor && (
            <div className="space-y-3">
              <div className="rounded-lg border p-3 bg-slate-50">
                <p className="font-semibold text-slate-800">Signed in as {portalDoctor.full_name}</p>
                <p className="text-xs text-slate-500">Token: {portalToken.slice(0, 12)}...</p>
              </div>

              <div className="overflow-x-auto border rounded-xl">
                <table className="w-full min-w-[720px]">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="p-2 text-left text-xs font-black">Patient</th>
                      <th className="p-2 text-left text-xs font-black">Mobile</th>
                      <th className="p-2 text-left text-xs font-black">Referred On</th>
                      <th className="p-2 text-left text-xs font-black">Revenue</th>
                      <th className="p-2 text-left text-xs font-black">Report Sent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portalReferrals.map(item => (
                      <tr key={item.id} className="border-b">
                        <td className="p-2 text-sm">{item.patient_name}</td>
                        <td className="p-2 text-sm">{item.patient_mobile || '-'}</td>
                        <td className="p-2 text-sm">{String(item.referred_on || '').slice(0, 10)}</td>
                        <td className="p-2 text-sm">INR {Number(item.revenue_amount || 0).toLocaleString()}</td>
                        <td className="p-2 text-sm">{item.report_sent ? 'Yes' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <DoctorFormModal
        open={showForm}
        initialDoctor={editingDoctor}
        onClose={() => {
          setShowForm(false)
          setEditingDoctor(null)
        }}
        onSubmit={submitDoctor}
      />

      <BulkPdfModal
        open={showBulkModal}
        selectedDoctors={selectedDoctors}
        onClose={() => setShowBulkModal(false)}
        onSend={handleBulkSend}
      />
    </div>
  )
}
