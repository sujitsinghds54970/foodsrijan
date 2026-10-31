export type MetricSourceStatus = "complete" | "partial" | "empty" | "unavailable" | "error";

export interface MetricMetaScope {
  level: string;
  company_id?: number | null;
  brand_id?: number | null;
  branch_id?: number | null;
  department_id?: number | null;
  company_ids: number[];
}

export interface MetricEnvelope<T> {
  data: T;
  meta: {
    as_of: string;
    scope: MetricMetaScope;
    source_status: MetricSourceStatus;
    degradation_level: string;
    cache: { hit: boolean; ttl_seconds: number };
    sources: string[];
    missing_sources: string[];
    refresh_after_seconds: number;
  };
  errors: Array<{ message?: string; code?: string }>;
}

export interface DerivedMetric {
  value: number | string | Record<string, unknown> | null;
  display_value?: string | null;
  delta?: number | null;
  trend?: string | null;
  source: string;
  source_status: MetricSourceStatus;
  as_of: string;
  confidence_level?: string;
  reconciled?: boolean | null;
  unit?: string | null;
  metric_name?: string;
  computation_time_ms?: number | null;
  cache_hit?: boolean;
  query_params_hash?: string | null;
  details?: Record<string, unknown> | null;
  deduplication_status?: string | null;
}

export interface DerivedBundleData {
  group_revenue: DerivedMetric;
  revenue_trend: DerivedMetric;
  customer_metrics: DerivedMetric;
  critical_alerts: DerivedMetric;
  decision_queue: DerivedMetric;
  portfolio_health: DerivedMetric;
  cash_conversion: DerivedMetric;
}

export interface PortfolioHealthMetric extends DerivedMetric {
  value: number | null;
}

export interface DecisionQueueMetric extends DerivedMetric {
  value: number;
}

export interface OkrProgressMetric {
  id: string;
  title: string;
  owner: string;
  target: number;
  actual: number;
  progress: number;
  status: "on_track" | "watch" | "at_risk";
}

export interface StrategyOkrSummary {
  period?: string;
  summary?: {
    score: number | null;
    status: string;
    revenue_target: number | null;
  };
  okrs: OkrProgressMetric[];
  unavailable_reason?: string;
  next_action?: { label: string; route: string; available: boolean };
}

export interface PerformanceSummary {
  period: string;
  metrics: {
    revenue: number | null;
    portfolio_health: number | null;
    active_customers: number | null;
    critical_alerts: number | null;
    cash_conversion: number | null;
  };
  status: "healthy" | "watch" | "critical";
  summary: string;
}

export interface MetricDefinition {
  name: string;
  label: string;
  description: string;
  authority: string;
  source_tables: string[];
  refresh_cadence_seconds: number;
  required_scopes: string[];
  owner: string;
  unit: string;
  supports_delta: boolean;
  supports_sparkline: boolean;
  unavailable_reason?: string | null;
  depends_on?: string[];
  related_metrics?: string[];
  sample_query?: string | null;
  icon_hint?: string;
}
