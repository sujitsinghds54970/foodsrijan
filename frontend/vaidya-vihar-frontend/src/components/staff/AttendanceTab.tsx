import { useEffect, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { useAuth } from '../../contexts/AuthContext'
import { getApiErrorMessage, resolveStaffMediaUrl, staffSelfApi } from './api'
import { AttendanceLogItem, LeaveBalance, LeaveRequestItem, LinkedDeviceItem } from './types'
import LeavePanel from './attendance/LeavePanel'
import LinkedDevicesCard from './attendance/LinkedDevicesCard'
import DisputeFab from './attendance/DisputeFab'
import ClockModal from './attendance/ClockModal'

const monthToken = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString()
}

const buildThumbUrl = (rawPath?: string | null, versionSeed?: string | null) => {
  const base = resolveStaffMediaUrl(rawPath)
  if (!base) return ''
  const seed = encodeURIComponent(versionSeed || '')
  return `${base}${base.includes('?') ? '&' : '?'}v=${seed}`
}

interface AttendanceTabProps {
  staffProfileId?: number
}

export default function AttendanceTab(_: AttendanceTabProps) {
  const { user } = useAuth()
  const [month, setMonth] = useState(monthToken(new Date()))
  const [previewLog, setPreviewLog] = useState<AttendanceLogItem | null>(null)
  const [previewImageUrl, setPreviewImageUrl] = useState<string>('')
  const [previewFileUrl, setPreviewFileUrl] = useState<string>('')
  const [previewFileType, setPreviewFileType] = useState<'image' | 'pdf' | ''>('')
  const [uploadingRowId, setUploadingRowId] = useState<number | null>(null)
  const [attachmentFiles, setAttachmentFiles] = useState<File[]>([])
  const [branchLabel, setBranchLabel] = useState<string>('')
  const attachmentInputRef = useRef<HTMLInputElement | null>(null)
  const historyRef = useRef<HTMLDivElement | null>(null)
  const branchName = useMemo(() => {
    if ((branchLabel || '').trim()) {
      return branchLabel.trim()
    }
    const fromAuthBranch = ((user as any)?.branch?.name || '').trim()
    const fromAuthName = ((user as any)?.branch_name || '').trim()
    const fromSelected = (localStorage.getItem('selectedBranchName') || '').trim()
    const fromLocal = (localStorage.getItem('branchName') || '').trim()
    const candidate = fromAuthBranch || fromAuthName || fromSelected || fromLocal
    if (!candidate || candidate.toLowerCase() === 'branch') {
      return 'Diagnostic Center'
    }
    return candidate
  }, [branchLabel, user])
  const branchAddress = useMemo(() => {
    const fromAuth = ((user as any)?.branch?.address || '').trim()
    const fromLocal = (localStorage.getItem('selectedBranchAddress') || localStorage.getItem('branchAddress') || '').trim()
    return fromAuth || fromLocal
  }, [user])
  const branchPhone = useMemo(() => {
    const fromAuth = ((user as any)?.branch?.phone || '').trim()
    const fromLocal = (localStorage.getItem('selectedBranchPhone') || localStorage.getItem('branchPhone') || '').trim()
    return fromAuth || fromLocal
  }, [user])
  const branchEmail = useMemo(() => {
    const fromAuth = ((user as any)?.branch?.email || '').trim()
    const fromLocal = (localStorage.getItem('selectedBranchEmail') || localStorage.getItem('branchEmail') || '').trim()
    return fromAuth || fromLocal
  }, [user])
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<AttendanceLogItem[]>([])
  const [leaves, setLeaves] = useState<LeaveRequestItem[]>([])
  const [upcomingLeaves, setUpcomingLeaves] = useState<LeaveRequestItem[]>([])
  const [devices, setDevices] = useState<LinkedDeviceItem[]>([])
  const [leaveBalance, setLeaveBalance] = useState<LeaveBalance | null>(null)

  const [showClockModal, setShowClockModal] = useState(false)
  const [clockAction, setClockAction] = useState<'in' | 'out'>('in')
  const [location, setLocation] = useState<{ lat?: number; lng?: number }>({})

  const [showLeaveApplyModal, setShowLeaveApplyModal] = useState(false)
  const [leaveType, setLeaveType] = useState('casual')
  const [leaveStart, setLeaveStart] = useState('')
  const [leaveEnd, setLeaveEnd] = useState('')
  const [leaveReason, setLeaveReason] = useState('')
  const [leaveFile, setLeaveFile] = useState<File | null>(null)
  const [taskStatusDraft, setTaskStatusDraft] = useState<Record<number, string>>({})
  const [taskDraft, setTaskDraft] = useState<Record<number, string>>({})
  const [staffNoteDraft, setStaffNoteDraft] = useState<Record<number, string>>({})

  const taskOptions = ['Sample Collection', 'Report Dispatch', 'Patient Follow-up', 'Inventory Check', 'Reception Duty', 'Admin Task']

  const isDirectorView = ((user?.role || '').toLowerCase() === 'branch_director')

  const refreshAll = async () => {
    setLoading(true)
    try {
      const [attendanceRows, leaveRows, upcoming, linked, balance, me] = await Promise.all([
        staffSelfApi.getAttendance(month),
        staffSelfApi.listLeaves(),
        staffSelfApi.getUpcomingLeaves(),
        staffSelfApi.getLinkedDevices(),
        staffSelfApi.getLeaveBalance(),
        staffSelfApi.getMe(),
      ])
      setLogs(attendanceRows)
      setLeaves(leaveRows)
      setUpcomingLeaves(upcoming.items)
      setDevices(linked)
      setLeaveBalance(balance)
      const liveBranchName = (me?.branch_name || '').trim()
      if (liveBranchName) {
        setBranchLabel(liveBranchName)
      }
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to load attendance dashboard'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month])

  const getLocation = (): Promise<{ lat: number; lng: number }> => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported by this browser."))
        return
      }
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          })
        },
        (error) => {
          console.warn("⚠️ Geolocation error:", error.message)
          reject(error)
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      )
    })
  }

  const requestClock = async (action: 'in' | 'out') => {
    setClockAction(action)
    try {
      const coords = await getLocation()
      setLocation({ lat: coords.lat, lng: coords.lng })
      console.log("✅ Location obtained:", coords)
      setShowClockModal(true)
    } catch (error: any) {
      console.warn("⚠️ Could not obtain location:", error)
      // Check if permission was denied
      if (error.code === 1) {
        toast.error("Location access denied. Please enable GPS in your browser settings.")
        return
      }
      // If location not available, show message but still allow clock-in
      console.log("GPS location unavailable, proceeding without location.")
      setLocation({})
      setShowClockModal(true)
    }
  }

  const submitClock = async (payload: { selfie?: File; workMode: 'onsite' | 'work_from_home'; wfhReason?: string }) => {
    const formData = new FormData()
    formData.append('action', clockAction)
    if (location.lat !== undefined) formData.append('location_lat', String(location.lat))
    if (location.lng !== undefined) formData.append('location_lng', String(location.lng))
    formData.append('work_mode', payload.workMode)
    if (payload.wfhReason) formData.append('wfh_reason', payload.wfhReason)
    if (payload.selfie) formData.append('selfie', payload.selfie)

    try {
      const saved = await staffSelfApi.clockAttendance(formData)
      setLogs((prev) => {
        const next = prev.filter((row) => row.id !== saved.id)
        return [...next, saved].sort((a, b) => a.date.localeCompare(b.date))
      })
      await refreshAll()
      toast.success(clockAction === 'in' ? 'Clock-in recorded' : 'Clock-out recorded')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Clock update failed'))
      throw error
    }
  }

  const cancelLeave = async (leaveId: number) => {
    try {
      await staffSelfApi.cancelLeave(leaveId)
      toast.success('Leave cancelled')
      await refreshAll()
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to cancel leave'))
    }
  }

  const applyLeave = async () => {
    if (!leaveStart || !leaveEnd) {
      toast.error('Please select start and end date')
      return
    }
    const formData = new FormData()
    formData.append('leave_type', leaveType)
    formData.append('start_date', new Date(`${leaveStart}T00:00:00`).toISOString())
    formData.append('end_date', new Date(`${leaveEnd}T00:00:00`).toISOString())
    if (leaveReason) formData.append('reason', leaveReason)
    if (leaveFile) formData.append('attachment', leaveFile)

    try {
      await staffSelfApi.createLeave(formData)
      toast.success('Leave request submitted')
      setShowLeaveApplyModal(false)
      setLeaveReason('')
      setLeaveFile(null)
      await refreshAll()
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to create leave request'))
    }
  }

  const submitDispute = async (payload: { attendance_date: string; reason: string }) => {
    try {
      await staffSelfApi.createDispute(payload)
      toast.success('Dispute submitted')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to submit dispute'))
      throw error
    }
  }

  const exportPdf = async () => {
    const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
    const pageWidth = doc.internal.pageSize.getWidth()
    const pageHeight = doc.internal.pageSize.getHeight()
    const headerHeight = 36
    const monthLabelText = (() => {
      const [year, mon] = month.split('-').map((x) => Number(x))
      if (!Number.isFinite(mon) || !Number.isFinite(year)) {
        return month
      }
      return `${new Date(year, mon - 1, 1).toLocaleString('en-US', { month: 'long' })} ${year}`
    })()

    doc.setFillColor(29, 78, 216)
    doc.rect(0, 0, pageWidth, headerHeight, 'F')
    doc.setFillColor(30, 64, 175)
    doc.rect(0, headerHeight - 3, pageWidth, 3, 'F')

    doc.setTextColor(255, 255, 255)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(21)
    doc.text(branchName, 12, 12)

    doc.setFont('helvetica', 'normal')
    doc.setFontSize(9)
    if (branchAddress) {
      const addressText = doc.splitTextToSize(branchAddress, 140)
      doc.text(addressText, 12, 18)
    }

    const contactParts: string[] = []
    if (branchPhone) contactParts.push(`Phone: ${branchPhone}`)
    if (branchEmail) contactParts.push(`Email: ${branchEmail}`)
    if (contactParts.length > 0) {
      doc.text(contactParts.join(' | '), 12, 24)
    }

    doc.setFont('helvetica', 'bold')
    doc.setFontSize(12)
    doc.text('Attendance Report', pageWidth - 78, 14)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    doc.text(`Month: ${monthLabelText}`, pageWidth - 78, 20)
    doc.text(`Generated: ${new Date().toLocaleDateString()}`, pageWidth - 78, 25)

    const body = logs.map((row) => [
      new Date(row.date).toLocaleDateString(),
      row.clock_in_time ? new Date(row.clock_in_time).toLocaleTimeString() : '-',
      row.clock_out_time ? new Date(row.clock_out_time).toLocaleTimeString() : '-',
      row.task || '-',
      row.task_status || 'Pending',
      row.leave_status || '-',
      row.staff_note || '-',
    ])

    autoTable(doc, {
      head: [['Date', 'In', 'Out', 'Task', 'Status', 'Leave', 'Note']],
      body,
      theme: 'grid',
      headStyles: {
        fillColor: [41, 128, 185],
        textColor: [255, 255, 255],
        fontSize: 10,
        halign: 'center',
      },
      bodyStyles: {
        fontSize: 9,
        valign: 'middle',
        cellPadding: 2.8,
      },
      alternateRowStyles: {
        fillColor: [240, 240, 240],
      },
      margin: { left: 12, right: 12, top: 44 },
      startY: 44,
      tableWidth: 'auto',
      styles: { overflow: 'linebreak' },
      columnStyles: {
        0: { cellWidth: 28 },
        1: { cellWidth: 24 },
        2: { cellWidth: 24 },
        3: { cellWidth: 56 },
        4: { cellWidth: 28 },
        5: { cellWidth: 24 },
        6: { cellWidth: 78 },
      },
    })

    doc.setTextColor(120, 120, 120)
    doc.setFontSize(9)
    doc.setFont('helvetica', 'normal')
    doc.text(`Generated on: ${new Date().toLocaleString()}`, 12, pageHeight - 8)

    const [year, mon] = month.split('-').map((x) => Number(x))
    const monthLabel = Number.isFinite(mon) ? new Date(year, mon - 1, 1).toLocaleString('en-US', { month: 'short' }) : 'Month'
    const safeBranch = branchName.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'Attendance'
    doc.save(`${safeBranch}_Attendance_${monthLabel}${year}.pdf`)
  }

  const isPdf = (value: string) => value.toLowerCase().endsWith('.pdf')

  const removeSelectedAttachment = (indexToRemove: number) => {
    setAttachmentFiles((prev) => prev.filter((_, index) => index !== indexToRemove))
  }

  const uploadAttachments = async () => {
    if (!uploadingRowId || attachmentFiles.length === 0) {
      toast.error('Please select attachment files first')
      return
    }
    try {
      const updated = await staffSelfApi.uploadAttendanceAttachments(uploadingRowId, attachmentFiles)
      setLogs((prev) => prev.map((row) => (row.id === uploadingRowId ? { ...row, ...updated } : row)))
      setAttachmentFiles([])
      setUploadingRowId(null)
      toast.success('Attachments uploaded')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to upload attachments'))
    }
  }

  const removeAttachment = async (rowId: number, fileUrl: string) => {
    try {
      const updated = await staffSelfApi.deleteAttendanceAttachment(rowId, fileUrl)
      setLogs((prev) => prev.map((row) => (row.id === rowId ? { ...row, ...updated } : row)))
      toast.success('Attachment deleted')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to delete attachment'))
    }
  }

  const presentDays = useMemo(() => logs.filter((item) => ['present', 'workfromhome'].includes(item.status.toLowerCase())).length, [logs])
  const leaveUsage = useMemo(() => {
    const casualTotal = Number(leaveBalance?.casual_total || 0)
    const sickTotal = Number(leaveBalance?.sick_total || 0)
    const earnedTotal = Number(leaveBalance?.earned_total || 0)
    const casualRemaining = Number(leaveBalance?.casual_remaining || 0)
    const sickRemaining = Number(leaveBalance?.sick_remaining || 0)
    const earnedRemaining = Number(leaveBalance?.earned_remaining || 0)

    const toUsedPercent = (remaining: number, total: number) => {
      if (total <= 0) return 0
      return Math.min(100, Math.max(0, Math.round(((total - remaining) / total) * 100)))
    }

    return {
      casual: toUsedPercent(casualRemaining, casualTotal),
      sick: toUsedPercent(sickRemaining, sickTotal),
      earned: toUsedPercent(earnedRemaining, earnedTotal),
    }
  }, [leaveBalance])

  const saveHistoryEdit = async (
    rowId: number,
    overrides?: { task?: string; task_status?: string; staff_note?: string },
  ) => {
    try {
      const updated = await staffSelfApi.updateAttendance(rowId, {
        task: overrides?.task ?? taskDraft[rowId],
        task_status: overrides?.task_status ?? taskStatusDraft[rowId],
        staff_note: overrides?.staff_note ?? staffNoteDraft[rowId],
      })
      setLogs((prev) => prev.map((x) => (x.id === rowId ? { ...x, ...updated } : x)))
      toast.success('Saved')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to save updates'))
    }
  }

  return (
    <div className="space-y-5">
      <section className="rounded-3xl border border-slate-200 bg-gradient-to-r from-teal-600 via-cyan-600 to-blue-700 p-6 text-white shadow-2xl dark:border-slate-700">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wider text-white/85">Attendance & Leave</p>
            <h2 className="text-2xl font-black">Staff Attendance Command Center</h2>
            <p className="text-sm text-white/90">Present days this month: {presentDays}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => requestClock('in')} className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-600">Clock In</button>
            <button onClick={() => requestClock('out')} className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-bold text-white hover:bg-orange-600">Clock Out</button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase text-slate-500 dark:text-slate-300">Casual Left</p>
          <p className="text-2xl font-black text-slate-900 dark:text-slate-100">{leaveBalance?.casual_remaining ?? 0}</p>
          <div className="mt-2 h-2 rounded bg-slate-100">
            <div className="h-2 rounded bg-emerald-500" style={{ width: `${leaveUsage.casual}%` }} />
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase text-slate-500 dark:text-slate-300">Sick Left</p>
          <p className="text-2xl font-black text-slate-900 dark:text-slate-100">{leaveBalance?.sick_remaining ?? 0}</p>
          <div className="mt-2 h-2 rounded bg-slate-100">
            <div className="h-2 rounded bg-amber-500" style={{ width: `${leaveUsage.sick}%` }} />
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase text-slate-500 dark:text-slate-300">Earned Left</p>
          <p className="text-2xl font-black text-slate-900 dark:text-slate-100">{leaveBalance?.earned_remaining ?? 0}</p>
          <div className="mt-2 h-2 rounded bg-slate-100">
            <div className="h-2 rounded bg-indigo-500" style={{ width: `${leaveUsage.earned}%` }} />
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs uppercase text-slate-500 dark:text-slate-300">Export</p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-300">Use the PDF button in the history panel.</p>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.3fr_1fr]">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <label className="text-sm font-semibold text-slate-700 dark:text-slate-200">Month</label>
            <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded-lg border px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100" />
            {loading && <span className="text-xs text-slate-500 dark:text-slate-300">Syncing...</span>}
          </div>
          <div
            ref={historyRef}
            className="w-full overflow-x-auto overflow-y-auto max-h-[600px] border rounded-lg relative bg-white dark:bg-slate-900 dark:border-slate-700"
          >
            <div className="relative">
              <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
                <div>
                  <h3 className="text-lg font-black bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">{branchName}</h3>
                </div>
                <button onClick={() => void exportPdf()} className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white">PDF</button>
              </div>
              <table className="min-w-[1200px] w-full text-sm">
                <thead className="sticky top-0 z-10 bg-blue-50 shadow-sm text-left text-xs uppercase text-slate-700">
                  <tr>
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Clock In</th>
                    <th className="px-3 py-2">Clock Out</th>
                    <th className="px-3 py-2">Task</th>
                    <th className="px-3 py-2">Task Status</th>
                    <th className="px-3 py-2">Leave Status</th>
                    <th className="px-3 py-2">In Selfie</th>
                    <th className="px-3 py-2">Out Selfie</th>
                    <th className="px-3 py-2">Attachments</th>
                    <th className="px-3 py-2">Note</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((row, index) => (
                    <tr key={row.id} className={`${index % 2 === 0 ? 'bg-gray-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-900'} border-t border-slate-100 dark:border-slate-800`}>
                      <td className="px-3 py-2">{new Date(row.date).toLocaleDateString()}</td>
                      <td className="px-3 py-2">{row.clock_in_time ? new Date(row.clock_in_time).toLocaleTimeString() : '-'}</td>
                      <td className="px-3 py-2">{row.clock_out_time ? new Date(row.clock_out_time).toLocaleTimeString() : '-'}</td>
                      <td className="px-3 py-2">
                        <select
                          className="w-44 rounded border px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
                          value={taskDraft[row.id] ?? row.task ?? ''}
                          onChange={(e) => {
                            const value = e.target.value
                            setTaskDraft((prev) => ({ ...prev, [row.id]: value }))
                            void saveHistoryEdit(row.id, { task: value })
                          }}
                        >
                          <option value="">Select Task</option>
                          {taskOptions.map((task) => (
                            <option key={task} value={task}>{task}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        <select
                          className="rounded border px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
                          value={taskStatusDraft[row.id] ?? row.task_status ?? 'Pending'}
                          onChange={(e) => {
                            const value = e.target.value
                            setTaskStatusDraft((prev) => ({ ...prev, [row.id]: value }))
                            void saveHistoryEdit(row.id, { task_status: value })
                          }}
                        >
                          <option>Pending</option>
                          <option>In Progress</option>
                          <option>Completed</option>
                        </select>
                      </td>
                      <td className="px-3 py-2">{row.leave_status || '-'}</td>
                      <td className="px-3 py-2">
                        {(row.clock_in_selfie_url || row.selfie_url) ? (
                          <img
                            key={`${row.id}-in-${row.clock_in_time || row.date}`}
                            src={buildThumbUrl(row.clock_in_selfie_url || row.selfie_url, row.clock_in_time || row.date)}
                            alt="In selfie"
                            className="w-12 h-12 rounded object-cover border border-gray-200 cursor-pointer hover:opacity-80"
                            style={{ width: '48px', height: '48px', objectFit: 'cover', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: 'pointer' }}
                            onError={(e) => {
                              e.currentTarget.src = '/placeholder-avatar.svg'
                            }}
                            onClick={() => {
                              setPreviewLog(row)
                              setPreviewImageUrl(buildThumbUrl(row.clock_in_selfie_url || row.selfie_url, row.clock_in_time || row.date))
                            }}
                          />
                        ) : '-'}
                      </td>
                      <td className="px-3 py-2">
                        {(row.clock_out_selfie_url || row.selfie_url) ? (
                          <img
                            key={`${row.id}-out-${row.clock_out_time || row.date}`}
                            src={buildThumbUrl(row.clock_out_selfie_url || row.selfie_url, row.clock_out_time || row.date)}
                            alt="Out selfie"
                            className="w-12 h-12 rounded object-cover border border-gray-200 cursor-pointer hover:opacity-80"
                            style={{ width: '48px', height: '48px', objectFit: 'cover', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: 'pointer' }}
                            onError={(e) => {
                              e.currentTarget.src = '/placeholder-avatar.svg'
                            }}
                            onClick={() => {
                              setPreviewLog(row)
                              setPreviewImageUrl(buildThumbUrl(row.clock_out_selfie_url || row.selfie_url, row.clock_out_time || row.date))
                            }}
                          />
                        ) : '-'}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {(row.attachments || []).map((fileUrl, idx) => (
                            <div key={`${row.id}-att-${idx}`} className="inline-flex items-center gap-1">
                              {isPdf(fileUrl) ? (
                                <button
                                  type="button"
                                  className="flex h-12 w-12 items-center justify-center rounded border border-gray-200 text-2xl cursor-pointer hover:opacity-80"
                                  style={{ width: '48px', height: '48px', minWidth: '48px', minHeight: '48px' }}
                                  onClick={() => {
                                    setPreviewFileUrl(resolveStaffMediaUrl(fileUrl))
                                    setPreviewFileType('pdf')
                                  }}
                                  aria-label="Open PDF attachment"
                                >
                                  📄
                                </button>
                              ) : (
                                <img
                                  src={resolveStaffMediaUrl(fileUrl)}
                                  alt="Attachment"
                                  className="w-12 h-12 object-cover rounded border border-gray-200 cursor-pointer hover:opacity-80"
                                  style={{ width: '48px', height: '48px', objectFit: 'cover', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: 'pointer', display: 'block' }}
                                  onClick={() => {
                                    setPreviewFileUrl(resolveStaffMediaUrl(fileUrl))
                                    setPreviewFileType('image')
                                  }}
                                />
                              )}
                              <button
                                type="button"
                                className="rounded border border-rose-200 px-1.5 py-1 text-[10px] text-rose-600 hover:bg-rose-50"
                                onClick={() => void removeAttachment(row.id, fileUrl)}
                              >
                                Delete
                              </button>
                            </div>
                          ))}
                          {(row.attachments || []).length < 6 && row.id > 0 && (
                            <button
                              type="button"
                              className="rounded bg-sky-600 px-2 py-1 text-xs font-semibold text-white hover:bg-sky-700"
                              onClick={() => setUploadingRowId(row.id)}
                            >
                              Upload
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <input
                          className="w-40 rounded border px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800"
                          value={staffNoteDraft[row.id] ?? row.staff_note ?? ''}
                          onChange={(e) => setStaffNoteDraft((prev) => ({ ...prev, [row.id]: e.target.value }))}
                          onBlur={(e) => void saveHistoryEdit(row.id, { staff_note: e.target.value })}
                          placeholder="Add note"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <LeavePanel upcoming={upcomingLeaves} leaves={leaves} onCancel={cancelLeave} onOpenApply={() => setShowLeaveApplyModal(true)} />

          <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Pending Actions Workflow Hub</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-300">Staff can cancel pending leave requests directly from the table.</p>
            {isDirectorView && (
              <div className="mt-3 flex gap-2">
                <button className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white">Approve</button>
                <button className="rounded-md bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white">Reject</button>
                <button className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-900">Ask for Reschedule</button>
              </div>
            )}
          </div>

          <LinkedDevicesCard devices={devices} onResetToken={async () => {
            try {
              await staffSelfApi.resetLinkedDeviceToken()
              toast.success('Device token reset')
              setDevices(await staffSelfApi.getLinkedDevices())
            } catch (error: any) {
              toast.error(getApiErrorMessage(error, 'Unable to reset device token'))
            }
          }} />
        </div>
      </section>

      <ClockModal
        open={showClockModal}
        action={clockAction}
        location={location}
        onClose={() => setShowClockModal(false)}
        onConfirm={submitClock}
      />

      {previewLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', padding: '16px' }} onClick={() => { setPreviewLog(null); setPreviewImageUrl('') }}>
          <div className="w-full max-w-3xl rounded-2xl bg-white p-5 shadow-2xl dark:bg-slate-900" style={{ width: '100%', maxWidth: '960px', background: '#ffffff', borderRadius: '16px', padding: '20px' }} onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-lg font-bold text-slate-900 dark:text-slate-100">Stamped Attendance Image</h4>
                <p className="text-xs text-slate-500">{new Date(previewLog.date).toLocaleDateString()}</p>
              </div>
              <button className="rounded border px-3 py-1.5 text-sm" onClick={() => { setPreviewLog(null); setPreviewImageUrl('') }}>Close</button>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <img src={previewImageUrl || resolveStaffMediaUrl(previewLog.clock_in_selfie_url || previewLog.selfie_url)} alt="preview" className="w-full rounded-xl border object-cover" style={{ width: '100%', maxHeight: '70vh', objectFit: 'contain', border: '1px solid #e5e7eb', borderRadius: '12px' }} />
              <div className="space-y-3 text-sm text-slate-700 dark:text-slate-200">
                <p><span className="font-semibold">Clock In:</span> {formatDate(previewLog.clock_in_time)}</p>
                <p><span className="font-semibold">Clock Out:</span> {formatDate(previewLog.clock_out_time)}</p>
                <p><span className="font-semibold">Task:</span> {previewLog.task || '-'}</p>
                <p><span className="font-semibold">Status:</span> {previewLog.status}</p>
                <p><span className="font-semibold">Location:</span> {previewLog.location_lat ?? '-'}, {previewLog.location_lng ?? '-'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {uploadingRowId && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4" onClick={() => { setUploadingRowId(null); setAttachmentFiles([]) }}>
          <div className="w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h4 className="text-lg font-bold text-slate-900">Upload Attendance Attachments</h4>
            <p className="mt-1 text-xs text-slate-500">Upload up to 6 files total (JPG/PDF).</p>

            <input
              ref={attachmentInputRef}
              type="file"
              accept=".jpg,.jpeg,.pdf"
              multiple
              className="hidden"
              onChange={(e) => setAttachmentFiles(Array.from(e.target.files || []).slice(0, 6))}
            />

            <button
              type="button"
              onClick={() => attachmentInputRef.current?.click()}
              className="mt-4 flex w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-sky-300 bg-sky-50 px-4 py-8 text-center hover:bg-sky-100"
            >
              <span className="text-3xl" aria-hidden="true">📎</span>
              <span className="mt-2 text-sm font-semibold text-slate-800">Click to select files</span>
              <span className="mt-1 text-xs text-slate-500">JPG and PDF only, max 6 files</span>
            </button>

            <div className="mt-4 max-h-40 space-y-2 overflow-y-auto">
              {attachmentFiles.length === 0 ? (
                <p className="text-xs text-slate-500">No files selected yet.</p>
              ) : attachmentFiles.map((file, index) => (
                <div key={`${file.name}-${index}`} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-800">{file.name}</p>
                    <p className="text-xs text-slate-500">{Math.max(1, Math.round(file.size / 1024))} KB</p>
                  </div>
                  <button
                    type="button"
                    className="rounded border border-rose-200 px-2 py-1 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                    onClick={() => removeSelectedAttachment(index)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button className="rounded border px-3 py-1.5 text-sm" onClick={() => { setUploadingRowId(null); setAttachmentFiles([]) }}>Cancel</button>
              <button className="rounded bg-sky-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50" disabled={attachmentFiles.length === 0} onClick={() => void uploadAttachments()}>Upload</button>
            </div>
          </div>
        </div>
      )}

      {previewFileType === 'image' && previewFileUrl && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4" style={{ position: 'fixed', inset: 0, zIndex: 70, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.7)', padding: '16px' }} onClick={() => { setPreviewFileUrl(''); setPreviewFileType('') }}>
          <img src={previewFileUrl} alt="attachment-preview" className="max-h-[85vh] max-w-[95vw] rounded-xl border border-white/30 object-contain" style={{ maxHeight: '85vh', maxWidth: '95vw', objectFit: 'contain', border: '1px solid rgba(255,255,255,0.3)', borderRadius: '12px' }} onClick={(e) => e.stopPropagation()} />
        </div>
      )}

      {previewFileType === 'pdf' && previewFileUrl && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 p-4" style={{ position: 'fixed', inset: 0, zIndex: 70, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.7)', padding: '16px' }} onClick={() => { setPreviewFileUrl(''); setPreviewFileType('') }}>
          <div className="h-[85vh] w-[95vw] overflow-hidden rounded-xl border border-white/30 bg-white" style={{ height: '85vh', width: '95vw', overflow: 'hidden', borderRadius: '12px', background: '#ffffff', border: '1px solid rgba(255,255,255,0.3)' }} onClick={(e) => e.stopPropagation()}>
            <iframe src={previewFileUrl} title="attachment-pdf-preview" className="h-full w-full" />
          </div>
        </div>
      )}

      {showLeaveApplyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 dark:bg-slate-900">
            <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Apply Leave</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} className="rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800">
                <option value="sick">Sick</option>
                <option value="casual">Casual</option>
                <option value="earned">Earned</option>
                <option value="compensatory">Compensatory</option>
              </select>
              <input type="file" onChange={(e) => setLeaveFile(e.target.files?.[0] || null)} className="rounded-lg border px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800" />
              <input type="date" value={leaveStart} onChange={(e) => setLeaveStart(e.target.value)} className="rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800" />
              <input type="date" value={leaveEnd} onChange={(e) => setLeaveEnd(e.target.value)} className="rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800" />
              <textarea value={leaveReason} onChange={(e) => setLeaveReason(e.target.value)} className="md:col-span-2 rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800" rows={3} placeholder="Reason" />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowLeaveApplyModal(false)} className="rounded-md border px-3 py-2 text-sm dark:border-slate-700">Close</button>
              <button onClick={applyLeave} className="rounded-md bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-700">Submit</button>
            </div>
          </div>
        </div>
      )}

      <DisputeFab onSubmit={submitDispute} />
    </div>
  )
}
