import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import axios from 'axios'
import {
  Cell,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'

type HealthScoreResponse = {
  score: number
  status: 'Green' | 'Yellow' | 'Red' | string
  collection_rate: number
  total_billed: number
  total_collected: number
  pending_dues_total: number
  aging_breakdown: {
    '0_30': number
    '31_60': number
    '61_90': number
    '90_plus': number
  }
  last_updated: string
  branch_name?: string | null
}

type TodayCollections = {
  total: number
  cash: number
  upi: number
  card: number
  insurance: number
  other: number
  timestamp: string
}

type TransactionRow = {
  id: string
  source: string
  patient_name: string
  patient_id?: string | null
  patient_mobile?: string | null
  patient_email?: string | null
  test_name: string
  test_package?: string | null
  amount: number
  total_amount: number
  method: string
  status: string
  timestamp: string
  payment_date: string
  receipt_number?: string | null
  discount_applied: number
  notes?: string | null
  invoice_number?: string | null
  gateway_reference?: string | null
}

type CustomerFinancial = {
  patient_id: number
  patient_code?: string | null
  full_name: string
  mobile?: string | null
  email?: string | null
  total_menu_items: number
  total_billed: number
  total_paid: number
  outstanding_balance: number
  payment_history: Array<{
    id: string
    type: string
    description: string
    amount: number
    status: string
    timestamp: string
    reference?: string | null
  }>
  refunds: Array<{
    id: number
    amount: number
    status: string
    reason?: string | null
    requested_at: string
    processed_at?: string | null
    reference?: string | null
  }>
  branch_name?: string | null
  last_payment_at?: string | null
}

type OutstandingDueRow = {
  patient_id: number
  patient_code?: string | null
  patient_name: string
  mobile?: string | null
  outstanding_amount: number
  oldest_due_date?: string | null
  aging_days: number
  total_billed: number
  total_paid: number
  last_payment_at?: string | null
}

type TrendPoint = { label: string; revenue: number }
type TrendResponse = { daily: TrendPoint[]; weekly: TrendPoint[]; monthly: TrendPoint[] }
type ForecastResponse = {
  horizon_days: number
  current_average_daily_revenue: number
  projected_revenue: number
  confidence: string
  series: TrendPoint[]
}
type AnomalyItem = {
  id: number
  type: string
  severity: string
  title: string
  description: string
  amount: number
  related_transaction_id?: string | null
  created_at: string
}
type SimulationResponse = {
  action: string
  current_collection_rate: number
  projected_collection_rate: number
  current_cash_flow: number
  projected_cash_flow: number
  impact: number
  note: string
}

type ReconciliationStatus = {
  transaction_id: string
  status: 'Reconciled' | 'Pending' | 'Discrepancy' | string
  message: string
  matched_reference?: string | null
}

type ReadinessScoreResponse = {
  score: number
  status: string
  branch_name?: string | null
  pending_invoices: number
  due_soon_invoices: number
  overdue_invoices: number
  blockers: string[]
  checklist: string[]
  last_updated: string
}

type SettlementRow = {
  date: string
  gateway: string
  amount_collected: number
  amount_settled: number
  discrepancy: number
  settlement_date: string
  bank_name?: string | null
  current_balance?: number | null
  status: string
}

type DiscrepancyAlert = {
  alert_id: number
  type: string
  description: string
  amount: number
  related_transaction_id?: string | null
  severity: string
  created_at: string
}

type SmartAlertItem = {
  alert_id: number
  category: string
  severity: string
  title: string
  message: string
  amount: number
  patient_id?: number | null
  patient_name?: string | null
  source?: string | null
  created_at: string
}

type BulkReconciliationResponse = {
  total_transactions: number
  reconciled: number
  pending: number
  discrepancy: number
  created_at: string
}

type BankReconcileRow = {
  row_number: number
  bank_reference: string
  bank_date?: string | null
  bank_amount: number
  system_reference?: string | null
  system_amount?: number | null
  status: string
  reason: string
}

type BankReconcileResponse = {
  filename: string
  total_rows: number
  matched_rows: number
  discrepancy_rows: number
  unmatched_rows: number
  rows: BankReconcileRow[]
}

type GeneratedInvoiceResponse = {
  invoice_id: number
  invoice_number: string
  patient_id: number
  patient_name: string
  branch_id: number
  branch_name?: string | null
  subtotal: number
  discount_amount: number
  taxable_amount: number
  gst_breakdown: {
    taxable_amount: number
    cgst: number
    sgst: number
    igst: number
    gst_total: number
    grand_total: number
  }
  final_amount: number
  due_date?: string | null
  pcpndt_compliance: string[]
  legal_text: string
  items: Array<{
    item_name: string
    quantity: number
    unit_price: number
    taxable_amount: number
    gst_rate: number
    gst_amount: number
    total_amount: number
  }>
}

const columnHelper = createColumnHelper<TransactionRow>()
const duesColumnHelper = createColumnHelper<OutstandingDueRow>()

const STATUS_STYLE: Record<string, string> = {
  Completed: 'bg-emerald-100 text-emerald-700',
  Pending: 'bg-amber-100 text-amber-700',
  Failed: 'bg-rose-100 text-rose-700',
  Refunded: 'bg-slate-100 text-slate-700',
  'Partially Paid': 'bg-blue-100 text-blue-700',
}

const METHOD_STYLE: Record<string, string> = {
  Cash: 'bg-emerald-50 text-emerald-700',
  UPI: 'bg-indigo-50 text-indigo-700',
  Card: 'bg-sky-50 text-sky-700',
  Insurance: 'bg-violet-50 text-violet-700',
  Other: 'bg-slate-50 text-slate-700',
}

const SEVERITY_STYLE: Record<string, string> = {
  Critical: 'border-rose-300 bg-rose-50 text-rose-700',
  High: 'border-red-300 bg-red-50 text-red-700',
  Medium: 'border-amber-300 bg-amber-50 text-amber-700',
  Low: 'border-emerald-300 bg-emerald-50 text-emerald-700',
  Info: 'border-sky-300 bg-sky-50 text-sky-700',
}

const API_BASE =
  process.env.REACT_APP_API_BASE_URL ||
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

function authHeaders(token?: string) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)
}

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function statusTone(status: string) {
  return STATUS_STYLE[status] || 'bg-slate-100 text-slate-700'
}

function methodTone(method: string) {
  return METHOD_STYLE[method] || METHOD_STYLE.Other
}

function healthColor(score: number) {
  if (score >= 80) return '#10b981'
  if (score >= 50) return '#f59e0b'
  return '#ef4444'
}

function safeNumber(input: string) {
  const value = Number(input)
  return Number.isFinite(value) ? value : 0
}

type TransactionFilters = {
  patient_name: string
  date_from: string
  date_to: string
  method: string
  amount: string
  status: string
}

function MetricCard({
  title,
  value,
  subtitle,
  tone = 'slate',
}: {
  title: string
  value: string
  subtitle?: string
  tone?: 'slate' | 'emerald' | 'amber' | 'rose' | 'indigo'
}) {
  const toneMap = {
    slate: 'border-slate-200 bg-white',
    emerald: 'border-emerald-200 bg-emerald-50/40',
    amber: 'border-amber-200 bg-amber-50/40',
    rose: 'border-rose-200 bg-rose-50/40',
    indigo: 'border-indigo-200 bg-indigo-50/40',
  }
  return (
    <div className={`rounded-2xl border p-4 shadow-sm ${toneMap[tone]}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
    </div>
  )
}

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
      {subtitle ? <p className="text-sm text-slate-500">{subtitle}</p> : null}
    </div>
  )
}

export default function BranchPaymentsDashboard() {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'dashboard' | 'reconciliation' | 'people' | 'brain' | 'settings'>('dashboard')
  const [loading, setLoading] = useState(false)
  const [healthScore, setHealthScore] = useState<HealthScoreResponse | null>(null)
  const [readinessScore, setReadinessScore] = useState<ReadinessScoreResponse | null>(null)
  const [todayCollections, setTodayCollections] = useState<TodayCollections | null>(null)
  const [feed, setFeed] = useState<TransactionRow[]>([])
  const [transactions, setTransactions] = useState<TransactionRow[]>([])
  const [transactionsTotal, setTransactionsTotal] = useState(0)
  const [transactionsPage, setTransactionsPage] = useState(1)
  const [transactionsPageSize] = useState(10)
  const [filters, setFilters] = useState<TransactionFilters>({
    patient_name: '',
    date_from: '',
    date_to: '',
    method: '',
    amount: '',
    status: '',
  })
  const [trendData, setTrendData] = useState<TrendResponse | null>(null)
  const [forecast, setForecast] = useState<ForecastResponse | null>(null)
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([])
  const [dues, setDues] = useState<OutstandingDueRow[]>([])
  const [reconciliationSummary, setReconciliationSummary] = useState<ReconciliationStatus | null>(null)
  const [settlements, setSettlements] = useState<SettlementRow[]>([])
  const [discrepancyAlerts, setDiscrepancyAlerts] = useState<DiscrepancyAlert[]>([])
  const [smartAlerts, setSmartAlerts] = useState<SmartAlertItem[]>([])
  const [bankReconcileResult, setBankReconcileResult] = useState<BankReconcileResponse | null>(null)
  const [selectedBankFile, setSelectedBankFile] = useState<File | null>(null)
  const [selectedTransaction, setSelectedTransaction] = useState<TransactionRow | null>(null)
  const [patientFinancial, setCustomerFinancial] = useState<CustomerFinancial | null>(null)
  const [patientLoading, setCustomerLoading] = useState(false)
  const [simulatorAction, setSimulatorAction] = useState('10% discount for early payment')
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null)
  const [invoiceResult, setInvoiceResult] = useState<GeneratedInvoiceResponse | null>(null)
  const [invoiceLoading, setInvoiceLoading] = useState(false)
  const [oneClickReconcileResult, setOneClickReconcileResult] = useState<BulkReconciliationResponse | null>(null)
  const [template, setTemplate] = useState({
    logoUrl: '',
    branchName: '',
    branchAddress: '',
    legalText: 'GST invoice generated by Vaidya Vihar Diagnostic. All services are branch-scoped and auditable.',
  })
  const [invoiceDraft, setInvoiceDraft] = useState({
    patientId: '',
    serviceType: '',
    notes: '',
    legalText: '',
    dueDays: '0',
    itemName: 'Diagnostic MenuItem',
    unitPrice: '1500',
    quantity: '1',
    gstRate: '',
    gstExempt: false,
  })

  const requestConfig = useMemo(() => ({ headers: authHeaders(token) }), [token])

  const openCustomerFinancial = useCallback(
    async (patientId?: number) => {
      if (!patientId) return
      setCustomerLoading(true)
      try {
        const response = await axios.get(`${API_BASE}/api/branch/customers/${patientId}/financial`, requestConfig)
        setCustomerFinancial(response.data)
        setActiveTab('people')
      } catch (error) {
        toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Failed to load patient financial profile')
      } finally {
        setCustomerLoading(false)
      }
    },
    [requestConfig]
  )

  const reconcileTransaction = useCallback(
    async (transactionId: string) => {
      try {
        const response = await axios.post(`${API_BASE}/api/branch/payments/reconcile`, null, {
          ...requestConfig,
          params: { transaction_id: transactionId },
        })
        setReconciliationSummary(response.data)
        toast.success('Reconciliation completed')
        setActiveTab('reconciliation')
      } catch (error) {
        toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Failed to reconcile transaction')
      }
    },
    [requestConfig]
  )

  const sendReminder = useCallback(
    async (patientIds: number[]) => {
      try {
        const response = await axios.post(
          `${API_BASE}/api/branch/payments/reminders`,
          { patient_ids: patientIds, channels: ['sms', 'email'] },
          requestConfig
        )
        toast.success(`Reminders sent to ${response.data.total_sent} patient(s)`)
      } catch (error) {
        toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Failed to send reminder')
      }
    },
    [requestConfig]
  )

  // Column config is intentionally stable; row action handlers read latest closures.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const transactionColumns = useMemo(
    () => [
      columnHelper.accessor('payment_date', {
        header: 'Date',
        cell: info => <span className="text-sm text-slate-700">{formatDateTime(info.getValue())}</span>,
      }),
      columnHelper.accessor('patient_name', {
        header: 'Customer',
        cell: info => (
          <button
            className="text-left font-semibold text-indigo-700 hover:underline"
            onClick={() => void openCustomerFinancial(info.row.original.patient_id ? Number(info.row.original.patient_id) : undefined)}
          >
            {info.getValue()}
          </button>
        ),
      }),
      columnHelper.accessor('test_name', {
        header: 'MenuItem',
        cell: info => <span className="text-sm text-slate-700">{info.getValue()}</span>,
      }),
      columnHelper.accessor('method', {
        header: 'Method',
        cell: info => <span className={`rounded-full px-2 py-1 text-xs font-semibold ${methodTone(info.getValue())}`}>{info.getValue()}</span>,
      }),
      columnHelper.accessor('status', {
        header: 'Status',
        cell: info => <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusTone(info.getValue())}`}>{info.getValue()}</span>,
      }),
      columnHelper.accessor('amount', {
        header: 'Amount',
        cell: info => <span className="font-semibold text-slate-900">{formatCurrency(info.getValue())}</span>,
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
              onClick={() => setSelectedTransaction(row.original)}
            >
              Details
            </button>
            <button
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white"
              onClick={() => void reconcileTransaction(row.original.id)}
            >
              Reconcile
            </button>
          </div>
        ),
      }),
    ],
    [openCustomerFinancial, reconcileTransaction]
  )

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const duesColumns = useMemo(
    () => [
      duesColumnHelper.accessor('patient_name', {
        header: 'Customer',
        cell: info => (
          <button className="font-semibold text-indigo-700 hover:underline" onClick={() => void openCustomerFinancial(info.row.original.patient_id)}>
            {info.getValue()}
          </button>
        ),
      }),
      duesColumnHelper.accessor('outstanding_amount', {
        header: 'Outstanding',
        cell: info => <span className="font-semibold text-rose-700">{formatCurrency(info.getValue())}</span>,
      }),
      duesColumnHelper.accessor('aging_days', {
        header: 'Aging',
        cell: info => <span>{info.getValue()} days</span>,
      }),
      duesColumnHelper.accessor('last_payment_at', {
        header: 'Last Payment',
        cell: info => <span>{formatDateTime(info.getValue())}</span>,
      }),
      duesColumnHelper.display({
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex gap-2">
            <button
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white"
              onClick={() => void sendReminder([row.original.patient_id])}
            >
              Send Reminder
            </button>
            <button
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white"
              onClick={() => void openCustomerFinancial(row.original.patient_id)}
            >
              View Profile
            </button>
          </div>
        ),
      }),
    ],
    [openCustomerFinancial, sendReminder]
  )

  const transactionTable = useReactTable({
    data: transactions,
    columns: transactionColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  const duesTable = useReactTable({
    data: dues,
    columns: duesColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  const buildTransactionParams = useCallback(() => {
    const params: Record<string, string | number> = {
      skip: (transactionsPage - 1) * transactionsPageSize,
      limit: transactionsPageSize,
    }
    if (filters.patient_name.trim()) params.patient_name = filters.patient_name.trim()
    if (filters.date_from || filters.date_to) params.date_range = `${filters.date_from || filters.date_to} to ${filters.date_to || filters.date_from}`
    if (filters.method) params.method = filters.method
    if (filters.amount.trim()) params.amount = safeNumber(filters.amount)
    if (filters.status) params.status = filters.status
    return params
  }, [filters.amount, filters.date_from, filters.date_to, filters.method, filters.patient_name, filters.status, transactionsPage, transactionsPageSize])

  const loadDashboard = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const [healthRes, readinessRes, todayRes, feedRes, trendsRes, forecastRes, anomaliesRes, duesRes, settlementsRes, alertsRes, smartAlertsRes] =
        await Promise.all([
          axios.get(`${API_BASE}/api/branch/payments/health-score`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/readiness-score`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/today`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/feed?limit=12`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/trends`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/forecast?horizon_days=30`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/anomalies`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/outstanding-dues`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/settlement`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/discrepancy-alerts`, requestConfig),
          axios.get(`${API_BASE}/api/branch/payments/smart-alerts`, requestConfig),
        ])

      setHealthScore(healthRes.data)
      setReadinessScore(readinessRes.data)
      setTodayCollections(todayRes.data)
      setFeed(Array.isArray(feedRes.data) ? feedRes.data : [])
      setTrendData(trendsRes.data)
      setForecast(forecastRes.data)
      setAnomalies(Array.isArray(anomaliesRes.data) ? anomaliesRes.data : [])
      setDues(Array.isArray(duesRes.data) ? duesRes.data : [])
      setSettlements(Array.isArray(settlementsRes.data) ? settlementsRes.data : [])
      setDiscrepancyAlerts(Array.isArray(alertsRes.data) ? alertsRes.data : [])
      setSmartAlerts(Array.isArray(smartAlertsRes.data) ? smartAlertsRes.data : [])
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Failed to load payments dashboard')
    } finally {
      setLoading(false)
    }
  }, [requestConfig, token])

  const loadTransactions = useCallback(async () => {
    if (!token) return
    try {
      const response = await axios.get(`${API_BASE}/api/branch/payments/transactions`, {
        ...requestConfig,
        params: buildTransactionParams(),
      })
      setTransactions(Array.isArray(response.data?.items) ? response.data.items : [])
      setTransactionsTotal(Number(response.data?.total || 0))
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Failed to load transactions')
    }
  }, [buildTransactionParams, requestConfig, token])

  const runOneClickReconciliation = useCallback(async () => {
    try {
      const response = await axios.post(`${API_BASE}/api/branch/payments/reconcile/all`, null, requestConfig)
      setOneClickReconcileResult(response.data)
      toast.success('One-click reconciliation completed')
      setActiveTab('reconciliation')
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'One-click reconciliation failed')
    }
  }, [requestConfig])

  const runSimulation = useCallback(async () => {
    try {
      const response = await axios.post(`${API_BASE}/api/branch/payments/simulate`, { action: simulatorAction }, requestConfig)
      setSimulation(response.data)
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Simulation failed')
    }
  }, [requestConfig, simulatorAction])

  const generateInvoice = useCallback(async () => {
    if (!invoiceDraft.patientId.trim()) {
      toast.error('Customer ID is required')
      return
    }
    setInvoiceLoading(true)
    try {
      const response = await axios.post(
        `${API_BASE}/api/branch/payments/invoice/generate`,
        {
          patient_id: Number(invoiceDraft.patientId),
          service_type: invoiceDraft.serviceType || undefined,
          notes: invoiceDraft.notes || undefined,
          legal_text: invoiceDraft.legalText || template.legalText,
          due_days: Number(invoiceDraft.dueDays || 0),
          items: [
            {
              item_name: invoiceDraft.itemName,
              unit_price: safeNumber(invoiceDraft.unitPrice),
              quantity: Math.max(1, Number(invoiceDraft.quantity || 1)),
              item_type: 'test',
              gst_rate: invoiceDraft.gstRate.trim() ? safeNumber(invoiceDraft.gstRate) : undefined,
              gst_exempt: invoiceDraft.gstExempt,
            },
          ],
        },
        requestConfig
      )
      setInvoiceResult(response.data)
      toast.success('Invoice generated')
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Invoice generation failed')
    } finally {
      setInvoiceLoading(false)
    }
  }, [invoiceDraft, requestConfig, template.legalText])

  const uploadBankStatement = useCallback(async () => {
    if (!selectedBankFile) {
      toast.error('Choose a CSV statement first')
      return
    }
    const formData = new FormData()
    formData.append('statement', selectedBankFile)
    try {
      const response = await axios.post(`${API_BASE}/api/branch/payments/bank-reconcile`, formData, {
        ...requestConfig,
        headers: { ...requestConfig.headers, 'Content-Type': 'multipart/form-data' },
      })
      setBankReconcileResult(response.data)
      toast.success('Bank reconciliation completed')
    } catch (error) {
      toast.error(axios.isAxiosError(error) ? error.response?.data?.detail || error.message : 'Bank reconciliation failed')
    }
  }, [requestConfig, selectedBankFile])

  useEffect(() => {
    void loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (!token) return
    void loadTransactions()
  }, [loadTransactions, token])

  useEffect(() => {
    setTransactionsPage(1)
  }, [filters])

  useEffect(() => {
    if (!token) return
    const id = window.setInterval(() => {
      void loadDashboard()
    }, 45000)
    return () => window.clearInterval(id)
  }, [loadDashboard, token])

  const healthGaugeData = useMemo(
    () => [{ name: 'Score', value: healthScore?.score ?? 0, fill: healthColor(healthScore?.score ?? 0) }],
    [healthScore]
  )

  const methodBreakdown = useMemo(
    () =>
      todayCollections
        ? [
            { name: 'Cash', value: todayCollections.cash },
            { name: 'UPI', value: todayCollections.upi },
            { name: 'Card', value: todayCollections.card },
            { name: 'Insurance', value: todayCollections.insurance },
            { name: 'Other', value: todayCollections.other },
          ].filter(point => point.value > 0)
        : [],
    [todayCollections]
  )

  const pageCount = Math.max(1, Math.ceil(transactionsTotal / transactionsPageSize))

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950 p-6 text-white shadow-2xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-300">Branch Director Financial Command Center</p>
            <h2 className="mt-2 text-3xl font-bold">Payments</h2>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">
              AI-assisted collections, reconciliation, patient financials, GST invoicing, and predictive analytics scoped to the active branch.
            </p>
            {loading ? <span className="mt-3 inline-flex rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white">Refreshing live data…</span> : null}
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-5">
            <MetricCard title="Health Score" value={`${healthScore?.score ?? 0}/100`} subtitle={healthScore?.status || '—'} tone="indigo" />
            <MetricCard title="Collection Rate" value={`${(healthScore?.collection_rate ?? 0).toFixed(1)}%`} subtitle="Billed vs collected" tone="emerald" />
            <MetricCard title="Readiness Score" value={`${readinessScore?.score ?? 0}/100`} subtitle={readinessScore?.status || '—'} tone="slate" />
            <MetricCard title="Today" value={formatCurrency(todayCollections?.total ?? 0)} subtitle="Collections" tone="amber" />
            <MetricCard title="Outstanding" value={formatCurrency(healthScore?.pending_dues_total ?? 0)} subtitle="Pending dues" tone="rose" />
          </div>
        </div>
      </div>

      {smartAlerts.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Smart Payment Alerts</p>
              <p className="text-sm text-amber-900">{smartAlerts[0]?.title}</p>
            </div>
            <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-amber-700">
              {smartAlerts.length} active
            </span>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {[
          ['dashboard', 'Dashboard'],
          ['reconciliation', 'Reconciliation'],
          ['people', 'People'],
          ['brain', 'Brain'],
          ['settings', 'Settings'],
        ].map(([key, label]) => (
          <button
            key={key}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${
              activeTab === key ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 shadow-sm ring-1 ring-slate-200'
            }`}
            onClick={() => setActiveTab(key as typeof activeTab)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'dashboard' && (
        <div className="grid gap-6 xl:grid-cols-[1.5fr_0.9fr]">
          <div className="space-y-6">
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-2xl border bg-white p-5 shadow-sm lg:col-span-1">
                <SectionTitle title="Payment Health Score" subtitle="Composite signal of collection rate and aging pressure." />
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadialBarChart
                      innerRadius="78%"
                      outerRadius="100%"
                      data={healthGaugeData}
                      startAngle={180}
                      endAngle={0}
                      barSize={24}
                    >
                      <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                      <RadialBar dataKey="value" background />
                      <Tooltip formatter={(value: number) => [`${value}`, 'Score']} />
                    </RadialBarChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3 rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">Status</p>
                  <p className="text-xl font-bold text-slate-900">{healthScore?.status || '—'}</p>
                  <p className="text-sm text-slate-500">Last updated {formatDateTime(healthScore?.last_updated)}</p>
                </div>
              </div>

              <div className="rounded-2xl border bg-white p-5 shadow-sm lg:col-span-1">
                <SectionTitle title="Today’s Collections" subtitle="Payment mix and live totals for the branch." />
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={methodBreakdown} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={4}>
                        {methodBreakdown.map((entry, index) => (
                          <Cell
                            key={entry.name}
                            fill={['#0f766e', '#4f46e5', '#0284c7', '#7c3aed', '#64748b'][index % 5]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {methodBreakdown.map(item => (
                    <div key={item.name} className="rounded-xl border bg-slate-50 p-3">
                      <p className="text-xs uppercase text-slate-500">{item.name}</p>
                      <p className="text-lg font-bold text-slate-900">{formatCurrency(item.value)}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border bg-white p-5 shadow-sm lg:col-span-1">
                <SectionTitle title="Pending Dues Aging" subtitle="Open balances grouped by bucket." />
                <div className="space-y-3">
                  {[
                    ['0_30', '0-30 days'],
                    ['31_60', '31-60 days'],
                    ['61_90', '61-90 days'],
                    ['90_plus', '90+ days'],
                  ].map(([key, label]) => (
                    <div key={key} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                      <span className="text-sm font-medium text-slate-700">{label}</span>
                      <span className="font-semibold text-slate-900">{formatCurrency(healthScore?.aging_breakdown[key as keyof HealthScoreResponse['aging_breakdown']] ?? 0)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Transaction Grid" subtitle="Search by patient, date range, method, amount, or status." />
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
                {[
                  { key: 'patient_name', label: 'Customer Name', placeholder: 'Search patient', value: filters.patient_name },
                  { key: 'date_from', label: 'From Date', placeholder: 'YYYY-MM-DD', value: filters.date_from },
                  { key: 'date_to', label: 'To Date', placeholder: 'YYYY-MM-DD', value: filters.date_to },
                  { key: 'method', label: 'Method', placeholder: 'Cash/UPI/Card/Insurance', value: filters.method },
                  { key: 'amount', label: 'Amount', placeholder: 'Exact amount', value: filters.amount },
                  { key: 'status', label: 'Status', placeholder: 'Completed/Pending/Failed', value: filters.status },
                ].map(field => (
                  <label key={field.key} className="space-y-1 text-sm">
                    <span className="font-medium text-slate-600">{field.label}</span>
                    <input
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 outline-none ring-0 focus:border-indigo-500"
                      placeholder={field.placeholder}
                      value={field.value}
                      onChange={e => setFilters(prev => ({ ...prev, [field.key]: e.target.value }))}
                    />
                  </label>
                ))}
              </div>
              <div className="mt-4 overflow-hidden rounded-2xl border">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    {transactionTable.getHeaderGroups().map(headerGroup => (
                      <tr key={headerGroup.id}>
                        {headerGroup.headers.map(header => (
                          <th key={header.id} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {transactionTable.getRowModel().rows.map(row => (
                      <tr key={row.id} className="hover:bg-slate-50/70">
                        {row.getVisibleCells().map(cell => (
                          <td key={cell.id} className="px-4 py-3 text-sm text-slate-700">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        ))}
                      </tr>
                    ))}
                    {!transactions.length ? (
                      <tr>
                        <td className="px-4 py-8 text-center text-slate-500" colSpan={6}>
                          No transactions found.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-slate-500">
                  Page {transactionsPage} of {pageCount} · {transactionsTotal} transactions
                </p>
                <div className="flex gap-2">
                  <button
                    className="rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-40"
                    disabled={transactionsPage <= 1}
                    onClick={() => setTransactionsPage(prev => Math.max(1, prev - 1))}
                  >
                    Previous
                  </button>
                  <button
                    className="rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-40"
                    disabled={transactionsPage >= pageCount}
                    onClick={() => setTransactionsPage(prev => Math.min(pageCount, prev + 1))}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Live Payment Feed" subtitle="Chronological stream of recent payment activity." />
              <div className="max-h-[520px] space-y-3 overflow-y-auto pr-1">
                {feed.map(item => (
                  <div
                    key={item.id}
                    className="w-full rounded-2xl border border-slate-200 p-4 text-left shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <button
                          type="button"
                          className="font-semibold text-indigo-700 hover:underline"
                          onClick={e => {
                            e.stopPropagation()
                            void openCustomerFinancial(item.patient_id ? Number(item.patient_id) : undefined)
                          }}
                        >
                          {item.patient_name}
                        </button>
                        <p className="text-sm text-slate-500">{item.test_name}</p>
                        <p className="mt-1 text-xs text-slate-400">{formatDateTime(item.timestamp)}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-slate-900">{formatCurrency(item.amount)}</p>
                        <span className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-semibold ${statusTone(item.status)}`}>
                          {item.status}
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="mt-3 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                      onClick={() => setSelectedTransaction(item)}
                    >
                      Open transaction
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-rose-200 bg-rose-50/60 p-5 shadow-sm">
              <SectionTitle title="Anomaly Detection Alerts" subtitle="AI-style highlights for recent outliers and risk signals." />
              <div className="space-y-3">
                {anomalies.map(item => (
                  <div key={item.id} className={`rounded-2xl border p-4 ${SEVERITY_STYLE[item.severity] || SEVERITY_STYLE.Info}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold">{item.title}</p>
                        <p className="text-sm opacity-90">{item.description}</p>
                      </div>
                      <span className="rounded-full bg-white/70 px-2 py-1 text-xs font-bold">{item.severity}</span>
                    </div>
                    <p className="mt-2 text-xs opacity-80">{formatDateTime(item.created_at)}</p>
                  </div>
                ))}
                {!anomalies.length ? <p className="text-sm text-slate-500">No anomalies detected.</p> : null}
              </div>
            </div>
          </aside>
        </div>
      )}

      {activeTab === 'reconciliation' && (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <MetricCard
                title="Reconciled"
                value={String(settlements.filter(row => row.status === 'Settled').length)}
                subtitle="Gateway settlements"
                tone="emerald"
              />
              <MetricCard title="Pending" value={String(discrepancyAlerts.filter(row => row.severity !== 'Critical').length)} subtitle="Needs review" tone="amber" />
              <MetricCard title="Discrepancy" value={String(discrepancyAlerts.filter(row => row.severity === 'Critical').length)} subtitle="Critical issues" tone="rose" />
            </div>

            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Auto-Reconciliation" subtitle="Run the reconciliation engine across all pending transactions at once." />
              <div className="flex flex-wrap items-center gap-3">
                <button
                  className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white"
                  onClick={() => void runOneClickReconciliation()}
                >
                  One-Click Reconciliation
                </button>
                <button
                  className="rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white"
                  onClick={() => {
                    const first = transactions[0]
                    if (!first) {
                      toast.error('No transaction selected')
                      return
                    }
                    void reconcileTransaction(first.id)
                  }}
                >
                  Reconcile Latest Transaction
                </button>
                {reconciliationSummary ? (
                  <div className="rounded-xl border bg-slate-50 px-4 py-3">
                    <p className="text-sm font-semibold text-slate-900">
                      {reconciliationSummary.status} · {reconciliationSummary.transaction_id}
                    </p>
                    <p className="text-sm text-slate-500">{reconciliationSummary.message}</p>
                  </div>
                ) : null}
                {oneClickReconcileResult ? (
                  <div className="rounded-xl border bg-emerald-50 px-4 py-3">
                    <p className="text-sm font-semibold text-emerald-800">
                      {oneClickReconcileResult.reconciled} reconciled · {oneClickReconcileResult.discrepancy} discrepancies
                    </p>
                    <p className="text-sm text-emerald-700">
                      {oneClickReconcileResult.pending} pending across {oneClickReconcileResult.total_transactions} transactions
                    </p>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Bank Reconciliation" subtitle="Upload a mock bank CSV and compare it with branch records." />
              <div className="flex flex-wrap items-center gap-3">
                <input
                  type="file"
                  accept=".csv"
                  className="block rounded-xl border border-dashed border-slate-300 px-3 py-2 text-sm"
                  onChange={e => setSelectedBankFile(e.target.files?.[0] ?? null)}
                />
                <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white" onClick={() => void uploadBankStatement()}>
                  Upload and Reconcile
                </button>
              </div>
              {bankReconcileResult ? (
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  <MetricCard title="Rows" value={String(bankReconcileResult.total_rows)} />
                  <MetricCard title="Matched" value={String(bankReconcileResult.matched_rows)} tone="emerald" />
                  <MetricCard title="Discrepancy" value={String(bankReconcileResult.discrepancy_rows)} tone="amber" />
                  <MetricCard title="Unmatched" value={String(bankReconcileResult.unmatched_rows)} tone="rose" />
                </div>
              ) : null}
            </div>

            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Daily Reconciliation SOP Checklist" subtitle="Operational reminders for branch finance teams." />
              <div className="grid gap-2 md:grid-cols-2">
                {[
                  'Check payment aggregator settlements',
                  'Verify denied insurance claims',
                  'Match UPI/QR references',
                  'Review failed or refunded transactions',
                  'Check bank credit entries',
                  'Close open cash counters',
                ].map(item => (
                  <label key={item} className="flex items-center gap-3 rounded-xl border bg-slate-50 px-3 py-2">
                    <input type="checkbox" className="h-4 w-4 rounded border-slate-300" />
                    <span className="text-sm text-slate-700">{item}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border bg-white p-5 shadow-sm">
            <SectionTitle title="Settlement Summary" subtitle="Gateway and bank-side settlement snapshot." />
            <div className="space-y-3">
              {settlements.map(row => (
                <div key={`${row.gateway}-${row.date}`} className="rounded-2xl border bg-slate-50 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-slate-900">{row.gateway}</p>
                      <p className="text-sm text-slate-500">{row.bank_name || 'Branch bank'}</p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${row.status === 'Settled' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                      {row.status}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <p className="text-slate-500">Collected</p>
                      <p className="font-semibold">{formatCurrency(row.amount_collected)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Settled</p>
                      <p className="font-semibold">{formatCurrency(row.amount_settled)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Gap</p>
                      <p className="font-semibold">{formatCurrency(row.discrepancy)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4">
              <h4 className="font-semibold text-rose-800">Discrepancy Alerts</h4>
              <div className="mt-3 space-y-3">
                {discrepancyAlerts.map(item => (
                  <div key={item.alert_id} className="rounded-xl border border-rose-200 bg-white p-3">
                    <p className="text-sm font-semibold text-rose-700">{item.type}</p>
                    <p className="text-sm text-slate-600">{item.description}</p>
                  </div>
                ))}
                {!discrepancyAlerts.length ? <p className="text-sm text-slate-500">No discrepancies flagged.</p> : null}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'people' && (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border bg-white p-5 shadow-sm">
            <SectionTitle title="Outstanding Dues" subtitle="Customers with pending balances sorted by amount and aging." />
            <div className="overflow-hidden rounded-2xl border">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  {duesTable.getHeaderGroups().map(headerGroup => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map(header => (
                        <th key={header.id} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {duesTable.getRowModel().rows.map(row => (
                    <tr key={row.id} className="hover:bg-slate-50/70">
                      {row.getVisibleCells().map(cell => (
                        <td key={cell.id} className="px-4 py-3 text-sm text-slate-700">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {!dues.length ? (
                    <tr>
                      <td className="px-4 py-8 text-center text-slate-500" colSpan={5}>
                        No outstanding dues found.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Customer Financial Profile" subtitle="Open a patient from the feed or dues table." />
              {patientLoading ? (
                <p className="text-sm text-slate-500">Loading profile...</p>
              ) : patientFinancial ? (
                <div className="space-y-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-2xl font-bold text-slate-900">{patientFinancial.full_name}</p>
                      <p className="text-sm text-slate-500">
                        {patientFinancial.patient_code || `Customer #${patientFinancial.patient_id}`} · {patientFinancial.branch_name || 'Branch scoped'}
                      </p>
                    </div>
                    <button className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold" onClick={() => setCustomerFinancial(null)}>
                      Close
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <MetricCard title="Total MenuItems" value={String(patientFinancial.total_menu_items)} />
                    <MetricCard title="Outstanding" value={formatCurrency(patientFinancial.outstanding_balance)} tone="rose" />
                    <MetricCard title="Billed" value={formatCurrency(patientFinancial.total_billed)} tone="amber" />
                    <MetricCard title="Paid" value={formatCurrency(patientFinancial.total_paid)} tone="emerald" />
                  </div>
                  <div className="rounded-2xl border bg-slate-50 p-4">
                    <p className="mb-2 text-sm font-semibold text-slate-700">Payment History</p>
                    <div className="space-y-2">
                      {patientFinancial.payment_history.slice(0, 6).map(item => (
                        <div key={item.id} className="flex items-center justify-between rounded-xl bg-white px-3 py-2 shadow-sm">
                          <div>
                            <p className="font-medium text-slate-900">{item.description}</p>
                            <p className="text-xs text-slate-500">{formatDateTime(item.timestamp)}</p>
                          </div>
                          <p className="font-semibold text-slate-900">{formatCurrency(item.amount)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button className="rounded-xl bg-emerald-600 px-4 py-2 font-semibold text-white" onClick={() => void sendReminder([patientFinancial.patient_id])}>
                      Send Reminder
                    </button>
                    <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white" onClick={() => setSelectedTransaction(feed[0] || null)}>
                      View Latest Payment
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Select a patient to view financial history.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'brain' && (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Revenue Trend Analysis" subtitle="Daily, weekly, and monthly revenue charts." />
              <div className="grid gap-6 xl:grid-cols-3">
                <div className="h-64 rounded-2xl border bg-slate-50 p-3">
                  <p className="mb-2 text-sm font-semibold text-slate-700">Daily</p>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={trendData?.daily || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" hide />
                      <YAxis />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Line type="monotone" dataKey="revenue" stroke="#4f46e5" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="h-64 rounded-2xl border bg-slate-50 p-3">
                  <p className="mb-2 text-sm font-semibold text-slate-700">Weekly</p>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={trendData?.weekly || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Line type="monotone" dataKey="revenue" stroke="#0f766e" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="h-64 rounded-2xl border bg-slate-50 p-3">
                  <p className="mb-2 text-sm font-semibold text-slate-700">Monthly</p>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={trendData?.monthly || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="label" />
                      <YAxis />
                      <Tooltip formatter={(value: number) => formatCurrency(value)} />
                      <Line type="monotone" dataKey="revenue" stroke="#7c3aed" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="What-If Scenario Simulator" subtitle="Estimate cash-flow impact from a policy change." />
              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  className="flex-1 rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-indigo-500"
                  value={simulatorAction}
                  onChange={e => setSimulatorAction(e.target.value)}
                  placeholder="e.g. 10% discount for early payment"
                />
                <button className="rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white" onClick={() => void runSimulation()}>
                  Simulate
                </button>
              </div>
              {simulation ? (
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  <MetricCard title="Current Rate" value={`${simulation.current_collection_rate.toFixed(1)}%`} />
                  <MetricCard title="Projected Rate" value={`${simulation.projected_collection_rate.toFixed(1)}%`} tone="emerald" />
                  <MetricCard title="Current Cash Flow" value={formatCurrency(simulation.current_cash_flow)} tone="amber" />
                  <MetricCard title="Projected Cash Flow" value={formatCurrency(simulation.projected_cash_flow)} tone="indigo" />
                </div>
              ) : null}
              {simulation ? <p className="mt-3 text-sm text-slate-500">{simulation.note}</p> : null}
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Revenue Forecast" subtitle={`Next ${forecast?.horizon_days || 30} days`} />
              {forecast ? (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <MetricCard title="Average / Day" value={formatCurrency(forecast.current_average_daily_revenue)} />
                    <MetricCard title="Projected" value={formatCurrency(forecast.projected_revenue)} tone="emerald" />
                  </div>
                  <p className="mt-3 text-sm text-slate-500">Confidence: {forecast.confidence}</p>
                  <div className="mt-4 h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={forecast.series}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" />
                        <YAxis />
                        <Tooltip formatter={(value: number) => formatCurrency(value)} />
                        <Line type="monotone" dataKey="revenue" stroke="#059669" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-500">Forecast unavailable.</p>
              )}
            </div>

            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="Collection Efficiency Order" subtitle="Quick efficiency snapshot for the branch." />
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                  <span>Collection Rate</span>
                  <span className="font-semibold">{(healthScore?.collection_rate ?? 0).toFixed(1)}%</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                  <span>Average Collection Time</span>
                  <span className="font-semibold">Branch KPI</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                  <span>UPI Efficiency</span>
                  <span className="font-semibold">{formatCurrency(todayCollections?.upi ?? 0)}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                  <span>Cash Efficiency</span>
                  <span className="font-semibold">{formatCurrency(todayCollections?.cash ?? 0)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border bg-white p-5 shadow-sm">
            <SectionTitle title="Invoice Customization" subtitle="Configure template branding and legal text." />
            <div className="space-y-4">
              <label className="block text-sm">
                <span className="font-medium text-slate-600">Logo URL</span>
                <input
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                  value={template.logoUrl}
                  onChange={e => setTemplate(prev => ({ ...prev, logoUrl: e.target.value }))}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-600">Branch Name</span>
                <input
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                  value={template.branchName}
                  onChange={e => setTemplate(prev => ({ ...prev, branchName: e.target.value }))}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-600">Branch Address</span>
                <textarea
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                  rows={3}
                  value={template.branchAddress}
                  onChange={e => setTemplate(prev => ({ ...prev, branchAddress: e.target.value }))}
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-600">Legal Text</span>
                <textarea
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                  rows={4}
                  value={template.legalText}
                  onChange={e => setTemplate(prev => ({ ...prev, legalText: e.target.value }))}
                />
              </label>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border bg-white p-5 shadow-sm">
              <SectionTitle title="GST Invoice Generator" subtitle="Generate a GST-compliant invoice with PCPNDT notes." />
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-sm">
                  <span className="font-medium text-slate-600">Customer ID</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.patientId}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, patientId: e.target.value }))}
                  />
                </label>
                <label className="text-sm">
                  <span className="font-medium text-slate-600">Service Type</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.serviceType}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, serviceType: e.target.value }))}
                  />
                </label>
                <label className="text-sm">
                  <span className="font-medium text-slate-600">Item Name</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.itemName}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, itemName: e.target.value }))}
                  />
                </label>
                <label className="text-sm">
                  <span className="font-medium text-slate-600">Unit Price</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.unitPrice}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, unitPrice: e.target.value }))}
                  />
                </label>
                <label className="text-sm">
                  <span className="font-medium text-slate-600">Quantity</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.quantity}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, quantity: e.target.value }))}
                  />
                </label>
                <label className="text-sm">
                  <span className="font-medium text-slate-600">Due Days</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.dueDays}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, dueDays: e.target.value }))}
                  />
                </label>
                <label className="text-sm md:col-span-2">
                  <span className="font-medium text-slate-600">Notes</span>
                  <textarea
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    rows={3}
                    value={invoiceDraft.notes}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, notes: e.target.value }))}
                  />
                </label>
                <label className="text-sm md:col-span-2">
                  <span className="font-medium text-slate-600">Custom Legal Text</span>
                  <textarea
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    rows={3}
                    value={invoiceDraft.legalText}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, legalText: e.target.value }))}
                  />
                </label>
                <label className="text-sm">
                  <span className="font-medium text-slate-600">GST Rate Override</span>
                  <input
                    className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2"
                    value={invoiceDraft.gstRate}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, gstRate: e.target.value }))}
                  />
                </label>
                <label className="flex items-center gap-2 text-sm md:pt-7">
                  <input
                    type="checkbox"
                    checked={invoiceDraft.gstExempt}
                    onChange={e => setInvoiceDraft(prev => ({ ...prev, gstExempt: e.target.checked }))}
                  />
                  GST exempt
                </label>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <button className="rounded-xl bg-slate-900 px-4 py-2 font-semibold text-white" onClick={() => void generateInvoice()} disabled={invoiceLoading}>
                  {invoiceLoading ? 'Generating...' : 'Generate Invoice'}
                </button>
              </div>
              {invoiceResult ? (
                <div className="mt-4 rounded-2xl border bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-slate-700">
                    {invoiceResult.invoice_number} · {invoiceResult.patient_name}
                  </p>
                  <p className="text-sm text-slate-600">Final Amount: {formatCurrency(invoiceResult.final_amount)}</p>
                  <p className="text-sm text-slate-500">{invoiceResult.legal_text}</p>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {selectedTransaction ? (
        <Modal title="Transaction Detail" onClose={() => setSelectedTransaction(null)}>
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <DetailItem label="Customer" value={selectedTransaction.patient_name} />
              <DetailItem label="MenuItem" value={selectedTransaction.test_name} />
              <DetailItem label="Method" value={selectedTransaction.method} />
              <DetailItem label="Status" value={selectedTransaction.status} />
              <DetailItem label="Receipt" value={selectedTransaction.receipt_number || '—'} />
              <DetailItem label="Payment Date" value={formatDateTime(selectedTransaction.payment_date)} />
            </div>
            <DetailItem label="Amount" value={formatCurrency(selectedTransaction.amount)} />
            <DetailItem label="Discount Applied" value={formatCurrency(selectedTransaction.discount_applied)} />
            <DetailItem label="Notes" value={selectedTransaction.notes || '—'} />
            <button
              className="rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white"
              onClick={() => void openCustomerFinancial(selectedTransaction.patient_id ? Number(selectedTransaction.patient_id) : undefined)}
            >
              Open Customer Financial Profile
            </button>
          </div>
        </Modal>
      ) : null}

      {patientFinancial && activeTab !== 'people' ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-2xl font-bold text-slate-900">{patientFinancial.full_name}</h3>
                <p className="text-sm text-slate-500">{patientFinancial.patient_code || `Customer #${patientFinancial.patient_id}`}</p>
              </div>
              <button className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold" onClick={() => setCustomerFinancial(null)}>
                Close
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <MetricCard title="MenuItems" value={String(patientFinancial.total_menu_items)} />
              <MetricCard title="Billed" value={formatCurrency(patientFinancial.total_billed)} tone="amber" />
              <MetricCard title="Paid" value={formatCurrency(patientFinancial.total_paid)} tone="emerald" />
              <MetricCard title="Outstanding" value={formatCurrency(patientFinancial.outstanding_balance)} tone="rose" />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-900">{value}</p>
    </div>
  )
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h3 className="text-2xl font-bold text-slate-900">{title}</h3>
          <button className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold" onClick={onClose}>
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
