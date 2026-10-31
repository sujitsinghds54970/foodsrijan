import axios from 'axios';
import api from './api';

export interface ApiEnvelope<T> {
  data: T;
  meta?: Record<string, unknown>;
  errors?: Array<Record<string, unknown>>;
}

export interface ProfileStats {
  companies_overseen: number;
  decisions_made: number;
  team_size: number;
  tenure_days: number;
}

export interface ProfileEntry {
  [key: string]: unknown;
}

export interface SuperCEOProfile {
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  email?: string | null;
  phone?: string | null;
  bio?: string | null;
  profile_photo_url?: string | null;
  cover_photo_url?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  location_city?: string | null;
  location_state?: string | null;
  location_country?: string | null;
  timezone?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  assistant_name?: string | null;
  assistant_email?: string | null;
  assistant_phone?: string | null;
  preferred_contact_method?: 'email' | 'phone' | 'whatsapp' | null;
  qualifications?: ProfileEntry[] | null;
  certifications?: ProfileEntry[] | null;
  achievements?: ProfileEntry[] | null;
  preferences?: Record<string, unknown> | null;
  recovery_email?: string | null;
  recovery_phone?: string | null;
  is_verified?: boolean;
  stats?: ProfileStats;
}

export interface ProfileActivity {
  id: number;
  action: string;
  resource?: string | null;
  timestamp?: string | null;
  changes?: Record<string, unknown> | null;
}

export interface ParentCompany {
  id: number;
  slug: string;
  is_parent: boolean;
  name?: string | null;
  tagline?: string | null;
  description?: string | null;
  logo_url?: string | null;
  banner_url?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  accent_color?: string | null;
  display_font?: string | null;
  body_font?: string | null;
  founded_date?: string | null;
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
  funding_stage?: string | null;
  last_funding_round_date?: string | null;
  total_funding_raised?: string | null;
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
  ios_app_url?: string | null;
  android_app_url?: string | null;
  support_email?: string | null;
  support_phone?: string | null;
  whatsapp_business_number?: string | null;
  business_domain?: string | null;
  sub_domains?: string[] | null;
  target_market?: string | null;
  employee_count_estimate?: string | null;
  published_at?: string | null;
  published_by?: number | null;
}

export type ParentCompanyUpdate = Omit<Partial<ParentCompany>, 'id' | 'slug' | 'is_parent' | 'published_at' | 'published_by' | 'sub_domains'> & {
  sub_domains?: string[] | null;
};

export interface ParentCompanyAudit {
  id: number;
  action: string;
  actor_id?: number | null;
  timestamp?: string | null;
  changes?: Record<string, unknown>;
}

interface UploadAsset {
  url: string;
  filename: string;
  size: number;
  mime: string;
}

const profilePath = '/api/super-ceo/profile';
const parentCompanyPath = '/api/super-ceo/parent-company';

export const superCeoProfileApi = {
  get: async () => (
    await api.get<ApiEnvelope<{ profile: SuperCEOProfile }>>(profilePath)
  ).data.data.profile,

  update: async (payload: Partial<SuperCEOProfile>) => (
    await api.put<ApiEnvelope<{ profile: SuperCEOProfile; updated_fields: string[] }>>(profilePath, payload)
  ).data.data,

  activity: async (params: { page?: number; page_size?: number } = {}) => (
    await api.get<ApiEnvelope<{ activity: ProfileActivity[]; total: number; page: number; page_size: number }>>(
      `${profilePath}/activity`,
      { params },
    )
  ).data.data,

  logout: async () => (
    await api.post<ApiEnvelope<{ logged_out: boolean }>>(`${profilePath}/logout`)
  ).data.data,

  upload: async (kind: 'profile-photo' | 'cover-photo' | 'company-logo' | 'company-banner', file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post<{ data: UploadAsset; errors: Array<Record<string, unknown>> }>(
      `/api/uploads/${kind}`,
      formData,
    );
    return response.data.data;
  },
};

export const parentCompanyApi = {
  get: async () => (
    await api.get<ApiEnvelope<{ published: ParentCompany; draft: Partial<ParentCompany> | null; has_draft: boolean }>>(
      parentCompanyPath,
    )
  ).data.data,

  saveDraft: async (payload: ParentCompanyUpdate) => (
    await api.put<ApiEnvelope<{ draft: Partial<ParentCompany>; has_draft: boolean }>>(parentCompanyPath, payload)
  ).data.data,

  discardDraft: async () => (
    await api.delete<ApiEnvelope<{ has_draft: boolean }>>(`${parentCompanyPath}/draft`)
  ).data.data,

  publish: async () => (
    await api.post<ApiEnvelope<{ published: ParentCompany; has_draft: boolean }>>(`${parentCompanyPath}/publish`)
  ).data.data,

  audit: async (params: { page?: number; page_size?: number; field?: string } = {}) => (
    await api.get<ApiEnvelope<{ audit: ParentCompanyAudit[]; total: number; page: number; page_size: number }>>(
      `${parentCompanyPath}/audit`,
      { params },
    )
  ).data.data,
};

export const requestErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError(error)) return fallback;
  const detail: unknown = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .filter((item): item is { msg: string } => Boolean(item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string'))
      .map((item) => item.msg);
    if (messages.length) return messages.join('. ');
  }
  return error.message || fallback;
};

export const resolveAssetUrl = (value: string): string => {
  if (!value.startsWith('/uploads/')) return value;
  const baseUrl = api.defaults.baseURL || (typeof window !== 'undefined' ? window.location.origin : '');
  return baseUrl ? new URL(value, baseUrl).toString() : value;
};
