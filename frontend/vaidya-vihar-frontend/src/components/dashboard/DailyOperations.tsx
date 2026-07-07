import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
  ColumnDef,
} from '@tanstack/react-table'
import axios from 'axios'
import toast from 'react-hot-toast'
import DatePicker from 'react-datepicker'
import QRCode from 'react-qr-code'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import 'react-datepicker/dist/react-datepicker.css'
import { useAuth } from '../../contexts/AuthContext'

interface DailyEntry {
  id: number
  branch_id: number
  auto_patient_id: string
  auto_entry_datetime: string
  patient_name: string
  mobile: string
  address: string
  referred_doctor?: string
  test_name: string
  report_pdf_url?: string
  status: string
  fee_amount: number
  tax_percent: number
  total_amount: number
  payment_method: string
  is_paid: boolean
  remarks?: string
  created_by: number
  created_at: string
  updated_at: string
}

interface DailyStats {
  total_revenue: number
  total_expense: number
  net_profit: number
  patient_count: number
  date: string
}

interface DailyExpense {
  id: number
  expense_item: string
  cost: number
  description?: string
  entry_date: string
}

interface BranchInfo {
  id: number
  name: string
  phone?: string
  email?: string
  address?: string
}

type ExportPeriod = 'daily' | 'monthly' | 'yearly'
type ExportFormat = 'csv' | 'pdf'

const columnHelper = createColumnHelper<DailyEntry>()

export default function DailyOperations() {
  const { user, token } = useAuth()
  const [entries, setEntries] = useState<DailyEntry[]>([])
  const [stats, setStats] = useState<DailyStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [sorting, setSorting] = useState<SortingState>([])

  const [patientNameFilter, setPatientNameFilter] = useState('')
  const [referredDoctorFilter, setReferredDoctorFilter] = useState('')
  const [testNameFilter, setTestNameFilter] = useState('')
  const [startDate, setStartDate] = useState<Date | null>(null)
  const [endDate, setEndDate] = useState<Date | null>(null)

  const [expenseForm, setExpenseForm] = useState({
    expense_item: '',
    cost: '',
    description: '',
  })

  const [uploadingEntryId, setUploadingEntryId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  const [deleteConfirmEntry, setDeleteConfirmEntry] = useState<DailyEntry | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const [pdfViewerEntry, setPdfViewerEntry] = useState<DailyEntry | null>(null)
  const [pdfShareEntry, setPdfShareEntry] = useState<DailyEntry | null>(null)

  const [upiQREntry, setUpiQREntry] = useState<DailyEntry | null>(null)
  const [branchBankDetails, setBranchBankDetails] = useState<any>(null)
  const upiFetchInProgressRef = useRef(false)
  const upiWarningLockRef = useRef(false)

  const [billEntry, setBillEntry] = useState<DailyEntry | null>(null)
  const [branchDetailsById, setBranchDetailsById] = useState<Record<number, BranchInfo>>({})

  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [openActionsMenuId, setOpenActionsMenuId] = useState<number | null>(null)

  const [isExportModalOpen, setIsExportModalOpen] = useState(false)
  const [exportPeriod, setExportPeriod] = useState<ExportPeriod>('daily')
  const [exportFormat, setExportFormat] = useState<ExportFormat>('csv')
  const [isExporting, setIsExporting] = useState(false)

  const API_BASE = (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://localhost:8000'
      : window.location.origin)

  const requestConfig = {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }

  const parseNumber = (value: unknown, fallback = 0) => {
    const n = Number(value)
    return Number.isFinite(n) ? n : fallback
  }

  const calculateTotal = (entry: Partial<DailyEntry>) => {
    const fee = parseNumber(entry.fee_amount, 0)
    const tax = parseNumber(entry.tax_percent, 0)
    return fee + (fee * tax) / 100
  }

  const showSingleUPIWarning = () => {
    if (upiWarningLockRef.current) return
    upiWarningLockRef.current = true
    toast.error('UPI ID not configured. Please add UPI ID in Branch Settings.', { id: 'upi-config-warning' })
    window.setTimeout(() => {
      upiWarningLockRef.current = false
    }, 2000)
  }

  const fetchBranchDetails = useCallback(async (branchId: number): Promise<BranchInfo | null> => {
    if (!branchId) return null
    if (branchDetailsById[branchId]) return branchDetailsById[branchId]

    try {
      const res = await axios.get(`${API_BASE}/api/branches/${branchId}`, requestConfig)
      const branchInfo: BranchInfo = {
        id: res.data.id,
        name: res.data.name,
        address: res.data.address,
        phone: res.data.phone,
        email: res.data.email,
      }
      setBranchDetailsById(prev => ({ ...prev, [branchId]: branchInfo }))
      return branchInfo
    } catch {
      return null
    }
  }, [API_BASE, branchDetailsById, token])

  const fetchEntries = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (patientNameFilter) params.append('patient_name', patientNameFilter)
      if (referredDoctorFilter) params.append('referred_doctor', referredDoctorFilter)
      if (testNameFilter) params.append('test_name', testNameFilter)
      if (startDate) params.append('start_date', startDate.toISOString().split('T')[0])
      if (endDate) params.append('end_date', endDate.toISOString().split('T')[0])

      const res = await axios.get(`${API_BASE}/api/daily-entries?${params.toString()}`, requestConfig)
      setEntries(res.data || [])
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to fetch entries')
    } finally {
      setLoading(false)
    }
  }, [token, patientNameFilter, referredDoctorFilter, testNameFilter, startDate, endDate, API_BASE])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const res = await axios.get(`${API_BASE}/api/daily-stats`, requestConfig)
      setStats(res.data)
    } catch {
      // Keep dashboard resilient even if stats API fails.
    }
  }, [token, API_BASE])

  useEffect(() => {
    fetchEntries()
    fetchStats()
  }, [fetchEntries, fetchStats])

  const updateEntryField = useCallback(async (
    rowId: number,
    field: keyof DailyEntry,
    value: any,
    options?: { silentSuccess?: boolean }
  ) => {
    const originalEntry = entries.find(e => e.id === rowId)
    if (!originalEntry) return

    const normalizedValue = field === 'fee_amount' || field === 'tax_percent'
      ? parseNumber(value, 0)
      : value

    const optimisticEntries = entries.map(entry => {
      if (entry.id !== rowId) return entry
      const updated = { ...entry, [field]: normalizedValue }
      return {
        ...updated,
        total_amount: calculateTotal(updated),
      }
    })
    setEntries(optimisticEntries)

    try {
      await axios.put(
        `${API_BASE}/api/daily-entries/${rowId}`,
        {
          [field]: normalizedValue,
        },
        requestConfig
      )
      if (!options?.silentSuccess) {
        toast.success('Entry auto-saved', { id: `entry-save-${rowId}` })
      }
      setLastSaved(new Date())
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save entry', { id: `entry-save-${rowId}` })
      fetchEntries()
    }
  }, [entries, API_BASE, token])

  const showUPIQR = useCallback(async (entry: DailyEntry) => {
    if (upiFetchInProgressRef.current) return
    upiFetchInProgressRef.current = true

    try {
      const res = await axios.get(`${API_BASE}/api/branches/${entry.branch_id}/bank-details`, requestConfig)
      if (!res.data?.upi_id) {
        showSingleUPIWarning()
        return
      }
      await fetchBranchDetails(entry.branch_id)
      setBranchBankDetails(res.data)
      setUpiQREntry(entry)
    } catch {
      showSingleUPIWarning()
      return
    } finally {
      upiFetchInProgressRef.current = false
    }
  }, [API_BASE, token, fetchBranchDetails])

  const handlePaymentMethodChange = async (entry: DailyEntry, method: string) => {
    await updateEntryField(entry.id, 'payment_method', method)
    if (method === 'UPI' || method === 'QR') {
      showUPIQR({ ...entry, payment_method: method })
    }
  }

  const addNewEntry = async () => {
    try {
      await axios.post(
        `${API_BASE}/api/daily-entries`,
        {
          patient_name: 'New Patient',
          mobile: '0000000000',
          address: 'Address',
          test_name: 'Test Name',
          fee_amount: 100,
          tax_percent: 0,
          payment_method: 'Cash',
          is_paid: true,
          auto_entry_datetime: new Date().toLocaleString(),
        },
        requestConfig
      )
      toast.success('New entry added')
      fetchEntries()
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to add entry')
    }
  }

  const confirmDelete = async () => {
    if (!deleteConfirmEntry) return
    setIsDeleting(true)
    try {
      await axios.delete(`${API_BASE}/api/daily-entries/${deleteConfirmEntry.id}`, requestConfig)
      toast.success('Entry deleted successfully')
      setDeleteConfirmEntry(null)
      fetchEntries()
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to delete entry')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleFileUpload = async (entryId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      await axios.post(
        `${API_BASE}/api/daily-entries/${entryId}/upload-report`,
        formData,
        {
          headers: {
            ...requestConfig.headers,
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      toast.success('Report uploaded successfully')
      fetchEntries()
      setUploadingEntryId(null)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to upload report')
    }
  }

  const viewPDF = (entry: DailyEntry) => {
    if (!entry.report_pdf_url) {
      toast.error('No PDF uploaded yet')
      return
    }
    setPdfViewerEntry(entry)
  }

  const deletePDF = async (entryId: number) => {
    if (!window.confirm('Delete this PDF report?')) return
    try {
      await axios.delete(`${API_BASE}/api/daily-entries/${entryId}/report`, requestConfig)
      toast.success('PDF deleted successfully')
      fetchEntries()
      setPdfViewerEntry(null)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to delete PDF')
    }
  }

  const sharePDFWhatsApp = (entry: DailyEntry) => {
    if (!entry.report_pdf_url) {
      toast.error('No PDF uploaded yet')
      return
    }
    const filename = entry.report_pdf_url.replace('/uploads/', '')
    const pdfUrl = `${API_BASE}/api/files/${filename}`
    const message = `Dear patient, your diagnostic report is ready. Please download it here: ${pdfUrl}`
    window.open(`https://wa.me/?text=${encodeURIComponent(message)}`, '_blank')
  }

  const sharePDFEmail = (entry: DailyEntry) => {
    if (!entry.report_pdf_url) {
      toast.error('No PDF uploaded yet')
      return
    }
    const filename = entry.report_pdf_url.replace('/uploads/', '')
    const pdfUrl = `${API_BASE}/api/files/${filename}`
    const subject = 'Your Diagnostic Report'
    const body = `Dear patient, your diagnostic report is ready. Please download it here: ${pdfUrl}`
    window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }

  const addExpense = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await axios.post(
        `${API_BASE}/api/daily-expenses`,
        {
          expense_item: expenseForm.expense_item,
          cost: parseFloat(expenseForm.cost),
          description: expenseForm.description,
        },
        requestConfig
      )
      toast.success('Expense added')
      setExpenseForm({ expense_item: '', cost: '', description: '' })
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to add expense')
    }
  }

  const clearFilters = () => {
    setPatientNameFilter('')
    setReferredDoctorFilter('')
    setTestNameFilter('')
    setStartDate(null)
    setEndDate(null)
  }

  const scrollToTop = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({ top: scrollContainerRef.current.scrollHeight, behavior: 'smooth' })
    }
  }

  const openBillModal = async (entry: DailyEntry) => {
    await fetchBranchDetails(entry.branch_id)
    setBillEntry(entry)
  }

  const handlePrintBill = () => {
    window.print()
  }

  const handleDownloadBillPDF = async () => {
    const billElement = document.getElementById('bill-invoice-content')
    if (!billElement) return

    try {
      const canvas = await html2canvas(billElement, {
        scale: 2,
        useCORS: true,
        logging: false,
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')
      const pdfWidth = pdf.internal.pageSize.getWidth()
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight)
      pdf.save(`Invoice_${billEntry?.auto_patient_id || 'bill'}.pdf`)
      toast.success('Invoice downloaded successfully')
    } catch {
      toast.error('Failed to generate PDF')
    }
  }

  const getPeriodRange = (period: ExportPeriod) => {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()

    if (period === 'daily') {
      const d = now.toISOString().split('T')[0]
      return { start: d, end: d, label: `Daily_${now.toISOString().slice(0, 10).replace(/-/g, '')}` }
    }

    if (period === 'monthly') {
      const start = new Date(year, month, 1)
      const end = new Date(year, month + 1, 0)
      const monthLabel = now.toLocaleString('en-US', { month: 'short' })
      return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0],
        label: `Monthly_${monthLabel}${year}`,
      }
    }

    const start = new Date(year, 0, 1)
    const end = new Date(year, 11, 31)
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      label: `Yearly_${year}`,
    }
  }

  const sanitizeFilePart = (value: string) => value.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '')

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  const toCsvCell = (value: unknown) => {
    const str = String(value ?? '')
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  const exportToCSV = async (period: ExportPeriod) => {
    const range = getPeriodRange(period)
    const [entryRes, expenseRes] = await Promise.all([
      axios.get(`${API_BASE}/api/daily-entries?start_date=${range.start}&end_date=${range.end}`, requestConfig),
      axios.get(`${API_BASE}/api/daily-expenses?start_date=${range.start}&end_date=${range.end}`, requestConfig),
    ])

    const periodEntries: DailyEntry[] = entryRes.data || []
    const periodExpenses: DailyExpense[] = expenseRes.data || []

    const branchId = periodEntries[0]?.branch_id || user?.branch_id
    let branchName = 'Branch'
    if (branchId) {
      const branch = await fetchBranchDetails(branchId)
      if (branch?.name) branchName = branch.name
    }

    const lines: string[] = []
    lines.push(`Branch Name,${toCsvCell(branchName)}`)
    lines.push(`Period,${period}`)
    lines.push('')

    if (period === 'monthly') {
      lines.push(['Sr. No.', 'Patient Name', 'Address', 'Referred Doctor', 'Fee (INR)', 'Date'].join(','))
      periodEntries.forEach((entry, index) => {
        lines.push([
          index + 1,
          entry.patient_name,
          entry.address,
          entry.referred_doctor || '',
          parseNumber(entry.fee_amount).toFixed(2),
          new Date(entry.auto_entry_datetime).toLocaleDateString(),
        ].map(toCsvCell).join(','))
      })
    } else {
      lines.push([
        'Sr. No.',
        'Patient ID',
        'Patient Name',
        'Mobile',
        'Address',
        'Referred Doctor',
        'Test Name',
        'Fee (INR)',
        'Tax %',
        'Total (INR)',
        'Payment Method',
        'Status',
        'Date Time',
      ].join(','))

      periodEntries.forEach((entry, index) => {
        lines.push([
          index + 1,
          entry.auto_patient_id,
          entry.patient_name,
          entry.mobile,
          entry.address,
          entry.referred_doctor || '',
          entry.test_name,
          parseNumber(entry.fee_amount).toFixed(2),
          parseNumber(entry.tax_percent).toFixed(2),
          calculateTotal(entry).toFixed(2),
          entry.payment_method,
          entry.status,
          new Date(entry.auto_entry_datetime).toLocaleString(),
        ].map(toCsvCell).join(','))
      })

      if (period === 'yearly') {
        const totalBusiness = periodEntries.reduce((sum, row) => sum + calculateTotal(row), 0)
        const totalExpenses = periodExpenses.reduce((sum, row) => sum + parseNumber(row.cost), 0)
        lines.push('')
        lines.push(['Yearly Summary', 'Amount (INR)'].map(toCsvCell).join(','))
        lines.push(['Total Business', totalBusiness.toFixed(2)].map(toCsvCell).join(','))
        lines.push(['Total Expenses', totalExpenses.toFixed(2)].map(toCsvCell).join(','))
      }
    }

    const branchIdFromEntries = periodEntries[0]?.branch_id || user?.branch_id
    const branchInfo = branchIdFromEntries ? await fetchBranchDetails(branchIdFromEntries) : null
    const finalBranchName = sanitizeFilePart(branchInfo?.name || branchName)
    const filename = `${finalBranchName}_${range.label}.csv`

    downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' }), filename)
  }

  const drawPdfCover = (
    pdf: jsPDF,
    branchName: string,
    period: ExportPeriod,
    totalRecords: number,
    totalRevenue: number,
    totalExpense: number,
    netProfit: number
  ) => {
    pdf.setFillColor(21, 91, 179)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.setTextColor(255, 255, 255)
    pdf.setFontSize(22)
    pdf.text('Business Analysis Report', 14, 20)
    pdf.setFontSize(12)
    pdf.text(branchName, 14, 30)

    pdf.setTextColor(0, 0, 0)
    pdf.setFontSize(13)
    pdf.text(`Period: ${period.toUpperCase()}`, 14, 58)
    pdf.text(`Generated: ${new Date().toLocaleString()}`, 14, 66)
    pdf.text(`Total Records: ${totalRecords}`, 14, 74)

    pdf.setFillColor(239, 246, 255)
    pdf.roundedRect(14, 84, 182, 45, 3, 3, 'F')
    pdf.setFontSize(12)
    pdf.text(`Total Revenue: INR ${totalRevenue.toFixed(2)}`, 20, 98)
    pdf.text(`Total Expense: INR ${totalExpense.toFixed(2)}`, 20, 108)
    pdf.text(`Net Profit: INR ${netProfit.toFixed(2)}`, 20, 118)
  }

  const exportToPDF = async (period: ExportPeriod) => {
    const range = getPeriodRange(period)
    const [entryRes, expenseRes] = await Promise.all([
      axios.get(`${API_BASE}/api/daily-entries?start_date=${range.start}&end_date=${range.end}`, requestConfig),
      axios.get(`${API_BASE}/api/daily-expenses?start_date=${range.start}&end_date=${range.end}`, requestConfig),
    ])

    const periodEntries: DailyEntry[] = entryRes.data || []
    const periodExpenses: DailyExpense[] = expenseRes.data || []
    const revenue = periodEntries.reduce((sum, row) => sum + calculateTotal(row), 0)
    const expense = periodExpenses.reduce((sum, row) => sum + parseNumber(row.cost), 0)
    const net = revenue - expense

    const branchId = periodEntries[0]?.branch_id || user?.branch_id
    const branchInfo = branchId ? await fetchBranchDetails(branchId) : null
    const branchName = branchInfo?.name || 'Branch'

    const pdf = new jsPDF('p', 'mm', 'a4')
    drawPdfCover(pdf, branchName, period, periodEntries.length, revenue, expense, net)

    pdf.addPage()
    pdf.setFontSize(12)
    pdf.text('Daily Entries Table', 14, 14)

    const headers = ['#', 'Patient', 'Test', 'Fee', 'Tax%', 'Total', 'Payment', 'Date']
    const colX = [14, 24, 62, 100, 120, 136, 154, 176]
    const lineHeight = 7
    let y = 22

    headers.forEach((h, i) => {
      pdf.setFontSize(9)
      pdf.text(h, colX[i], y)
    })
    y += 4
    pdf.line(14, y, 198, y)
    y += 5

    periodEntries.forEach((entry, index) => {
      if (y > 280) {
        pdf.addPage()
        y = 20
      }
      const row = [
        String(index + 1),
        (entry.patient_name || '').slice(0, 16),
        (entry.test_name || '').slice(0, 18),
        parseNumber(entry.fee_amount).toFixed(0),
        parseNumber(entry.tax_percent).toFixed(0),
        calculateTotal(entry).toFixed(0),
        entry.payment_method,
        new Date(entry.auto_entry_datetime).toLocaleDateString(),
      ]
      row.forEach((cell, i) => {
        pdf.setFontSize(8)
        pdf.text(cell, colX[i], y)
      })
      y += lineHeight
    })

    if (y > 250) {
      pdf.addPage()
      y = 20
    }

    y += 8
    pdf.line(14, y, 198, y)
    y += 8
    pdf.setFontSize(11)
    pdf.text(`Summary Revenue: INR ${revenue.toFixed(2)}`, 14, y)
    y += 7
    pdf.text(`Summary Expense: INR ${expense.toFixed(2)}`, 14, y)
    y += 7
    pdf.text(`Summary Net Profit: INR ${net.toFixed(2)}`, 14, y)

    const filename = `${sanitizeFilePart(branchName)}_${range.label}.pdf`
    pdf.save(filename)
  }

  const handleExportData = async () => {
    setIsExporting(true)
    try {
      if (exportFormat === 'csv') {
        await exportToCSV(exportPeriod)
      } else {
        await exportToPDF(exportPeriod)
      }
      toast.success('Export completed successfully')
      setIsExportModalOpen(false)
    } catch {
      toast.error('Failed to export data')
    } finally {
      setIsExporting(false)
    }
  }

  const columns = useMemo<ColumnDef<DailyEntry, any>[]>(() => [
    columnHelper.display({
      id: 'row_number',
      header: 'Sr.No',
      size: 38,
      minSize: 38,
      cell: info => <span className="font-bold text-slate-600">{info.row.index + 1}</span>,
    }),
    columnHelper.accessor('auto_patient_id', {
      header: 'Patient ID',
      size: 130,
      minSize: 130,
      cell: info => <span className="font-mono text-xs">{info.getValue()}</span>,
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Actions',
      size: 48,
      minSize: 48,
      cell: info => (
        <div className="relative">
          <button
            onClick={() => setOpenActionsMenuId(openActionsMenuId === info.row.original.id ? null : info.row.original.id)}
            className="h-7 w-7 rounded-md border border-slate-200 text-slate-700 text-sm hover:bg-slate-100"
            title="More Actions"
          >
            ⋮
          </button>
          {openActionsMenuId === info.row.original.id && (
            <ul className="absolute left-0 mt-2 w-44 bg-white shadow-xl rounded-lg border z-[60] py-1">
              {info.row.original.report_pdf_url ? (
                <>
                  <li>
                    <button
                      onClick={() => {
                        viewPDF(info.row.original)
                        setOpenActionsMenuId(null)
                      }}
                      className="w-full px-3 py-2 text-left text-xs hover:bg-slate-100"
                    >
                      View Report
                    </button>
                  </li>
                  <li>
                    <button
                      onClick={() => {
                        setPdfShareEntry(info.row.original)
                        setOpenActionsMenuId(null)
                      }}
                      className="w-full px-3 py-2 text-left text-xs hover:bg-slate-100"
                    >
                      Share PDF
                    </button>
                  </li>
                </>
              ) : (
                <li>
                  <button
                    onClick={() => {
                      setUploadingEntryId(info.row.original.id)
                      fileInputRef.current?.click()
                      setOpenActionsMenuId(null)
                    }}
                    className="w-full px-3 py-2 text-left text-xs hover:bg-slate-100"
                  >
                    Upload PDF
                  </button>
                </li>
              )}
              <li>
                <button
                  onClick={() => {
                    showUPIQR(info.row.original)
                    setOpenActionsMenuId(null)
                  }}
                  className="w-full px-3 py-2 text-left text-xs hover:bg-slate-100"
                >
                  Generate UPI QR
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    openBillModal(info.row.original)
                    setOpenActionsMenuId(null)
                  }}
                  className="w-full px-3 py-2 text-left text-xs hover:bg-slate-100"
                >
                  Generate Bill/Invoice
                </button>
              </li>
              <li>
                <button
                  onClick={() => {
                    setDeleteConfirmEntry(info.row.original)
                    setOpenActionsMenuId(null)
                  }}
                  className="w-full px-3 py-2 text-left text-xs text-red-600 hover:bg-red-50"
                >
                  Delete Entry
                </button>
              </li>
            </ul>
          )}
        </div>
      ),
    }),
    columnHelper.accessor('patient_name', {
      header: 'Patient Name',
      size: 120,
      minSize: 120,
      cell: info => (
        <input
          type="text"
          defaultValue={info.getValue()}
          onBlur={e => updateEntryField(info.row.original.id, 'patient_name', e.target.value)}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('mobile', {
      header: 'Mobile',
      size: 105,
      minSize: 105,
      cell: info => (
        <input
          type="text"
          defaultValue={info.getValue()}
          onBlur={e => updateEntryField(info.row.original.id, 'mobile', e.target.value)}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('auto_entry_datetime', {
      header: 'Date & Time',
      size: 130,
      minSize: 130,
      cell: info => (
        <input
          type="text"
          defaultValue={new Date(info.getValue()).toLocaleString()}
          onBlur={e => updateEntryField(info.row.original.id, 'auto_entry_datetime', e.target.value)}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('address', {
      header: 'Address',
      size: 130,
      minSize: 130,
      cell: info => (
        <input
          type="text"
          defaultValue={info.getValue()}
          onBlur={e => updateEntryField(info.row.original.id, 'address', e.target.value)}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('referred_doctor', {
      header: 'Doctor',
      size: 100,
      minSize: 100,
      cell: info => (
        <input
          type="text"
          defaultValue={info.getValue() || ''}
          onBlur={e => updateEntryField(info.row.original.id, 'referred_doctor', e.target.value)}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('test_name', {
      header: 'Test Name',
      size: 110,
      minSize: 110,
      cell: info => (
        <input
          type="text"
          defaultValue={info.getValue()}
          onBlur={e => updateEntryField(info.row.original.id, 'test_name', e.target.value)}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('fee_amount', {
      header: 'Fee (INR)',
      size: 75,
      minSize: 75,
      cell: info => (
        <input
          type="number"
          defaultValue={parseNumber(info.getValue())}
          onBlur={e => updateEntryField(info.row.original.id, 'fee_amount', parseNumber(e.target.value, 0))}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.accessor('tax_percent', {
      header: 'Tax %',
      size: 60,
      minSize: 60,
      cell: info => (
        <select
          defaultValue={parseNumber(info.getValue(), 0)}
          onChange={e => updateEntryField(info.row.original.id, 'tax_percent', parseNumber(e.target.value, 0))}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        >
          <option value="0">0%</option>
          <option value="5">5%</option>
          <option value="12">12%</option>
          <option value="18">18%</option>
        </select>
      ),
    }),
    columnHelper.display({
      id: 'total_amount',
      header: 'Total (INR)',
      size: 80,
      minSize: 80,
      meta: { editable: false },
      cell: info => {
        const row = info.row.original
        const total = parseNumber(row.fee_amount, 0) + (parseNumber(row.fee_amount, 0) * parseNumber(row.tax_percent, 0)) / 100
        return <span className="font-bold text-blue-700">INR {total.toFixed(2)}</span>
      },
    }),
    columnHelper.accessor('payment_method', {
      header: 'Payment',
      size: 130,
      minSize: 130,
      cell: info => (
        <select
          defaultValue={info.getValue()}
          onChange={e => handlePaymentMethodChange(info.row.original, e.target.value)}
          className="w-full min-w-[120px] px-1 py-1 border rounded focus:outline-none focus:border-blue-500"
        >
          <option value="Cash">Cash</option>
          <option value="Card">Card</option>
          <option value="UPI">UPI</option>
          <option value="Online">Online</option>
          <option value="QR">QR</option>
        </select>
      ),
    }),
    columnHelper.accessor('status', {
      header: 'Status',
      size: 85,
      minSize: 85,
      cell: info => {
        const status = info.getValue()
        const color = status === 'Completed' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'
        return <span className={`px-2 py-1 rounded-full text-xs font-bold ${color}`}>{status}</span>
      },
    }),
  ], [
    updateEntryField,
    handlePaymentMethodChange,
    showUPIQR,
    openBillModal,
    openActionsMenuId,
  ])

  const table = useReactTable({
    data: entries,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    meta: {
      onCellValueChanged: updateEntryField,
    },
  })

  if (user?.role !== 'branch_admin' && user?.role !== 'super_admin') {
    return (
      <div className="premium-card p-8">
        <h2 className="text-2xl font-black gradient-text">Daily Operations</h2>
        <p className="text-slate-600 mt-3">Access restricted to Branch Admin and Super Admin only.</p>
      </div>
    )
  }

  const invoiceBranch = billEntry ? branchDetailsById[billEntry.branch_id] : undefined
  const invoiceSubtotal = billEntry ? parseNumber(billEntry.fee_amount, 0) : 0
  const invoiceTaxAmount = billEntry ? (invoiceSubtotal * parseNumber(billEntry.tax_percent, 0)) / 100 : 0
  const invoiceGrandTotal = invoiceSubtotal + invoiceTaxAmount

  return (
    <div className="space-y-6">
      <div className="premium-card p-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-black gradient-text">Daily Operations</h2>
            <p className="text-slate-600 mt-2">Manage daily patient entries, billing, payment, and exports</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={addNewEntry}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold hover:shadow-xl transition"
            >
              Add New Entry
            </button>
            <button
              onClick={fetchEntries}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold hover:shadow-xl transition"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="premium-card p-6 bg-gradient-to-br from-emerald-50 to-teal-50">
            <p className="text-xs uppercase tracking-wider text-emerald-600 font-bold mb-2">Total Revenue</p>
            <p className="text-3xl font-black text-emerald-700">INR {parseNumber(stats.total_revenue).toLocaleString()}</p>
          </div>
          <div className="premium-card p-6 bg-gradient-to-br from-red-50 to-rose-50">
            <p className="text-xs uppercase tracking-wider text-red-600 font-bold mb-2">Total Expense</p>
            <p className="text-3xl font-black text-red-700">INR {parseNumber(stats.total_expense).toLocaleString()}</p>
          </div>
          <div className="premium-card p-6 bg-gradient-to-br from-blue-50 to-cyan-50">
            <p className="text-xs uppercase tracking-wider text-blue-600 font-bold mb-2">Net Profit</p>
            <p className="text-3xl font-black text-blue-700">INR {parseNumber(stats.net_profit).toLocaleString()}</p>
          </div>
          <div className="premium-card p-6 bg-gradient-to-br from-violet-50 to-fuchsia-50">
            <p className="text-xs uppercase tracking-wider text-violet-600 font-bold mb-2">Patient Count</p>
            <p className="text-3xl font-black text-violet-700">{stats.patient_count}</p>
          </div>
        </div>
      )}

      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">Advanced Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <input
            type="text"
            placeholder="Patient Name"
            value={patientNameFilter}
            onChange={e => setPatientNameFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Referred Doctor"
            value={referredDoctorFilter}
            onChange={e => setReferredDoctorFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Test Name"
            value={testNameFilter}
            onChange={e => setTestNameFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <DatePicker
            selected={startDate}
            onChange={date => setStartDate(date)}
            placeholderText="Start Date"
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none w-full"
          />
          <DatePicker
            selected={endDate}
            onChange={date => setEndDate(date)}
            placeholderText="End Date"
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none w-full"
          />
        </div>
        <div className="flex gap-3 mt-4">
          <button
            onClick={fetchEntries}
            className="px-6 py-2 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition"
          >
            Apply Filters
          </button>
          <button
            onClick={clearFilters}
            className="px-6 py-2 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300 transition"
          >
            Clear Filters
          </button>
        </div>
      </div>

      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">Export Data</h3>
        <button
          onClick={() => setIsExportModalOpen(true)}
          className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-700 text-white font-bold hover:shadow-xl transition"
        >
          Open Export Data
        </button>
      </div>

      <div className="premium-card p-6 relative">
        <h3 className="text-xl font-black text-slate-900 mb-4">Daily Entries ({entries.length} records)</h3>
        <div ref={scrollContainerRef} className="w-full max-h-[600px] overflow-x-auto overflow-y-auto border rounded-lg relative">
          <table className="w-full min-w-[1080px] border-collapse" style={{ minWidth: '1080px' }}>
            <thead className="bg-slate-100 sticky top-0 z-10">
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <th
                      key={header.id}
                      className="border border-slate-300 px-2 py-2 text-left text-xs font-bold text-slate-700 cursor-pointer hover:bg-slate-200"
                      style={{ width: header.getSize(), minWidth: header.getSize() }}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: ' ▲', desc: ' ▼' }[header.column.getIsSorted() as string] ?? null}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={table.getAllColumns().length} className="text-center py-8 text-slate-500">Loading entries...</td>
                </tr>
              ) : (
                table.getRowModel().rows.map(row => (
                  <tr key={row.id} className="hover:bg-slate-50">
                    {row.getVisibleCells().map(cell => (
                      <td
                        key={cell.id}
                        className="border border-slate-300 px-2 py-1 text-xs align-top"
                        style={{ width: cell.column.getSize(), minWidth: cell.column.getSize() }}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {entries.length > 10 && (
            <div className="absolute bottom-4 right-4 flex flex-col gap-2 z-20">
              <button
                onClick={scrollToTop}
                className="p-3 bg-white text-slate-700 rounded-full shadow-lg hover:shadow-xl hover:bg-slate-50 transition border border-slate-200"
              >
                ↑
              </button>
              <button
                onClick={scrollToBottom}
                className="p-3 bg-white text-slate-700 rounded-full shadow-lg hover:shadow-xl hover:bg-slate-50 transition border border-slate-200"
              >
                ↓
              </button>
            </div>
          )}
        </div>

        {lastSaved && (
          <div className="mt-3 text-right text-sm text-slate-500">Last saved: {lastSaved.toLocaleTimeString()}</div>
        )}
      </div>

      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">Add Daily Expense</h3>
        <form onSubmit={addExpense} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Expense Item"
            value={expenseForm.expense_item}
            onChange={e => setExpenseForm({ ...expenseForm, expense_item: e.target.value })}
            required
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Cost"
            value={expenseForm.cost}
            onChange={e => setExpenseForm({ ...expenseForm, cost: e.target.value })}
            required
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={expenseForm.description}
            onChange={e => setExpenseForm({ ...expenseForm, description: e.target.value })}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <button
            type="submit"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold hover:shadow-xl transition"
          >
            Add Expense
          </button>
        </form>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={e => {
          if (e.target.files && e.target.files[0] && uploadingEntryId) {
            handleFileUpload(uploadingEntryId, e.target.files[0])
          }
        }}
      />

      {deleteConfirmEntry && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-black text-red-600 mb-4">Confirm Deletion</h3>
            <div className="bg-slate-100 p-4 rounded-xl mb-6">
              <p className="text-sm"><strong>Patient:</strong> {deleteConfirmEntry.patient_name}</p>
              <p className="text-sm"><strong>ID:</strong> {deleteConfirmEntry.auto_patient_id}</p>
              <p className="text-sm"><strong>Test:</strong> {deleteConfirmEntry.test_name}</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirmEntry(null)}
                disabled={isDeleting}
                className="flex-1 px-6 py-3 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={isDeleting}
                className="flex-1 px-6 py-3 rounded-xl bg-red-600 text-white font-bold hover:bg-red-700 transition"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {upiQREntry && branchBankDetails && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-black text-indigo-700 mb-4">UPI Payment QR</h3>
            <div className="flex justify-center mb-4 bg-white p-4 rounded-xl border">
              <QRCode
                value={`upi://pay?pa=${branchBankDetails.upi_id}&pn=${branchBankDetails.account_holder_name || 'Diagnostic Center'}&am=${calculateTotal(upiQREntry).toFixed(2)}&cu=INR&tn=Payment for ${upiQREntry.test_name}`}
                size={240}
              />
            </div>
            <div className="bg-indigo-50 p-4 rounded-xl mb-4 text-sm">
              <p><strong>Patient:</strong> {upiQREntry.patient_name}</p>
              <p><strong>Amount:</strong> INR {calculateTotal(upiQREntry).toFixed(2)}</p>
              <p><strong>Test:</strong> {upiQREntry.test_name}</p>
              <p><strong>UPI ID:</strong> {branchBankDetails.upi_id}</p>
            </div>
            <button
              onClick={() => {
                setUpiQREntry(null)
                setBranchBankDetails(null)
              }}
              className="w-full px-6 py-3 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-700 transition"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {pdfViewerEntry && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-4xl w-full h-[90vh] shadow-2xl flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-2xl font-black text-slate-900">View Report</h3>
              <button onClick={() => setPdfViewerEntry(null)} className="px-4 py-2 rounded-xl bg-slate-200">Close</button>
            </div>
            <div className="flex-1 mb-4 border rounded-xl overflow-hidden">
              <iframe
                src={`${API_BASE}/api/files/${pdfViewerEntry.report_pdf_url?.replace('/uploads/', '')}`}
                className="w-full h-full"
                title="PDF Viewer"
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setUploadingEntryId(pdfViewerEntry.id)
                  fileInputRef.current?.click()
                }}
                className="flex-1 px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700"
              >
                Replace PDF
              </button>
              <button
                onClick={() => deletePDF(pdfViewerEntry.id)}
                className="flex-1 px-4 py-3 rounded-xl bg-red-600 text-white font-bold hover:bg-red-700"
              >
                Delete PDF
              </button>
            </div>
          </div>
        </div>
      )}

      {pdfShareEntry && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-black text-cyan-600 mb-4">Share Report</h3>
            <div className="bg-cyan-50 p-4 rounded-xl mb-6 text-sm">
              <p><strong>Patient:</strong> {pdfShareEntry.patient_name}</p>
              <p><strong>Test:</strong> {pdfShareEntry.test_name}</p>
              <p><strong>Mobile:</strong> {pdfShareEntry.mobile}</p>
            </div>
            <div className="space-y-3">
              <button
                onClick={() => {
                  sharePDFWhatsApp(pdfShareEntry)
                  setPdfShareEntry(null)
                }}
                className="w-full px-6 py-3 rounded-xl bg-green-600 text-white font-bold hover:bg-green-700 transition"
              >
                Share via WhatsApp
              </button>
              <button
                onClick={() => {
                  sharePDFEmail(pdfShareEntry)
                  setPdfShareEntry(null)
                }}
                className="w-full px-6 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition"
              >
                Share via Email
              </button>
              <button
                onClick={() => setPdfShareEntry(null)}
                className="w-full px-6 py-3 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {isExportModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-lg w-full shadow-2xl">
            <h3 className="text-2xl font-black text-slate-900 mb-2">Export Data</h3>
            <p className="text-sm text-slate-600 mb-6">Choose period and format for your business export.</p>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Time Period</label>
                <select
                  value={exportPeriod}
                  onChange={e => setExportPeriod(e.target.value as ExportPeriod)}
                  className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
                >
                  <option value="daily">Daily</option>
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Format</label>
                <select
                  value={exportFormat}
                  onChange={e => setExportFormat(e.target.value as ExportFormat)}
                  className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
                >
                  <option value="csv">CSV</option>
                  <option value="pdf">PDF</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-8">
              <button
                onClick={() => setIsExportModalOpen(false)}
                disabled={isExporting}
                className="flex-1 px-4 py-3 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleExportData}
                disabled={isExporting}
                className="flex-1 px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition"
              >
                {isExporting ? 'Exporting...' : 'Export'}
              </button>
            </div>
          </div>
        </div>
      )}

      {billEntry && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl p-6 max-w-5xl w-full max-h-[90vh] overflow-auto shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-2xl font-black text-slate-900">Medical Invoice</h3>
              <button onClick={() => setBillEntry(null)} className="px-4 py-2 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300">Close</button>
            </div>

            <div id="bill-invoice-content" className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
              <div className="bg-gradient-to-r from-blue-700 to-blue-500 text-white p-8">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <div className="h-12 w-12 rounded-xl bg-white/20 flex items-center justify-center text-xl font-black">+</div>
                      <div>
                        <h1 className="text-3xl font-black">{invoiceBranch?.name || 'Diagnostic Center'}</h1>
                        <p className="text-blue-100 text-sm">Medical Invoice</p>
                      </div>
                    </div>
                    <p className="text-sm text-blue-100 mt-4">{invoiceBranch?.address || 'Address not available'}</p>
                    <p className="text-sm text-blue-100">{invoiceBranch?.phone || 'Phone not available'}</p>
                    <p className="text-sm text-blue-100">{invoiceBranch?.email || 'Email not available'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-blue-100">Invoice No</p>
                    <p className="text-lg font-bold">INV-{billEntry.auto_patient_id}</p>
                    <p className="text-sm text-blue-100 mt-2">Date</p>
                    <p className="font-semibold">{new Date(billEntry.auto_entry_datetime).toLocaleDateString()}</p>
                  </div>
                </div>
              </div>

              <div className="p-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  <div className="bg-slate-50 rounded-xl p-4">
                    <p className="text-xs font-bold uppercase text-slate-500 mb-2">Patient Info</p>
                    <p className="font-semibold">{billEntry.patient_name}</p>
                    <p className="text-sm text-slate-600">{billEntry.address}</p>
                    <p className="text-sm text-slate-600">{billEntry.mobile}</p>
                    <p className="text-sm text-slate-600">Patient ID: {billEntry.auto_patient_id}</p>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-4">
                    <p className="text-xs font-bold uppercase text-slate-500 mb-2">Invoice Info</p>
                    <p className="text-sm text-slate-700">Date & Time: {new Date(billEntry.auto_entry_datetime).toLocaleString()}</p>
                    <p className="text-sm text-slate-700">Payment Method: {billEntry.payment_method}</p>
                    <p className="text-sm text-slate-700">Payment Status: <span className={billEntry.is_paid ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>{billEntry.is_paid ? 'PAID' : 'UNPAID'}</span></p>
                  </div>
                </div>

                <div className="overflow-hidden rounded-xl border border-slate-200">
                  <table className="w-full border-collapse">
                    <thead className="bg-blue-50 text-blue-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-bold">Test Name</th>
                        <th className="px-4 py-3 text-left text-sm font-bold">Description</th>
                        <th className="px-4 py-3 text-right text-sm font-bold">Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-t border-slate-200">
                        <td className="px-4 py-3 text-sm font-semibold">{billEntry.test_name}</td>
                        <td className="px-4 py-3 text-sm text-slate-600">Referred by {billEntry.referred_doctor || 'Self'} | Diagnostic service charge</td>
                        <td className="px-4 py-3 text-sm text-right">INR {invoiceSubtotal.toFixed(2)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="mt-8 flex justify-end">
                  <div className="w-full max-w-sm rounded-xl border border-slate-200 p-4 bg-slate-50">
                    <div className="flex justify-between py-2 text-sm">
                      <span className="text-slate-600">Subtotal</span>
                      <span className="font-semibold">INR {invoiceSubtotal.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between py-2 text-sm border-t border-slate-200">
                      <span className="text-slate-600">Tax ({parseNumber(billEntry.tax_percent).toFixed(2)}%)</span>
                      <span className="font-semibold">INR {invoiceTaxAmount.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between py-3 mt-2 rounded-lg px-3 bg-blue-600 text-white font-bold">
                      <span>Grand Total</span>
                      <span>INR {invoiceGrandTotal.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button onClick={handlePrintBill} className="flex-1 px-6 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition">Print</button>
              <button onClick={handleDownloadBillPDF} className="flex-1 px-6 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-700 transition">Download PDF</button>
              <button onClick={() => setBillEntry(null)} className="flex-1 px-6 py-3 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300 transition">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
