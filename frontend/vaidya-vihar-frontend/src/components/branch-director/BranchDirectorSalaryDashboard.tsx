import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Bar,
  BarChart,
  Cell,
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
import { createColumnHelper, flexRender, getCoreRowModel, RowSelectionState, useReactTable } from '@tanstack/react-table'

import { branchPayrollApi } from './branchPayrollApi'
import {
  BranchPayrollAnalytics,
  BranchPayrollGridRow,
  BranchPayrollHealthScore,
  BranchPayrollReadiness,
  BranchPayrollSimulationResponse,
  BranchPayrollStatutoryReport,
  PayrollAnomalyItem,
  PayrollWellnessData,
  TopEarnerItem,
} from './branchPayrollTypes'

const PIE_COLORS = ['#2563eb', '#7c3aed', '#0f766e', '#ea580c', '#e11d48', '#0891b2']
const topEarnerColumnHelper = createColumnHelper<TopEarnerItem>()
const gridColumnHelper = createColumnHelper<BranchPayrollGridRow>()

function computeNetPay(row: BranchPayrollGridRow): number {
  const gross =
    Number(row.basic || 0) +
    Number(row.da || 0) +
    Number(row.hra || 0) +
    Number(row.shift_allowance || 0) +
    Number(row.ot || 0) +
    Number(row.incentives || 0)
  const deductions = Number(row.lop || 0) + Number(row.statutory_deductions || 0)
  return gross - deductions
}

export default function BranchDirectorSalaryDashboard() {
  const today = new Date()
  const [month, setMonth] = useState<number>(today.getMonth() + 1)
  const [year, setYear] = useState<number>(today.getFullYear())
  const [health, setHealth] = useState<BranchPayrollHealthScore | null>(null)
  const [analytics, setAnalytics] = useState<BranchPayrollAnalytics | null>(null)
  const [readiness, setReadiness] = useState<BranchPayrollReadiness | null>(null)
  const [statutory, setStatutory] = useState<BranchPayrollStatutoryReport | null>(null)
  const [anomalies, setAnomalies] = useState<PayrollAnomalyItem[]>([])
  const [wellness, setWellness] = useState<PayrollWellnessData | null>(null)
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(false)
  const [gridRows, setGridRows] = useState<BranchPayrollGridRow[]>([])
  const [selectedTopEarner, setSelectedTopEarner] = useState<TopEarnerItem | null>(null)
  const [simDepartment, setSimDepartment] = useState('')
  const [simHikePercentage, setSimHikePercentage] = useState<number>(10)
  const [simResult, setSimResult] = useState<BranchPayrollSimulationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [bulkMode, setBulkMode] = useState<'percent' | 'fixed'>('percent')
  const [bulkValue, setBulkValue] = useState<number>(5)
  const [targetDepartment, setTargetDepartment] = useState<string>('')
  const [unlockReason, setUnlockReason] = useState<string>('')
  const [isReviewMode, setIsReviewMode] = useState(false)
  const [savingByStaffId, setSavingByStaffId] = useState<Record<number, boolean>>({})
  const [savedByStaffId, setSavedByStaffId] = useState<Record<number, boolean>>({})
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const debounceRef = useRef<Record<number, ReturnType<typeof setTimeout>>>({})

  const activeRunId = health?.payroll_run?.id || null
  const runStatus = health?.payroll_run_status || 'Draft'
  const isLocked = runStatus.toLowerCase() === 'locked'
  const isGridReadOnly = isLocked || isReviewMode
  const selectedStaffIds = useMemo(
    () => Object.keys(rowSelection).filter((key) => rowSelection[key]).map((key) => Number(key)).filter((id) => Number.isFinite(id) && id > 0),
    [rowSelection],
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [healthRes, analyticsRes, readinessRes, anomalyRes, twoFactorRes] = await Promise.all([
        branchPayrollApi.getHealthScore(month, year),
        branchPayrollApi.getAnalytics(month, year),
        branchPayrollApi.getReadiness(month, year),
        branchPayrollApi.getAnomalies(month, year),
        branchPayrollApi.getTwoFactorState(),
      ])
      setHealth(healthRes)
      setAnalytics(analyticsRes)
      setReadiness(readinessRes)
      setAnomalies(anomalyRes.anomalies || [])
      setTwoFactorEnabled(twoFactorRes.two_factor_enabled)
      setSelectedTopEarner((prev) => {
        if (!prev) return analyticsRes.top_earners[0] || null
        return analyticsRes.top_earners.find((item) => item.staff_profile_id === prev.staff_profile_id) || analyticsRes.top_earners[0] || null
      })
      if (healthRes.payroll_run?.id) {
        const [statutoryRes, wellnessRes, previewRes] = await Promise.all([
          branchPayrollApi.getStatutoryReport(healthRes.payroll_run.id),
          branchPayrollApi.getWellness(healthRes.payroll_run.id),
          branchPayrollApi.preview(healthRes.payroll_run.id),
        ])
        setStatutory(statutoryRes)
        setWellness(wellnessRes)
        setGridRows(previewRes.grid_rows.map((row) => ({ ...row, net_pay: computeNetPay(row) })))
      } else {
        setStatutory(null)
        setWellness(null)
        setGridRows([])
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to load branch payroll dashboard')
    } finally {
      setLoading(false)
    }
  }, [month, year])

  const previewRun = async (runId: number) => {
    setPreviewLoading(true)
    try {
      const response = await branchPayrollApi.preview(runId)
      setGridRows(response.grid_rows.map((row) => ({ ...row, net_pay: computeNetPay(row) })))
      toast.success('Payroll preview refreshed')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to preview payroll run')
    } finally {
      setPreviewLoading(false)
    }
  }

  const refreshPayrollData = useCallback(async () => {
    try {
      const response = await branchPayrollApi.generate(month, year, 'fetch_data')
      setGridRows(response.grid_rows.map((row) => ({ ...row, net_pay: computeNetPay(row) })))
      await load()
      toast.success('Payroll data refreshed')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to refresh payroll data')
      if (activeRunId) {
        await previewRun(activeRunId)
      }
    }
  }, [activeRunId, load, month, year])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const syncPayrollAfterSalarySave = () => {
      void refreshPayrollData()
    }
    window.addEventListener('staff-salary-updated', syncPayrollAfterSalarySave)
    return () => window.removeEventListener('staff-salary-updated', syncPayrollAfterSalarySave)
  }, [refreshPayrollData])

  const handleBulkAdjust = async () => {
    if (!activeRunId) {
      toast.error('Generate a payroll run first')
      return
    }
    try {
      const response = await branchPayrollApi.adjust({
        payroll_run_id: activeRunId,
        adjustment_type: bulkMode,
        value: bulkValue,
        target_department: targetDepartment || undefined,
        unlock_reason: unlockReason || undefined,
      })
      setGridRows((response.grid_rows as BranchPayrollGridRow[]).map((row) => ({ ...row, net_pay: computeNetPay(row) })))
      toast.success(`${response.message} (${response.affected_employees} employees)`)
      setUnlockReason('')
      await load()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Bulk adjustment failed')
    }
  }

  const handleSimulate = async () => {
    if (!simDepartment.trim()) {
      toast.error('Enter a department for simulation')
      return
    }
    try {
      const response = await branchPayrollApi.simulate(simDepartment.trim(), simHikePercentage)
      setSimResult(response)
      toast.success('Simulation completed')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Simulation failed')
    }
  }

  const toggleTwoFactor = async () => {
    try {
      const response = await branchPayrollApi.setTwoFactorState(!twoFactorEnabled)
      setTwoFactorEnabled(response.two_factor_enabled)
      toast.success(`Two-factor ${response.two_factor_enabled ? 'enabled' : 'disabled'}`)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to update two-factor setting')
    }
  }

  const handleApprove = async () => {
    if (!activeRunId) {
      toast.error('No payroll run available for approval')
      return
    }
    try {
      const response = await branchPayrollApi.approve(activeRunId)
      toast.success(`${response.message || 'Payroll approved'}${response?.payslips_emailed !== undefined ? ` • Emails sent: ${response.payslips_emailed}` : ''}`)
      setIsReviewMode(true)
      await load()
      await previewRun(activeRunId)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Approval failed')
    }
  }

  const handleFreeze = async () => {
    if (isLocked) {
      toast.error('Payroll is already locked')
      return
    }
    try {
      const response = await branchPayrollApi.generate(month, year, 'freeze')
      setGridRows(response.grid_rows.map((row) => ({ ...row, net_pay: computeNetPay(row) })))
      toast.success(response.message || 'Payroll frozen')
      await load()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Freeze failed')
    }
  }

  const handleReviewToggle = async () => {
    if (!isReviewMode) {
      try {
        const response = await branchPayrollApi.generate(month, year, 'review')
        setGridRows(response.grid_rows.map((row) => ({ ...row, net_pay: computeNetPay(row) })))
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Unable to move run into review')
      }
    }
    setIsReviewMode((prev) => !prev)
  }

  const handleProcessSelected = async () => {
    if (!activeRunId) {
      toast.error('Generate a payroll run first')
      return
    }
    if (!selectedStaffIds.length) {
      toast.error('Select at least one staff row to process')
      return
    }
    try {
      const response = await branchPayrollApi.processSelected(selectedStaffIds, activeRunId)
      toast.success(`${response.message} • Emails sent: ${response.emails_sent}`)
      if (response.email_failures?.length) {
        console.log('PROCESS_SELECTED_EMAIL_FAILURES:', response.email_failures)
      }
      setRowSelection({})
      await load()
      await previewRun(activeRunId)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Process Selected failed')
    }
  }

  const persistGridRow = useCallback(
    async (staffProfileId: number, rowData: BranchPayrollGridRow) => {
      if (!activeRunId || isGridReadOnly) return
      setSavingByStaffId((prev) => ({ ...prev, [staffProfileId]: true }))
      try {
        await branchPayrollApi.updateStaffPayrollRow(staffProfileId, {
          payroll_run_id: activeRunId,
          basic: Number(rowData.basic || 0),
          da: Number(rowData.da || 0),
          hra: Number(rowData.hra || 0),
          shift_allowance: Number(rowData.shift_allowance || 0),
          ot: Number(rowData.ot || 0),
          lop: Number(rowData.lop || 0),
          incentives: Number(rowData.incentives || 0),
          statutory_deductions: Number(rowData.statutory_deductions || 0),
        })
        setSavedByStaffId((prev) => ({ ...prev, [staffProfileId]: true }))
        setTimeout(() => {
          setSavedByStaffId((prev) => {
            const next = { ...prev }
            delete next[staffProfileId]
            return next
          })
        }, 2000)
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Failed to save payroll row')
      } finally {
        setSavingByStaffId((prev) => ({ ...prev, [staffProfileId]: false }))
      }
    },
    [activeRunId, isGridReadOnly],
  )

  const queuePersistGridRow = useCallback(
    (staffProfileId: number, rowData: BranchPayrollGridRow) => {
      if (debounceRef.current[staffProfileId]) {
        clearTimeout(debounceRef.current[staffProfileId])
      }
      debounceRef.current[staffProfileId] = setTimeout(() => {
        void persistGridRow(staffProfileId, rowData)
      }, 550)
    },
    [persistGridRow],
  )

  const handleEditableCellChange = useCallback((rowIndex: number, key: keyof BranchPayrollGridRow, value: number) => {
    if (isGridReadOnly) return
    let updatedRow: BranchPayrollGridRow | null = null
    setGridRows((prev) =>
      prev.map((row, index) => {
        if (index !== rowIndex) return row
        updatedRow = { ...row, [key]: Number.isFinite(value) ? value : 0 }
        return { ...updatedRow, net_pay: computeNetPay(updatedRow) }
      }),
    )
    if (updatedRow) {
      queuePersistGridRow(updatedRow.staff_profile_id, updatedRow)
    }
  }, [isGridReadOnly, queuePersistGridRow])

  useEffect(() => {
    const timers = debounceRef.current
    return () => {
      Object.values(timers).forEach((timer) => clearTimeout(timer))
    }
  }, [])

  useEffect(() => {
    const available = new Set(gridRows.map((row) => String(row.staff_profile_id)))
    setRowSelection((prev) => {
      const next: RowSelectionState = {}
      Object.entries(prev).forEach(([key, value]) => {
        if (value && available.has(key)) next[key] = true
      })
      return next
    })
  }, [gridRows])

  const statusBadgeClass = useMemo(() => {
    const normalized = runStatus.toLowerCase()
    if (normalized.includes('locked') || normalized.includes('processed')) return 'bg-emerald-100 text-emerald-700'
    if (normalized.includes('approved') || normalized.includes('ready')) return 'bg-blue-100 text-blue-700'
    if (normalized.includes('review')) return 'bg-amber-100 text-amber-700'
    return 'bg-slate-200 text-slate-700'
  }, [runStatus])

  const topEarnerColumns = useMemo(
    () => [
      topEarnerColumnHelper.accessor('employee_name', { header: 'Employee' }),
      topEarnerColumnHelper.accessor('department', { header: 'Department' }),
      topEarnerColumnHelper.accessor('net_pay', {
        header: 'Net Pay',
        cell: (info) => `INR ${Number(info.getValue() || 0).toLocaleString()}`,
      }),
      topEarnerColumnHelper.accessor('incentives', {
        header: 'Incentives',
        cell: (info) => `INR ${Number(info.getValue() || 0).toLocaleString()}`,
      }),
    ],
    [],
  )

  const topEarnerTable = useReactTable({
    data: analytics?.top_earners || [],
    columns: topEarnerColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  const gridColumns = useMemo(
    () => [
    gridColumnHelper.display({
      id: 'select',
      header: ({ table }) => (
        <input
          type="checkbox"
          checked={table.getIsAllRowsSelected()}
          ref={(el) => {
            if (el) el.indeterminate = table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
          }}
          onChange={table.getToggleAllRowsSelectedHandler()}
          className="h-3.5 w-3.5 rounded border-slate-300"
          disabled={isLocked}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          className="h-3.5 w-3.5 rounded border-slate-300"
          disabled={isLocked}
        />
      ),
    }),
    gridColumnHelper.accessor('employee_name', {
      header: 'Employee Name',
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span>{row.original.employee_name}</span>
          {savingByStaffId[row.original.staff_profile_id] && <span className="text-[10px] font-semibold text-amber-600">Saving...</span>}
          {savedByStaffId[row.original.staff_profile_id] && <span className="text-[10px] font-semibold text-emerald-600">Saved</span>}
        </div>
      ),
    }),
    gridColumnHelper.accessor('basic', {
      header: 'Basic',
      cell: ({ row }) => (
        <input
          type="number"
          value={Number(row.original.basic || 0)}
          onChange={(event) => handleEditableCellChange(row.index, 'basic', Number(event.target.value || 0))}
          className="w-24 rounded border border-slate-300 px-2 py-1 text-xs"
          disabled={isGridReadOnly}
        />
      ),
    }),
    gridColumnHelper.accessor('da', {
      header: 'DA',
      cell: ({ row }) => (
        <input
          type="number"
          value={Number(row.original.da || 0)}
          onChange={(event) => handleEditableCellChange(row.index, 'da', Number(event.target.value || 0))}
          className="w-20 rounded border border-slate-300 px-2 py-1 text-xs"
          disabled={isGridReadOnly}
        />
      ),
    }),
    gridColumnHelper.accessor('hra', {
      header: 'HRA',
      cell: ({ row }) => (
        <input
          type="number"
          value={Number(row.original.hra || 0)}
          onChange={(event) => handleEditableCellChange(row.index, 'hra', Number(event.target.value || 0))}
          className="w-20 rounded border border-slate-300 px-2 py-1 text-xs"
          disabled={isGridReadOnly}
          />
        ),
      }),
      gridColumnHelper.accessor('shift_allowance', {
        header: 'Shift Allowance',
        cell: ({ row, getValue }) => (
          <input
            type="number"
            value={Number(getValue() || 0)}
            onChange={(event) => handleEditableCellChange(row.index, 'shift_allowance', Number(event.target.value || 0))}
            className="w-24 rounded border border-slate-300 px-2 py-1 text-xs"
            disabled={isGridReadOnly}
          />
        ),
      }),
      gridColumnHelper.accessor('ot', {
        header: 'OT',
        cell: ({ row, getValue }) => (
          <input
            type="number"
            value={Number(getValue() || 0)}
            onChange={(event) => handleEditableCellChange(row.index, 'ot', Number(event.target.value || 0))}
            className="w-20 rounded border border-slate-300 px-2 py-1 text-xs"
            disabled={isGridReadOnly}
          />
        ),
      }),
      gridColumnHelper.accessor('lop', {
        header: 'LOP',
        cell: ({ row, getValue }) => (
          <input
            type="number"
            value={Number(getValue() || 0)}
            onChange={(event) => handleEditableCellChange(row.index, 'lop', Number(event.target.value || 0))}
            className="w-20 rounded border border-slate-300 px-2 py-1 text-xs"
            disabled={isGridReadOnly}
          />
        ),
      }),
      gridColumnHelper.accessor('incentives', {
        header: 'Incentives',
        cell: ({ row, getValue }) => (
          <input
            type="number"
            value={Number(getValue() || 0)}
            onChange={(event) => handleEditableCellChange(row.index, 'incentives', Number(event.target.value || 0))}
            className="w-24 rounded border border-slate-300 px-2 py-1 text-xs"
            disabled={isGridReadOnly}
          />
        ),
      }),
      gridColumnHelper.accessor('statutory_deductions', {
        header: 'Statutory Deductions',
        cell: ({ row, getValue }) => (
          <input
            type="number"
            value={Number(getValue() || 0)}
            onChange={(event) => handleEditableCellChange(row.index, 'statutory_deductions', Number(event.target.value || 0))}
            className="w-28 rounded border border-slate-300 px-2 py-1 text-xs"
            disabled={isGridReadOnly}
          />
        ),
      }),
      gridColumnHelper.accessor((row) => computeNetPay(row), {
        id: 'net_pay',
        header: 'Net Pay',
        cell: ({ row }) => <span className="font-bold text-slate-900">INR {Number(computeNetPay(row.original) || 0).toLocaleString()}</span>,
      }),
    ],
    [handleEditableCellChange, isGridReadOnly, isLocked, savedByStaffId, savingByStaffId],
  )

  const gridTable = useReactTable({
    data: gridRows,
    columns: gridColumns,
    getRowId: (row) => String(row.staff_profile_id),
    enableRowSelection: true,
    state: { rowSelection },
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
  })

  const gaugeData = [{ name: 'score', value: health?.health_score || 0, fill: '#2563eb' }]

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-black text-slate-900">Salary Management Command Center</h2>
            <p className="mt-1 text-sm text-slate-600">Branch payroll pulse, analytics insights, processing and approval workflow.</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={12}
              value={month}
              onChange={(event) => setMonth(Number(event.target.value || 1))}
              className="w-16 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            />
            <input
              type="number"
              min={2000}
              max={2200}
              value={year}
              onChange={(event) => setYear(Number(event.target.value || today.getFullYear()))}
              className="w-20 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg lg:col-span-2">
            <h3 className="text-sm font-bold text-slate-800">Payroll Readiness Score</h3>
            <p className="mt-1 text-3xl font-black text-slate-900">{readiness?.readiness_score ?? 0}</p>
            <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
                Attendance Completeness: {Number(readiness?.attendance_completeness_percent || 0).toFixed(1)}%
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700">
                Leave Approval Coverage: {Number(readiness?.leave_approval_percent || 0).toFixed(1)}%
              </div>
            </div>
            <ul className="mt-2 space-y-1 text-xs text-slate-600">
              {(readiness?.reasons || []).map((reason) => (
                <li key={reason}>• {reason}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg">
            <h3 className="text-sm font-bold text-slate-800">Security</h3>
            <p className="mt-1 text-xs text-slate-600">Two-factor protection for payroll approvals (mock toggle).</p>
            <button
              type="button"
              onClick={() => void toggleTwoFactor()}
              className={`mt-3 inline-flex rounded-full px-3 py-1.5 text-xs font-bold ${twoFactorEnabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-700'}`}
            >
              2FA {twoFactorEnabled ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg xl:col-span-1">
          <h3 className="text-sm font-bold text-slate-700">Payroll Health Scorecard</h3>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart innerRadius="60%" outerRadius="90%" data={gaugeData} startAngle={90} endAngle={-270}>
                <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                <RadialBar background dataKey="value" cornerRadius={10} />
              </RadialBarChart>
            </ResponsiveContainer>
          </div>
          <div className="text-center">
            <p className="text-3xl font-black text-slate-900">{health?.health_score ?? 0}</p>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{health?.health_band || 'N/A'}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:col-span-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg">
            <p className="text-xs uppercase text-slate-500">Total Branch Payroll</p>
            <p className="mt-1 text-2xl font-black text-slate-900">INR {Number(health?.total_branch_payroll || 0).toLocaleString()}</p>
            <p className="mt-1 text-xs text-slate-500">MoM {Number(health?.mom_variance_percent || 0).toFixed(2)}% • YoY {Number(health?.yoy_variance_percent || 0).toFixed(2)}%</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg">
            <p className="text-xs uppercase text-slate-500">Cost-to-Income Ratio</p>
            <p className="mt-1 text-2xl font-black text-slate-900">{Number(health?.cost_to_income_ratio || 0).toFixed(2)}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg">
            <p className="text-xs uppercase text-slate-500">Payroll Run Status</p>
            <span className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-bold ${statusBadgeClass}`}>{runStatus}</span>
            <p className="mt-2 text-xs text-slate-500">
              {health?.payroll_run ? `Run #${health.payroll_run.id} (${String(health.payroll_run.month).padStart(2, '0')}/${health.payroll_run.year})` : 'No run generated'}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-lg md:col-span-3">
            <h4 className="text-sm font-bold text-slate-800">Pending Actions</h4>
            <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-3">
              {(health?.pending_actions || []).map((item) => (
                <div key={item.title} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-700">{item.title}</p>
                  <p className="text-xl font-black text-slate-900">{item.count}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
          <h3 className="text-base font-bold text-slate-900">Department-wise Burn</h3>
          <div className="mt-3 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={analytics?.department_wise_burn || []} dataKey="amount" nameKey="department" innerRadius={58} outerRadius={95}>
                  {(analytics?.department_wise_burn || []).map((entry, index) => (
                    <Cell key={`${entry.department}-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: any) => `INR ${Number(value || 0).toLocaleString()}`} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
              <h3 className="text-base font-bold text-slate-900">Salary Hike Simulator</h3>
              <p className="mt-1 text-sm text-slate-600">What-if scenario modeling by department.</p>
              <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
                <input
                  value={simDepartment}
                  onChange={(event) => setSimDepartment(event.target.value)}
                  placeholder="Department (e.g. Radiology)"
                  className="rounded border border-slate-300 px-2 py-2 text-sm md:col-span-2"
                />
                <input
                  type="number"
                  value={simHikePercentage}
                  onChange={(event) => setSimHikePercentage(Number(event.target.value || 0))}
                  className="rounded border border-slate-300 px-2 py-2 text-sm"
                />
              </div>
              <button type="button" onClick={() => void handleSimulate()} className="mt-3 rounded-lg bg-cyan-600 px-3 py-2 text-xs font-bold text-white hover:bg-cyan-700">
                Run Simulation
              </button>
              {simResult && (
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                  <p>Current: INR {simResult.current_total_cost.toLocaleString()} → Projected: INR {simResult.projected_total_cost.toLocaleString()}</p>
                  <p>Delta: INR {simResult.projected_delta.toLocaleString()} | Health Score Impact: {simResult.health_score_impact}</p>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
              <h3 className="text-base font-bold text-slate-900">Export Options</h3>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" onClick={() => window.open(branchPayrollApi.payrollReportUrl('pdf', activeRunId || undefined), '_blank')} className="rounded bg-slate-700 px-3 py-2 text-xs font-bold text-white">Payroll PDF</button>
                <button type="button" onClick={() => window.open(branchPayrollApi.payrollReportUrl('excel', activeRunId || undefined), '_blank')} className="rounded bg-slate-700 px-3 py-2 text-xs font-bold text-white">Payroll Excel</button>
                <button type="button" onClick={() => window.open(branchPayrollApi.payrollReportUrl('csv', activeRunId || undefined), '_blank')} className="rounded bg-slate-700 px-3 py-2 text-xs font-bold text-white">Payroll CSV</button>
                <button type="button" onClick={() => window.open(branchPayrollApi.bankFileUrl(activeRunId || undefined), '_blank')} className="rounded bg-emerald-700 px-3 py-2 text-xs font-bold text-white">Bank File</button>
              </div>
              <p className="mt-3 text-xs text-slate-500">Includes statutory-ready summaries for salary disbursement workflows.</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
          <h3 className="text-base font-bold text-slate-900">12-Month Payroll Trend</h3>
          <div className="mt-3 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics?.payroll_trend_12m || []}>
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(value) => `${Math.round((value || 0) / 1000)}k`} />
                <Tooltip formatter={(value: any) => `INR ${Number(value || 0).toLocaleString()}`} />
                <Line type="monotone" dataKey="payroll_cost" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
              <h3 className="text-base font-bold text-slate-900">Statutory Compliance Report</h3>
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead className="bg-slate-100">
                    <tr>
                      <th className="px-2 py-2 text-left">Department</th>
                      <th className="px-2 py-2 text-right">PF</th>
                      <th className="px-2 py-2 text-right">ESI</th>
                      <th className="px-2 py-2 text-right">PT</th>
                      <th className="px-2 py-2 text-right">TDS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(statutory?.contributions || []).map((row) => (
                      <tr key={row.department} className="border-b border-slate-100">
                        <td className="px-2 py-2">{row.department}</td>
                        <td className="px-2 py-2 text-right">INR {row.pf.toLocaleString()}</td>
                        <td className="px-2 py-2 text-right">INR {row.esi.toLocaleString()}</td>
                        <td className="px-2 py-2 text-right">INR {row.pt.toLocaleString()}</td>
                        <td className="px-2 py-2 text-right">INR {row.tds.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
              <h3 className="text-base font-bold text-slate-900">Anomaly Detection Alerts</h3>
              <div className="mt-3 space-y-2">
                {anomalies.length === 0 ? (
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-700">No payroll anomalies flagged for this month.</div>
                ) : (
                  anomalies.map((item) => (
                    <div key={`${item.staff_profile_id}-${item.message}`} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                      <p className="font-bold">{item.employee_name} ({item.department})</p>
                      <p>{item.message}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
            <h3 className="text-base font-bold text-slate-900">Employee Financial Wellness Dashboard</h3>
            <p className="mt-1 text-sm text-slate-600">Average salary, distribution, and financial stress indicators.</p>
            <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Average Salary</p>
                <p className="mt-1 text-xl font-black text-slate-900">INR {Number(wellness?.average_salary || 0).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">High Advance Requests</p>
                <p className="mt-1 text-xl font-black text-slate-900">{wellness?.financial_stress?.high_advance_requests || 0}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs uppercase text-slate-500">Pending Advances</p>
                <p className="mt-1 text-xl font-black text-slate-900">{wellness?.financial_stress?.pending_advance_requests || 0}</p>
              </div>
            </div>
            <div className="mt-4 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={wellness?.salary_distribution || []}>
                  <XAxis dataKey="bucket" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            OT: INR {Number(analytics?.overtime_allowance_breakdown?.overtime || 0).toLocaleString()} • Allowances: INR {Number(analytics?.overtime_allowance_breakdown?.allowances || 0).toLocaleString()}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
        <h3 className="text-base font-bold text-slate-900">Top Earners</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100">
              {topEarnerTable.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="px-3 py-2 text-left text-xs font-bold uppercase text-slate-600">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {topEarnerTable.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={`cursor-pointer border-b border-slate-100 ${selectedTopEarner?.staff_profile_id === row.original.staff_profile_id ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                  onClick={() => setSelectedTopEarner(row.original)}
                >
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
        {selectedTopEarner && (
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <p className="font-bold text-slate-900">{selectedTopEarner.employee_name} • {selectedTopEarner.department}</p>
            <p className="mt-1">Basic: INR {selectedTopEarner.basic.toLocaleString()} | Incentives: INR {selectedTopEarner.incentives.toLocaleString()} | Deductions: INR {selectedTopEarner.deductions.toLocaleString()}</p>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-bold text-slate-900">Payroll Run Dashboard</h3>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" onClick={() => void refreshPayrollData()} className="rounded-lg bg-slate-700 px-3 py-2 text-xs font-bold text-white hover:bg-slate-800">Fetch Data</button>
            <button type="button" onClick={() => void handleReviewToggle()} className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-bold text-white hover:bg-blue-700">{isReviewMode ? 'Exit Review' : 'Review'}</button>
            <button type="button" disabled={!activeRunId || isLocked} onClick={() => void handleFreeze()} className="rounded-lg bg-indigo-600 px-3 py-2 text-xs font-bold text-white hover:bg-indigo-700 disabled:opacity-50">Freeze</button>
            <button type="button" disabled={!activeRunId || !selectedStaffIds.length || isLocked} onClick={() => void handleProcessSelected()} className="rounded-lg bg-teal-600 px-3 py-2 text-xs font-bold text-white hover:bg-teal-700 disabled:opacity-50">Process Selected</button>
            <button type="button" disabled={!activeRunId || previewLoading} onClick={() => activeRunId && void previewRun(activeRunId)} className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Preview</button>
            <button type="button" disabled={!activeRunId || isLocked} onClick={() => void handleApprove()} className="rounded-lg bg-purple-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50">Approve</button>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs font-bold uppercase text-slate-600">Bulk Adjustments</p>
          <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-6">
            <select value={bulkMode} onChange={(event) => setBulkMode(event.target.value as 'percent' | 'fixed')} className="rounded border border-slate-300 px-2 py-2 text-sm">
              <option value="percent">Percentage (%)</option>
              <option value="fixed">Fixed Amount</option>
            </select>
            <input type="number" value={bulkValue} onChange={(event) => setBulkValue(Number(event.target.value || 0))} className="rounded border border-slate-300 px-2 py-2 text-sm" />
            <input placeholder="Target department (optional)" value={targetDepartment} onChange={(event) => setTargetDepartment(event.target.value)} className="md:col-span-2 rounded border border-slate-300 px-2 py-2 text-sm" />
            <input placeholder="Unlock reason (required only if locked)" value={unlockReason} onChange={(event) => setUnlockReason(event.target.value)} className="rounded border border-slate-300 px-2 py-2 text-sm" />
            <button type="button" disabled={!activeRunId} onClick={() => void handleBulkAdjust()} className="rounded bg-amber-600 px-3 py-2 text-sm font-bold text-white disabled:opacity-50">Apply</button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full border border-slate-200 text-xs">
            <thead className="bg-slate-100">
              {gridTable.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="border border-slate-200 px-2 py-2 text-left font-bold text-slate-700">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {gridTable.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="border border-slate-200 px-2 py-2 text-slate-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {!gridRows.length && (
            <div className="mt-3 rounded-lg border border-dashed border-slate-300 p-4 text-center text-sm text-slate-500">
              {loading ? 'Loading dashboard...' : 'No payroll grid data yet. Start with Fetch Data.'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
