import React, { useState, useEffect } from 'react'
import PayrollDashboard from '../payroll/PayrollDashboard'

interface HRProps {
  activeTab: string
}

interface LeaveRequest {
  id: number
  user_id: number
  leave_type: string
  start_date: string
  end_date: string
  total_days: number
  status: string
  reason: string
}

interface Attendance {
  id: number
  user_id: number
  attendance_date: string
  status: string
  check_in: string | null
  check_out: string | null
}

interface Holiday {
  id: number
  holiday_name: string
  holiday_date: string
  is_national_holiday: boolean
}

export default function HR({ activeTab }: HRProps) {
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([])
  const [attendance, setAttendance] = useState<Attendance[]>([])
  const [holidays, setHolidays] = useState<Holiday[]>([])
  const [loading, setLoading] = useState(false)
  const [activeView, setActiveView] = useState<'attendance' | 'leave' | 'holidays' | 'payroll'>('attendance')

  useEffect(() => {
    if (activeTab === 'hr') {
      fetchAttendance()
      fetchLeaveRequests()
      fetchHolidays()
    }
  }, [activeTab])

  const fetchAttendance = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/hr/attendance')
      const data = await response.json()
      if (data.success) {
        setAttendance(data.attendance || [])
      }
    } catch (error) {
      console.error('Error fetching attendance:', error)
    }
    setLoading(false)
  }

  const fetchLeaveRequests = async () => {
    try {
      const response = await fetch('/api/hr/leave-requests')
      const data = await response.json()
      if (data.success) {
        setLeaveRequests(data.leave_requests || [])
      }
    } catch (error) {
      console.error('Error fetching leave requests:', error)
    }
  }

  const fetchHolidays = async () => {
    try {
      const response = await fetch('/api/hr/holidays')
      const data = await response.json()
      if (data.success) {
        setHolidays(data.holidays || [])
      }
    } catch (error) {
      console.error('Error fetching holidays:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'present': return 'bg-green-100 text-green-800'
      case 'absent': return 'bg-red-100 text-red-800'
      case 'late': return 'bg-yellow-100 text-yellow-800'
      case 'leave': return 'bg-blue-100 text-blue-800'
      case 'approved': return 'bg-green-100 text-green-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'rejected': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (activeTab !== 'hr') return null

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">HR & Payroll</h1>
          <p className="text-gray-600">Leave management and attendance tracking</p>
        </div>
        <div className="space-x-2">
          <button
            onClick={() => setActiveView('attendance')}
            className={`px-4 py-2 rounded-lg ${activeView === 'attendance' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Attendance
          </button>
          <button
            onClick={() => setActiveView('leave')}
            className={`px-4 py-2 rounded-lg ${activeView === 'leave' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Leave
          </button>
          <button
            onClick={() => setActiveView('holidays')}
            className={`px-4 py-2 rounded-lg ${activeView === 'holidays' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Holidays
          </button>
          <button
            onClick={() => setActiveView('payroll')}
            className={`px-4 py-2 rounded-lg ${activeView === 'payroll' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Payroll
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Present Today</div>
          <div className="text-2xl font-bold text-green-600">
            {attendance.filter(a => a.status === 'present').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">On Leave</div>
          <div className="text-2xl font-bold text-blue-600">
            {attendance.filter(a => a.status === 'leave').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Pending Requests</div>
          <div className="text-2xl font-bold text-yellow-600">
            {leaveRequests.filter(l => l.status === 'pending').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Holidays This Year</div>
          <div className="text-2xl font-bold">{holidays.length}</div>
        </div>
      </div>

      {/* Attendance View */}
      {activeView === 'attendance' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Today's Attendance</h2>
          </div>
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : attendance.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No attendance records found</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Employee ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Check In</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Check Out</th>
                </tr>
              </thead>
              <tbody>
                {attendance.slice(0, 10).map(record => (
                  <tr key={record.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3">#{record.user_id}</td>
                    <td className="px-4 py-3 text-sm">
                      {new Date(record.attendance_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(record.status)}`}>
                        {record.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {record.check_in ? new Date(record.check_in).toLocaleTimeString() : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {record.check_out ? new Date(record.check_out).toLocaleTimeString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Leave View */}
      {activeView === 'leave' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Leave Requests</h2>
          </div>
          {leaveRequests.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No leave requests found</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Employee</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Leave Type</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Duration</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Reason</th>
                </tr>
              </thead>
              <tbody>
                {leaveRequests.slice(0, 10).map(request => (
                  <tr key={request.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3">#{request.user_id}</td>
                    <td className="px-4 py-3 capitalize">{request.leave_type}</td>
                    <td className="px-4 py-3">
                      {request.total_days} day(s)
                      <div className="text-xs text-gray-500">
                        {new Date(request.start_date).toLocaleDateString()} - {new Date(request.end_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(request.status)}`}>
                        {request.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{request.reason || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Holidays View */}
      {activeView === 'holidays' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Company Holidays</h2>
          </div>
          {holidays.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No holidays configured</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Date</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Holiday Name</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Type</th>
                </tr>
              </thead>
              <tbody>
                {holidays.map(holiday => (
                  <tr key={holiday.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {new Date(holiday.holiday_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 font-medium">{holiday.holiday_name}</td>
                    <td className="px-4 py-3">
                      {holiday.is_national_holiday ? (
                        <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-800">National</span>
                      ) : (
                        <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">Optional</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeView === 'payroll' && <PayrollDashboard />}
    </div>
  )
}

