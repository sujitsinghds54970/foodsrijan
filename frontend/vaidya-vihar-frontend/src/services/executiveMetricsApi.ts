import api from './api';
import type {
  DerivedBundleData,
  MetricDefinition,
  MetricEnvelope,
  PerformanceSummary,
  StrategyOkrSummary,
} from '../types/metrics';

export interface ExecutiveActivity {
  id: string;
  type: string;
  actor?: { id?: number | null; name?: string | null };
  description?: string | null;
  timestamp?: string | null;
  severity?: string;
}

export interface SuperCeoUser {
  id: number;
  username: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  role?: string | null;
  is_active: boolean;
  companies?: Array<{ id: number; name: string }>;
}

export interface SuperCeoCompany {
  id: number;
  name: string;
  is_active: boolean;
}

export interface CompanyHealth {
  company: { id: number; name: string };
  health_score: number | null;
  health_status: string;
  metrics?: Record<string, { score?: number | null; weight?: number }>;
  data_quality?: { available_weight?: number; renormalized?: boolean };
}

export interface PortfolioHealthData {
  value: number | null;
  display_value?: string | null;
  source_status: string;
  details?: { companies?: CompanyHealth[] };
}

export interface DecisionQueueData {
  value: number;
  display_value?: string | null;
  source_status: string;
  details?: { items?: DecisionQueueItem[]; total_value?: number };
}

export interface DecisionQueueItem {
  id: string;
  title: string;
  priority: 'urgent' | 'high' | 'medium' | 'low';
  requested_by?: { id?: number | null; name?: string | null };
  created_at?: string | null;
  status?: string;
}

const withParams = (params?: Record<string, string | number | undefined>) => ({
  params: Object.fromEntries(Object.entries(params || {}).filter(([, value]) => value !== undefined)),
});

const getEnvelope = async <T>(path: string, period?: string): Promise<MetricEnvelope<T>> => {
  const response = await api.get<MetricEnvelope<T>>(path, withParams({ period }));
  return response.data;
};

export const executiveMetricsApi = {
  getOverviewMetrics: (period?: string) =>
    getEnvelope<Record<string, DerivedBundleData[keyof DerivedBundleData]>>(
      '/api/super-ceo/overview/metrics?include=derived',
      period,
    ),
  getDerivedBundle: (period?: string) =>
    getEnvelope<DerivedBundleData>('/api/super-ceo/derived/bundle', period).then((envelope) => ({
      ...envelope,
      data: (envelope.data as DerivedBundleData & { bundle?: DerivedBundleData }).bundle || envelope.data,
    })),
  getActivityFeed: async (types?: string[]) => {
    const response = await api.get<MetricEnvelope<ExecutiveActivity[]>>(
      '/api/super-ceo/overview/activity-feed',
      withParams({ types: types?.length ? types.join(',') : undefined }),
    );
    return response.data;
  },
  getPortfolioHealth: (period?: string) =>
    getEnvelope<PortfolioHealthData>('/api/super-ceo/portfolio-health', period),
  getDecisionQueue: (period?: string) =>
    getEnvelope<DecisionQueueData>('/api/super-ceo/decision-queue', period),
  getStrategyOkrs: (period?: string) =>
    getEnvelope<StrategyOkrSummary>('/api/super-ceo/strategy/okrs', period),
  getPerformanceSummary: (period?: string) =>
    getEnvelope<PerformanceSummary>('/api/super-ceo/performance/summary', period),
  getDefinitions: () => getEnvelope<{ metrics: MetricDefinition[] }>('/api/super-ceo/metrics/definitions'),
  getUsers: async () => ({ data: (await api.get<{ users: SuperCeoUser[] }>('/api/super-admin/users')).data.users }),
  getCompanies: async () => ({ data: (await api.get<{ companies: SuperCeoCompany[] }>('/api/super-admin/companies')).data.companies }),
};
