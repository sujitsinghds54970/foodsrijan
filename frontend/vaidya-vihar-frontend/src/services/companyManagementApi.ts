import axios from 'axios';
import api from './api';

export interface Company {
  id: number;
  name: string;
  slug: string;
  tagline?: string | null;
  description?: string | null;
  legal_name?: string | null;
  registration_number?: string | null;
  gstin?: string | null;
  pan_number?: string | null;
  fssai_license?: string | null;
  cin_number?: string | null;
  registered_address?: string | null;
  corporate_address?: string | null;
  bank_account_name?: string | null;
  bank_account_number?: string | null;
  ifsc_code?: string | null;
  bank_name?: string | null;
  annual_revenue_range?: string | null;
  business_domain?: string | null;
  funding_stage?: string | null;
  founded_date?: string | null;
  headquarters_city?: string | null;
  headquarters_state?: string | null;
  headquarters_country?: string | null;
  headquarters_pincode?: string | null;
  website_url?: string | null;
  linkedin_url?: string | null;
  instagram_url?: string | null;
  facebook_url?: string | null;
  twitter_url?: string | null;
  youtube_url?: string | null;
  mobile_app_url?: string | null;
  support_email?: string | null;
  support_phone?: string | null;
  operating_regions?: string[] | null;
  sub_domains?: string[] | null;
  target_market?: string | null;
  employee_count_estimate?: string | null;
  business_description?: string | null;
  number_of_branches?: number | null;
  status: 'active' | 'inactive' | 'suspended' | 'archived';
  onboarding_status?: string | null;
  is_active: boolean;
  is_deleted: boolean;
  created_at?: string | null;
}

export interface CompanyCeo {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  company_id: number | null;
  is_company_ceo: boolean;
  is_active: boolean;
  force_password_change: boolean;
  ceo_assigned_at?: string | null;
}

export interface CompanyAuditEvent {
  id: number;
  action: string;
  actor_id?: number | null;
  created_at?: string | null;
  request_meta?: Record<string, unknown>;
}

export interface ApiEnvelope<T> {
  data: T;
  meta?: Record<string, unknown>;
  errors?: Array<Record<string, unknown>>;
}

interface CompanyListData {
  companies: Company[];
  total: number;
  page: number;
  page_size: number;
}

interface CompanyDetailData {
  company: Company & { ceo?: CompanyCeo | null };
}

interface CompanyMutationData {
  company: Company;
}

interface CEOResponse {
  ceo: CompanyCeo | null;
  credentials?: {
    login_url: string;
    username: string;
    password: string;
    note: string;
  };
}

export interface CompanyCEOProfileInput {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
}

interface AuditData {
  company_id: number;
  events: CompanyAuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface CompanyPortfolioStats {
  active_companies: number;
  active_branches: number;
  active_users: number;
  pending_onboarding: number;
}

interface MetricsData {
  metrics: {
    branches: number;
    employees: number;
    customers: number;
    revenue: number;
  };
}

export interface CompanyPayload {
  name: string;
  [key: string]: string | number | string[] | Record<string, unknown> | null | undefined;
}

export interface CompanyCEOInput {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  username: string;
  password: string;
  password_confirm: string;
}

const companiesPath = '/api/super-ceo/companies';

export const companyManagementApi = {
  list: async (params: {
    page: number;
    page_size: number;
    search?: string;
    status?: string;
    business_domain?: string;
    include_deleted?: boolean;
  }) => (await api.get<ApiEnvelope<CompanyListData>>(companiesPath, { params })).data,

  stats: async () =>
    (await api.get<ApiEnvelope<{ stats: CompanyPortfolioStats }>>(`${companiesPath}/stats`)).data,

  get: async (companyId: number) =>
    (await api.get<ApiEnvelope<CompanyDetailData>>(`${companiesPath}/${companyId}`)).data,

  create: async (payload: CompanyPayload) =>
    (await api.post<ApiEnvelope<CompanyMutationData>>(companiesPath, payload)).data,

  update: async (companyId: number, payload: Partial<CompanyPayload>) =>
    (await api.put<ApiEnvelope<CompanyMutationData>>(`${companiesPath}/${companyId}`, payload)).data,

  remove: async (companyId: number) =>
    (await api.delete<ApiEnvelope<{ company_id: number; deleted: boolean }>>(`${companiesPath}/${companyId}`)).data,

  restore: async (companyId: number) =>
    (await api.post<ApiEnvelope<CompanyMutationData>>(`${companiesPath}/${companyId}/restore`)).data,

  metrics: async (companyId: number) =>
    (await api.get<ApiEnvelope<MetricsData>>(`${companiesPath}/${companyId}/metrics`)).data,

  audit: async (companyId: number, params?: { page?: number; page_size?: number; action?: string }) =>
    (await api.get<ApiEnvelope<AuditData>>(`${companiesPath}/${companyId}/audit`, { params })).data,

  createCEO: async (companyId: number, payload: CompanyCEOInput) =>
    (await api.post<ApiEnvelope<CEOResponse>>(`${companiesPath}/${companyId}/ceo`, payload)).data,

  updateCEO: async (companyId: number, payload: CompanyCEOProfileInput) =>
    (await api.put<ApiEnvelope<CEOResponse>>(`${companiesPath}/${companyId}/ceo`, payload)).data,

  resetCEOPassword: async (companyId: number) =>
    (await api.post<ApiEnvelope<CEOResponse>>(`${companiesPath}/${companyId}/ceo/reset-password`)).data,

  removeCEO: async (companyId: number) =>
    (await api.delete<ApiEnvelope<{ company_id: number; ceo_removed: boolean }>>(`${companiesPath}/${companyId}/ceo`)).data,

  testCEOLogin: async (companyId: number, payload: { username: string; password: string }) =>
    (await api.post<ApiEnvelope<{ valid: boolean; company_id: number }>>(`${companiesPath}/${companyId}/ceo/test-login`, payload)).data,
};

export const apiErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError(error)) return fallback;
  const detail: unknown = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && 'message' in detail && typeof detail.message === 'string') {
    const blockers = 'blockers' in detail && detail.blockers && typeof detail.blockers === 'object'
      ? Object.entries(detail.blockers)
        .filter(([, count]) => typeof count === 'number' && count > 0)
        .map(([name, count]) => `${name.replace(/_/g, ' ')}: ${count}`)
      : [];
    return [detail.message, ...blockers].join(' · ');
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .filter((item): item is { msg: string } => Boolean(item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string'))
      .map((item) => item.msg);
    if (messages.length) return messages.join('. ');
  }
  return error.message || fallback;
};
