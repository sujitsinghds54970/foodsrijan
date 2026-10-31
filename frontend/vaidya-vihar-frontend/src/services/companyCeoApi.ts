import api from './api';
import type { ApiEnvelope, Company, CompanyAuditEvent, CompanyCeo } from './companyManagementApi';

export interface CompanyCeoBranch {
  id: number;
  name: string;
  branch_code: string;
  city: string;
  state: string;
  is_active: boolean;
}

export interface CompanyCeoWorkspaceData {
  executive: CompanyCeo;
  company: Company;
  metrics: {
    company_id: number;
    branches: number;
    employees: number;
    customers: number;
    revenue: number;
    active_users: number;
  };
  branches: CompanyCeoBranch[];
  brands: Array<{ id: number; name: string; slug: string; description?: string | null; is_active: boolean }>;
  departments: Array<{ id: number; name: string; code?: string | null; description?: string | null; is_active: boolean }>;
  audit: { events: CompanyAuditEvent[]; total: number };
}

export const companyCeoApi = {
  workspace: async () =>
    (await api.get<ApiEnvelope<CompanyCeoWorkspaceData>>('/api/company-ceo/workspace')).data,
};
