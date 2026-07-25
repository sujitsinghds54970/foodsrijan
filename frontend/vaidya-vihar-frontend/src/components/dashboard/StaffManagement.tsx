import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'

interface StaffMember {
  id: number
  employee_id: string
  branch_id: number
  user_id: number
  department: string
  position: string
  date_of_joining: string
  salary: number
  date_of_birth: string
  qualification?: string | null
  experience_years: number
  total_leaves: number
  leaves_taken: number
  performance_rating: number
  is_active: boolean
  created_at: string
  first_name: string
  last_name: string
  username: string
  email: string
  phone: string
  role: string
  branch_name: string
  branch_location: string
}

interface AttendanceRecord {
  id: number
  staff_id: number
  attendance_date: string
  check_in_time?: string | null
  check_out_time?: string | null
  status: string
  late_minutes: number
  overtime_minutes: number
  notes?: string | null
  approved_by?: number | null
  created_at: string
  employee_id: string
  staff_name: string
  department: string
}

interface SalaryRecord {
  id: number
  staff_id: number
  month: number
  year: number
  base_salary: number
  bonus: number
  deductions: number
  gross_salary: number
  net_salary: number
  payment_date?: string | null
  payment_status: string
  payment_mode?: string | null
  created_at: string
  employee_id: string
  staff_name: string
  department: string
}

type StaffView = 'directory' | 'attendance' | 'payroll'

export default function StaffManagement() {
  const { user, token } = useAuth()
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([])
  const [salaryRecords, setSalaryRecords] = useState<SalaryRecord[]>([])
  const [departments, setDepartments] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [attendanceLoading, setAttendanceLoading] = useState(false)
  const [salaryLoading, setSalaryLoading] = useState(false)
  const [activeView, setActiveView] = useState<StaffView>('directory')
  const [searchTerm, setSearchTerm] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('all')
  const [selectedStaffId, setSelectedStaffId] = useState<number | 'all'>('all')
  const [deleteConfirmModal, setDeleteConfirmModal] = useState<{ isOpen: boolean; staffId?: number; staffName?: string }>({ isOpen: false })
  const [isDeleting, setIsDeleting] = useState(false)
  const today = new Date()
  const [payrollMonth, setPayrollMonth] = useState(today.getMonth() + 1)
  const [payrollYear, setPayrollYear] = useState(today.getFullYear())

  const API_BASE = (process as any).env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const requestConfig = useMemo(() => ({
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }), [token])

  const getErrorMessage = useCallback((err: unknown, fallback: string) => {
    const errorObj = err as any
    return errorObj?.response?.data?.detail || errorObj?.message || fallback
  }, [])

  const fetchStaff = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('limit', '200')
      if (searchTerm.trim()) params.set('search', searchTerm.trim())
      if (departmentFilter !== 'all') params.set('department', departmentFilter)

      const response = await axios.get(`${API_BASE}/api/staff?${params.toString()}`, requestConfig)
      const rows = Array.isArray(response.data) ? response.data : (response.data?.items || [])
      setStaff(rows)
      if (selectedStaffId !== 'all' && !rows.some((item: StaffMember) => item.id === selectedStaffId)) {
        setSelectedStaffId('all')
      }
    } catch (err) {
      console.error('Failed to load staff directory', err)
      toast.error(getErrorMessage(err, 'Failed to load staff directory'))
    } finally {
      setLoading(false)
    }
  }, [API_BASE, requestConfig, token, searchTerm, departmentFilter, selectedStaffId, getErrorMessage])

  const fetchDepartments = useCallback(async () => {
    if (!token) return
    try {
      const response = await axios.get(`${API_BASE}/api/staff/departments`, requestConfig)
      const rows = Array.isArray(response.data) ? response.data : []
      setDepartments(rows.map((item: { department: string }) => item.department).filter(Boolean))
    } catch {
      setDepartments([])
    }
  }, [API_BASE, requestConfig, token])

  const fetchAttendance = useCallback(async () => {
    if (!token) return
    setAttendanceLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('limit', '100')
      if (selectedStaffId !== 'all') params.set('staff_id', String(selectedStaffId))
      const response = await axios.get(`${API_BASE}/api/staff/attendance/?${params.toString()}`, requestConfig)
      setAttendance(Array.isArray(response.data) ? response.data : [])
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load attendance records'))
    } finally {
      setAttendanceLoading(false)
    }
  }, [API_BASE, requestConfig, token, selectedStaffId, getErrorMessage])

  const fetchSalaryRecords = useCallback(async () => {
    if (!token) return
    setSalaryLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('limit', '100')
      params.set('month', String(payrollMonth))
      params.set('year', String(payrollYear))
      if (selectedStaffId !== 'all') params.set('staff_id', String(selectedStaffId))
      const response = await axios.get(`${API_BASE}/api/staff/salary/?${params.toString()}`, requestConfig)
      setSalaryRecords(Array.isArray(response.data) ? response.data : [])
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to load payroll records'))
    } finally {
      setSalaryLoading(false)
    }
  }, [API_BASE, requestConfig, token, payrollMonth, payrollYear, selectedStaffId, getErrorMessage])

  const handleDeleteStaff = useCallback(async (staffId: number) => {
    if (!token) return
    setIsDeleting(true)
    try {
      await axios.delete(`${API_BASE}/api/director/staff/${staffId}`, requestConfig)
      toast.success('Staff member deactivated successfully')
      // Refresh the staff list
      await fetchStaff()
      setDeleteConfirmModal({ isOpen: false })
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to deactivate staff member'))
    } finally {
      setIsDeleting(false)
    }
  }, [API_BASE, requestConfig, token, getErrorMessage, fetchStaff])

  useEffect(() => {
    void fetchStaff()
  }, [fetchStaff])

  useEffect(() => {
    void fetchDepartments()
  }, [fetchDepartments])

  useEffect(() => {
    if (activeView === 'attendance') {
      void fetchAttendance()
    }
  }, [activeView, fetchAttendance])

  useEffect(() => {
    if (activeView === 'payroll') {
      void fetchSalaryRecords()
    }
  }, [activeView, fetchSalaryRecords])

  const markSalaryPaid = async (salaryId: number) => {
    try {
      await axios.put(`${API_BASE}/api/staff/salary/${salaryId}/mark-paid`, {}, requestConfig)
      toast.success('Salary marked as paid')
      void fetchSalaryRecords()
    } catch (err) {
      toast.error(getErrorMessage(err, 'Failed to update salary status'))
    }
  }

  const totalMonthlyCost = useMemo(
    () => staff.reduce((sum, employee) => sum + Number(employee.salary || 0), 0),
    [staff]
  )

  const activeStaffCount = useMemo(
    () => staff.filter(employee => employee.is_active).length,
    [staff]
  )

  const selectedStaffName = useMemo(() => {
    if (selectedStaffId === 'all') return 'All Staff'
    const member = staff.find(item => item.id === selectedStaffId)
    return member ? `${member.first_name} ${member.last_name}` : 'Selected Staff'
  }, [selectedStaffId, staff])

  if (!user) return null

  return (
    <div className="space-y-6">
      <div className="premium-card p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-black gradient-text">Staff Operations</h1>
            <p className="text-slate-600 mt-2">Live staff directory, attendance tracking, and payroll visibility</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setActiveView('directory')}
              className={`px-5 py-2 rounded-xl font-bold transition ${activeView === 'directory' ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Directory
            </button>
            <button
              onClick={() => setActiveView('attendance')}
              className={`px-5 py-2 rounded-xl font-bold transition ${activeView === 'attendance' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Attendance
            </button>
            <button
              onClick={() => setActiveView('payroll')}
              className={`px-5 py-2 rounded-xl font-bold transition ${activeView === 'payroll' ? 'bg-violet-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Payroll
            </button>
            <button
              onClick={() => {
                void fetchStaff()
                if (activeView === 'attendance') void fetchAttendance()
                if (activeView === 'payroll') void fetchSalaryRecords()
              }}
              className="px-5 py-2 rounded-xl bg-slate-900 text-white font-bold hover:bg-slate-700 transition"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="premium-card p-6 bg-gradient-to-br from-blue-50 to-cyan-50">
          <p className="text-xs uppercase tracking-wider text-blue-600 font-bold mb-2">Total Staff</p>
          <p className="text-3xl font-black text-slate-900">{staff.length}</p>
        </div>
        <div className="premium-card p-6 bg-gradient-to-br from-emerald-50 to-teal-50">
          <p className="text-xs uppercase tracking-wider text-emerald-600 font-bold mb-2">Active Staff</p>
          <p className="text-3xl font-black text-slate-900">{activeStaffCount}</p>
        </div>
        <div className="premium-card p-6 bg-gradient-to-br from-violet-50 to-fuchsia-50">
          <p className="text-xs uppercase tracking-wider text-violet-600 font-bold mb-2">Departments</p>
          <p className="text-3xl font-black text-slate-900">{departments.length}</p>
        </div>
        <div className="premium-card p-6 bg-gradient-to-br from-amber-50 to-orange-50">
          <p className="text-xs uppercase tracking-wider text-amber-700 font-bold mb-2">Monthly Salary Cost</p>
          <p className="text-3xl font-black text-slate-900">INR {totalMonthlyCost.toLocaleString()}</p>
        </div>
      </div>

      <div className="premium-card p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Search by name, username, employee ID"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          />
          <select
            value={departmentFilter}
            onChange={e => setDepartmentFilter(e.target.value)}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Departments</option>
            {departments.map(department => (
              <option key={department} value={department}>{department}</option>
            ))}
          </select>
          <select
            value={selectedStaffId}
            onChange={e => setSelectedStaffId(e.target.value === 'all' ? 'all' : Number(e.target.value))}
            className="px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Staff</option>
            {staff.map(member => (
              <option key={member.id} value={member.id}>{member.employee_id} - {member.first_name} {member.last_name}</option>
            ))}
          </select>
          <button
            onClick={() => {
              void fetchStaff()
              if (activeView === 'attendance') void fetchAttendance()
              if (activeView === 'payroll') void fetchSalaryRecords()
            }}
            className="px-4 py-3 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 transition"
          >
            Apply Filters
          </button>
        </div>
      </div>

      {activeView === 'directory' && (
        <div className="premium-card overflow-hidden">
          <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900">Staff Directory</h2>
              <p className="text-sm text-slate-500 mt-1">Operational roster for branch staff and admins</p>
            </div>
            <span className="text-sm font-bold text-slate-500">{staff.length} records</span>
          </div>

          {loading ? (
            <div className="p-10 text-center text-slate-500">Loading staff directory...</div>
          ) : staff.length === 0 ? (
            <div className="p-10 text-center text-slate-500">No staff records found for the current filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Employee ID</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Role</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Department</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Position</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Salary</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {staff.map(member => (
                    <tr key={member.id} className="border-t border-slate-200 hover:bg-slate-50">
                      <td className="px-4 py-4 text-sm font-bold text-slate-900">{member.employee_id}</td>
                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900">{member.first_name} {member.last_name}</div>
                        <div className="text-xs text-slate-500">{member.email}</div>
                        <div className="text-xs text-slate-500">{member.phone}</div>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">{member.role}</td>
                      <td className="px-4 py-4 text-sm text-slate-700">{member.department}</td>
                      <td className="px-4 py-4 text-sm text-slate-700">{member.position}</td>
                      <td className="px-4 py-4 text-sm font-semibold text-slate-900">INR {Number(member.salary || 0).toLocaleString()}</td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${member.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                          {member.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm">
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => {
                              setSelectedStaffId(member.id)
                              setActiveView('attendance')
                            }}
                            className="px-3 py-1 rounded-lg bg-emerald-50 text-emerald-700 font-semibold hover:bg-emerald-100"
                          >
                            Attendance
                          </button>
                          <button
                            onClick={() => {
                              setSelectedStaffId(member.id)
                              setActiveView('payroll')
                            }}
                            className="px-3 py-1 rounded-lg bg-violet-50 text-violet-700 font-semibold hover:bg-violet-100"
                          >
                            Payroll
                          </button>
                          <button
                            onClick={() => setDeleteConfirmModal({ isOpen: true, staffId: member.id, staffName: `${member.first_name} ${member.last_name}` })}
                            className="px-3 py-1 rounded-lg bg-rose-50 text-rose-700 font-semibold hover:bg-rose-100"
                            title="Delete staff member"
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeView === 'attendance' && (
        <div className="premium-card overflow-hidden">
          <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900">Attendance Tracker</h2>
              <p className="text-sm text-slate-500 mt-1">Showing records for {selectedStaffName}</p>
            </div>
            <button
              onClick={() => void fetchAttendance()}
              className="px-4 py-2 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-700"
            >
              Refresh Attendance
            </button>
          </div>

          {attendanceLoading ? (
            <div className="p-10 text-center text-slate-500">Loading attendance records...</div>
          ) : attendance.length === 0 ? (
            <div className="p-10 text-center text-slate-500">No attendance records found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Employee</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Check In</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Check Out</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Late</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Overtime</th>
                  </tr>
                </thead>
                <tbody>
                  {attendance.map(record => (
                    <tr key={record.id} className="border-t border-slate-200 hover:bg-slate-50">
                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900">{record.staff_name}</div>
                        <div className="text-xs text-slate-500">{record.employee_id} • {record.department}</div>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">{new Date(record.attendance_date).toLocaleDateString()}</td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${record.status === 'present' ? 'bg-emerald-100 text-emerald-700' : record.status === 'late' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'}`}>
                          {record.status}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">{record.check_in_time ? new Date(record.check_in_time).toLocaleTimeString() : '-'}</td>
                      <td className="px-4 py-4 text-sm text-slate-700">{record.check_out_time ? new Date(record.check_out_time).toLocaleTimeString() : '-'}</td>
                      <td className="px-4 py-4 text-sm text-slate-700">{record.late_minutes} min</td>
                      <td className="px-4 py-4 text-sm text-slate-700">{record.overtime_minutes} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeView === 'payroll' && (
        <div className="premium-card overflow-hidden">
          <div className="px-6 py-5 border-b border-slate-200 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900">Payroll Monitor</h2>
              <p className="text-sm text-slate-500 mt-1">Showing records for {selectedStaffName}</p>
            </div>
            <div className="flex gap-3">
              <select
                value={payrollMonth}
                onChange={e => setPayrollMonth(Number(e.target.value))}
                className="px-4 py-2 rounded-xl border-2 border-slate-200 focus:border-violet-500 focus:outline-none"
              >
                {Array.from({ length: 12 }, (_, index) => index + 1).map(month => (
                  <option key={month} value={month}>{month.toString().padStart(2, '0')}</option>
                ))}
              </select>
              <select
                value={payrollYear}
                onChange={e => setPayrollYear(Number(e.target.value))}
                className="px-4 py-2 rounded-xl border-2 border-slate-200 focus:border-violet-500 focus:outline-none"
              >
                {Array.from({ length: 5 }, (_, index) => today.getFullYear() - 2 + index).map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
              <button
                onClick={() => void fetchSalaryRecords()}
                className="px-4 py-2 rounded-xl bg-violet-600 text-white font-bold hover:bg-violet-700"
              >
                Refresh Payroll
              </button>
            </div>
          </div>

          {salaryLoading ? (
            <div className="p-10 text-center text-slate-500">Loading payroll records...</div>
          ) : salaryRecords.length === 0 ? (
            <div className="p-10 text-center text-slate-500">No payroll records found for the selected month.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Employee</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Base</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Bonus</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Deductions</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Net Salary</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {salaryRecords.map(record => (
                    <tr key={record.id} className="border-t border-slate-200 hover:bg-slate-50">
                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900">{record.staff_name}</div>
                        <div className="text-xs text-slate-500">{record.employee_id} • {record.department}</div>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">INR {Number(record.base_salary || 0).toLocaleString()}</td>
                      <td className="px-4 py-4 text-sm text-slate-700">INR {Number(record.bonus || 0).toLocaleString()}</td>
                      <td className="px-4 py-4 text-sm text-slate-700">INR {Number(record.deductions || 0).toLocaleString()}</td>
                      <td className="px-4 py-4 text-sm font-bold text-slate-900">INR {Number(record.net_salary || 0).toLocaleString()}</td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${record.payment_status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                          {record.payment_status}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        {record.payment_status !== 'paid' ? (
                          <button
                            onClick={() => void markSalaryPaid(record.id)}
                            className="px-3 py-1 rounded-lg bg-violet-600 text-white font-semibold hover:bg-violet-700"
                          >
                            Mark Paid
                          </button>
                        ) : (
                          <span className="text-xs text-slate-500">Paid {record.payment_date ? new Date(record.payment_date).toLocaleDateString() : ''}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmModal.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-slate-900 mb-2">Deactivate Staff Member</h3>
            <p className="text-slate-600 mb-6">
              Are you sure you want to permanently deactivate <strong>{deleteConfirmModal.staffName}</strong>? They will no longer be able to log in, and all their historical data will be archived.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteConfirmModal({ isOpen: false })}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 font-semibold hover:bg-slate-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteConfirmModal.staffId && void handleDeleteStaff(deleteConfirmModal.staffId)}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-rose-600 text-white font-semibold hover:bg-rose-700 disabled:opacity-50"
              >
                {isDeleting ? 'Deleting...' : 'Delete Staff'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
