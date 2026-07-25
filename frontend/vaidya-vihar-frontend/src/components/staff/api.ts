import axios from 'axios'
import {
  AttendanceDisputeItem,
  AttendanceEntry,
  AttendanceLogItem,
  LeaveBalance,
  LeaveEntry,
  LeaveRequestItem,
  LinkedDeviceItem,
  StaffNotification,
  StaffCreatePayload,
  StaffCredentialsPayload,
  StaffDetail,
  StaffSelfAttendanceRow,
  StaffSelfProfile,
  StaffSalaryResponse,
  StaffSalary,
  StaffSummary,
  StaffTask,
  TaskAttachmentItem,
  TaskCommentItem,
  TaskItem,
  StaffPerformance,
  StaffUpdatePayload,
} from './types'

const API_BASE =
  (process as any).env.REACT_APP_API_BASE_URL ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

const STAFF_BASE = `${API_BASE}/api/staff`
const TASK_BASE = `${API_BASE}/api/tasks`

function getMediaAccessToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  const token = window.localStorage.getItem('patient_portal_token') || window.localStorage.getItem('token')
  const normalized = (token || '').trim()
  return normalized || null
}

function withMediaToken(url: string): string {
  const token = getMediaAccessToken()
  if (!token || typeof window === 'undefined') {
    return url
  }

  try {
    const resolved = new URL(url, window.location.origin)
    const apiFilesBase = new URL(`${API_BASE}/api/files/`, window.location.origin)

    if (resolved.origin !== apiFilesBase.origin || !resolved.pathname.startsWith(apiFilesBase.pathname)) {
      return resolved.toString()
    }

    if (!resolved.searchParams.has('access_token')) {
      resolved.searchParams.set('access_token', token)
    }

    return resolved.toString()
  } catch {
    return url
  }
}

export function resolveStaffMediaUrl(path?: string | null): string {
  if (!path) return ''
  const raw = path.trim()
  if (!raw) return ''

  if (raw.startsWith('data:') || raw.startsWith('blob:')) {
    return raw
  }

  if (/^https?:\/\//i.test(raw)) {
    return withMediaToken(raw)
  }

  if (raw.startsWith('/api/files/')) {
    return withMediaToken(`${API_BASE}${raw}`)
  }

  if (raw.startsWith('/')) {
    return withMediaToken(`${API_BASE}${raw}`)
  }

  return withMediaToken(`${API_BASE}/api/files/${raw}`)
}

export function getApiErrorMessage(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = detail.map((entry: any) => {
      if (typeof entry === 'string') return entry
      if (entry && typeof entry === 'object') {
        const loc = Array.isArray(entry.loc) ? `${entry.loc.join('.')}: ` : ''
        const msg = typeof entry.msg === 'string' ? entry.msg : JSON.stringify(entry)
        return `${loc}${msg}`
      }
      return String(entry)
    })
    return messages.join(', ')
  }

  if (detail && typeof detail === 'object') {
    try {
      return JSON.stringify(detail)
    } catch {
      return fallback
    }
  }

  return fallback
}

export const staffApi = {
  async list(search?: string): Promise<StaffSummary[]> {
    const response = await axios.get(`${STAFF_BASE}`, {
      params: search ? { search } : undefined,
    })
    return response.data?.items || []
  },

  async create(payload: StaffCreatePayload): Promise<{ staff: StaffDetail; temporary_password?: string }> {
    const response = await axios.post(`${STAFF_BASE}`, payload)
    return response.data
  },

  async get(staffProfileId: number): Promise<StaffDetail> {
    const response = await axios.get(`${STAFF_BASE}/${staffProfileId}`)
    return response.data
  },

  async update(staffProfileId: number, payload: StaffUpdatePayload): Promise<StaffDetail> {
    const response = await axios.put(`${STAFF_BASE}/${staffProfileId}`, payload)
    return response.data?.staff
  },

  async bulkToggleDailyOps(staffProfileIds: number[], canAccessDailyOps: boolean): Promise<number> {
    const response = await axios.post(`${STAFF_BASE}/bulk-toggle-daily-ops`, {
      staff_profile_ids: staffProfileIds,
      can_access_daily_ops: canAccessDailyOps,
    })
    return Number(response.data?.updated_count || 0)
  },

  async updateCredentials(staffProfileId: number, payload: StaffCredentialsPayload): Promise<string> {
    const response = await axios.put(`${STAFF_BASE}/${staffProfileId}/credentials`, payload)
    return response.data?.username
  },

  async uploadPhoto(staffProfileId: number, file: File): Promise<string> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post(`${STAFF_BASE}/${staffProfileId}/photo`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data?.photo_url
  },

  async updateSalary(staffProfileId: number, payload: StaffSalary): Promise<StaffSalary> {
    const response = await axios.post(`${STAFF_BASE}/${staffProfileId}/salary`, payload)
    return response.data?.salary
  },

  async listAttendance(staffProfileId: number, month: number, year: number): Promise<AttendanceEntry[]> {
    const response = await axios.get(`${STAFF_BASE}/${staffProfileId}/attendance`, {
      params: { month, year },
    })
    return response.data?.items || []
  },

  async markAttendance(staffProfileId: number, payload: {
    attendance_date: string
    attendance_type: 'present' | 'absent' | 'leave' | 'holiday'
    clock_in_time?: string
    clock_out_time?: string
  }): Promise<void> {
    await axios.post(`${STAFF_BASE}/${staffProfileId}/attendance`, payload)
  },

  async listLeave(staffProfileId: number): Promise<LeaveEntry[]> {
    const response = await axios.get(`${STAFF_BASE}/${staffProfileId}/leave`)
    return response.data?.items || []
  },

  async applyLeave(staffProfileId: number, payload: {
    leave_type: string
    start_date: string
    end_date: string
    reason?: string
  }): Promise<void> {
    await axios.post(`${STAFF_BASE}/${staffProfileId}/leave`, payload)
  },

  async decideLeave(leaveRequestId: number, payload: { status: 'approved' | 'rejected' | 'cancelled'; review_comment?: string }): Promise<void> {
    await axios.put(`${API_BASE}/api/leave/${leaveRequestId}/approve`, payload)
  },
}

export const staffSelfApi = {
  async getMe(): Promise<StaffSelfProfile> {
    const response = await axios.get(`${STAFF_BASE}/me`)
    return response.data
  },

  async updateMe(payload: Partial<StaffSelfProfile>): Promise<StaffSelfProfile> {
    const response = await axios.put(`${STAFF_BASE}/me`, payload)
    return response.data?.profile
  },

  async uploadMyPhoto(file: File): Promise<StaffSelfProfile> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post(`${STAFF_BASE}/me/photo`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data?.profile
  },

  async getMyAttendance(month: string): Promise<StaffSelfAttendanceRow[]> {
    const response = await axios.get(`${STAFF_BASE}/me/attendance`, { params: { month } })
    return response.data?.items || []
  },

  async clockMyAttendance(payload: { action: 'in' | 'out'; latitude?: string; longitude?: string }): Promise<void> {
    await axios.post(`${STAFF_BASE}/me/attendance/clock`, payload)
  },

  async getMySalary(): Promise<StaffSalaryResponse> {
    const response = await axios.get(`${STAFF_BASE}/me/salary`)
    return response.data
  },

  async getMyTasks(status?: string): Promise<StaffTask[]> {
    const response = await axios.get(`${TASK_BASE}`, { params: status ? { status } : undefined })
    return (response.data?.items || []).map((row: any) => ({
      id: row.id,
      task_name: row.title || row.task_name,
      description: row.description,
      deadline: row.due_date || row.deadline,
      status: row.status,
      priority: row.priority,
      created_at: row.created_at,
      updated_at: row.updated_at,
    }))
  },

  async updateMyTaskStatus(taskId: number, status: string): Promise<void> {
    await axios.put(`${TASK_BASE}/${taskId}/status`, { status })
  },

  async getLeaveBalance(): Promise<LeaveBalance> {
    const response = await axios.get(`${STAFF_BASE}/me/leave-balance`)
    return response.data
  },

  async applyLeave(payload: { leave_type: string; start_date: string; end_date: string; reason?: string }): Promise<void> {
    await axios.post(`${STAFF_BASE}/me/leave`, payload)
  },

  async getNotifications(): Promise<StaffNotification[]> {
    const response = await axios.get(`${STAFF_BASE}/me/notifications`)
    return response.data?.items || []
  },

  async markNotificationRead(notificationId: number): Promise<void> {
    await axios.post(`${STAFF_BASE}/me/notifications/${notificationId}/read`)
  },

  async getMyPerformance(month?: string): Promise<StaffPerformance> {
    const response = await axios.get(`${STAFF_BASE}/me/performance`, { params: month ? { month } : undefined })
    return response.data
  },

  async getAttendance(month: string): Promise<AttendanceLogItem[]> {
    const response = await axios.get(`${STAFF_BASE}/attendance`, { params: { month } })
    return response.data?.items || []
  },

  async clockAttendance(formData: FormData): Promise<AttendanceLogItem> {
    const response = await axios.post(`${STAFF_BASE}/attendance/clock`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data?.attendance
  },

  async updateAttendance(attendanceId: number, payload: { task?: string; task_status?: string; staff_note?: string }): Promise<AttendanceLogItem> {
    const response = await axios.put(`${STAFF_BASE}/attendance/${attendanceId}`, payload)
    return response.data?.attendance
  },

  async uploadAttendanceAttachments(attendanceId: number, files: File[]): Promise<AttendanceLogItem> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    const response = await axios.post(`${STAFF_BASE}/attendance/${attendanceId}/attachments`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data?.attendance
  },

  async deleteAttendanceAttachment(attendanceId: number, fileUrl: string): Promise<AttendanceLogItem> {
    const response = await axios.delete(`${STAFF_BASE}/attendance/${attendanceId}/attachments`, {
      params: { file_url: fileUrl },
    })
    return response.data?.attendance
  },

  async listLeaves(): Promise<LeaveRequestItem[]> {
    const response = await axios.get(`${STAFF_BASE}/leaves`)
    return response.data?.items || []
  },

  async createLeave(formData: FormData): Promise<void> {
    await axios.post(`${STAFF_BASE}/leaves`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  async cancelLeave(leaveId: number): Promise<void> {
    await axios.put(`${STAFF_BASE}/leaves/${leaveId}`, { status: 'cancel' })
  },

  async getUpcomingLeaves(): Promise<{ items: LeaveRequestItem[]; next_leave: LeaveRequestItem | null }> {
    const response = await axios.get(`${STAFF_BASE}/leaves/upcoming`)
    return {
      items: response.data?.items || [],
      next_leave: response.data?.next_leave || null,
    }
  },

  async getLinkedDevices(): Promise<LinkedDeviceItem[]> {
    const response = await axios.get(`${STAFF_BASE}/linked-devices`)
    return response.data?.items || []
  },

  async resetLinkedDeviceToken(): Promise<void> {
    await axios.post(`${STAFF_BASE}/linked-devices/reset-token`)
  },

  async createDispute(payload: { attendance_date: string; reason: string }): Promise<void> {
    await axios.post(`${STAFF_BASE}/disputes`, payload)
  },

  async listDisputes(): Promise<AttendanceDisputeItem[]> {
    const response = await axios.get(`${STAFF_BASE}/disputes`)
    return response.data?.items || []
  },
}

export const taskApi = {
  async list(params?: { status?: string; due_date?: string }): Promise<TaskItem[]> {
    const response = await axios.get(`${TASK_BASE}`, { params })
    return response.data?.items || []
  },

  async create(payload: {
    assigned_to: number
    title: string
    description?: string
    due_date?: string
    priority: string
  }): Promise<TaskItem> {
    const response = await axios.post(`${TASK_BASE}`, payload)
    return response.data?.task
  },

  async update(taskId: number, payload: {
    assigned_to?: number
    title?: string
    description?: string
    due_date?: string
    priority?: string
  }): Promise<TaskItem> {
    const response = await axios.put(`${TASK_BASE}/${taskId}`, payload)
    return response.data?.task
  },

  async remove(taskId: number): Promise<void> {
    await axios.delete(`${TASK_BASE}/${taskId}`)
  },

  async updateStatus(taskId: number, status: 'In Progress' | 'Completed' | 'Pending' | 'Overdue' | 'Cancelled'): Promise<TaskItem> {
    const response = await axios.put(`${TASK_BASE}/${taskId}/status`, { status })
    return response.data?.task
  },

  async listComments(taskId: number): Promise<TaskCommentItem[]> {
    const response = await axios.get(`${TASK_BASE}/${taskId}/comments`)
    return response.data?.items || []
  },

  async addComment(taskId: number, message: string): Promise<TaskCommentItem> {
    const response = await axios.post(`${TASK_BASE}/${taskId}/comments`, { message })
    return response.data?.comment
  },

  async listAttachments(taskId: number): Promise<TaskAttachmentItem[]> {
    const response = await axios.get(`${TASK_BASE}/${taskId}/attachments`)
    return response.data?.items || []
  },

  async uploadAttachment(taskId: number, file: File): Promise<TaskAttachmentItem> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post(`${TASK_BASE}/${taskId}/attachments`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data?.attachment
  },
}

export const directorAttendanceApi = {
  async getStaffAttendance(staffProfileId: number, month: string): Promise<AttendanceLogItem[]> {
    const response = await axios.get(`${STAFF_BASE}/${staffProfileId}/attendance`, {
      params: { month },
    })
    return response.data?.items || []
  },

  async assignTask(staffProfileId: number, attendanceId: number, payload: { task: string; task_status?: string }): Promise<AttendanceLogItem> {
    const response = await axios.put(`${STAFF_BASE}/${staffProfileId}/attendance/${attendanceId}/task`, payload)
    return response.data?.attendance
  },

  async updateAttendanceReview(
    staffProfileId: number,
    attendanceId: number,
    payload: { hr_remark?: string; dispute_resolved?: boolean; staff_note?: string },
  ): Promise<AttendanceLogItem> {
    const response = await axios.put(`${STAFF_BASE}/${staffProfileId}/attendance/${attendanceId}/review`, payload)
    return response.data?.attendance
  },
}
