import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { AgGridReact } from 'ag-grid-react'
import { ColDef, GridApi, GridReadyEvent } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { QRCodeSVG } from 'qrcode.react'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'

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

interface DailyExpense {
  id: number
  branch_id: number
  entry_date: string
  expense_item: string
  cost: number
  description?: string
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

export default function DailyEntryModule() {
  const { user, token } = useAuth()
  const [entries, setEntries] = useState<DailyEntry[]>([])
  const [, setExpenses] = useState<DailyExpense[]>([])
  const [stats, setStats] = useState<DailyStats | null>(null)
  const [, setLoading] = useState(false)
  const [, setGridApi] = useState<GridApi | null>(null)
  
  // Filters
  const [patientNameFilter, setCustomerNameFilter] = useState('')
  const [referredStaffFilter, setReferredStaffFilter] = useState('')
  const [testNameFilter, setMenuItemNameFilter] = useState('')
  const [startDate, setStartDate] = useState<Date | null>(null)
  const [endDate, setEndDate] = useState<Date | null>(null)
  
  // Expense form
  const [expenseForm, setExpenseForm] = useState({
    expense_item: '',
    cost: '',
    description: ''
  })
  
  // QR Code modal
  const [qrCodeData, setQrCodeData] = useState<{ patientId: string; qrCode: string } | null>(null)
  
  // Upload modal
  const [uploadingEntryId, setUploadingEntryId] = useState<number | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const API_BASE = (process as any).env.REACT_APP_API_BASE_URL || 
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  }), [token])

  // Fetch entries with filters
  const fetchEntries = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (patientNameFilter) params.append('patient_name', patientNameFilter)
      if (referredStaffFilter) params.append('referred_doctor', referredStaffFilter)
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
  }, [token, patientNameFilter, referredStaffFilter, testNameFilter, startDate, endDate, API_BASE, requestConfig])

  // Fetch expenses
  const fetchExpenses = useCallback(async () => {
    if (!token) return
    try {
      const res = await axios.get(`${API_BASE}/api/daily-expenses`, requestConfig)
      setExpenses(res.data || [])
    } catch (err: any) {
      console.error('Failed to fetch expenses:', err)
    }
  }, [token, API_BASE, requestConfig])

  // Fetch stats
  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const res = await axios.get(`${API_BASE}/api/daily-stats`, requestConfig)
      setStats(res.data)
    } catch (err: any) {
      console.error('Failed to fetch stats:', err)
    }
  }, [token, API_BASE, requestConfig])

  useEffect(() => {
    fetchEntries()
    fetchExpenses()
    fetchStats()
  }, [fetchEntries, fetchExpenses, fetchStats])

  // Auto-save on cell value change
  const onCellValueChanged = async (params: any) => {
    const updatedEntry = params.data
    try {
      await axios.put(
        `${API_BASE}/api/daily-entries/${updatedEntry.id}`,
        {
          patient_name: updatedEntry.patient_name,
          mobile: updatedEntry.mobile,
          address: updatedEntry.address,
          referred_doctor: updatedEntry.referred_doctor,
          test_name: updatedEntry.test_name,
          fee_amount: parseFloat(updatedEntry.fee_amount),
          tax_percent: parseFloat(updatedEntry.tax_percent),
          payment_method: updatedEntry.payment_method,
          is_paid: updatedEntry.is_paid,
          remarks: updatedEntry.remarks
        },
        requestConfig
      )
      toast.success('Entry auto-saved')
      fetchEntries()
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save entry')
      fetchEntries() // Revert changes
    }
  }

  // Add new entry
  const addNewEntry = async () => {
    try {
      await axios.post(
        `${API_BASE}/api/daily-entries`,
        {
          patient_name: 'New Customer',
          mobile: '0000000000',
          address: 'Address',
          test_name: 'MenuItem Name',
          fee_amount: 100,
          tax_percent: 0,
          payment_method: 'Cash',
          is_paid: true
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

  // Delete entry
  const deleteEntry = async (id: number) => {
    if (!window.confirm('Delete this entry?')) return
    try {
      await axios.delete(`${API_BASE}/api/daily-entries/${id}`, requestConfig)
      toast.success('Entry deleted')
      fetchEntries()
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to delete entry')
    }
  }

  // Upload PDF
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
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      toast.success('Order uploaded successfully')
      fetchEntries()
      setUploadingEntryId(null)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to upload report')
    }
  }

  // Show QR Code
  const showQRCode = async (entryId: number) => {
    try {
      const res = await axios.get(`${API_BASE}/api/daily-entries/${entryId}/qr-code`, requestConfig)
      setQrCodeData(res.data)
    } catch (err: any) {
      toast.error('Failed to generate QR code')
    }
  }

  // Add expense
  const addExpense = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await axios.post(
        `${API_BASE}/api/daily-expenses`,
        {
          expense_item: expenseForm.expense_item,
          cost: parseFloat(expenseForm.cost),
          description: expenseForm.description
        },
        requestConfig
      )
      toast.success('Expense added')
      setExpenseForm({ expense_item: '', cost: '', description: '' })
      fetchExpenses()
      fetchStats()
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to add expense')
    }
  }

  // Export functions
  const exportCSV = async (period: 'daily' | 'monthly' | 'yearly') => {
    try {
      const res = await axios.get(
        `${API_BASE}/api/daily-entries/export?type=csv&period=${period}`,
        { ...requestConfig, responseType: 'blob' }
      )
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `daily_entries_${period}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success('CSV downloaded')
    } catch (err: any) {
      toast.error('Failed to export CSV')
    }
  }

  const exportPDF = async (period: 'daily' | 'monthly' | 'yearly') => {
    try {
      const res = await axios.get(
        `${API_BASE}/api/daily-entries/export?type=pdf&period=${period}`,
        { ...requestConfig, responseType: 'blob' }
      )
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `daily_entries_${period}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success('PDF downloaded')
    } catch (err: any) {
      toast.error('Failed to export PDF')
    }
  }

  // Column definitions
  const columnDefs: ColDef[] = [
    { field: 'auto_patient_id', headerName: 'Customer ID', width: 150, editable: false },
    { field: 'patient_name', headerName: 'Customer Name', width: 180, editable: true },
    { field: 'mobile', headerName: 'Mobile', width: 130, editable: true },
    { field: 'address', headerName: 'Address', width: 200, editable: true },
    { field: 'referred_doctor', headerName: 'Referred Staff', width: 160, editable: true },
    { field: 'test_name', headerName: 'MenuItem Name', width: 200, editable: true },
    { 
      field: 'fee_amount', 
      headerName: 'Fee (₹)', 
      width: 110, 
      editable: true,
      valueFormatter: (params) => `₹${params.value?.toFixed(2) || '0.00'}`
    },
    { 
      field: 'tax_percent', 
      headerName: 'GST %', 
      width: 100, 
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: [0, 5, 12, 18] }
    },
    { 
      field: 'total_amount', 
      headerName: 'Total (₹)', 
      width: 120, 
      editable: false,
      valueFormatter: (params) => `₹${params.value?.toFixed(2) || '0.00'}`
    },
    { 
      field: 'payment_method', 
      headerName: 'Payment', 
      width: 120, 
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: ['Cash', 'UPI', 'QR', 'Card'] }
    },
    { 
      field: 'status', 
      headerName: 'Status', 
      width: 110,
      cellRenderer: (params: any) => {
        const status = params.value
        const color = status === 'Completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
        return `<span class="px-2 py-1 rounded-full text-xs font-bold ${color}">${status}</span>`
      }
    },
    { field: 'remarks', headerName: 'Remarks', width: 150, editable: true },
    {
      headerName: 'Actions',
      width: 280,
      cellRenderer: (params: any) => {
        const entry = params.data
        return `
          <div class="flex gap-2">
            <button class="upload-btn px-3 py-1 bg-blue-600 text-white rounded text-xs font-bold" data-id="${entry.id}">📄 Upload</button>
            <button class="qr-btn px-3 py-1 bg-purple-600 text-white rounded text-xs font-bold" data-id="${entry.id}">QR</button>
            <button class="delete-btn px-3 py-1 bg-red-600 text-white rounded text-xs font-bold" data-id="${entry.id}">Delete</button>
          </div>
        `
      }
    }
  ]

  const onGridReady = (params: GridReadyEvent) => {
    setGridApi(params.api)
    
    // Add event listeners for action buttons
    setTimeout(() => {
      document.querySelectorAll('.upload-btn').forEach(btn => {
        btn.addEventListener('click', (e: any) => {
          const id = parseInt(e.target.dataset.id)
          setUploadingEntryId(id)
          fileInputRef.current?.click()
        })
      })
      
      document.querySelectorAll('.qr-btn').forEach(btn => {
        btn.addEventListener('click', (e: any) => {
          const id = parseInt(e.target.dataset.id)
          showQRCode(id)
        })
      })
      
      document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e: any) => {
          const id = parseInt(e.target.dataset.id)
          deleteEntry(id)
        })
      })
    }, 100)
  }

  const clearFilters = () => {
    setCustomerNameFilter('')
    setReferredStaffFilter('')
    setMenuItemNameFilter('')
    setStartDate(null)
    setEndDate(null)
  }

  if (user?.role !== 'branch_admin' && user?.role !== 'super_admin') {
    return (
      <div className="premium-card p-8">
        <h2 className="text-2xl font-black gradient-text">Daily Entry Module</h2>
        <p className="text-slate-600 mt-3">Access restricted to Branch Admin and Super Admin only.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="premium-card p-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-black gradient-text">📊 Daily Entry Module</h2>
            <p className="text-slate-600 mt-2">Manage daily patient entries, expenses, and orders for your branch</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={addNewEntry}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold hover:shadow-xl transition"
            >
              ➕ Add New Entry
            </button>
            <button
              onClick={fetchEntries}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold hover:shadow-xl transition"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Stats Dashboard */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="premium-card p-6 bg-gradient-to-br from-emerald-50 to-teal-50">
            <p className="text-xs uppercase tracking-wider text-emerald-600 font-bold mb-2">💰 Total Revenue</p>
            <p className="text-3xl font-black text-emerald-700">₹{stats.total_revenue.toLocaleString()}</p>
          </div>
          <div className="premium-card p-6 bg-gradient-to-br from-red-50 to-rose-50">
            <p className="text-xs uppercase tracking-wider text-red-600 font-bold mb-2">💸 Total Expense</p>
            <p className="text-3xl font-black text-red-700">₹{stats.total_expense.toLocaleString()}</p>
          </div>
          <div className="premium-card p-6 bg-gradient-to-br from-blue-50 to-cyan-50">
            <p className="text-xs uppercase tracking-wider text-blue-600 font-bold mb-2">📈 Net Profit</p>
            <p className="text-3xl font-black text-blue-700">₹{stats.net_profit.toLocaleString()}</p>
          </div>
          <div className="premium-card p-6 bg-gradient-to-br from-purple-50 to-pink-50">
            <p className="text-xs uppercase tracking-wider text-purple-600 font-bold mb-2">👥 Customer Count</p>
            <p className="text-3xl font-black text-purple-700">{stats.patient_count}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">🔍 Advanced Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <input
            type="text"
            placeholder="Customer Name"
            value={patientNameFilter}
            onChange={(e) => setCustomerNameFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Referred Staff"
            value={referredStaffFilter}
            onChange={(e) => setReferredStaffFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="MenuItem Name"
            value={testNameFilter}
            onChange={(e) => setMenuItemNameFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none"
          />
          <DatePicker
            selected={startDate}
            onChange={(date) => setStartDate(date)}
            placeholderText="Start Date"
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none w-full"
          />
          <DatePicker
            selected={endDate}
            onChange={(date) => setEndDate(date)}
            placeholderText="End Date"
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none w-full"
          />
        </div>
        <div className="flex gap-3 mt-4">
          <button
            onClick={fetchEntries}
            className="px-6 py-2 rounded-xl bg-purple-600 text-white font-bold hover:bg-purple-700 transition"
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

      {/* Export Buttons */}
      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">📥 Export Data</h3>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => exportCSV('daily')}
            className="px-5 py-3 rounded-xl bg-green-600 text-white font-bold hover:shadow-xl transition"
          >
            📄 Download Today's CSV
          </button>
          <button
            onClick={() => exportPDF('monthly')}
            className="px-5 py-3 rounded-xl bg-blue-600 text-white font-bold hover:shadow-xl transition"
          >
            📑 Download Monthly PDF
          </button>
          <button
            onClick={() => exportPDF('yearly')}
            className="px-5 py-3 rounded-xl bg-purple-600 text-white font-bold hover:shadow-xl transition"
          >
            📊 Download Yearly PDF
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">📋 Daily Entries</h3>
        <div className="ag-theme-alpine" style={{ height: 500, width: '100%' }}>
          <AgGridReact
            rowData={entries}
            columnDefs={columnDefs}
            onGridReady={onGridReady}
            onCellValueChanged={onCellValueChanged}
            defaultColDef={{
              sortable: true,
              filter: true,
              resizable: true
            }}
            animateRows={true}
            rowSelection="single"
          />
        </div>
      </div>

      {/* Expense Form */}
      <div className="premium-card p-6">
        <h3 className="text-xl font-black text-slate-900 mb-4">💸 Add Daily Expense</h3>
        <form onSubmit={addExpense} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Expense Item"
            value={expenseForm.expense_item}
            onChange={(e) => setExpenseForm({ ...expenseForm, expense_item: e.target.value })}
            required
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none"
          />
          <input
            type="number"
            step="0.01"
            placeholder="Cost"
            value={expenseForm.cost}
            onChange={(e) => setExpenseForm({ ...expenseForm, cost: e.target.value })}
            required
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={expenseForm.description}
            onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-purple-500 focus:outline-none"
          />
          <button
            type="submit"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold hover:shadow-xl transition"
          >
            ➕ Add Expense
          </button>
        </form>
      </div>

      {/* Hidden file input for PDF upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={(e) => {
          if (e.target.files && e.target.files[0] && uploadingEntryId) {
            handleFileUpload(uploadingEntryId, e.target.files[0])
          }
        }}
      />

      {/* QR Code Modal */}
      {qrCodeData && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-black text-slate-900 mb-4">QR Code</h3>
            <div className="flex justify-center mb-4">
              <QRCodeSVG value={qrCodeData.patientId} size={256} />
            </div>
            <p className="text-center text-slate-600 font-semibold mb-6">
              Customer ID: <span className="font-black">{qrCodeData.patientId}</span>
            </p>
            <button
              onClick={() => setQrCodeData(null)}
              className="w-full px-6 py-3 rounded-xl bg-slate-900 text-white font-bold hover:bg-slate-800 transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
