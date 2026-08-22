import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip, LineChart, Line, XAxis, YAxis, CartesianGrid, Legend } from 'recharts'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'

type LISHealth = {
  score: number
  status: string
  average_tat_minutes: number
  qc_failure_rate: number
  sample_rejection_rate: number
  pending_menu_items: number
  branch_name?: string | null
  last_updated: string
}

type LISStats = {
  todays_test_volume: number
  average_tat_minutes: number
  tat_breakdown: Record<string, number>
  pending_menu_items_count: number
  pending_by_department: Record<string, number>
  sample_rejection_rate: number
  qc_status: string
  delayed_samples: number
  last_updated: string
}

type LISOrder = {
  id: number
  order_number: string
  source: string
  patient_name: string
  patient_code?: string | null
  doctor_name?: string | null
  priority: string
  status: string
  expected_tat_minutes: number
  due_at?: string | null
  menu_items: Array<Record<string, unknown>>
  created_at: string
}

type LISSample = {
  id: number
  order_id: number
  sample_code: string
  barcode_value: string
  barcode_image_base64?: string | null
  sample_type: string
  department: string
  analyzer_name?: string | null
  storage_location?: string | null
  status: string
  rejection_reason?: string | null
  registered_at?: string | null
  expected_completion_at?: string | null
}

type LIPanel = {
  id: number
  panel_name: string
  description?: string | null
  menu_items: Array<{ test_name?: string }>
}

type CatalogItem = {
  id: number
  test_code: string
  test_name: string
  department: string
  sample_type: string
  turnaround_minutes: number
}

type CustomerSuggestion = { id: string; name: string; patient_id?: string }
type StaffSuggestion = { id: string; name: string }

type QCDashboard = {
  summary: { pass: number; warning: number; out_of_control: number }
  westgard_findings: Array<{ test_code: string; rule: string; level: string; message: string; at: string }>
  trend: Array<{ time: string; test_code: string; status: string; score: number }>
}

type InventoryOverview = {
  total_items: number
  low_stock_alerts: Array<{ item_id: number; item_name: string; department: string; current_qty: number; min_threshold: number }>
  lot_expiry_tracking: Array<{ item_id: number; item_name: string; lot_number?: string | null; expiry_date?: string | null; days_to_expiry?: number | null }>
}

type ConsumptionAnalytics = {
  usage_by_test: Array<{ name: string; quantity: number }>
  usage_by_department: Array<{ name: string; quantity: number }>
  usage_by_analyzer: Array<{ name: string; quantity: number }>
  cost_per_test: Array<{ name: string; cost: number }>
}

type PerformanceAnalytics = {
  departments: Array<{ department: string; volume: number; reported: number; avg_tat_minutes: number; productivity_percent: number; qc_status: string }>
}

type TATAnalytics = {
  tat_by_day_of_week: Array<{ day: string; avg_tat_minutes: number }>
  tat_by_priority: Array<{ priority: string; avg_tat_minutes: number }>
  tat_by_department: Array<{ department: string; avg_tat_minutes: number }>
  predicted_breaches: Array<{ sample_id: number; sample_code: string; department: string; predicted_delay_minutes: number }>
}

type FinancialAnalytics = {
  revenue: number
  reagent_cost: number
  profitability: number
  margin_percent: number
  cost_per_test: number
}

type AIInsights = {
  tat_prediction: Array<{ sample_code: string; department: string; predicted_breach: boolean }>
  demand_forecast: Array<{ day: string; forecasted_volume: number }>
  instrument_failure_prediction: Array<{ analyzer_name: string; failure_risk: string; qc_fail_rate: number }>
  anomaly_detection: Array<{ type: string; message: string }>
}

type OrderArchive = Array<{ id: number; report_number: string; version: number; template_name: string; status: string; signed_by?: string | null; created_at?: string | null }>

const normalizeApiBase = (rawBase: string): string => {
  const trimmed = (rawBase || '').trim()
  if (!trimmed) return ''
  try {
    const parsed = new URL(trimmed)
    if (parsed.hostname === 'localhost') {
      parsed.hostname = '127.0.0.1'
    }
    return parsed.toString().replace(/\/$/, '')
  } catch {
    return trimmed.replace('://localhost', '://127.0.0.1').replace(/\/$/, '')
  }
}

const configuredApiBase = normalizeApiBase((process as any).env.REACT_APP_API_BASE_URL || '')
const API_BASE = configuredApiBase ||
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

function authHeaders(token?: string) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function colorForHealth(score: number) {
  if (score > 80) return '#22c55e'
  if (score >= 50) return '#f59e0b'
  return '#ef4444'
}

function statusTone(status: string) {
  if (status === 'Ordered') return 'bg-emerald-100 text-emerald-700'
  if (status === 'Rejected') return 'bg-rose-100 text-rose-700'
  if (status === 'Delayed') return 'bg-orange-100 text-orange-700'
  if (status === 'QC Passed') return 'bg-blue-100 text-blue-700'
  if (status === 'In Processing') return 'bg-violet-100 text-violet-700'
  return 'bg-slate-100 text-slate-700'
}

function formatDate(value?: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString()
}

const orderColumnHelper = createColumnHelper<LISOrder>()

export default function BranchLISDashboard() {
  const { token } = useAuth()
  const requestConfig = useMemo(() => ({ headers: authHeaders(token) }), [token])

  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<LISHealth | null>(null)
  const [stats, setStats] = useState<LISStats | null>(null)
  const [orders, setOrders] = useState<LISOrder[]>([])
  const [samples, setSamples] = useState<LISSample[]>([])
  const [panels, setPanels] = useState<LIPanel[]>([])
  const [catalog, setCatalog] = useState<CatalogItem[]>([])
  const [barcodeImage, setBarcodeImage] = useState<string | null>(null)
  const [qcDashboard, setQcDashboard] = useState<QCDashboard | null>(null)
  const [inventoryOverview, setInventoryOverview] = useState<InventoryOverview | null>(null)
  const [consumptionAnalytics, setConsumptionAnalytics] = useState<ConsumptionAnalytics | null>(null)
  const [performanceAnalytics, setPerformanceAnalytics] = useState<PerformanceAnalytics | null>(null)
  const [tatAnalytics, setTatAnalytics] = useState<TATAnalytics | null>(null)
  const [financialAnalytics, setFinancialAnalytics] = useState<FinancialAnalytics | null>(null)
  const [aiInsights, setAiInsights] = useState<AIInsights | null>(null)
  const [reportArchive, setOrderArchive] = useState<OrderArchive>([])

  const [patientQuery, setCustomerQuery] = useState('')
  const [doctorQuery, setStaffQuery] = useState('')
  const [patientHits, setCustomerHits] = useState<CustomerSuggestion[]>([])
  const [doctorHits, setStaffHits] = useState<StaffSuggestion[]>([])

  const [orderForm, setOrderForm] = useState({
    patient_id: '',
    patient_name: '',
    patient_code: '',
    doctor_name: '',
    priority: 'Routine',
    panel_id: '',
    selected_test_id: '',
    notes: '',
  })
  const loadInFlightRef = useRef(false)

  const loadDashboard = useCallback(async () => {
    if (!token) return
    if (loadInFlightRef.current) return
    loadInFlightRef.current = true
    setLoading(true)
    try {
      const [
        healthRes,
        statsRes,
        ordersRes,
        samplesRes,
        panelsRes,
        catalogRes,
        qcRes,
        inventoryRes,
        consumptionRes,
        perfRes,
        tatRes,
        financialRes,
        aiRes,
        archiveRes,
      ] = await Promise.allSettled([
        axios.get<LISHealth>(`${API_BASE}/api/lis/health-score`, requestConfig),
        axios.get<LISStats>(`${API_BASE}/api/lis/stats`, requestConfig),
        axios.get<LISOrder[]>(`${API_BASE}/api/lis/orders`, requestConfig),
        axios.get<LISSample[]>(`${API_BASE}/api/lis/samples`, requestConfig),
        axios.get<LIPanel[]>(`${API_BASE}/api/lis/panels`, requestConfig),
        axios.get<CatalogItem[]>(`${API_BASE}/api/lis/catalog`, requestConfig),
        axios.get<QCDashboard>(`${API_BASE}/api/lis/qc/dashboard`, requestConfig),
        axios.get<InventoryOverview>(`${API_BASE}/api/lis/inventory/overview`, requestConfig),
        axios.get<ConsumptionAnalytics>(`${API_BASE}/api/lis/inventory/consumption-analytics`, requestConfig),
        axios.get<PerformanceAnalytics>(`${API_BASE}/api/lis/analytics/performance`, requestConfig),
        axios.get<TATAnalytics>(`${API_BASE}/api/lis/analytics/tat`, requestConfig),
        axios.get<FinancialAnalytics>(`${API_BASE}/api/lis/analytics/financial`, requestConfig),
        axios.get<AIInsights>(`${API_BASE}/api/lis/analytics/ai-insights`, requestConfig),
        axios.get<OrderArchive>(`${API_BASE}/api/lis/orders/archive`, requestConfig),
      ])

      let failedWidgets = 0
      const markFailure = () => {
        failedWidgets += 1
      }

      if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data)
      else markFailure()
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data)
      else markFailure()
      if (ordersRes.status === 'fulfilled') setOrders(ordersRes.value.data)
      else markFailure()
      if (samplesRes.status === 'fulfilled') setSamples(samplesRes.value.data)
      else markFailure()
      if (panelsRes.status === 'fulfilled') setPanels(panelsRes.value.data)
      else markFailure()
      if (catalogRes.status === 'fulfilled') setCatalog(catalogRes.value.data)
      else markFailure()
      if (qcRes.status === 'fulfilled') setQcDashboard(qcRes.value.data)
      else markFailure()
      if (inventoryRes.status === 'fulfilled') setInventoryOverview(inventoryRes.value.data)
      else markFailure()
      if (consumptionRes.status === 'fulfilled') setConsumptionAnalytics(consumptionRes.value.data)
      else markFailure()
      if (perfRes.status === 'fulfilled') setPerformanceAnalytics(perfRes.value.data)
      else markFailure()
      if (tatRes.status === 'fulfilled') setTatAnalytics(tatRes.value.data)
      else markFailure()
      if (financialRes.status === 'fulfilled') setFinancialAnalytics(financialRes.value.data)
      else markFailure()
      if (aiRes.status === 'fulfilled') setAiInsights(aiRes.value.data)
      else markFailure()
      if (archiveRes.status === 'fulfilled') setOrderArchive(archiveRes.value.data)
      else markFailure()

      const rejected = [
        healthRes,
        statsRes,
        ordersRes,
        samplesRes,
        panelsRes,
        catalogRes,
        qcRes,
        inventoryRes,
        consumptionRes,
        perfRes,
        tatRes,
        financialRes,
        aiRes,
        archiveRes,
      ].filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      const networkFailures = rejected.filter((result) => !result.reason?.response).length

      if (failedWidgets > 0) {
        if (networkFailures > 0 && failedWidgets === 14) {
          toast.error('LIS load failed: backend is unreachable. Please restart backend and retry.', { id: 'lis-dashboard-network-failed' })
        } else {
          toast.error(`LIS loaded partially: ${failedWidgets} widget${failedWidgets > 1 ? 's' : ''} failed`, { id: 'lis-dashboard-partial-failed' })
        }
      }
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message
      toast.error(detail ? `Unable to load LIS dashboard: ${detail}` : 'Unable to load LIS dashboard', { id: 'lis-dashboard-load-failed' })
    } finally {
      setLoading(false)
      loadInFlightRef.current = false
    }
  }, [requestConfig, token])

  useEffect(() => {
    if (!token) return
    loadDashboard()
  }, [loadDashboard, token])

  useEffect(() => {
    if (!token || patientQuery.trim().length < 2) {
      setCustomerHits([])
      return
    }
    const id = setTimeout(async () => {
      try {
        const { data } = await axios.get<CustomerSuggestion[]>(`${API_BASE}/api/customers/search`, {
          ...requestConfig,
          params: { q: patientQuery.trim() },
        })
        setCustomerHits(data)
      } catch {
        setCustomerHits([])
      }
    }, 200)
    return () => clearTimeout(id)
  }, [patientQuery, requestConfig, token])

  useEffect(() => {
    if (!token || doctorQuery.trim().length < 2) {
      setStaffHits([])
      return
    }
    const id = setTimeout(async () => {
      try {
        const { data } = await axios.get<StaffSuggestion[]>(`${API_BASE}/api/staff/search`, {
          ...requestConfig,
          params: { q: doctorQuery.trim() },
        })
        setStaffHits(data)
      } catch {
        setStaffHits([])
      }
    }, 200)
    return () => clearTimeout(id)
  }, [doctorQuery, requestConfig, token])

  const submitOrder = useCallback(async () => {
    if (!token) return
    const selectedPanelId = Number(orderForm.panel_id || 0)
    const selectedMenuItem = catalog.find((item) => String(item.id) === orderForm.selected_test_id)
    const numericCustomerId = Number(orderForm.patient_id)
    const resolvedCustomerId = Number.isFinite(numericCustomerId) && numericCustomerId > 0 ? numericCustomerId : null
    if (!orderForm.patient_name.trim()) {
      toast.error('Customer name is required')
      return
    }
    if (!selectedPanelId && !selectedMenuItem) {
      toast.error('Choose a panel or a test')
      return
    }
    const payload: Record<string, unknown> = {
      patient_id: resolvedCustomerId,
      patient_name: orderForm.patient_name.trim(),
      patient_code: orderForm.patient_code.trim() || null,
      doctor_name: orderForm.doctor_name.trim() || null,
      priority: orderForm.priority,
      notes: orderForm.notes.trim() || null,
    }
    if (selectedPanelId) {
      payload.panel_id = selectedPanelId
    } else if (selectedMenuItem) {
      payload.menu_items = [
        {
          test_code: selectedMenuItem.test_code,
          test_name: selectedMenuItem.test_name,
          department: selectedMenuItem.department,
          sample_type: selectedMenuItem.sample_type,
          turnaround_minutes: selectedMenuItem.turnaround_minutes,
        },
      ]
    }
    try {
      await axios.post(`${API_BASE}/api/lis/orders`, payload, requestConfig)
      toast.success('LIS order registered')
      setOrderForm((prev) => ({ ...prev, notes: '', selected_test_id: '', panel_id: '' }))
      await loadDashboard()
    } catch {
      toast.error('Failed to create LIS order')
    }
  }, [catalog, loadDashboard, orderForm, requestConfig, token])

  const generateBarcode = useCallback(
    async (orderId: number) => {
      if (!token) return
      try {
        const { data } = await axios.post<{ barcode_image_base64: string }>(
          `${API_BASE}/api/lis/orders/${orderId}/barcode`,
          {},
          requestConfig
        )
        setBarcodeImage(data.barcode_image_base64)
        toast.success('Barcode generated')
        await loadDashboard()
      } catch {
        toast.error('Barcode generation failed')
      }
    },
    [loadDashboard, requestConfig, token]
  )

  const updateSampleStatus = useCallback(
    async (sampleId: number, status: string) => {
      if (!token) return
      try {
        await axios.put(`${API_BASE}/api/lis/samples/${sampleId}/status`, { status }, requestConfig)
        toast.success(`Sample moved to ${status}`)
        await loadDashboard()
      } catch {
        toast.error('Unable to update sample status')
      }
    },
    [loadDashboard, requestConfig, token]
  )

  const generateOrder = useCallback(
    async (orderId: number) => {
      if (!token) return
      try {
        await axios.post(
          `${API_BASE}/api/lis/orders/generate`,
          { order_id: orderId, channels: ['sms', 'email', 'whatsapp', 'patient_portal'], signed_by: 'Branch Pathologist' },
          requestConfig
        )
        toast.success('Order generated and dispatched')
        await loadDashboard()
      } catch {
        toast.error('Failed to generate report')
      }
    },
    [loadDashboard, requestConfig, token]
  )

  const markQcPassed = useCallback(
    async (sample: LISSample) => {
      if (!token) return
      try {
        await axios.post(
          `${API_BASE}/api/lis/qc/results`,
          {
            sample_id: sample.id,
            analyzer_name: sample.analyzer_name || 'Default Analyzer',
            test_code: sample.sample_code,
            qc_status: 'Passed',
          },
          requestConfig
        )
        toast.success('QC result recorded')
        await loadDashboard()
      } catch {
        toast.error('Failed to record QC')
      }
    },
    [loadDashboard, requestConfig, token]
  )

  const table = useReactTable({
    data: orders,
    columns: [
      orderColumnHelper.accessor('order_number', { header: 'Order #' }),
      orderColumnHelper.accessor('patient_name', { header: 'Customer' }),
      orderColumnHelper.accessor('priority', {
        header: 'Priority',
        cell: ({ getValue }) => (
          <span className={getValue() === 'Emergency' ? 'text-rose-600 font-semibold' : getValue() === 'STAT' ? 'text-amber-600 font-semibold' : 'text-slate-700'}>
            {getValue()}
          </span>
        ),
      }),
      orderColumnHelper.accessor('status', {
        header: 'Status',
        cell: ({ getValue }) => <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusTone(getValue())}`}>{getValue()}</span>,
      }),
      orderColumnHelper.accessor('expected_tat_minutes', { header: 'TAT (min)' }),
      orderColumnHelper.display({
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => generateBarcode(row.original.id)}
              className="rounded-md border border-indigo-200 px-2 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-50"
            >
              Barcode
            </button>
            <button
              type="button"
              onClick={() => generateOrder(row.original.id)}
              className="rounded-md border border-emerald-200 px-2 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-50"
            >
              Generate Order
            </button>
          </div>
        ),
      }),
    ],
    getCoreRowModel: getCoreRowModel(),
  })

  const pieData = useMemo(() => {
    if (!stats) return []
    return Object.entries(stats.pending_by_department).map(([name, value]) => ({ name, value }))
  }, [stats])

  const delayedSamples = useMemo(
    () =>
      samples.filter((sample) => {
        if (!sample.expected_completion_at) return false
        if (sample.status === 'Ordered' || sample.status === 'Rejected') return false
        return new Date(sample.expected_completion_at).getTime() < Date.now()
      }),
    [samples]
  )

  const kanbanColumns = ['Registered', 'In Processing', 'QC Passed', 'Ordered', 'Delayed', 'Rejected']

  if (loading && !health) {
    return <div className="rounded-2xl bg-white/80 p-10 text-center text-slate-600 shadow-sm">Loading LIS command center...</div>
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Lab Operations Health Score</h2>
          <p className="text-sm text-slate-500">AI score based on TAT, QC failures, rejections, and pending workload</p>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart innerRadius="68%" outerRadius="100%" barSize={26} data={[{ value: health?.score || 0 }]} startAngle={180} endAngle={0}>
                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                <RadialBar dataKey="value" cornerRadius={14} fill={colorForHealth(health?.score || 0)} />
                <text x="50%" y="52%" textAnchor="middle" className="fill-slate-900 text-4xl font-bold">
                  {health?.score ?? 0}
                </text>
                <text x="50%" y="66%" textAnchor="middle" className="fill-slate-500 text-sm font-medium">
                  {health?.status || 'Unknown'}
                </text>
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Today's MenuItem Volume</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{stats?.todays_test_volume ?? 0}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Average TAT</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{Math.round(stats?.average_tat_minutes ?? 0)} min</p>
            <p className="mt-1 text-xs text-slate-500">
              Routine {Math.round(stats?.tat_breakdown?.Routine || 0)} · STAT {Math.round(stats?.tat_breakdown?.STAT || 0)} · Emergency{' '}
              {Math.round(stats?.tat_breakdown?.Emergency || 0)}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Pending MenuItems</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{stats?.pending_menu_items_count ?? 0}</p>
            <p className="mt-1 text-xs text-slate-500">QC: {stats?.qc_status || 'Unknown'}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Sample Rejection Rate</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{stats?.sample_rejection_rate ?? 0}%</p>
            <p className="mt-1 text-xs text-rose-600">Delayed samples: {stats?.delayed_samples ?? 0}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Order Entry & Registration</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Customer Lookup</label>
              <input
                value={patientQuery}
                onChange={(event) => setCustomerQuery(event.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                placeholder="Type name or patient ID"
              />
              {patientHits.length > 0 && (
                <div className="mt-1 max-h-24 overflow-auto rounded-lg border border-slate-200 bg-white text-xs">
                  {patientHits.map((hit) => (
                    <button
                      key={hit.id}
                      type="button"
                      onClick={() => {
                        setOrderForm((prev) => ({
                          ...prev,
                          patient_id: '',
                          patient_code: hit.patient_id || hit.id,
                          patient_name: hit.name || prev.patient_name,
                        }))
                        setCustomerQuery(hit.name)
                        setCustomerHits([])
                      }}
                      className="block w-full border-b border-slate-100 px-2 py-1 text-left hover:bg-slate-50"
                    >
                      {hit.name} ({hit.patient_id || hit.id})
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Staff</label>
              <input
                value={doctorQuery}
                onChange={(event) => setStaffQuery(event.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                placeholder="Type doctor name"
              />
              {doctorHits.length > 0 && (
                <div className="mt-1 max-h-24 overflow-auto rounded-lg border border-slate-200 bg-white text-xs">
                  {doctorHits.map((hit) => (
                    <button
                      key={hit.id}
                      type="button"
                      onClick={() => {
                        setOrderForm((prev) => ({ ...prev, doctor_name: hit.name }))
                        setStaffQuery(hit.name)
                        setStaffHits([])
                      }}
                      className="block w-full border-b border-slate-100 px-2 py-1 text-left hover:bg-slate-50"
                    >
                      {hit.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <input
              value={orderForm.patient_name}
              onChange={(event) => setOrderForm((prev) => ({ ...prev, patient_name: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder="Customer full name"
            />
            <input
              value={orderForm.patient_code}
              onChange={(event) => setOrderForm((prev) => ({ ...prev, patient_code: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder="Customer code (optional)"
            />

            <select
              value={orderForm.priority}
              onChange={(event) => setOrderForm((prev) => ({ ...prev, priority: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="Routine">Routine</option>
              <option value="STAT">STAT</option>
              <option value="Emergency">Emergency</option>
            </select>

            <select
              value={orderForm.panel_id}
              onChange={(event) => setOrderForm((prev) => ({ ...prev, panel_id: event.target.value, selected_test_id: '' }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="">Choose Panel (optional)</option>
              {panels.map((panel) => (
                <option key={panel.id} value={panel.id}>
                  {panel.panel_name}
                </option>
              ))}
            </select>

            <select
              value={orderForm.selected_test_id}
              onChange={(event) => setOrderForm((prev) => ({ ...prev, selected_test_id: event.target.value, panel_id: '' }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm sm:col-span-2"
            >
              <option value="">Or choose single test</option>
              {catalog.map((test) => (
                <option key={test.id} value={test.id}>
                  {test.test_name} ({test.department})
                </option>
              ))}
            </select>

            <textarea
              value={orderForm.notes}
              onChange={(event) => setOrderForm((prev) => ({ ...prev, notes: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm sm:col-span-2"
              rows={2}
              placeholder="Notes / Clinical context"
            />
            <button
              type="button"
              onClick={submitOrder}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 sm:col-span-2"
            >
              Register LIS Order
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Pending by Department</h3>
          <div className="mt-4 h-56">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={90} label>
                    {pieData.map((entry, index) => (
                      <Cell key={entry.name} fill={['#4f46e5', '#0891b2', '#65a30d', '#ca8a04', '#be123c'][index % 5]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="pt-16 text-center text-sm text-slate-500">No pending department load</div>
            )}
          </div>
          {barcodeImage && (
            <div className="mt-3 rounded-xl border border-slate-200 p-3">
              <p className="text-xs font-medium text-slate-600">Latest Sample Barcode</p>
              <img src={barcodeImage} alt="Sample barcode" className="mt-2 h-24 w-24" />
            </div>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">LIS Order Queue</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="px-3 py-2 text-left font-semibold text-slate-600">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-slate-100">
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2 text-slate-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Sample Status Dashboard</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            {kanbanColumns.map((column) => (
              <div key={column} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">{column}</p>
                <div className="space-y-2">
                  {samples
                    .filter((sample) => sample.status === column)
                    .slice(0, 8)
                    .map((sample) => (
                      <div key={sample.id} className="rounded-lg border border-slate-200 bg-white p-2">
                        <p className="text-xs font-semibold text-slate-700">{sample.sample_code}</p>
                        <p className="text-[11px] text-slate-500">{sample.department}</p>
                        <select
                          value={sample.status}
                          onChange={(event) => updateSampleStatus(sample.id, event.target.value)}
                          className="mt-1 w-full rounded border border-slate-200 px-1 py-1 text-[11px]"
                        >
                          {kanbanColumns.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                        {sample.status === 'In Processing' && (
                          <button
                            type="button"
                            onClick={() => markQcPassed(sample)}
                            className="mt-1 w-full rounded border border-blue-200 px-1 py-1 text-[11px] font-semibold text-blue-700 hover:bg-blue-50"
                          >
                            Mark QC Passed
                          </button>
                        )}
                      </div>
                    ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-rose-300 bg-rose-50 p-5 shadow-sm">
          <h3 className="text-base font-semibold text-rose-700">Delayed Sample Alerts</h3>
          <p className="mt-1 text-xs text-rose-600">Samples that exceeded expected processing window</p>
          <div className="mt-3 space-y-2">
            {delayedSamples.length === 0 && <p className="text-sm text-rose-600">No delayed samples right now.</p>}
            {delayedSamples.map((sample) => (
              <div key={sample.id} className="rounded-lg border border-rose-200 bg-white p-2">
                <p className="text-sm font-semibold text-rose-700">{sample.sample_code}</p>
                <p className="text-xs text-slate-600">
                  Dept: {sample.department} · Due: {formatDate(sample.expected_completion_at)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">QC Dashboard & Westgard</h3>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-emerald-50 p-2">
              <p className="text-xs text-emerald-700">Pass</p>
              <p className="text-xl font-semibold text-emerald-700">{qcDashboard?.summary.pass ?? 0}</p>
            </div>
            <div className="rounded-lg bg-amber-50 p-2">
              <p className="text-xs text-amber-700">Warning</p>
              <p className="text-xl font-semibold text-amber-700">{qcDashboard?.summary.warning ?? 0}</p>
            </div>
            <div className="rounded-lg bg-rose-50 p-2">
              <p className="text-xs text-rose-700">Out of Control</p>
              <p className="text-xl font-semibold text-rose-700">{qcDashboard?.summary.out_of_control ?? 0}</p>
            </div>
          </div>
          <div className="mt-4 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={qcDashboard?.trend || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" hide />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 space-y-2">
            {(qcDashboard?.westgard_findings || []).slice(0, 4).map((item) => (
              <div key={`${item.test_code}-${item.rule}-${item.at}`} className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs">
                <span className="font-semibold">{item.rule}</span> · {item.test_code} · {item.message}
              </div>
            ))}
            {(qcDashboard?.westgard_findings || []).length === 0 && <p className="text-xs text-slate-500">No active Westgard violations.</p>}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Inventory, Lots & Reagent Consumption</h3>
          <p className="mt-1 text-xs text-slate-500">Live low-stock alerts and expiry safeguards</p>
          <div className="mt-3 space-y-2">
            {(inventoryOverview?.low_stock_alerts || []).slice(0, 5).map((item) => (
              <div key={item.item_id} className="rounded-lg border border-rose-200 bg-rose-50 p-2 text-xs">
                <span className="font-semibold">{item.item_name}</span> ({item.department}) - {item.current_qty}/{item.min_threshold}
              </div>
            ))}
            {(inventoryOverview?.low_stock_alerts || []).length === 0 && <p className="text-xs text-slate-500">No low-stock alerts.</p>}
          </div>
          <div className="mt-4 h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarLikePie data={(consumptionAnalytics?.usage_by_department || []).slice(0, 6)} />
            </ResponsiveContainer>
          </div>
          <div className="mt-3 space-y-1">
            {(inventoryOverview?.lot_expiry_tracking || []).slice(0, 3).map((lot) => (
              <p key={lot.item_id} className="text-xs text-slate-600">
                {lot.item_name} lot {lot.lot_number || 'N/A'} expires in {lot.days_to_expiry ?? 'N/A'} days
              </p>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">TAT & Department Performance Analytics</h3>
          <div className="mt-4 h-52">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={tatAnalytics?.tat_by_day_of_week || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="avg_tat_minutes" name="Avg TAT (min)" stroke="#0f766e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {(performanceAnalytics?.departments || []).slice(0, 6).map((dept) => (
              <div key={dept.department} className="rounded-lg border border-slate-200 p-2 text-xs">
                <p className="font-semibold text-slate-800">{dept.department}</p>
                <p className="text-slate-600">Volume: {dept.volume} · Ordered: {dept.reported}</p>
                <p className="text-slate-600">TAT: {Math.round(dept.avg_tat_minutes)} min · QC: {dept.qc_status}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">Financial + AI Insights</h3>
          <div className="mt-2 space-y-1 text-sm">
            <p>Revenue: ₹{Math.round(financialAnalytics?.revenue || 0)}</p>
            <p>Reagent Cost: ₹{Math.round(financialAnalytics?.reagent_cost || 0)}</p>
            <p>Profitability: ₹{Math.round(financialAnalytics?.profitability || 0)} ({financialAnalytics?.margin_percent || 0}%)</p>
            <p>Cost/MenuItem: ₹{financialAnalytics?.cost_per_test || 0}</p>
          </div>
          <div className="mt-4 space-y-2">
            {(aiInsights?.anomaly_detection || []).slice(0, 4).map((anomaly) => (
              <div key={anomaly.type} className="rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700">
                <span className="font-semibold">{anomaly.type}</span>: {anomaly.message}
              </div>
            ))}
            {(aiInsights?.anomaly_detection || []).length === 0 && <p className="text-xs text-slate-500">No anomalies detected.</p>}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">Order Archive & Version Control</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">Order #</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">Version</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">Template</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">Status</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">Signed By</th>
                <th className="px-3 py-2 text-left font-semibold text-slate-600">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {reportArchive.slice(0, 15).map((report) => (
                <tr key={report.id}>
                  <td className="px-3 py-2">{report.report_number}</td>
                  <td className="px-3 py-2">{report.version}</td>
                  <td className="px-3 py-2">{report.template_name}</td>
                  <td className="px-3 py-2">{report.status}</td>
                  <td className="px-3 py-2">{report.signed_by || '—'}</td>
                  <td className="px-3 py-2">{formatDate(report.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function BarLikePie({ data }: { data: Array<{ name: string; quantity: number }> }) {
  if (!data.length) {
    return <div className="pt-14 text-center text-xs text-slate-500">No reagent consumption data</div>
  }
  return (
    <PieChart>
      <Pie data={data} dataKey="quantity" nameKey="name" outerRadius={60} label>
        {data.map((entry, index) => (
          <Cell key={entry.name} fill={['#0ea5e9', '#6366f1', '#14b8a6', '#f59e0b', '#ef4444', '#64748b'][index % 6]} />
        ))}
      </Pie>
      <Tooltip />
    </PieChart>
  )
}
