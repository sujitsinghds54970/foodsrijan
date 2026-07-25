export interface StaffSummary {
  staff_profile_id: number
  user_id?: number
  staff_id: string
  username: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  mobile: string
  department?: string | null
  designation?: string | null
  status: string
  can_access_daily_ops?: boolean
  photo_url?: string | null
}

export interface StaffSalary {
  basic: number
  hra: number
  allowances: number
  deductions: number
  net_pay: number
  bank_name?: string | null
  account_number?: string | null
  ifsc_code?: string | null
  upi_id?: string | null
}

export interface StaffDetail extends StaffSummary {
  user_id: number
  branch_id: number
  specialization?: string | null
  shift_timings?: string | null
  date_of_joining?: string | null
  address?: string | null
  emergency_contact?: string | null
  photo_path?: string | null
  created_at?: string
  updated_at?: string
  salary: StaffSalary
}

export interface AttendanceEntry {
  id: number
  attendance_date: string
  attendance_type: 'present' | 'absent' | 'leave' | 'holiday'
  clock_in_time?: string | null
  clock_out_time?: string | null
}

export interface LeaveEntry {
  id: number
  leave_type: string
  start_date: string
  end_date: string
  total_days: number
  reason?: string | null
  status: 'pending' | 'approved' | 'rejected' | 'cancelled'
  review_comment?: string | null
  created_at?: string
}

export interface StaffCreatePayload {
  first_name: string
  last_name: string
  email: string
  mobile: string
  department?: string
  designation?: string
  specialization?: string
  shift_timings?: string
  date_of_joining?: string
  address?: string
  emergency_contact?: string
  can_access_daily_ops?: boolean
  temporary_password?: string
}

export interface StaffUpdatePayload {
  first_name?: string
  last_name?: string
  email?: string
  mobile?: string
  department?: string
  designation?: string
  specialization?: string
  shift_timings?: string
  date_of_joining?: string
  address?: string
  emergency_contact?: string
  can_access_daily_ops?: boolean
  status?: string
}

export interface StaffCredentialsPayload {
  username?: string
  password?: string
}

export interface StaffSelfProfile {
  id: number
  staff_profile_id: number
  full_name: string
  photo_url?: string | null
  mobile?: string | null
  email?: string | null
  address?: string | null
  role: string
  department?: string | null
  bank_name?: string | null
  bank_account_number?: string | null
  ifsc_code?: string | null
  upi_id?: string | null
  branch_id?: number | null
  can_access_daily_ops?: boolean
  branch_name?: string | null
  branch_logo_url?: string | null
}

export interface StaffSelfAttendanceRow {
  id: number
  attendance_date: string
  clock_in_time?: string | null
  clock_out_time?: string | null
  status: 'Present' | 'Absent' | 'Leave' | 'Holiday' | string
}

export interface LeaveBalance {
  casual_total: number
  sick_total: number
  earned_total?: number
  casual_remaining: number
  sick_remaining: number
  earned_remaining?: number
}

export interface AttendanceLogItem {
  id: number
  date: string
  attendance_date: string
  clock_in_time?: string | null
  clock_out_time?: string | null
  location_lat?: number | null
  location_lng?: number | null
  selfie_url?: string | null
  clock_in_selfie_url?: string | null
  clock_out_selfie_url?: string | null
  status: 'Present' | 'Late' | 'Absent' | 'ApprovedLeave' | 'WorkFromHome' | string
  work_mode?: 'onsite' | 'work_from_home' | string
  wfh_reason?: string | null
  task?: string | null
  task_status?: 'Pending' | 'In Progress' | 'Completed' | string
  staff_note?: string | null
  attachments?: string[]
  hr_remark?: string | null
  dispute_resolved?: boolean
  leave_status?: string | null
  is_remote?: boolean
  distance_from_branch_meters?: number | null
  late_minutes?: number
  absence_reason?: string | null
}

export interface LeaveRequestItem {
  id: number
  leave_type: string
  start_date: string
  end_date: string
  start_time?: string | null
  end_time?: string | null
  duration_days: number
  duration_hours: number
  reason?: string | null
  attachments?: string | null
  status: 'Pending' | 'Approved' | 'Rejected' | 'Cancelled' | string
  approved_by?: number | null
  approval_date?: string | null
  created_at?: string | null
}

export interface LinkedDeviceItem {
  id: number
  device_id: string
  device_type: 'Biometric' | 'Rfid' | 'Mobile' | string
  is_active: boolean
  last_sync?: string | null
}

export interface AttendanceDisputeItem {
  id: number
  attendance_date: string
  reason: string
  status: 'Open' | 'Resolved' | string
  resolution_notes?: string | null
  created_at?: string | null
}

export interface StaffNotification {
  id: number
  title: string
  message: string
  status: string
  link?: string | null
  is_read?: boolean
  created_at?: string
}

export interface StaffSalaryHistoryRow {
  id: number
  month: number
  year: number
  basic: number
  hra: number
  allowances: number
  deductions: number
  net_pay: number
  generated_at?: string | null
}

export interface StaffSalarySummary {
  basic: number
  hra: number
  allowances: number
  deductions: number
  net_pay: number
  bank_name?: string | null
  account_number?: string | null
  ifsc_code?: string | null
  upi_id?: string | null
}

export interface StaffSalaryResponse {
  current: StaffSalarySummary
  history: StaffSalaryHistoryRow[]
}

export interface StaffTask {
  id: number
  task_name: string
  description?: string | null
  deadline?: string | null
  status: 'Pending' | 'In Progress' | 'Completed' | string
  priority: 'Low' | 'Medium' | 'High' | string
  created_at?: string
  updated_at?: string
}

export interface StaffPerformance {
  month: string
  attendance_percentage: number
  attendance_days: number
  present_days: number
  tasks_completed: number
  tasks_total: number
  revenue_generated: number
}

export interface TaskItem {
  id: number
  branch_id: number
  assigned_by?: number | null
  assigned_to?: number | null
  title: string
  task_name?: string
  description?: string | null
  due_date?: string | null
  deadline?: string | null
  priority: 'Low' | 'Medium' | 'High' | 'Urgent' | string
  status: 'Pending' | 'In Progress' | 'Completed' | 'Overdue' | 'Cancelled' | string
  created_at?: string
  updated_at?: string
  completed_at?: string | null
}

export interface TaskCommentItem {
  id: number
  task_id: number
  user_id: number
  message: string
  created_at?: string
}

export interface TaskAttachmentItem {
  id: number
  task_id: number
  file_url: string
  uploaded_by: number
  created_at?: string
}
