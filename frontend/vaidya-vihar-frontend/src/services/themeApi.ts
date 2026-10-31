import api from './api';

export interface ProfileType {
  id: number;
  key: string;
  display_name: string;
  description?: string | null;
  is_system: boolean;
  is_active: boolean;
}

export interface ThemeRecord {
  id: number;
  profile_type_id: number;
  profile_type_key?: string | null;
  company_id?: number | null;
  brand_id?: number | null;
  name: string;
  slug: string;
  status: string;
  current_version_id?: number | null;
}

export interface ThemeVersion {
  id: number;
  theme_id: number;
  version_number: number;
  status: string;
  tokens: Record<string, any>;
  contrast_report?: Record<string, any>;
  change_summary?: string | null;
  created_at?: string | null;
  published_at?: string | null;
}

export const themeApi = {
  getProfileTypes: () => api.get<{ profile_types: ProfileType[] }>('/api/super-ceo/themes/profile-types').then((response) => response.data),
  getThemes: (profileTypeKey: string) => api.get<{ themes: ThemeRecord[] }>('/api/super-ceo/themes', { params: { profile_type_key: profileTypeKey } }).then((response) => response.data),
  getVersions: (themeId: number) => api.get<{ versions: ThemeVersion[] }>(`/api/super-ceo/themes/${themeId}/versions`).then((response) => response.data),
  saveVersion: (themeId: number, tokens: Record<string, any>, changeSummary = 'Updated design tokens') => api.post<ThemeVersion>(`/api/super-ceo/themes/${themeId}/versions`, { tokens, change_summary: changeSummary }).then((response) => response.data),
  validate: (themeId: number, tokens: Record<string, any>) => api.post(`/api/super-ceo/themes/${themeId}/validate`, { tokens }).then((response) => response.data),
  publish: (themeId: number, versionId: number) => api.post<ThemeVersion>(`/api/super-ceo/themes/${themeId}/versions/${versionId}/publish`).then((response) => response.data),
  rollback: (themeId: number, versionId: number) => api.post<ThemeVersion>(`/api/super-ceo/themes/${themeId}/versions/${versionId}/rollback`).then((response) => response.data),
  getPresets: () => api.get<{ presets: Array<{ id: string; name: string; tokens: Record<string, any> }> }>('/api/super-ceo/themes/presets').then((response) => response.data),
};
