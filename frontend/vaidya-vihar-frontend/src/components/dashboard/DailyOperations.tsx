import React, { useState, useEffect, useLayoutEffect, useCallback, useRef, useMemo } from 'react'
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
import { useNavigate } from 'react-router-dom'

interface DailyEntry {
  id: number
  branch_id: number
  auto_patient_id: string
  auto_entry_datetime: string
  patient_name: string
  age?: string | number | null
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
  logo_url?: string | null
}

type ExportPeriod = 'daily' | 'monthly' | 'yearly'
type ExportFormat = 'csv' | 'pdf'

const columnHelper = createColumnHelper<DailyEntry>()

interface EditableCellInputProps {
  initialValue: string | number
  onCommit: (value: string) => void
  type?: 'text' | 'number'
  className?: string
}

function EditableCellInput({ initialValue, onCommit, type = 'text', className }: EditableCellInputProps) {
  const [localValue, setLocalValue] = useState(String(initialValue ?? ''))
  const inputRef = useRef<HTMLInputElement>(null)
  const isFocusedRef = useRef(false)

  useEffect(() => {
    if (!isFocusedRef.current) {
      setLocalValue(String(initialValue ?? ''))
    }
  }, [initialValue])

  const commitIfChanged = useCallback(() => {
    if (String(initialValue ?? '') !== localValue) {
      onCommit(localValue)
    }
  }, [initialValue, localValue, onCommit])

  return (
    <input
      ref={inputRef}
      type={type}
      value={localValue}
      onChange={e => setLocalValue(e.target.value)}
      onFocus={() => {
        isFocusedRef.current = true
      }}
      onBlur={() => {
        isFocusedRef.current = false
        commitIfChanged()
      }}
      onKeyDown={e => {
        if (e.key === 'Enter') {
          e.preventDefault()
          e.currentTarget.blur()
        }
      }}
      className={className || 'w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500'}
    />
  )
}

// Debounce hook for search queries
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay)
    return () => clearTimeout(handler)
  }, [value, delay])
  return debouncedValue
}

interface AutocompleteOption {
  id: string | number
  name: string
}

interface AutocompleteCellProps {
  value: string
  onChange: (value: string) => void
  fetchOptions: (searchTerm: string) => Promise<AutocompleteOption[]>
  placeholder: string
}

function AutocompleteCell({ value, onChange, fetchOptions, placeholder }: AutocompleteCellProps) {
  const [localValue, setLocalValue] = useState(String(value ?? ''))
  const [options, setOptions] = useState<AutocompleteOption[]>([])
  const [isFocused, setIsFocused] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const debouncedSearchTerm = useDebounce(localValue, 500)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (String(value ?? '') !== localValue && !isFocused) {
      setLocalValue(String(value ?? ''))
    }
  }, [value, isFocused])

  useEffect(() => {
    if (!isFocused || debouncedSearchTerm.length === 0) {
      setOptions([])
      return
    }

    const loadOptions = async () => {
      try {
        setIsLoading(true)
        const results = await fetchOptions(debouncedSearchTerm)
        setOptions(results)
      } catch (error) {
        console.error('Error fetching autocomplete options:', error)
        setOptions([])
      } finally {
        setIsLoading(false)
      }
    }

    loadOptions()
  }, [debouncedSearchTerm, isFocused, fetchOptions])

  const handleSelectOption = (option: AutocompleteOption) => {
    setLocalValue(option.name)
    onChange(option.name)
    setOptions([])
    setIsFocused(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value)
  }

  const handleInputBlur = () => {
    setTimeout(() => {
      setIsFocused(false)
      if (String(value ?? '') !== localValue) {
        onChange(localValue)
      }
    }, 100)
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <input
        ref={inputRef}
        type="text"
        value={localValue}
        onChange={handleInputChange}
        onFocus={() => setIsFocused(true)}
        onBlur={handleInputBlur}
        onKeyDown={e => {
          if (e.key === 'Enter') {
            e.preventDefault()
            inputRef.current?.blur()
          }
        }}
        placeholder={placeholder}
        className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
      />
      {isFocused && options.length > 0 && (
        <div className="absolute top-10 left-0 z-50 bg-white shadow-lg border rounded-lg w-full max-h-60 overflow-y-auto">
          {options.map(option => (
            <div
              key={option.id}
              onClick={() => handleSelectOption(option)}
              className="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b last:border-b-0"
            >
              {option.name}
            </div>
          ))}
        </div>
      )}
      {isFocused && isLoading && (
        <div className="absolute top-10 left-0 z-50 bg-white shadow-lg border rounded-lg w-full px-3 py-2 text-xs text-gray-500">
          Loading...
        </div>
      )}
    </div>
  )
}

interface DailyOperationsProps {
  branchId?: number
}

export default function DailyOperations({ branchId }: DailyOperationsProps) {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const [entries, setEntries] = useState<DailyEntry[]>([])
  const [entriesLoadError, setEntriesLoadError] = useState(false)
  const [isAdding, setIsAdding] = useState(false)
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
  const restoreScrollYRef = useRef<number | null>(null)
  const restoreContainerScrollTopRef = useRef<number | null>(null)
  const autoRefreshInFlightRef = useRef(false)

  const [deleteConfirmEntry, setDeleteConfirmEntry] = useState<DailyEntry | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const [pdfViewerEntry, setPdfViewerEntry] = useState<DailyEntry | null>(null)
  const [pdfShareEntry, setPdfShareEntry] = useState<DailyEntry | null>(null)

  const [upiQREntry, setUpiQREntry] = useState<DailyEntry | null>(null)
  const [branchBankDetails, setBranchBankDetails] = useState<any>(null)
  const [upiQRCodeValue, setUpiQRCodeValue] = useState('')
  const [upiAvailabilityByBranch, setUpiAvailabilityByBranch] = useState<Record<number, boolean>>({})
  const upiAvailabilityRef = useRef<Record<number, boolean>>({})
  const [upiLookupLoading, setUpiLookupLoading] = useState(false)
  const upiFetchInProgressRef = useRef(false)
  const upiWarningShownRef = useRef(false)

  const [billEntry, setBillEntry] = useState<DailyEntry | null>(null)
  const [branchDetailsById, setBranchDetailsById] = useState<Record<number, BranchInfo>>({})

  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [openActionsMenuId, setOpenActionsMenuId] = useState<number | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(40)

  const [isExportModalOpen, setIsExportModalOpen] = useState(false)
  const [exportPeriod, setExportPeriod] = useState<ExportPeriod>('daily')
  const [exportFormat, setExportFormat] = useState<ExportFormat>('csv')
  const [isExporting, setIsExporting] = useState(false)

  const filtersRef = useRef({
    patientNameFilter: '',
    referredDoctorFilter: '',
    testNameFilter: '',
    startDate: null as Date | null,
    endDate: null as Date | null,
  })

  const rawApiBase = (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)
  const API_BASE =
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? String(rawApiBase).replace('://localhost', '://127.0.0.1')
      : rawApiBase

  const normalizedRole = (user?.role || '').trim().toLowerCase()
  const isStaff = normalizedRole === 'staff'
  const isDirector = normalizedRole === 'branch_director'
  const isAdminOrDirector = normalizedRole === 'super_admin' || normalizedRole === 'branch_admin' || isDirector
  const forcedBranchId = Number(branchId)
  const effectiveBranchId = Number.isFinite(forcedBranchId) && forcedBranchId > 0
    ? forcedBranchId
    : (user?.branch_id ? Number(user.branch_id) : null)

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token])

  useEffect(() => {
    if (!user) return
    if (isStaff && !Boolean((user as any)?.can_access_daily_ops)) {
      navigate('/staff/profile', { replace: true })
    }
  }, [isStaff, navigate, user])

  const parseNumber = useCallback((value: unknown, fallback = 0) => {
    const n = Number(value)
    return Number.isFinite(n) ? n : fallback
  }, [])

  const resolveInvoiceMediaUrl = useCallback((path?: string | null) => {
    if (!path) return ''
    const raw = path.trim()
    if (!raw) return ''

    if (raw.startsWith('data:') || raw.startsWith('blob:')) {
      return raw
    }

    if (/^https?:\/\//i.test(raw)) {
      return raw
    }

    if (raw.startsWith('/')) {
      return `${API_BASE}${raw}`
    }

    return `${API_BASE}/api/files/${raw}`
  }, [API_BASE])

  const getErrorMessage = useCallback((err: unknown, fallback: string) => {
    const errorObj = err as any
    const detail = errorObj?.response?.data?.detail ?? errorObj?.response?.data?.message ?? errorObj?.message

    if (Array.isArray(detail)) {
      const combined = detail
        .map((item: any) => {
          if (typeof item === 'string') return item
          if (item && typeof item.msg === 'string') return item.msg
          try {
            return JSON.stringify(item)
          } catch {
            return ''
          }
        })
        .filter(Boolean)
        .join(' | ')
      return combined || fallback
    }

    if (detail && typeof detail === 'object') {
      if (typeof detail.msg === 'string') return detail.msg
      try {
        return JSON.stringify(detail)
      } catch {
        return fallback
      }
    }

    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }

    return fallback
  }, [])

  const calculateTotal = useCallback((entry: Partial<DailyEntry>) => {
    const fee = parseNumber(entry.fee_amount, 0)
    const tax = parseNumber(entry.tax_percent, 0)
    return fee + (fee * tax) / 100
  }, [parseNumber])

  const showSingleUPIWarning = () => {
    if (upiWarningShownRef.current) return
    upiWarningShownRef.current = true
    toast.error('UPI ID not configured. Please contact admin.', { id: 'upi-config-warning' })
  }

  const hasValidUPI = useCallback((branchId?: number | null) => {
    if (!branchId) return false
    return !!upiAvailabilityByBranch[branchId]
  }, [upiAvailabilityByBranch])

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
        logo_url: res.data.logo_url || res.data.branch_logo_url || null,
      }
      setBranchDetailsById(prev => ({ ...prev, [branchId]: branchInfo }))
      return branchInfo
    } catch {
      return null
    }
  }, [API_BASE, branchDetailsById, requestConfig])

  useEffect(() => {
    filtersRef.current = {
      patientNameFilter,
      referredDoctorFilter,
      testNameFilter,
      startDate,
      endDate,
    }
  }, [patientNameFilter, referredDoctorFilter, testNameFilter, startDate, endDate])

  const fetchEntries = useCallback(async (options?: { background?: boolean; preserveScroll?: boolean }) => {
    if (!token) return
    const isBackground = !!options?.background
    if (!isBackground) {
      setLoading(true)
    }

    if (options?.preserveScroll) {
      restoreScrollYRef.current = window.scrollY
      restoreContainerScrollTopRef.current = scrollContainerRef.current?.scrollTop ?? null
    }

    try {
      const params = new URLSearchParams()
      const activeFilters = filtersRef.current
      if (activeFilters.patientNameFilter) params.append('patient_name', activeFilters.patientNameFilter)
      if (activeFilters.referredDoctorFilter) params.append('referred_doctor', activeFilters.referredDoctorFilter)
      if (activeFilters.testNameFilter) params.append('test_name', activeFilters.testNameFilter)
      if (activeFilters.startDate) params.append('start_date', activeFilters.startDate.toISOString().split('T')[0])
      if (activeFilters.endDate) params.append('end_date', activeFilters.endDate.toISOString().split('T')[0])
      if (effectiveBranchId) params.append('branch_id', String(effectiveBranchId))

      const res = await axios.get(`${API_BASE}/api/daily-entries?${params.toString()}`, requestConfig)
      const data = Array.isArray(res.data) ? res.data : []
      const sortedData = [...data].sort((a, b) => {
        const timeA = new Date(a.created_at).getTime()
        const timeB = new Date(b.created_at).getTime()
        return timeA - timeB
      })
      setEntries(sortedData)
      setEntriesLoadError(false)
    } catch (err: any) {
      const statusCode = Number(err?.response?.status || 0)
      const detail = String(err?.response?.data?.detail || '').toLowerCase()
      const needsGuardRedirect = isStaff && (statusCode === 403 || detail.includes('disabled by director') || detail.includes('insufficient permissions'))
      if (needsGuardRedirect) {
        navigate('/staff/profile', { replace: true })
        return
      }
      setEntriesLoadError(true)
      if (!isBackground) {
        toast.error(getErrorMessage(err, 'Failed to fetch entries'))
      }
    } finally {
      if (!isBackground) {
        setLoading(false)
      }
    }
  }, [token, API_BASE, requestConfig, getErrorMessage, isStaff, navigate, effectiveBranchId])

  useLayoutEffect(() => {
    if (restoreScrollYRef.current === null && restoreContainerScrollTopRef.current === null) return

    const nextWindowY = restoreScrollYRef.current
    const nextContainerTop = restoreContainerScrollTopRef.current

    const timeoutId = window.setTimeout(() => {
      if (nextWindowY !== null) {
        window.scrollTo(0, nextWindowY)
      }
      if (nextContainerTop !== null && scrollContainerRef.current) {
        scrollContainerRef.current.scrollTop = nextContainerTop
      }
      restoreScrollYRef.current = null
      restoreContainerScrollTopRef.current = null
    }, 0)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [entries])

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const statsParams = new URLSearchParams()
      if (effectiveBranchId) statsParams.append('branch_id', String(effectiveBranchId))
      const statsUrl = statsParams.toString() ? `${API_BASE}/api/daily-stats?${statsParams.toString()}` : `${API_BASE}/api/daily-stats`
      const res = await axios.get(statsUrl, requestConfig)
      setStats(res.data)
    } catch {
      // Keep dashboard resilient even if stats API fails.
    }
  }, [token, API_BASE, requestConfig, effectiveBranchId])

  useEffect(() => {
    if (!token) return
    fetchEntries()
    fetchStats()
  }, [token, fetchEntries, fetchStats])

  useEffect(() => {
    if (!token) return

    const intervalId = window.setInterval(() => {
      const activeElement = document.activeElement as HTMLElement | null
      const isEditingInsideTable = !!(activeElement && scrollContainerRef.current?.contains(activeElement))
      if (isEditingInsideTable) return
      if (autoRefreshInFlightRef.current) return
      autoRefreshInFlightRef.current = true
      void fetchEntries({ background: true, preserveScroll: true }).finally(() => {
        autoRefreshInFlightRef.current = false
      })
    }, 4000)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [token, fetchEntries])

  useEffect(() => {
    setCurrentPage(1)
  }, [patientNameFilter, referredDoctorFilter, testNameFilter, startDate, endDate])

  useEffect(() => {
    upiAvailabilityRef.current = upiAvailabilityByBranch
  }, [upiAvailabilityByBranch])

  useEffect(() => {
    if (!token || entries.length === 0) return

    const uniqueBranchIds = Array.from(new Set(entries.map(entry => entry.branch_id).filter(Boolean)))
    const branchIdsToFetch = uniqueBranchIds.filter(branchId => upiAvailabilityRef.current[branchId] === undefined)

    if (branchIdsToFetch.length === 0) return

    let cancelled = false

    const fetchUPIAvailability = async () => {
      const checks = await Promise.all(
        branchIdsToFetch.map(async (branchId) => {
          try {
            const res = await axios.get(`${API_BASE}/api/branches/${branchId}/bank-details`, requestConfig)
            const upiId = String(res.data?.upi_id || '').trim()
            return { branchId, hasUpi: upiId.length > 0 }
          } catch {
            return { branchId, hasUpi: false }
          }
        })
      )

      if (cancelled) return

      setUpiAvailabilityByBranch(prev => {
        const next = { ...prev }
        checks.forEach(({ branchId, hasUpi }) => {
          next[branchId] = hasUpi
        })
        return next
      })
    }

    fetchUPIAvailability()

    return () => {
      cancelled = true
    }
  }, [token, entries, API_BASE, requestConfig])

  // Autocomplete fetch functions
  const fetchDoctorOptions = useCallback(async (searchTerm: string) => {
    if (!token) return []
    try {
      const res = await axios.get(`${API_BASE}/api/doctors/search?q=${encodeURIComponent(searchTerm)}`, requestConfig)
      return res.data || []
    } catch (error) {
      console.error('Error fetching doctors:', error)
      return []
    }
  }, [token, API_BASE, requestConfig])

  const fetchTestOptions = useCallback(async (searchTerm: string) => {
    if (!token) return []
    try {
      const res = await axios.get(`${API_BASE}/api/tests/search?q=${encodeURIComponent(searchTerm)}`, requestConfig)
      return res.data || []
    } catch (error) {
      console.error('Error fetching tests:', error)
      return []
    }
  }, [token, API_BASE, requestConfig])

  const fetchPatientOptions = useCallback(async (searchTerm: string) => {
    if (!token) return []
    try {
      const res = await axios.get(`${API_BASE}/api/patients/search?q=${encodeURIComponent(searchTerm)}`, requestConfig)
      return res.data || []
    } catch (error) {
      console.error('Error fetching patients:', error)
      return []
    }
  }, [token, API_BASE, requestConfig])

  const updateEntryField = useCallback(async (
    rowId: number,
    field: keyof DailyEntry,
    value: any,
    options?: { silentSuccess?: boolean }
  ) => {
    const originalEntry = entries.find(e => e.id === rowId)
    if (!originalEntry) return

    const normalizedValue = field === 'age'
      ? (value === '' ? null : String(value))
      : field === 'fee_amount' || field === 'tax_percent'
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
      toast.error(getErrorMessage(err, 'Failed to save entry'), { id: `entry-save-${rowId}` })
      fetchEntries()
    }
  }, [entries, API_BASE, requestConfig, calculateTotal, fetchEntries, fetchStats, parseNumber, getErrorMessage])

  const handleUPIQR = useCallback(async (entry: DailyEntry, options?: { manual?: boolean }) => {
    const isManualAction = !!options?.manual
    if (upiLookupLoading) return
    if (upiFetchInProgressRef.current) return
    setUpiLookupLoading(true)
    upiFetchInProgressRef.current = true

    try {
      const res = await axios.get(`${API_BASE}/api/branches/${entry.branch_id}/bank-details`, requestConfig)
      const details = res.data || {}
      const upiId = String(details.upi_id || '').trim()

      if (!upiId) {
        if (isManualAction) showSingleUPIWarning()
        return
      }

      const branchInfo = await fetchBranchDetails(entry.branch_id)
      const branchName = branchInfo?.name || 'Branch'
      const amount = parseNumber(entry.total_amount, calculateTotal(entry)).toFixed(2)
      const deepLink = `upi://pay?pa=${upiId}&pn=${branchName}&am=${amount}&cu=INR`

      setUpiQRCodeValue(deepLink)
      setBranchBankDetails({ ...details, branch_name: branchName })
      setUpiQREntry(entry)
    } catch {
      if (isManualAction) showSingleUPIWarning()
      return
    } finally {
      setUpiLookupLoading(false)
      upiFetchInProgressRef.current = false
    }
  }, [API_BASE, requestConfig, fetchBranchDetails, upiLookupLoading, calculateTotal, parseNumber])

  const handlePaymentMethodChange = useCallback(async (entry: DailyEntry, method: string) => {
    if (method === 'UPI' && !hasValidUPI(entry.branch_id)) {
      return
    }
    await updateEntryField(entry.id, 'payment_method', method)
  }, [hasValidUPI, updateEntryField])

  const handleAddEntry = async () => {
    if (isAdding) return
    setIsAdding(true)
    try {
      await axios.post(
        `${API_BASE}/api/daily-entries`,
        {
          patient_name: 'New Patient',
          age: null,
          mobile: '0000000000',
          address: 'Address',
          test_name: 'Test Name',
          fee_amount: 100,
          tax_percent: 0,
          payment_method: 'Hold',
          is_paid: false,
          auto_entry_datetime: new Date().toLocaleString(),
          ...(effectiveBranchId ? { branch_id: effectiveBranchId } : {}),
        },
        requestConfig
      )
      toast.success('New entry added')
      restoreScrollYRef.current = window.scrollY
      restoreContainerScrollTopRef.current = scrollContainerRef.current?.scrollTop ?? null
      void fetchEntries({ preserveScroll: true })
      void fetchStats()
    } catch (err: any) {
      toast.error(getErrorMessage(err, 'Failed to add entry'))
    } finally {
      setIsAdding(false)
    }
  }

  const scrollTableLeft = () => {
    scrollContainerRef.current?.scrollBy({ left: -200, behavior: 'smooth' })
  }

  const scrollTableRight = () => {
    scrollContainerRef.current?.scrollBy({ left: 200, behavior: 'smooth' })
  }

  const scrollToTop = () => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const scrollToBottom = () => {
    const container = scrollContainerRef.current
    if (!container) return
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
  }

  const handleTableKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return

    const activeElement = document.activeElement as HTMLElement | null
    if (!activeElement) return

    const currentCell = activeElement.closest('td[data-row-index][data-col-index]') as HTMLTableCellElement | null
    if (!currentCell) return

    const rowIndex = Number(currentCell.dataset.rowIndex)
    const colIndex = Number(currentCell.dataset.colIndex)
    const nextRowIndex = event.key === 'ArrowUp' ? rowIndex - 1 : rowIndex + 1
    if (nextRowIndex < 0) return

    const selector = `td[data-row-index="${nextRowIndex}"][data-col-index="${colIndex}"]`
    const nextCell = currentCell.closest('table')?.querySelector(selector) as HTMLTableCellElement | null
    if (!nextCell) return

    event.preventDefault()
    const target = nextCell.querySelector('input, select, textarea, button, [tabindex]') as HTMLElement | null
    if (target) {
      target.focus()
    } else {
      nextCell.focus()
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
      toast.error(getErrorMessage(err, 'Failed to delete entry'))
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
      toast.error(getErrorMessage(err, 'Failed to upload report'))
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
      toast.error(getErrorMessage(err, 'Failed to delete PDF'))
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
      toast.error(getErrorMessage(err, 'Failed to add expense'))
    }
  }

  const clearFilters = () => {
    setPatientNameFilter('')
    setReferredDoctorFilter('')
    setTestNameFilter('')
    setStartDate(null)
    setEndDate(null)
  }

  const openBillModal = useCallback(async (entry: DailyEntry) => {
    if (entry.is_paid) {
      await fetchBranchDetails(entry.branch_id)
      setBillEntry(entry)
      return
    }

    if (entry.payment_method === 'UPI') {
      toast.error('UPI payment pending. Please wait for confirmation.')
      return
    }

    if (entry.payment_method === 'Cash') {
      await updateEntryField(entry.id, 'is_paid', true, { silentSuccess: true })
      await fetchBranchDetails(entry.branch_id)
      setBillEntry({ ...entry, is_paid: true })
      return
    }

    await fetchBranchDetails(entry.branch_id)
    setBillEntry(entry)
  }, [fetchBranchDetails, updateEntryField])

  const handlePrintBill = () => {
    window.print()
  }

  const handleDownloadBillPDF = async () => {
    const billElement = document.getElementById('invoice-capture')
    if (!billElement) return

    try {
      const canvas = await html2canvas(billElement, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a5')
      const pdfWidth = pdf.internal.pageSize.getWidth() - 10
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width
      pdf.addImage(imgData, 'PNG', 5, 5, pdfWidth, pdfHeight)
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
    const branchQuery = effectiveBranchId ? `&branch_id=${effectiveBranchId}` : ''
    const [entryRes, expenseRes] = await Promise.all([
      axios.get(`${API_BASE}/api/daily-entries?start_date=${range.start}&end_date=${range.end}${branchQuery}`, requestConfig),
      axios.get(`${API_BASE}/api/daily-expenses?start_date=${range.start}&end_date=${range.end}${branchQuery}`, requestConfig),
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
    const branchQuery = effectiveBranchId ? `&branch_id=${effectiveBranchId}` : ''
    const [entryRes, expenseRes] = await Promise.all([
      axios.get(`${API_BASE}/api/daily-entries?start_date=${range.start}&end_date=${range.end}${branchQuery}`, requestConfig),
      axios.get(`${API_BASE}/api/daily-expenses?start_date=${range.start}&end_date=${range.end}${branchQuery}`, requestConfig),
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
      size: 40,
      minSize: 40,
      cell: info => <span className="font-bold text-slate-600">{(currentPage - 1) * pageSize + info.row.index + 1}</span>,
    }),
    columnHelper.accessor('auto_patient_id', {
      header: 'Patient ID',
      size: 135,
      minSize: 135,
      cell: info => <span className="font-mono text-xs">{String(info.getValue() || '')}</span>,
    }),
    columnHelper.accessor('patient_name', {
      header: 'Patient Name',
      size: 130,
      minSize: 130,
      cell: info => (
        <AutocompleteCell
          value={String(info.getValue() || '')}
          onChange={value => updateEntryField(info.row.original.id, 'patient_name', value)}
          fetchOptions={fetchPatientOptions}
          placeholder="Search patient..."
        />
      ),
    }),
    columnHelper.accessor('age', {
      header: 'Age/Gender',
      size: 80,
      minSize: 80,
      cell: info => (
        <EditableCellInput
          initialValue={info.getValue() ?? ''}
          onCommit={value => updateEntryField(info.row.original.id, 'age', value)}
          type="text"
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Actions',
      size: 50,
      minSize: 50,
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
                    handleUPIQR(info.row.original, { manual: true })
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
    columnHelper.accessor('mobile', {
      header: 'Mobile',
      size: 100,
      minSize: 100,
      cell: info => (
        <EditableCellInput
          initialValue={String(info.getValue() || '')}
          onCommit={value => updateEntryField(info.row.original.id, 'mobile', value)}
        />
      ),
    }),
    columnHelper.accessor('auto_entry_datetime', {
      header: 'Date & Time',
      size: 135,
      minSize: 135,
      cell: info => (
        <EditableCellInput
          initialValue={new Date(info.getValue()).toLocaleString()}
          onCommit={value => updateEntryField(info.row.original.id, 'auto_entry_datetime', value)}
        />
      ),
    }),
    columnHelper.accessor('address', {
      header: 'Address',
      size: 100,
      minSize: 100,
      cell: info => (
        <EditableCellInput
          initialValue={String(info.getValue() || '')}
          onCommit={value => updateEntryField(info.row.original.id, 'address', value)}
        />
      ),
    }),
    columnHelper.accessor('referred_doctor', {
      header: 'Doctor',
      size: 100,
      minSize: 100,
      cell: info => (
        <AutocompleteCell
          value={String(info.getValue() || '')}
          onChange={value => updateEntryField(info.row.original.id, 'referred_doctor', value)}
          fetchOptions={fetchDoctorOptions}
          placeholder="Search doctor..."
        />
      ),
    }),
    columnHelper.accessor('test_name', {
      header: 'Test Name',
      size: 100,
      minSize: 100,
      cell: info => (
        <AutocompleteCell
          value={String(info.getValue() || '')}
          onChange={value => updateEntryField(info.row.original.id, 'test_name', value)}
          fetchOptions={fetchTestOptions}
          placeholder="Search test..."
        />
      ),
    }),
    columnHelper.accessor('fee_amount', {
      header: 'Fee (INR)',
      size: 65,
      minSize: 65,
      cell: info => (
        <EditableCellInput
          type="number"
          initialValue={parseNumber(info.getValue())}
          onCommit={value => updateEntryField(info.row.original.id, 'fee_amount', parseNumber(value, 0))}
        />
      ),
    }),
    columnHelper.accessor('tax_percent', {
      header: 'Tax %',
      size: 55,
      minSize: 55,
      cell: info => (
        <input
          type="number"
          step="0.01"
          min="0"
          max="100"
          defaultValue={parseNumber(info.getValue(), 0)}
          onBlur={e => updateEntryField(info.row.original.id, 'tax_percent', parseNumber(e.target.value, 0))}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:border-blue-500"
        />
      ),
    }),
    columnHelper.display({
      id: 'total_amount',
      header: 'Total (INR)',
      size: 75,
      minSize: 75,
      maxSize: 75,
      meta: { editable: false },
      cell: info => {
        const row = info.row.original
        const total = parseNumber(row.fee_amount, 0) + (parseNumber(row.fee_amount, 0) * parseNumber(row.tax_percent, 0)) / 100
        return <span className="font-bold text-blue-700">INR {total.toFixed(2)}</span>
      },
    }),
    columnHelper.accessor('payment_method', {
      header: 'Payment',
      size: 100,
      minSize: 100,
      maxSize: 100,
      cell: info => {
        const upiEnabled = hasValidUPI(info.row.original.branch_id)

        return (
          <div className="flex items-center">
            <select
              defaultValue={String(info.getValue() || 'Hold')}
              onChange={e => handlePaymentMethodChange(info.row.original, e.target.value)}
              className="w-full min-w-[90px] px-1 py-1 border rounded focus:outline-none focus:border-blue-500"
            >
              <option value="Hold">Hold</option>
              <option value="Cash">Cash</option>
              <option value="UPI" disabled={!upiEnabled}>UPI{!upiEnabled ? ' (Not configured)' : ''}</option>
            </select>
          </div>
        )
      },
    }),
    columnHelper.accessor('status', {
      header: 'Status',
      size: 85,
      minSize: 85,
      cell: info => {
        const { payment_method, is_paid } = info.row.original
        const isPaidState = (payment_method === 'Cash' || payment_method === 'UPI') && is_paid === true
        const isUnpaidState = payment_method === 'Hold' && is_paid === false

        if (isPaidState) {
          return <span className="text-green-600 font-bold">Paid</span>
        }

        if (isUnpaidState) {
          return <span className="text-red-600 font-bold">Unpaid</span>
        }

        return <span className="text-red-600 font-bold">Unpaid</span>
      },
    }),
  ], [
    currentPage,
    pageSize,
    parseNumber,
    updateEntryField,
    handlePaymentMethodChange,
    handleUPIQR,
    hasValidUPI,
    openBillModal,
    openActionsMenuId,
    fetchDoctorOptions,
    fetchPatientOptions,
    fetchTestOptions,
  ])

  const totalPages = Math.max(1, Math.ceil(entries.length / pageSize))
  const paginatedEntries = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    const end = currentPage * pageSize
    return entries.slice(start, end)
  }, [entries, currentPage, pageSize])

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages)
    }
  }, [currentPage, totalPages])

  const table = useReactTable({
    data: paginatedEntries,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  if (!isAdminOrDirector && !isStaff) {
    return (
      <div className="premium-card p-8">
        <h2 className="text-2xl font-black gradient-text">Daily Operations</h2>
        <p className="text-slate-600 mt-3">Access restricted to authorized branch operations users only.</p>
      </div>
    )
  }

  const canAddEntry = !isStaff
  const canExport = !isStaff
  const canManageExpenses = !isStaff

  const invoiceBranch = billEntry ? branchDetailsById[billEntry.branch_id] : undefined
  const invoiceSubtotal = billEntry ? parseNumber(billEntry.fee_amount, 0) : 0
  const invoiceTaxAmount = billEntry ? (invoiceSubtotal * parseNumber(billEntry.tax_percent, 0)) / 100 : 0
  const invoiceGrandTotal = invoiceSubtotal + invoiceTaxAmount
  const invoiceDate = billEntry ? new Date(billEntry.auto_entry_datetime) : null
  const invoiceDueDate = new Date()
  invoiceDueDate.setDate(invoiceDueDate.getDate() + 7)
  const invoiceNumber = billEntry ? `INV-${billEntry.auto_patient_id}` : 'INV-BILL'
  const invoiceLogoUrl = resolveInvoiceMediaUrl(invoiceBranch?.logo_url)

  return (
    <div className="space-y-6">
      {entriesLoadError && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">Daily operations data is temporarily unavailable</p>
          <p className="mt-1 text-xs text-amber-700">Data will auto-refresh when the connection is restored.</p>
        </div>
      )}
      <div className="premium-card p-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-black gradient-text">Daily Operations</h2>
            <p className="text-slate-600 mt-2">Manage daily patient entries, billing, payment, and exports</p>
          </div>
          <div className="flex gap-3">
            {canAddEntry && (
              <button
                onClick={handleAddEntry}
                disabled={isAdding}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold hover:shadow-xl transition"
              >
                {isAdding ? 'Adding...' : 'Add New Entry'}
              </button>
            )}
            <button
              onClick={() => { void fetchEntries() }}
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
            onClick={() => {
              void fetchEntries()
            }}
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

      {canExport && (
        <div className="premium-card p-6">
          <h3 className="text-xl font-black text-slate-900 mb-4">Export Data</h3>
          <button
            onClick={() => setIsExportModalOpen(true)}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-700 text-white font-bold hover:shadow-xl transition"
          >
            Open Export Data
          </button>
        </div>
      )}

      <div className="premium-card p-6 relative">
        <h3 className="text-xl font-black text-slate-900 mb-4">Daily Entries ({entries.length} records)</h3>

        <div className="relative">
          <button
            onClick={scrollTableLeft}
            className="absolute left-2 top-1/2 -translate-y-1/2 z-20 bg-white shadow-lg p-2 rounded-full hover:bg-gray-100 border border-slate-200"
            aria-label="Scroll table left"
          >
            ←
          </button>

          <div
            ref={scrollContainerRef}
            className="w-full max-h-[600px] overflow-x-auto overflow-y-auto border rounded-lg relative"
            onKeyDown={handleTableKeyDown}
          >
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
                  table.getRowModel().rows.map((row, rowIndex) => (
                    <tr key={row.id} className="hover:bg-slate-50">
                      {row.getVisibleCells().map((cell, colIndex) => (
                        <td
                          key={cell.id}
                          data-row-index={rowIndex}
                          data-col-index={colIndex}
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

          <button
            onClick={scrollTableRight}
            className="absolute right-2 top-1/2 -translate-y-1/2 z-20 bg-white shadow-lg p-2 rounded-full hover:bg-gray-100 border border-slate-200"
            aria-label="Scroll table right"
          >
            →
          </button>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm text-slate-700">
            <span>Rows per page</span>
            <select
              value={pageSize}
              onChange={e => {
                setPageSize(Number(e.target.value))
                setCurrentPage(1)
              }}
              className="px-2 py-1 border rounded"
            >
              <option value={40}>40</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 rounded border border-slate-300 text-slate-700 disabled:opacity-50"
            >
              {'<< Prev'}
            </button>
            <span className="text-sm font-semibold text-slate-700">Page {currentPage} of {totalPages}</span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage >= totalPages}
              className="px-3 py-1 rounded border border-slate-300 text-slate-700 disabled:opacity-50"
            >
              {'Next >>'}
            </button>
          </div>
        </div>

        {lastSaved && (
          <div className="mt-3 text-right text-sm text-slate-500">Last saved: {lastSaved.toLocaleTimeString()}</div>
        )}
      </div>

      {canManageExpenses && (
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
      )}

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

      {upiQREntry && branchBankDetails && upiQRCodeValue && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <h3 className="text-2xl font-black text-indigo-700 mb-4">UPI Payment QR</h3>
            <div className="flex justify-center mb-4 bg-white p-4 rounded-xl border">
              <QRCode
                value={upiQRCodeValue}
                size={240}
              />
            </div>
            <div className="bg-indigo-50 p-4 rounded-xl mb-4 text-sm">
              <p><strong>Patient:</strong> {upiQREntry.patient_name}</p>
              <p><strong>Amount:</strong> INR {calculateTotal(upiQREntry).toFixed(2)}</p>
              <p><strong>Test:</strong> {upiQREntry.test_name}</p>
              <p><strong>Branch:</strong> {branchBankDetails.branch_name || '-'}</p>
              <p><strong>UPI ID:</strong> {branchBankDetails.upi_id}</p>
            </div>
            <button
              onClick={() => {
                setUpiQREntry(null)
                setBranchBankDetails(null)
                setUpiQRCodeValue('')
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

      {canExport && isExportModalOpen && (
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
          <style>{`
            @page {
              size: A5 portrait;
              margin: 10mm;
            }

            @media print {
              body * {
                visibility: hidden;
              }

              #invoice-capture,
              #invoice-capture * {
                visibility: visible;
              }

              .bill-print-shell {
                position: static !important;
                inset: auto !important;
                display: block !important;
                background: #ffffff !important;
                padding: 0 !important;
              }

              .bill-print-modal {
                box-shadow: none !important;
                max-height: none !important;
                overflow: visible !important;
                padding: 0 !important;
                border-radius: 0 !important;
              }

              .bill-screen-heading,
              .bill-print-actions {
                display: none !important;
              }

              #invoice-capture {
                position: absolute;
                left: 0;
                top: 0;
                width: 148mm !important;
                max-width: 148mm !important;
                margin: 0 !important;
                padding: 8mm !important;
                box-shadow: none !important;
                border: none !important;
              }
            }
          `}</style>
          <div className="bill-print-modal bg-white rounded-3xl p-6 max-w-3xl w-full max-h-[90vh] overflow-auto shadow-2xl">
            <div className="bill-screen-heading flex justify-between items-center mb-6">
              <h3 className="text-2xl font-black text-slate-900">Medical Invoice</h3>
              <button onClick={() => setBillEntry(null)} className="px-4 py-2 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300">Close</button>
            </div>

            <div className="bill-print-shell">
              <div id="invoice-capture" className="w-full max-w-[600px] mx-auto bg-white p-6 text-slate-900 border border-slate-200 rounded-2xl shadow-sm">
                <div className="border-b border-slate-200 pb-4">
                  <div className="flex justify-between items-start w-full mb-6">
                    <div className="text-left min-w-0">
                      <p className="text-lg font-bold tracking-tight text-slate-900">{invoiceBranch?.name || 'Diagnostic Center'}</p>
                      <p className="mt-2 text-xs leading-5 text-slate-600 whitespace-pre-line">{invoiceBranch?.address || 'Address not available'}</p>
                      <p className="text-xs leading-5 text-slate-600">Contact: {invoiceBranch?.phone || 'Phone not available'}</p>
                      <p className="text-xs leading-5 text-slate-600">Email: {invoiceBranch?.email || 'Email not available'}</p>
                    </div>
                    {invoiceLogoUrl ? (
                      <img
                        src={invoiceLogoUrl}
                        alt={`${invoiceBranch?.name || 'Clinic'} logo`}
                        className="w-16 h-16 object-contain rounded-md shadow-sm"
                      />
                    ) : null}
                  </div>
                  <div className="text-center">
                    <h1 className="text-xl font-bold tracking-[0.24em] text-slate-900">MEDICAL INVOICE</h1>
                  </div>
                </div>

                <div className="flex justify-between items-start w-full my-4">
                  {/* Left Column: Bill To */}
                  <div className="text-left space-y-1">
                    <h3 className="font-bold text-gray-800 text-lg">Bill To</h3>
                    <p><strong>Patient Name:</strong> {billEntry.patient_name}</p>
                    <p><strong>Mobile:</strong> {billEntry.mobile || '-'}</p>
                    <p><strong>Address:</strong> {billEntry.address || '-'}</p>
                    <p><strong>Patient ID:</strong> {billEntry.auto_patient_id}</p>
                  </div>
                  {/* Right Column: Invoice Details */}
                  <div className="text-right space-y-1">
                    <h3 className="font-bold text-gray-800 text-lg">Invoice Details</h3>
                    <p><strong>Invoice #:</strong> {invoiceNumber}</p>
                    <p><strong>Date:</strong> {invoiceDate ? invoiceDate.toLocaleDateString() : '-'}</p>
                    <p><strong>Due Date:</strong> {invoiceDueDate.toLocaleDateString()}</p>
                    <p><strong>Payment Method:</strong> {billEntry.payment_method || '-'}</p>
                  </div>
                </div>

                {/* Service Table */}
                <table className="w-full border-collapse border border-gray-200 text-sm">
                  <thead>
                    <tr className="bg-gray-100 border-b-2 border-gray-300">
                      <th className="px-4 py-3 text-sm font-bold text-gray-900 text-center w-10">#</th>
                      <th className="px-4 py-3 text-sm font-bold text-gray-900 text-left">Description</th>
                      <th className="px-4 py-3 text-sm font-bold text-gray-900 text-center w-16">Qty</th>
                      <th className="px-4 py-3 text-sm font-bold text-gray-900 text-right w-24">Unit Price</th>
                      <th className="px-4 py-3 text-sm font-bold text-gray-900 text-right w-24">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-gray-200 bg-white">
                      <td className="border p-2 text-center">1</td>
                      <td className="border p-2">
                        <strong>{billEntry.test_name}</strong><br />
                        <span className="text-xs text-gray-500">Referring Doctor: {billEntry.referred_doctor || 'Self'}</span>
                      </td>
                      <td className="border p-2 text-center">1</td>
                      <td className="border p-2 text-right">INR {invoiceSubtotal.toFixed(2)}</td>
                      <td className="border p-2 text-right font-medium">INR {invoiceSubtotal.toFixed(2)}</td>
                    </tr>
                  </tbody>
                </table>

                {/* Summary Block (Right-Aligned) */}
                <div className="mt-6 ml-auto w-64 space-y-2 text-right">
                  <div className="flex justify-between border-b border-gray-300 pb-1 text-sm">
                    <span>Subtotal</span>
                    <span>INR {invoiceSubtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-300 pb-1 text-sm">
                    <span>Tax ({parseNumber(billEntry.tax_percent).toFixed(2)}%)</span>
                    <span>INR {invoiceTaxAmount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold border-t-2 border-black pt-3 mt-1">
                    <span>Total</span>
                    <span>INR {invoiceGrandTotal.toFixed(2)}</span>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-200">
                  <p className="text-[11px] leading-5 text-slate-500">Terms & Conditions: Payment is due in 7 days. Thank you for choosing us.</p>
                </div>
              </div>
            </div>

            <div className="bill-print-actions flex gap-3 mt-6">
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
