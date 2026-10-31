import api from './api';
import type { ApiEnvelope } from './companyManagementApi';
import { superCeoProfileApi } from './superCeoProfileApi';

export const MANAGER_STAFF_API_BASE = '/api/manager/staff';
export const STAFF_SELF_API_BASE = '/api/staff/me';

export const STAFF_ROLES = ['staff', 'is_staff'] as const;

export type StaffTone = 'gold' | 'teal' | 'violet' | 'sunset' | 'rose';

export interface StaffRecord {
  id?: number;
  staff_profile_id?: number;
  user_id?: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
  display_name?: string | null;
  employee_code?: string | null;
  staff_id?: string | null;
  role?: string | null;
  staff_role?: string | null;
  designation?: string | null;
  role_label?: string | null;
  email?: string | null;
  phone?: string | null;
  mobile?: string | null;
  photo_url?: string | null;
  status?: string | null;
  is_active?: boolean | null;
  joined_at?: string | null;
  joining_date?: string | null;
  date_of_joining?: string | null;
  shift?: string | null;
  shift_preference?: string | null;
  outlet_id?: number | null;
  outlet_name?: string | null;
  outlet_code?: string | null;
  outlet?: Record<string, unknown> | null;
  current_address?: string | null;
  permanent_address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  emergency_contact_relation?: string | null;
  aadhaar_number?: string | null;
  aadhaar_masked?: string | null;
  pan_number?: string | null;
  pan_masked?: string | null;
  voter_id?: string | null;
  voter_id_masked?: string | null;
  driving_license?: string | null;
  driving_license_masked?: string | null;
  bank_account_name?: string | null;
  bank_account_number?: string | null;
  bank_account_number_masked?: string | null;
  ifsc_code?: string | null;
  bank_name?: string | null;
  branch_name?: string | null;
  upi_id?: string | null;
  upi_id_masked?: string | null;
  employment_type?: string | null;
  salary_type?: string | null;
  salary_amount?: number | string | null;
  weekly_off_day?: string | null;
  years_of_experience?: number | string | null;
  previous_employer?: string | null;
  skills?: string[] | string | null;
  qualifications?: Array<Record<string, unknown>> | null;
  certifications?: Array<Record<string, unknown>> | null;
  attendance?: Array<Record<string, unknown>> | null;
  payslips?: Array<Record<string, unknown>> | null;
  performance?: Array<Record<string, unknown>> | Record<string, unknown> | null;
  activity?: Array<Record<string, unknown>> | null;
  documents?: Record<string, unknown> | Array<Record<string, unknown>> | null;
  preferences?: Record<string, unknown> | null;
  force_password_change?: boolean | null;
  created_at?: string | null;
  updated_at?: string | null;
  [key: string]: unknown;
}

export interface StaffListParams {
  search?: string;
  role?: string;
  status?: string;
  shift?: string;
  page?: number;
  page_size?: number;
}

export interface StaffListData {
  items?: StaffRecord[];
  staff?: StaffRecord[];
  results?: StaffRecord[];
  total?: number;
  page?: number;
  page_size?: number;
  [key: string]: unknown;
}

export interface StaffStatsData {
  stats?: Record<string, unknown>;
  summary?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface StaffWorkspaceData {
  me: StaffRecord;
  outlet: Record<string, unknown> | null;
}

const asObject = (value: unknown): Record<string, unknown> | null => (
  value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
);

const textValue = (value: unknown): string | null => {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed || null;
};

const numberValue = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const pickFirst = (sources: Array<Record<string, unknown> | null | undefined>, keys: string[]): unknown => {
  for (const source of sources) {
    if (!source) continue;
    for (const key of keys) {
      if (source[key] != null) return source[key];
    }
  }
  return undefined;
};

export const normalizeRoleKey = (role?: string | null): string => (role || '').trim().toLowerCase().replace(/[-\s]+/g, '_');

export const isStaffRole = (role?: string | null): boolean => {
  const normalized = normalizeRoleKey(role);
  return normalized === 'staff' || normalized === 'is_staff';
};

export const staffRoleLabel = (role?: string | null): string => {
  const normalized = normalizeRoleKey(role);
  if (!normalized) return 'Staff';
  if (normalized === 'is_staff') return 'Staff';
  return normalized.split('_').map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
};

export const staffRoleTone = (role?: string | null): StaffTone => {
  const normalized = normalizeRoleKey(role);
  if (['chef', 'sous_chef', 'kitchen_helper'].includes(normalized)) return 'sunset';
  if (normalized === 'cashier') return 'rose';
  if (['waiter', 'cleaner'].includes(normalized)) return 'teal';
  if (['delivery_rider', 'rider', 'store_keeper', 'storekeeper'].includes(normalized)) return 'violet';
  if (normalized === 'shift_supervisor' || normalized === 'supervisor') return 'gold';
  return 'teal';
};

const buildWorkspaceMe = (payload: Record<string, unknown>): StaffRecord => {
  const staff = asObject(pickFirst([payload], ['staff', 'profile', 'me', 'user'])) || payload;
  const outlet = asObject(pickFirst([payload, staff], ['outlet']));
  const firstName = textValue(pickFirst([staff, payload], ['first_name'])) || '';
  const lastName = textValue(pickFirst([staff, payload], ['last_name'])) || '';
  const fullName = textValue(pickFirst([staff, payload], ['full_name', 'display_name'])) || [firstName, lastName].filter(Boolean).join(' ') || textValue(pickFirst([staff, payload], ['username'])) || 'Staff User';
  return {
    ...payload,
    ...staff,
    full_name: fullName,
    first_name: firstName || fullName.split(/\s+/)[0] || '',
    last_name: lastName || fullName.split(/\s+/).slice(1).join(' ') || '',
    role: textValue(pickFirst([staff, payload], ['role', 'staff_role'])) || 'staff',
    role_label: staffRoleLabel(textValue(pickFirst([staff, payload], ['role', 'staff_role'])) || 'staff'),
    employee_code: textValue(pickFirst([staff, payload], ['employee_code', 'staff_id', 'employee_id'])) || null,
    photo_url: textValue(pickFirst([staff, payload], ['photo_url', 'profile_photo_url'])) || null,
    phone: textValue(pickFirst([staff, payload], ['phone', 'mobile'])) || null,
    outlet_name: textValue(pickFirst([staff, payload, outlet], ['outlet_name', 'branch_name', 'name'])) || null,
    outlet_code: textValue(pickFirst([staff, payload, outlet], ['outlet_code', 'code'])) || null,
    joined_at: textValue(pickFirst([staff, payload], ['joining_date', 'date_of_joining', 'joined_at'])) || null,
  };
};

export const staffApi = {
  list: async (params: StaffListParams = {}) => (
    await api.get<ApiEnvelope<StaffListData>>(MANAGER_STAFF_API_BASE, { params })
  ).data,

  get: async (id: number | string) => (
    await api.get<ApiEnvelope<{ staff?: StaffRecord; member?: StaffRecord; employee?: StaffRecord } & StaffRecord>>(`${MANAGER_STAFF_API_BASE}/${id}`)
  ).data,

  create: async (data: Record<string, unknown>) => (
    await api.post<ApiEnvelope<{ staff?: StaffRecord; credentials?: Record<string, unknown> } & Record<string, unknown>>>(MANAGER_STAFF_API_BASE, data)
  ).data,

  update: async (id: number | string, data: Record<string, unknown>) => (
    await api.put<ApiEnvelope<{ staff?: StaffRecord } & Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}`, data)
  ).data,

  deactivate: async (id: number | string, reason?: string) => (
    await api.delete<ApiEnvelope<Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}`, { data: { reason } })
  ).data,

  restore: async (id: number | string) => (
    await api.post<ApiEnvelope<Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}/restore`)
  ).data,

  resetPassword: async (id: number | string) => (
    await api.post<ApiEnvelope<Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}/reset-password`)
  ).data,

  testLogin: async (id: number | string, payload?: Record<string, unknown>) => (
    await api.post<ApiEnvelope<Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}/test-login`, payload || {})
  ).data,

  revealField: async (id: number | string, field: string) => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}/reveal`, { params: { field } })
  ).data,

  getAudit: async (id: number | string) => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${MANAGER_STAFF_API_BASE}/${id}/audit`)
  ).data,

  getStats: async () => (
    await api.get<ApiEnvelope<StaffStatsData>>(`${MANAGER_STAFF_API_BASE}/stats`)
  ).data,

  uploadPhoto: async (id: number | string, file: File) => {
    const asset = await superCeoProfileApi.upload('profile-photo', file);
    return staffApi.update(id, { photo_url: asset.url });
  },

  getMe: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(STAFF_SELF_API_BASE)
  ).data,

  updateMe: async (data: Record<string, unknown>) => (
    await api.put<ApiEnvelope<Record<string, unknown>>>(STAFF_SELF_API_BASE, data)
  ).data,

  uploadMyPhoto: async (file: File) => {
    const asset = await superCeoProfileApi.upload('profile-photo', file);
    return staffApi.updateMe({ photo_url: asset.url });
  },

  getMyOutlet: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/outlet`)
  ).data,

  getMyDashboard: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/dashboard`)
  ).data,

  getMyAttendance: async (params: { page?: number; page_size?: number } = {}) => (
    await api.get<ApiEnvelope<{ items: Array<{ id: number; attendance_date: string | null; clock_in_time: string | null; clock_out_time: string | null; status: string; task?: string | null }>; pagination: { page: number; page_size: number; total: number } }>>(`${STAFF_SELF_API_BASE}/attendance`, { params })
  ).data,

  getMyTasks: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/tasks`)
  ).data,

  getMyPayslips: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/payslips`)
  ).data,

  submitRequest: async (data: Record<string, unknown>) => (
    await api.post<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/requests`, data)
  ).data,

  getMyRequests: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/requests`)
  ).data,

  getMyActivity: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>(`${STAFF_SELF_API_BASE}/activity`)
  ).data,

  changeMyPassword: async (data: { current_password: string; new_password: string }) => (
    await api.post<ApiEnvelope<Record<string, unknown>>>('/api/auth/change-password', data)
  ).data,

  getMySessions: async () => (
    await api.get<ApiEnvelope<Record<string, unknown>>>('/api/auth/sessions')
  ).data,

  loadWorkspace: async (): Promise<StaffWorkspaceData> => {
    const [meResponse, outletResponse] = await Promise.allSettled([
      staffApi.getMe(),
      staffApi.getMyOutlet(),
    ]);

    if (meResponse.status !== 'fulfilled') {
      throw meResponse.reason;
    }

    const mePayload = asObject(meResponse.value.data) || {};
    const me = buildWorkspaceMe(mePayload);
    const outletPayload = outletResponse.status === 'fulfilled' ? asObject(outletResponse.value.data) : null;
    const outlet = asObject(pickFirst([outletPayload], ['outlet', 'branch', 'location'])) || outletPayload || asObject(me.outlet) || null;

    if (outlet) {
      me.outlet_name = textValue(pickFirst([me, outlet], ['outlet_name', 'branch_name', 'name'])) || me.outlet_name || null;
      me.outlet_code = textValue(pickFirst([me, outlet], ['outlet_code', 'code'])) || me.outlet_code || null;
      me.outlet_id = numberValue(pickFirst([me, outlet], ['outlet_id', 'branch_id', 'id']));
    }

    return { me, outlet };
  },
};

export default staffApi;
