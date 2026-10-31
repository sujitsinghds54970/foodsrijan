import api from './api';
import type { ApiEnvelope } from './companyManagementApi';

export interface AttendanceRecord {
  id: number;
  company_id: number;
  outlet_id: number;
  staff_id: number;
  work_date: string;
  shift_id: number | null;
  clock_in: string;
  clock_out: string | null;
  status: string;
  flags: string[];
  minutes_worked: number | null;
}

export interface LeaveRecord {
  id: number;
  staff_id: number;
  outlet_id: number;
  start_date: string;
  end_date: string;
  leave_type: string;
  reason: string;
  status: string;
}

export interface CorrectionRecord {
  id: number;
  record_id: number;
  staff_id?: number;
  status: string;
  reason: string;
}

export interface ShiftRecord {
  id: number;
  name: string;
  start_time: string;
  end_time: string;
  grace_minutes: number;
  active: boolean;
}

export const localDate = (date = new Date()): string =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

export const attendanceTime = (value?: string | null): string => {
  if (!value) return '—';
  const parsed = new Date(`${value}Z`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

export const monthBounds = (month: string): { start: string; end: string } => {
  const [year, number] = month.split('-').map(Number);
  return { start: `${month}-01`, end: localDate(new Date(year, number, 0)) };
};

const deviceId = (): string => {
  const key = 'attendance.deviceId';
  let id = window.localStorage.getItem(key);
  if (!id) {
    id = window.crypto.randomUUID();
    window.localStorage.setItem(key, id);
  }
  return id;
};

const currentLocation = (): Promise<{
  latitude: number; longitude: number; accuracy_meters: number; device_id: string; mock_location: boolean;
}> => new Promise((resolve, reject) => {
  if (!navigator.geolocation) {
    reject(new Error('Location is not available on this device.'));
    return;
  }
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => resolve({
      latitude: coords.latitude, longitude: coords.longitude, accuracy_meters: coords.accuracy,
      device_id: deviceId(), mock_location: false,
    }),
    (error) => reject(new Error(`Location could not be obtained: ${error.message}`)),
    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
  );
});

export const attendanceApi = {
  mine: async (params: { start: string; end: string }) =>
    (await api.get<ApiEnvelope<{ records: AttendanceRecord[] }>>('/api/staff/attendance', { params })).data,
  clock: async (action: 'in' | 'out') =>
    (await api.post<ApiEnvelope<{ record: AttendanceRecord }>>(`/api/staff/attendance/clock-${action === 'in' ? 'in' : 'out'}`, await currentLocation())).data,
  myShifts: async (params: { start: string; end: string }) =>
    (await api.get<ApiEnvelope<{ assignments: Array<{ id: number; shift_id: number; work_date: string }> }>>('/api/staff/attendance/shifts', { params })).data,
  myLeaves: async () =>
    (await api.get<ApiEnvelope<{ leaves: LeaveRecord[] }>>('/api/staff/attendance/leaves')).data,
  requestLeave: async (payload: { start_date: string; end_date: string; leave_type: string; reason: string }) =>
    (await api.post('/api/staff/attendance/leaves', payload)).data,
  myCorrections: async () =>
    (await api.get<ApiEnvelope<{ corrections: CorrectionRecord[] }>>('/api/staff/attendance/corrections')).data,
  requestCorrection: async (payload: { record_id: number; requested_clock_in?: string; requested_clock_out?: string; reason: string }) =>
    (await api.post('/api/staff/attendance/corrections', payload)).data,
  managerRecords: async (params: { start: string; end: string; staff_id?: number }) =>
    (await api.get<ApiEnvelope<{ records: AttendanceRecord[] }>>('/api/manager/attendance', { params })).data,
  managerLeaves: async (status?: string) =>
    (await api.get<ApiEnvelope<{ leaves: LeaveRecord[] }>>('/api/manager/attendance/leaves', { params: { status } })).data,
  managerCorrections: async (status?: string) =>
    (await api.get<ApiEnvelope<{ corrections: CorrectionRecord[] }>>('/api/manager/attendance/corrections', { params: { status } })).data,
  reviewLeave: async (id: number, decision: 'approved' | 'rejected', note: string) =>
    (await api.post(`/api/manager/attendance/leaves/${id}/review`, { decision, note })).data,
  reviewCorrection: async (id: number, decision: 'approved' | 'rejected', note: string) =>
    (await api.post(`/api/manager/attendance/corrections/${id}/review`, { decision, note })).data,
  shifts: async () =>
    (await api.get<ApiEnvelope<{ shifts: ShiftRecord[] }>>('/api/manager/attendance/shifts')).data,
  createShift: async (payload: { name: string; start_time: string; end_time: string; grace_minutes: number }) =>
    (await api.post('/api/manager/attendance/shifts', payload)).data,
  assignShift: async (payload: { staff_id: number; shift_id: number; work_date: string }) =>
    (await api.post('/api/manager/attendance/assignments', payload)).data,
  geofence: async () =>
    (await api.get<ApiEnvelope<{ geofence: { latitude: number; longitude: number; radius_meters: number; enabled: boolean } | null }>>('/api/manager/attendance/geofence')).data,
  saveGeofence: async (payload: { latitude: number; longitude: number; radius_meters: number; enabled: boolean }) =>
    (await api.put('/api/manager/attendance/geofence', payload)).data,
  companyRecords: async (params: { start: string; end: string; outlet_id?: number }) =>
    (await api.get<ApiEnvelope<{ records: AttendanceRecord[] }>>('/api/company-ceo/attendance', { params })).data,
  portfolioRecords: async (params: { company_id: number; start: string; end: string; outlet_id?: number }) =>
    (await api.get<ApiEnvelope<{ records: AttendanceRecord[] }>>('/api/super-ceo/attendance', { params })).data,
};
