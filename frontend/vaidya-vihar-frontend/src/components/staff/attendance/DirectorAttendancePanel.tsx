import { useEffect, useMemo, useState } from 'react'
import Calendar from 'react-calendar'
import toast from 'react-hot-toast'
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'

import { AttendanceLogItem } from '../types'
import { directorAttendanceApi, getApiErrorMessage, resolveStaffMediaUrl } from '../api'

const monthToken = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`

const toDateKey = (value: Date | string) => {
  const d = typeof value === 'string' ? new Date(value) : value
  const tz = d.getTimezoneOffset() * 60000
  return new Date(d.getTime() - tz).toISOString().slice(0, 10)
}

const statusClass = (status?: string) => {
  const s = (status || '').trim().toLowerCase()
  if (s === 'present') return 'bg-green-500 text-white'
  if (s === 'late') return 'bg-yellow-500 text-white'
  if (s === 'absent') return 'bg-red-500 text-white'
  if (s === 'leave') return 'bg-blue-500 text-white'
  return 'bg-slate-200 text-slate-700'
}

interface DirectorAttendancePanelProps {
  staffProfileId: number
}

export default function DirectorAttendancePanel({ staffProfileId }: DirectorAttendancePanelProps) {
  const [month, setMonth] = useState(monthToken(new Date()))
  const [rows, setRows] = useState<AttendanceLogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [taskDraft, setTaskDraft] = useState<Record<number, string>>({})
  const [taskStatusDraft, setTaskStatusDraft] = useState<Record<number, string>>({})
  const [selectedLog, setSelectedLog] = useState<AttendanceLogItem | null>(null)
  const [expandedImage, setExpandedImage] = useState<string>('')
  const [previewFileUrl, setPreviewFileUrl] = useState<string>('')
  const [previewFileType, setPreviewFileType] = useState<'image' | 'pdf' | ''>('')
  const [hrRemarkDraft, setHrRemarkDraft] = useState<Record<number, string>>({})
  const [disputeResolvedDraft, setDisputeResolvedDraft] = useState<Record<number, boolean>>({})
  const branchName = (localStorage.getItem('selectedBranchName') || localStorage.getItem('branchName') || 'Branch').trim()

  const isPdf = (value: string) => value.toLowerCase().endsWith('.pdf')

  const load = async () => {
    try {
      setLoading(true)
      const data = await directorAttendanceApi.getStaffAttendance(staffProfileId, month)
      setRows(data)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to load attendance table'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staffProfileId, month])

  const byDate = useMemo(() => new Map(rows.map((x) => [x.date, x])), [rows])

  const selectedMeta = useMemo(() => {
    if (!selectedLog) return null
    return {
      clockIn: selectedLog.clock_in_time ? new Date(selectedLog.clock_in_time).toLocaleString() : '-',
      clockOut: selectedLog.clock_out_time ? new Date(selectedLog.clock_out_time).toLocaleString() : '-',
      inSelfieUrl: selectedLog.clock_in_selfie_url || selectedLog.selfie_url,
      outSelfieUrl: selectedLog.clock_out_selfie_url,
    }
  }, [selectedLog])

  const assignTask = async (attendanceId: number) => {
    if (!attendanceId || attendanceId < 0) {
      toast.error('Task can be assigned only for marked attendance records')
      return
    }
    const task = (taskDraft[attendanceId] || '').trim()
    if (!task) {
      toast.error('Task is required')
      return
    }
    try {
      const updated = await directorAttendanceApi.assignTask(staffProfileId, attendanceId, {
        task,
        task_status: taskStatusDraft[attendanceId] || 'Pending',
      })
      setRows((prev) => prev.map((x) => (x.id === attendanceId ? updated : x)))
      toast.success('Task assigned')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Task assignment failed'))
    }
  }

  const saveDirectorReview = async (attendanceId: number) => {
    if (!attendanceId || attendanceId < 0) {
      toast.error('Review can be updated only for marked attendance records')
      return
    }
    try {
      const updated = await directorAttendanceApi.updateAttendanceReview(staffProfileId, attendanceId, {
        hr_remark: hrRemarkDraft[attendanceId],
        dispute_resolved: disputeResolvedDraft[attendanceId],
      })
      setRows((prev) => prev.map((row) => (row.id === attendanceId ? { ...row, ...updated } : row)))
      toast.success('Review updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to update review'))
    }
  }

  const exportAttendancePdf = () => {
    const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
    const pageWidth = doc.internal.pageSize.getWidth()
    const pageHeight = doc.internal.pageSize.getHeight()

    doc.setFillColor(29, 78, 216)
    doc.rect(0, 0, pageWidth, 28, 'F')

    doc.setTextColor(255, 255, 255)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(18)
    doc.text(branchName, 12, 11)

    doc.setFont('helvetica', 'normal')
    doc.setFontSize(10)
    doc.text(`Staff Attendance Order (Staff ID: ${staffProfileId})`, 12, 18)
    doc.text(`Month: ${month}`, pageWidth - 56, 18)

    const body = rows.map((row) => [
      new Date(row.date).toLocaleDateString(),
      row.clock_in_time ? new Date(row.clock_in_time).toLocaleTimeString() : '-',
      row.clock_out_time ? new Date(row.clock_out_time).toLocaleTimeString() : '-',
      row.task || '-',
      row.task_status || 'Pending',
      row.leave_status || '-',
      row.staff_note || '-',
      row.hr_remark || '-',
      row.dispute_resolved ? 'Resolved' : 'Open',
    ])

    autoTable(doc, {
      head: [['Date', 'In', 'Out', 'Task', 'Status', 'Leave', 'Note', 'HR Remark', 'Dispute']],
      body,
      theme: 'grid',
      headStyles: {
        fillColor: [41, 128, 185],
        textColor: [255, 255, 255],
        fontSize: 9,
        halign: 'center',
      },
      bodyStyles: {
        fontSize: 8,
        valign: 'middle',
        cellPadding: 2,
      },
      alternateRowStyles: {
        fillColor: [245, 245, 245],
      },
      margin: { left: 10, right: 10, top: 36 },
      startY: 36,
      styles: { overflow: 'linebreak' },
      columnStyles: {
        0: { cellWidth: 20 },
        1: { cellWidth: 18 },
        2: { cellWidth: 18 },
        3: { cellWidth: 42 },
        4: { cellWidth: 20 },
        5: { cellWidth: 18 },
        6: { cellWidth: 56 },
        7: { cellWidth: 56 },
        8: { cellWidth: 20 },
      },
    })

    doc.setTextColor(120, 120, 120)
    doc.setFontSize(8)
    doc.text(`Generated on: ${new Date().toLocaleString()}`, 10, pageHeight - 6)

    const safeBranch = branchName.replace(/[^a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'Branch'
    doc.save(`${safeBranch}_Staff_${staffProfileId}_Attendance_${month}.pdf`)
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base font-bold text-slate-900">Attendance Overview</h3>
        <div className="flex items-center gap-2">
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="rounded border px-2 py-1.5 text-sm" />
          <button
            type="button"
            onClick={exportAttendancePdf}
            className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
          >
            Download PDF
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <div className="rounded-xl border border-slate-200 p-3">
          <Calendar
            value={new Date()}
            tileClassName={({ date, view }) => {
              if (view !== 'month') return ''
              const row = byDate.get(toDateKey(date))
              if (!row) return 'rounded-md bg-slate-100'
              return `rounded-md ${statusClass(row.status)}`
            }}
            onClickDay={(day) => {
              const row = byDate.get(toDateKey(day)) || null
              setSelectedLog(row)
              if (row) {
                setExpandedImage(resolveStaffMediaUrl(row.clock_in_selfie_url || row.selfie_url || row.clock_out_selfie_url || ''))
              } else {
                setExpandedImage('')
              }
            }}
          />
          <p className="mt-2 text-xs text-slate-500">Click a date to inspect Clock In/Out, selfies, and location.</p>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-[1200px] w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2 text-left">Date</th>
                <th className="px-3 py-2 text-left">Clock In Time</th>
                <th className="px-3 py-2 text-left">Clock Out Time</th>
                <th className="px-3 py-2 text-left">Task Provided</th>
                <th className="px-3 py-2 text-left">Task Status</th>
                <th className="px-3 py-2 text-left">Note</th>
                <th className="px-3 py-2 text-left">In-Time Selfie</th>
                <th className="px-3 py-2 text-left">Out-Time Selfie</th>
                <th className="px-3 py-2 text-left">Attachments</th>
                <th className="px-3 py-2 text-left">Location</th>
                <th className="px-3 py-2 text-left">Leave Status</th>
                <th className="px-3 py-2 text-left">HR Remark</th>
                <th className="px-3 py-2 text-left">Dispute</th>
                <th className="px-3 py-2 text-left">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className="px-3 py-4" colSpan={14}>Loading...</td></tr>
              ) : rows.length === 0 ? (
                <tr><td className="px-3 py-4" colSpan={14}>No attendance records in this month.</td></tr>
              ) : rows.map((row) => {
                const lat = row.location_lat
                const lng = row.location_lng
                const mapLink = lat !== undefined && lat !== null && lng !== undefined && lng !== null
                  ? `https://maps.google.com/?q=${lat},${lng}`
                  : ''
                return (
                  <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-3 py-2">{new Date(row.date).toLocaleDateString()}</td>
                    <td className="px-3 py-2">{row.clock_in_time ? new Date(row.clock_in_time).toLocaleTimeString() : '-'}</td>
                    <td className="px-3 py-2">{row.clock_out_time ? new Date(row.clock_out_time).toLocaleTimeString() : '-'}</td>
                    <td className="px-3 py-2">
                      <input
                        className="w-56 rounded border px-2 py-1"
                        value={taskDraft[row.id] ?? row.task ?? ''}
                        onChange={(e) => setTaskDraft((prev) => ({ ...prev, [row.id]: e.target.value }))}
                        placeholder="Assign task"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        className="rounded border px-2 py-1"
                        value={taskStatusDraft[row.id] ?? row.task_status ?? 'Pending'}
                        onChange={(e) => setTaskStatusDraft((prev) => ({ ...prev, [row.id]: e.target.value }))}
                      >
                        <option>Pending</option>
                        <option>In Progress</option>
                        <option>Completed</option>
                      </select>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-700">{row.staff_note || '-'}</td>
                    <td className="px-3 py-2">
                      {(row.clock_in_selfie_url || row.selfie_url) ? (
                        <img
                          src={resolveStaffMediaUrl(row.clock_in_selfie_url || row.selfie_url)}
                          alt="In selfie"
                          className="w-12 h-12 rounded object-cover border border-gray-200 cursor-pointer hover:opacity-80"
                          style={{ width: '48px', height: '48px', objectFit: 'cover', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: 'pointer' }}
                          onClick={() => {
                            setSelectedLog(row)
                            setExpandedImage(resolveStaffMediaUrl(row.clock_in_selfie_url || row.selfie_url || ''))
                          }}
                        />
                      ) : '-'}
                    </td>
                    <td className="px-3 py-2">
                      {(row.clock_out_selfie_url || row.selfie_url) ? (
                        <img
                          src={resolveStaffMediaUrl(row.clock_out_selfie_url || row.selfie_url)}
                          alt="Out selfie"
                          className="w-12 h-12 rounded object-cover border border-gray-200 cursor-pointer hover:opacity-80"
                          style={{ width: '48px', height: '48px', objectFit: 'cover', border: '1px solid #e5e7eb', borderRadius: '6px', cursor: 'pointer' }}
                          onClick={() => {
                            setSelectedLog(row)
                            setExpandedImage(resolveStaffMediaUrl(row.clock_out_selfie_url || row.selfie_url || ''))
                          }}
                        />
                      ) : '-'}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        {(row.attachments || []).length === 0 ? (
                          <span className="text-xs text-slate-400">-</span>
                        ) : (row.attachments || []).map((fileUrl, index) => (
                          <div key={`${row.id}-attachment-${index}`} className="inline-flex items-center gap-1">
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
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {mapLink ? <a className="text-sky-600 underline" href={mapLink} target="_blank" rel="noreferrer">{lat}, {lng}</a> : '-'}
                    </td>
                    <td className="px-3 py-2">{row.leave_status || '-'}</td>
                    <td className="px-3 py-2">
                      <input
                        className="w-52 rounded border px-2 py-1 text-xs"
                        value={hrRemarkDraft[row.id] ?? row.hr_remark ?? ''}
                        onChange={(e) => setHrRemarkDraft((prev) => ({ ...prev, [row.id]: e.target.value }))}
                        placeholder="Add HR remark"
                        disabled={row.id < 0}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <label className="inline-flex items-center gap-2 text-xs">
                        <input
                          type="checkbox"
                          checked={disputeResolvedDraft[row.id] ?? !!row.dispute_resolved}
                          onChange={(e) => setDisputeResolvedDraft((prev) => ({ ...prev, [row.id]: e.target.checked }))}
                          disabled={row.id < 0}
                        />
                        Resolved
                      </label>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button className="rounded bg-indigo-600 px-2 py-1 text-xs font-semibold text-white" onClick={() => void assignTask(row.id)}>
                          Add Task
                        </button>
                        <button className="rounded bg-slate-800 px-2 py-1 text-xs font-semibold text-white" onClick={() => void saveDirectorReview(row.id)}>
                          Save Review
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)', padding: '16px' }} onClick={() => { setSelectedLog(null); setExpandedImage('') }}>
          <div className="w-full max-w-3xl rounded-2xl bg-white p-5 shadow-2xl" style={{ width: '100%', maxWidth: '960px', background: '#ffffff', borderRadius: '16px', padding: '20px' }} onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-lg font-bold text-slate-900">Attendance Detail - {new Date(selectedLog.date).toLocaleDateString()}</h4>
              </div>
              <button className="rounded border px-3 py-1.5 text-sm" onClick={() => { setSelectedLog(null); setExpandedImage('') }}>Close</button>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <img
                src={expandedImage || resolveStaffMediaUrl(selectedMeta?.inSelfieUrl || selectedMeta?.outSelfieUrl || '')}
                alt="preview"
                className="w-full rounded-xl border object-cover"
                style={{ width: '100%', maxHeight: '70vh', objectFit: 'contain', border: '1px solid #e5e7eb', borderRadius: '12px' }}
              />
              <div className="space-y-3 text-sm text-slate-700">
                <p><span className="font-semibold">Clock In:</span> {selectedMeta?.clockIn || '-'}</p>
                <p><span className="font-semibold">Clock Out:</span> {selectedMeta?.clockOut || '-'}</p>
                <p><span className="font-semibold">Task:</span> {selectedLog.task || '-'}</p>

                <div className="flex gap-2 pt-2">
                  {selectedMeta?.inSelfieUrl && (
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
                      onClick={() => setExpandedImage(resolveStaffMediaUrl(selectedMeta.inSelfieUrl || ''))}
                    >
                      View In Selfie
                    </button>
                  )}
                  {selectedMeta?.outSelfieUrl && (
                    <button
                      type="button"
                      className="rounded border border-slate-300 px-3 py-1.5 text-xs font-semibold hover:bg-slate-50"
                      onClick={() => setExpandedImage(resolveStaffMediaUrl(selectedMeta.outSelfieUrl || ''))}
                    >
                      View Out Selfie
                    </button>
                  )}
                </div>
              </div>
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
    </div>
  )
}
