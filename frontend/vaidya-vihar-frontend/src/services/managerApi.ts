import api from './api';
import type { ApiEnvelope } from './companyManagementApi';
import type { Outlet, OutletManager } from './outletApi';

export const MANAGER_API_BASE = '/api/manager';

export type ManagerScopeKind = 'outlet' | 'kitchen' | 'store' | 'branch';

export interface ManagerOutlet {
  id: number;
  name: string;
  code?: string | null;
  kind?: ManagerScopeKind;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  pincode?: string | null;
  address_line_1?: string | null;
  address_line_2?: string | null;
  logo_url?: string | null;
  cover_photo_url?: string | null;
  company_id?: number | null;
  company_name?: string | null;
  outlet_email?: string | null;
  outlet_phone?: string | null;
  opening_time?: string | null;
  closing_time?: string | null;
  google_maps_url?: string | null;
  fssai_license?: string | null;
  trade_license?: string | null;
  fire_safety_certificate?: string | null;
  health_permit?: string | null;
  license_expiry_date?: string | null;
  is_delivery_enabled?: boolean | null;
  is_dine_in_enabled?: boolean | null;
  is_takeaway_enabled?: boolean | null;
  is_active: boolean;
}

export interface ManagerIdentity {
  user_id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  role: string;
  role_label: string;
  photo_url?: string | null;
  assigned_at?: string | null;
}

export interface ManagerMetrics {
  outlet_id: number | null;
  team_size: number | null;
  open_shifts: number | null;
  attendance_rate: number | null;
  sales_today: number | null;
  orders_today: number;
  low_stock_items: number | null;
  open_incidents: number | null;
}

export type ManagerResponsibilityStatus = 'active' | 'planned' | 'delegated';

export interface ManagerResponsibility {
  id: string;
  title: string;
  description: string;
  domain: string;
  status: ManagerResponsibilityStatus;
  authority: string;
  escalates_to?: string | null;
}

export interface ManagerAlert {
  id: string;
  title: string;
  detail?: string | null;
  severity: 'info' | 'warning' | 'critical';
  raised_at?: string | null;
}

export interface ManagerWorkspaceData {
  manager: ManagerIdentity;
  outlet: ManagerOutlet | null;
  metrics: ManagerMetrics;
  responsibilities: ManagerResponsibility[];
  alerts: ManagerAlert[];
  source: 'service';
}

export interface ManagerOverviewData {
  metrics: ManagerMetrics;
  alerts: ManagerAlert[];
  generated_at?: string | null;
}

export interface ManagerProfileData {
  manager: ManagerIdentity;
  outlet: ManagerOutlet | null;
  responsibilities: ManagerResponsibility[];
}

export type DashboardSourceStatus = 'ok' | 'live' | 'partial' | 'degraded' | 'pending' | 'unavailable' | 'empty' | 'error' | string;

export interface ManagerDashboardPayload {
  [key: string]: unknown;
}

export const MANAGER_ROLES = ['outlet_manager'] as const;

export type ManagerRole = (typeof MANAGER_ROLES)[number];

export const normalizeRoleKey = (role?: string | null): string =>
  (role || '').trim().toLowerCase().replace(/[-\s]+/g, '_');

export const isManagerRole = (role?: string | null): boolean =>
  (MANAGER_ROLES as readonly string[]).includes(normalizeRoleKey(role));

export const managerRoleLabel = (role?: string | null): string => {
  const key = normalizeRoleKey(role);
  if (!key) return 'Manager';
  return key
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
};

const emptyMetrics = (outletId: number | null): ManagerMetrics => ({
  outlet_id: outletId,
  team_size: null,
  open_shifts: null,
  attendance_rate: null,
  sales_today: null,
  orders_today: 0,
  low_stock_items: null,
  open_incidents: null,
});

export const FOUNDATION_RESPONSIBILITIES: ManagerResponsibility[] = [
  {
    id: 'daily-operations',
    title: 'Daily outlet operations',
    description: 'Open, run, and close the outlet against the published operating standard.',
    domain: 'Operations',
    status: 'active',
    authority: 'Execute and record; cannot change outlet configuration.',
    escalates_to: 'Company CEO',
  },
  {
    id: 'team-roster',
    title: 'Team roster and attendance',
    description: 'Plan shifts, approve attendance, and cover gaps inside the approved headcount.',
    domain: 'People',
    status: 'active',
    authority: 'Approve within roster budget; hiring stays with company scope.',
    escalates_to: 'Company CEO',
  },
  {
    id: 'stock-control',
    title: 'Stock and indent control',
    description: 'Raise indents, record consumption and wastage, and keep counts reconciled.',
    domain: 'Inventory',
    status: 'active',
    authority: 'Request and record; purchase approval stays with company scope.',
    escalates_to: 'Supply chain',
  },
  {
    id: 'service-quality',
    title: 'Service and customer recovery',
    description: 'Own service quality, complaint handling, and first-line customer recovery.',
    domain: 'Commercial',
    status: 'active',
    authority: 'Resolve within the outlet goodwill limit.',
    escalates_to: 'Company CEO',
  },
  {
    id: 'food-safety',
    title: 'Food safety and compliance',
    description: 'Run daily hygiene checks, log corrective action, and keep licences visible.',
    domain: 'Compliance',
    status: 'active',
    authority: 'Execute checks and raise incidents; sign-off stays with compliance.',
    escalates_to: 'Quality & compliance',
  },
  {
    id: 'cash-reconciliation',
    title: 'Cash and shift reconciliation',
    description: 'Reconcile shift sales, settlements, and deposits before day close.',
    domain: 'Commercial',
    status: 'planned',
    authority: 'Record and reconcile; ledger posting stays with finance.',
    escalates_to: 'Finance',
  },
];

interface ManagerSelfData {
  manager: OutletManager & { display_name?: string | null; profile_photo_url?: string | null };
  outlet: Outlet;
  company: { id: number; name: string };
}

interface ManagerStatsData {
  stats: {
    outlet_id: number;
    staff_count: number;
    orders_today: number;
    pending_orders: number;
    revenue_today: number;
    avg_bill_value_today: number;
  };
}

const managerDisplayName = (manager: ManagerSelfData['manager']): string =>
  manager.display_name
  || [manager.first_name, manager.last_name].filter(Boolean).join(' ')
  || manager.username;

const buildManagerIdentity = (manager: ManagerSelfData['manager']): ManagerIdentity => ({
  user_id: manager.id,
  username: manager.username,
  first_name: manager.first_name,
  last_name: manager.last_name,
  display_name: manager.display_name || null,
  full_name: managerDisplayName(manager),
  email: manager.email,
  phone: manager.phone,
  role: 'outlet_manager',
  role_label: 'Outlet Manager',
  photo_url: manager.profile_photo_url || manager.manager_photo_url,
  assigned_at: manager.manager_assigned_at,
});

const buildManagerOutlet = (outlet: Outlet, company?: ManagerSelfData['company'] | null): ManagerOutlet => ({
  id: outlet.id,
  name: outlet.name,
  code: outlet.code,
  city: outlet.city,
  state: outlet.state,
  country: outlet.country,
  pincode: outlet.pincode,
  address_line_1: outlet.address_line_1,
  address_line_2: outlet.address_line_2,
  logo_url: outlet.logo_url,
  cover_photo_url: outlet.cover_photo_url,
  company_id: company?.id ?? outlet.company_id,
  company_name: company?.name || null,
  outlet_email: outlet.outlet_email,
  outlet_phone: outlet.outlet_phone,
  opening_time: outlet.opening_time,
  closing_time: outlet.closing_time,
  google_maps_url: outlet.google_maps_url,
  fssai_license: outlet.fssai_license,
  trade_license: outlet.trade_license,
  fire_safety_certificate: outlet.fire_safety_certificate,
  health_permit: outlet.health_permit,
  license_expiry_date: outlet.license_expiry_date,
  is_delivery_enabled: outlet.is_delivery_enabled,
  is_dine_in_enabled: outlet.is_dine_in_enabled,
  is_takeaway_enabled: outlet.is_takeaway_enabled,
  is_active: outlet.status === 'active',
});

export const managerApi = {
  me: async (): Promise<ApiEnvelope<ManagerSelfData>> =>
    (await api.get<ApiEnvelope<ManagerSelfData>>(`${MANAGER_API_BASE}/me`)).data,
  stats: async (): Promise<ApiEnvelope<ManagerStatsData>> =>
    (await api.get<ApiEnvelope<ManagerStatsData>>(`${MANAGER_API_BASE}/me/stats`)).data,
  kpis: async (): Promise<ApiEnvelope<ManagerDashboardPayload>> =>
    (await api.get<ApiEnvelope<ManagerDashboardPayload>>(`${MANAGER_API_BASE}/dashboard/kpis`)).data,
  liveOrders: async (): Promise<ApiEnvelope<ManagerDashboardPayload>> =>
    (await api.get<ApiEnvelope<ManagerDashboardPayload>>(`${MANAGER_API_BASE}/dashboard/live-orders`)).data,
  staffOnShift: async (): Promise<ApiEnvelope<ManagerDashboardPayload>> =>
    (await api.get<ApiEnvelope<ManagerDashboardPayload>>(`${MANAGER_API_BASE}/dashboard/staff-on-shift`)).data,
  activity: async (): Promise<ApiEnvelope<ManagerDashboardPayload>> =>
    (await api.get<ApiEnvelope<ManagerDashboardPayload>>(`${MANAGER_API_BASE}/dashboard/activity`)).data,
  health: async (): Promise<ApiEnvelope<ManagerDashboardPayload>> =>
    (await api.get<ApiEnvelope<ManagerDashboardPayload>>(`${MANAGER_API_BASE}/dashboard/health`)).data,
  updateMe: async (payload: Partial<Pick<OutletManager, 'first_name' | 'last_name' | 'phone' | 'manager_photo_url'>>) =>
    (await api.put<ApiEnvelope<ManagerSelfData>>(`${MANAGER_API_BASE}/me`, payload)).data,
  outlet: async () => (await api.get<ApiEnvelope<{ outlet: Outlet }>>(`${MANAGER_API_BASE}/outlet`)).data,
  loadWorkspace: async (): Promise<ManagerWorkspaceData> => {
    const [selfResponse, outletResponse, statsResponse] = await Promise.all([managerApi.me(), managerApi.outlet(), managerApi.stats()]);
    const { manager, company } = selfResponse.data;
    const { outlet } = outletResponse.data;
    const { stats } = statsResponse.data;
    return {
      manager: buildManagerIdentity(manager),
      outlet: buildManagerOutlet(outlet, company),
      metrics: {
        ...emptyMetrics(outlet.id),
        team_size: stats.staff_count,
        orders_today: stats.orders_today,
        sales_today: stats.revenue_today,
      },
      responsibilities: FOUNDATION_RESPONSIBILITIES,
      alerts: [],
      source: 'service',
    };
  },
};

export default managerApi;
