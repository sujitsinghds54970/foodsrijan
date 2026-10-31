import api from './api';
import type { ApiEnvelope, CompanyAuditEvent } from './companyManagementApi';

export type OutletStatus = 'planning' | 'setup' | 'active' | 'temporarily_closed' | 'permanently_closed';
export type OutletType = 'dine_in' | 'takeaway' | 'cloud_kitchen' | 'kiosk' | 'food_truck' | 'cafe' | 'bakery' | 'bar' | 'fine_dine' | 'qsr' | 'buffet' | 'drive_through' | 'other';

export interface Outlet {
  id: number;
  company_id: number;
  name: string;
  slug: string;
  code: string;
  outlet_type: OutletType;
  status: OutletStatus;
  brand_id?: number | null;
  description?: string | null;
  opening_date?: string | null;
  logo_url?: string | null;
  cover_photo_url?: string | null;
  address_line_1: string;
  address_line_2?: string | null;
  city: string;
  state: string;
  country?: string | null;
  pincode: string;
  latitude?: number | null;
  longitude?: number | null;
  region?: string | null;
  timezone?: string | null;
  opening_time?: string | null;
  closing_time?: string | null;
  operating_days?: string[] | null;
  seating_capacity?: number | null;
  kitchen_capacity?: number | null;
  is_delivery_enabled?: boolean;
  is_dine_in_enabled?: boolean;
  is_takeaway_enabled?: boolean;
  delivery_radius_km?: number | null;
  fssai_license?: string | null;
  gstin?: string | null;
  trade_license?: string | null;
  fire_safety_certificate?: string | null;
  health_permit?: string | null;
  license_expiry_date?: string | null;
  rent_amount?: number | string | null;
  security_deposit?: number | string | null;
  lease_start_date?: string | null;
  lease_end_date?: string | null;
  bank_account_name?: string | null;
  bank_account_number?: string | null;
  ifsc_code?: string | null;
  bank_name?: string | null;
  branch_name?: string | null;
  upi_id?: string | null;
  cost_center_code?: string | null;
  manager_contact_email?: string | null;
  manager_contact_phone?: string | null;
  outlet_email?: string | null;
  outlet_phone?: string | null;
  google_maps_url?: string | null;
  swiggy_store_id?: string | null;
  zomato_store_id?: string | null;
  metadata?: Record<string, unknown> | null;
  manager?: Pick<OutletManager, 'id' | 'username' | 'first_name' | 'last_name' | 'email' | 'phone' | 'manager_photo_url'> | null;
  staff_count?: number;
  is_deleted?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export type OutletInput = Partial<Omit<Outlet, 'id' | 'company_id' | 'slug' | 'is_deleted' | 'created_at' | 'updated_at'>> & Pick<Outlet, 'name' | 'code' | 'outlet_type' | 'address_line_1' | 'city' | 'state' | 'pincode'>;

export interface OutletManager {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  is_active: boolean;
  force_password_change?: boolean;
  manager_photo_url?: string | null;
  manager_address?: string | null;
  manager_bank_account_name?: string | null;
  manager_bank_account_number?: string | null;
  manager_ifsc_code?: string | null;
  manager_bank_name?: string | null;
  manager_assigned_at?: string | null;
}

export interface ManagerInput {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  username?: string;
  password?: string;
  password_confirm?: string;
  replace_existing?: boolean;
}

export type ManagerProfileInput = Partial<Pick<OutletManager, 'first_name' | 'last_name' | 'email' | 'phone' | 'manager_photo_url' | 'manager_address' | 'manager_bank_account_name' | 'manager_bank_account_number' | 'manager_ifsc_code' | 'manager_bank_name' | 'is_active'>>;

export interface OneTimeCredentials {
  login_url: string;
  username: string;
  password: string;
  note?: string;
}

export interface OutletStats {
  total_outlets: number;
  active_outlets: number;
  outlets_without_manager: number;
  by_status: Record<OutletStatus, number>;
  by_type: Partial<Record<OutletType, number>>;
  deleted_outlets: number;
  outlets_with_manager: number;
  total_staff: number;
  revenue_30d: number;
}

const path = '/api/company-ceo/outlets';

export const outletApi = {
  list: async (params: { page: number; page_size: number; search?: string; status?: string; outlet_type?: string; city?: string; region?: string; include_deleted?: boolean }) =>
    (await api.get<ApiEnvelope<{ outlets: Outlet[]; total: number; page: number; page_size: number }>>(path, { params })).data,
  stats: async () => (await api.get<ApiEnvelope<{ stats: OutletStats }>>(`${path}/stats`)).data,
  get: async (id: number) => (await api.get<ApiEnvelope<{ outlet: Outlet }>>(`${path}/${id}`)).data,
  create: async (payload: OutletInput) => (await api.post<ApiEnvelope<{ outlet: Outlet }>>(path, payload)).data,
  update: async (id: number, payload: Partial<OutletInput>) => (await api.put<ApiEnvelope<{ outlet: Outlet }>>(`${path}/${id}`, payload)).data,
  remove: async (id: number) => (await api.delete<ApiEnvelope<{ outlet_id: number; deleted: boolean }>>(`${path}/${id}`)).data,
  restore: async (id: number) => (await api.post<ApiEnvelope<{ outlet: Outlet }>>(`${path}/${id}/restore`)).data,
  audit: async (id: number, params?: { page?: number; page_size?: number }) =>
    (await api.get<ApiEnvelope<{ events: CompanyAuditEvent[]; total: number }>>(`${path}/${id}/audit`, { params })).data,
  manager: async (id: number) => (await api.get<ApiEnvelope<{ manager: OutletManager | null }>>(`${path}/${id}/manager`)).data,
  createManager: async (id: number, payload: ManagerInput) =>
    (await api.post<ApiEnvelope<{ manager: OutletManager; credentials?: OneTimeCredentials }>>(`${path}/${id}/manager`, payload)).data,
  updateManager: async (id: number, payload: ManagerProfileInput) =>
    (await api.put<ApiEnvelope<{ manager: OutletManager }>>(`${path}/${id}/manager`, payload)).data,
  resetManagerPassword: async (id: number) =>
    (await api.post<ApiEnvelope<{ manager: OutletManager; credentials: OneTimeCredentials }>>(`${path}/${id}/manager/reset-password`)).data,
  removeManager: async (id: number) =>
    (await api.delete<ApiEnvelope<{ outlet_id: number; manager_removed: boolean }>>(`${path}/${id}/manager`)).data,
  testManagerLogin: async (id: number, payload: { username: string; password: string }) =>
    (await api.post<ApiEnvelope<{ valid: boolean; outlet_id: number }>>(`${path}/${id}/manager/test-login`, payload)).data,
};
