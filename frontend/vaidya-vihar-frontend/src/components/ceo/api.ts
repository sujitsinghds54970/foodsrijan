import axios from 'axios'

const rawApiBase =
  (process as any).env.REACT_APP_API_BASE_URL ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

// Normalize localhost to 127.0.0.1 in local dev to avoid mixed-origin CORS mismatches.
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? String(rawApiBase).replace('://localhost', '://127.0.0.1')
  : rawApiBase

export interface BehavioralMetricsPayload {
  sample_window_seconds: number
  mouse: {
    move_count: number
    total_distance: number
    average_speed: number
  }
  keystroke: {
    key_count: number
    average_interval_ms: number
    rhythm_variance_ms: number
  }
  scroll: {
    event_count: number
    total_delta: number
    average_burst: number
  }
}

export interface BehavioralAnalyzeResponse {
  step_up_required: boolean
  deviation_percent: number
  risk_level: 'low' | 'medium' | 'high' | string
  message: string
}

export interface CeoDashboardResponse {
  generated_at: string
  kpis: {
    financial: {
      title: string
      revenue_today: number
      revenue_month: number
      expense_month: number
      net_month: number
    }
    operational: {
      title: string
      daily_entries_today: number
      tests_processed_today: number
      average_tat_minutes: number
      machine_utilization_percent: number
    }
    sales: {
      title: string
      new_patients_month: number
      appointments_month: number
      doctor_referrals_total: number
      patient_visits_total: number
    }
    people: {
      title: string
      active_staff: number
      inactive_staff: number
      present_today: number
      attendance_rate: number
      attrition_rate: number
      pending_leave_requests: number
    }
    risk: {
      title: string
      risk_score: number
      pending_license_renewals: number
      pending_statutory_compliance: number
      break_glass_events_7d: number
    }
  }
  charts: {
    revenue_trend: Array<{ label: string; value: number }>
    financial_daily_revenue: Array<{ label: string; value: number }>
    financial_branch_revenue: Array<{ branch_id: number; branch_name: string; revenue: number; expense: number; net: number }>
    ops_mix: Array<{ label: string; value: number }>
    sales_mix: Array<{ label: string; value: number }>
    people_mix: Array<{ label: string; value: number }>
    risk_mix: Array<{ label: string; value: number }>
  }
  sales_branch_breakdown: Array<{ branch_id: number; branch_name: string; doctor_referrals: number; patient_visits: number }>
  highlights: string[]
}

export interface CeoAskNlpResponse {
  query: string
  intent: string
  answer: string
  data_points: Array<{ label: string; value: number }>
  suggestions: string[]
  generated_at: string
}

export interface CeoMasterDataBranch {
  id: number
  name: string
  city: string
  state: string
  phone: string
}

export interface CeoApprovalItem {
  request_id: number
  branch: string
  amount: number
  reason: string
  status: 'pending' | 'approved' | 'rejected' | string
}

export interface CeoExecutiveItem {
  name: string
  branch: string
  revenue: number
  staff_attrition_percent: number
  patient_count: number
}

export interface CeoSimulationResponse {
  target_city: string
  breakeven_months: number
  projected_annual_revenue: number
  risk_factor: 'Low' | 'Medium' | 'High' | string
}

export interface CeoDailyBriefResponse {
  date: string
  brief: string
}

export interface CeoBrandingResponse {
  company_name: string
  legal_name: string
  registration_number: string
  tagline: string
  description: string
  contact_info: {
    address: string
    phone: string
    email: string
    website: string
  }
  social_media_links: {
    facebook: string
    instagram: string
    linkedin: string
    x: string
  }
  assets: {
    primary_logo_url: string
    favicon_url: string
    app_icon_url: string
    background_banner_url: string
  }
}

export interface CeoMfaStatusResponse {
  enabled: boolean
  last_otp_verified_at: string | null
}

export interface CeoSessionRow {
  session_id: string
  device_id: string
  ip_address: string
  user_agent: string
  last_active: string | null
  created_at: string | null
}

export interface CeoAuditLogRow {
  id: number
  action: string
  http_method: string
  endpoint: string
  response_status: number
  created_at: string | null
  request_meta: Record<string, any>
}

export interface CeoRetentionPolicyResponse {
  enabled: boolean
  retention_days: number
}

export interface CeoSystemHealthResponse {
  branches_status: { online: number; offline: number }
  critical_integrations: Array<{ name: string; status: string }>
  server_db_health: {
    cpu_percent: number
    memory_percent: number
    storage_percent: number
    last_backup_at: string
  }
  global_activity_feed: Array<{ id: number; event: string; timestamp: string | null }>
}

export interface CeoGlobalSettingsResponse {
  currency: string
  timezone: string
  language: string
  financial_year: string
  tax_gst_settings: { gst_enabled?: boolean; gst_percent?: number; [key: string]: any }
  notification_preferences: { email?: boolean; sms?: boolean; in_app?: boolean; [key: string]: any }
}

export interface CeoPolicyItem {
  id: number
  policy_type: 'leave_attendance' | 'expense' | 'data_privacy' | string
  title: string
  content: string
  effective_from?: string | null
  published: boolean
  published_at?: string | null
  published_by?: number | null
  created_at?: string
  updated_at?: string
}

export interface CeoMasterSummaryResponse {
  total_branches: number
  total_users: number
  total_patients: number
}

export interface CeoUserDirectoryRow {
  id: string
  name: string
  username: string
  email: string
  role: string
  branch: string
  status: string
  source: 'users' | 'patients' | string
}

export interface CeoProactiveInsightsResponse {
  financial_risk: string
  operational_risk: string
  opportunity: string
  board_agenda_item: string
}

export interface CeoPeopleHealthScoreResponse {
  is_mock: boolean
  score: number
  trend: string
  drivers: {
    engagement: number
    attrition: number
    leadership: number
  }
  monthly_trend: Array<{
    month: string
    score: number
  }>
  benchmark: {
    industry_average: number
    our_score: number
  }
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleTalentRetentionResponse {
  is_mock: boolean
  headcount: {
    total: number
    by_branch: Array<{ name: string; count: number }>
    by_department: Array<{ name: string; count: number }>
  }
  attrition_retention: {
    ytd_attrition_percent: number
    retention_rate_percent: number
    by_branch: Array<{ name: string; attrition: number; retention: number }>
    by_department: Array<{ name: string; attrition: number; retention: number }>
    by_role: Array<{ name: string; attrition: number; retention: number }>
  }
  hiring_velocity: {
    avg_time_to_hire_days: number
    avg_time_to_fill_days: number
    critical_roles: Array<{ role: string; days_to_fill: number }>
  }
  quality_of_hire: {
    six_month_avg_rating: number
    new_hires_evaluated: number
  }
  open_positions: Array<{
    role: string
    branch: string
    department: string
    critical: boolean
  }>
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleEngagementCultureResponse {
  is_mock: boolean
  enps: {
    score: number
    description: string
  }
  engagement_index: {
    score: number
    source: string
  }
  recognition_feed: Array<{
    id: number
    timestamp: string
    actor: string
    message: string
    source: string
  }>
  pulse_survey_results: Array<{
    theme: string
    positive: number
    negative: number
  }>
  branch_effect: Array<{
    name: string
    engagement: number
  }>
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleLeadershipDevelopmentResponse {
  is_mock: boolean
  leadership_pipeline: Array<{
    level: string
    count: number
  }>
  manager_effectiveness: Array<{
    branch: string
    engagement_score: number
    retention_score: number
    overall_score: number
  }>
  internal_promotion_rate_percent: number
  skills_gap_analysis: string[]
  hipo_talent_pool: Array<{
    employee_id: string
    name: string
    branch: string
    role: string
    readiness: string
  }>
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleWorkforceProductivityResponse {
  is_mock: boolean
  revenue_per_employee: number
  total_workforce_cost: number
  workforce_cost_percent_of_revenue: number
  branch_cost_comparison: Array<{
    branch: string
    revenue: number
    workforce_cost: number
  }>
  labor_cost_forecast: Array<{
    month: string
    forecast_cost: number
  }>
  forecast_notes: string
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleDeiResponse {
  is_mock: boolean
  workforce_demographics: {
    gender: Array<{ name: string; value: number }>
    age: Array<{ name: string; value: number }>
    ethnicity: Array<{ name: string; value: number }>
  }
  dei_scorecard: {
    score: number
    representation_score: number
    pay_equity_score: number
    inclusion_score: number
  }
  pay_equity_analysis: Array<{
    role: string
    gender_or_ethnicity: string
    avg_pay: number
  }>
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleWowFeaturesResponse {
  is_mock: boolean
  ceo_daily_pulse: string
  flight_risk_employees: Array<{
    employee_id: string
    name: string
    branch: string
    role: string
    tenure_months: number
    engagement_score: number
    risk_level: 'high' | 'medium' | 'low' | string
  }>
  culture_heatmap: Array<{
    branch: string
    department: string
    engagement_score: number
  }>
  default_what_if: {
    input: string
    attrition_impact_percent: number
    workforce_cost_impact_percent: number
    estimated_monthly_cost_increase: number
    summary: string
  }
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPeopleWhatIfResponse {
  is_mock: boolean
  input: string
  role_name: string
  salary_increase_percent: number
  attrition_impact_percent: number
  workforce_cost_impact_percent: number
  estimated_monthly_cost_increase: number
  summary: string
  table_reference: {
    staff_profiles_count: number
    payroll_runs_count: number
    attendance_logs_count: number
    branches_count: number
    generated_at: string
  }
}

export interface CeoFinanceHealthScoreResponse {
  is_mock: boolean
  score: number
  color: 'green' | 'yellow' | 'red' | string
  drivers: {
    revenue_growth: number
    cash_flow: number
    profitability: number
  }
  monthly_health_trend: Array<{
    month: string
    score: number
  }>
  monthly_revenue_vs_expense: Array<{
    month: string
    revenue: number
    expense: number
  }>
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceCashLiquidityResponse {
  is_mock: boolean
  cash_position: {
    cash_in_hand: number
    cash_in_bank: number
    total_available_liquidity: number
  }
  forecast_30_60_90: Array<{
    day: string
    inflow: number
    outflow: number
  }>
  cash_burn_rate_per_month: number
  runway_months: number
  liquidity_threshold: number
  zero_balance_alert: {
    enabled: boolean
    message: string
  }
  operating_cash_flow: {
    value: number
    score: number
  }
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceProfitabilityRevenueResponse {
  is_mock: boolean
  consolidated_pnl: {
    current_month: {
      revenue: number
      expenses: number
      net_profit: number
    }
    ytd: {
      revenue: number
      expenses: number
      net_profit: number
    }
  }
  branch_profitability: Array<{
    branch: string
    revenue: number
    expenses: number
    net_profit: number
  }>
  test_profitability: Array<{
    test_type: string
    profitability: number
  }>
  revenue_per_unit: {
    avg_revenue_per_patient: number
    avg_revenue_per_test: number
  }
  ebitda: {
    value: number
    margin_percent: number
  }
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceReceivablesCycleResponse {
  is_mock: boolean
  ar_aging: Array<{
    bucket: string
    amount: number
  }>
  collection_effectiveness_index_percent: number
  bad_debt_ratio_percent: number
  insurance_vs_self_pay_mix: Array<{
    payer_type: string
    value: number
  }>
  days_sales_outstanding: number
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceCostControlResponse {
  is_mock: boolean
  expense_breakdown: Array<{
    category: string
    amount: number
  }>
  branch_cost_comparison: Array<{
    branch: string
    cost: number
  }>
  cost_per_unit: {
    avg_cost_per_test: number
    avg_cost_per_patient: number
  }
  vendor_spend_analysis: Array<{
    vendor: string
    category: string
    total_spend: number
  }>
  cost_to_income_ratio_percent: number
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceComplianceTaxationResponse {
  is_mock: boolean
  tax_compliance: Array<{
    tax_type: string
    status: string
    period: string
    due_date: string
  }>
  pf_esi_compliance: Array<{
    compliance_type: string
    employee_contribution: number
    employer_contribution: number
    due_date: string
    status: string
  }>
  license_tracker: Array<{
    license_name: string
    expiry_date: string
    status: string
    renewal_alert: boolean
  }>
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinancePredictiveAnalyticsResponse {
  is_mock: boolean
  revenue_forecast: Array<{
    month: string
    projected_revenue: number
  }>
  profitability_forecast: Array<{
    month: string
    projected_net_profit: number
  }>
  risk_alerts: Array<{
    severity: 'high' | 'medium' | 'low' | string
    title: string
    message: string
  }>
  automated_financial_commentary: string
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceDoctorReferralFinancialsResponse {
  is_mock: boolean
  referral_revenue_breakdown: Array<{
    doctor_name: string
    revenue: number
  }>
  doctor_commission_tracking: Array<{
    doctor_name: string
    referred_revenue: number
    commission_percent: number
    commission_earned: number
  }>
  referral_cost_percent_of_revenue: number
  doctor_wise_profitability: Array<{
    doctor_name: string
    revenue: number
    referral_cost: number
    service_cost: number
    net_profit: number
  }>
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceCfoBriefingResponse {
  is_mock: boolean
  title: string
  generated_at: string
  brief: string
  highlights: Array<{
    label: string
    value: string
  }>
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceBranchProfitabilityHeatmapResponse {
  is_mock: boolean
  items: Array<{
    branch: string
    profitability_score: number
    status: 'profitable' | 'break_even' | 'loss_making' | string
  }>
  legend: {
    profitable: string
    break_even: string
    loss_making: string
  }
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoFinanceWhatIfSimulatorResponse {
  is_mock: boolean
  scenario: string
  inputs: {
    city: string
    discount_percent: number
  }
  projections: {
    projected_revenue_impact_percent: number
    projected_cost_impact_percent: number
    projected_net_profit_impact_percent: number
    estimated_monthly_revenue_delta: number
    estimated_monthly_cost_delta: number
  }
  ai_summary: string
  table_reference: {
    daily_entries: number
    expense_entries: number
    payroll_runs: number
    branches: number
    inventory_items: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoDoctorNetworkHealthResponse {
  is_mock: boolean
  score: number
  total_doctors: number
  growth_mom_percent: number
  revenue_contribution_percent: number
  engagement_score: number
  attrition_risk_percent: number
  regional_density: Array<{
    region: string
    doctor_count: number
  }>
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoDoctorPerformanceAnalyticsResponse {
  is_mock: boolean
  leaderboard: Array<{
    doctor_id: number
    doctor_name: string
    branch: string
    specialty: string
    time_period: string
    total_referrals: number
    revenue_generated: number
    commission_earned: number
    conversion_rate_percent: number
  }>
  referral_trend: {
    network: Array<{
      month: string
      referrals: number
    }>
    by_doctor: Array<{
      doctor_id: number
      doctor_name: string
      points: Array<{
        month: string
        referrals: number
      }>
    }>
  }
  referral_leakage_alerts: Array<{
    doctor_id: number
    doctor_name: string
    branch: string
    decline_percent: number
    message: string
  }>
  patient_conversion_rate_percent: number
  test_mix: Array<{
    test_type: string
    value: number
  }>
  doctor_summaries: Array<{
    doctor_id: number
    doctor_name: string
    total_referrals: number
    revenue_generated: number
    commission_earned: number
    interaction_history: string[]
  }>
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoDoctorFinancialCommissionResponse {
  is_mock: boolean
  commission_dashboard: Array<{
    doctor_id: number
    doctor_name: string
    earned: number
    paid: number
    pending: number
  }>
  referral_cost_percent_of_revenue: number
  doctor_profitability: Array<{
    doctor_id: number
    doctor_name: string
    revenue: number
    referral_cost: number
    service_cost: number
    net_profit: number
  }>
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoDoctorCommissionSimulatorResponse {
  is_mock: boolean
  structure: string
  base_commission_percent: number
  projections: {
    projected_referral_growth_percent: number
    projected_commission_cost_growth_percent: number
    projected_profitability_impact_percent: number
    estimated_monthly_revenue_delta: number
    estimated_monthly_commission_delta: number
  }
  ai_summary: string
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
}

export interface CeoDoctorPayoutAutomationResponse {
  is_mock: boolean
  generated_at: string
  run_id: string
  status: string
  statements_generated: number
  payouts_queued: number
  total_payout_amount: number
  message: string
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
}

export interface CeoDoctorEngagementRelationshipResponse {
  is_mock: boolean
  doctor_profiles: Array<{
    doctor_id: number
    doctor_name: string
    specialty: string
    branch: string
    engagement_score: number
    last_interaction: string
    preferred_channel: string
  }>
  engagement_calendar: Array<{
    date: string
    event_type: string
    doctor_name: string
    notes: string
  }>
  flight_risk_doctors: Array<{
    doctor_id: number
    doctor_name: string
    risk_level: string
    reason: string
  }>
  doctor_nps_feedback: {
    nps_score: number
    positive_themes: string[]
    improvement_themes: string[]
  }
  communication_hub: {
    available: boolean
    message: string
  }
  white_label_portal: {
    available: boolean
    message: string
  }
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
}

export interface CeoDoctorGrowthAcquisitionResponse {
  is_mock: boolean
  market_opportunities: Array<{
    doctor_name: string
    city: string
    specialty: string
    estimated_monthly_referrals: number
  }>
  campaign_performance: Array<{
    campaign: string
    investment: number
    revenue_generated: number
    roi_percent: number
  }>
  competitor_leakage_report: Array<{
    doctor_name: string
    city: string
    estimated_leakage_percent: number
    competitor_hint: string
  }>
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
}

export interface CeoDoctorGrowthWhatIfResponse {
  is_mock: boolean
  scenario: string
  inputs: {
    specialty: string
    commission_increase_percent: number
  }
  projections: {
    projected_referral_volume_growth_percent: number
    projected_profitability_impact_percent: number
    estimated_monthly_revenue_delta: number
    estimated_monthly_commission_delta: number
  }
  ai_summary: string
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
}

export interface CeoDoctorOperationalExcellenceResponse {
  is_mock: boolean
  service_level_dashboard: {
    average_tat_hours: number
    sample_rejection_rate_percent: number
    report_quality_score: number
    tat_trend: Array<{
      week: string
      tat_hours: number
    }>
  }
  doctor_issue_tracker: Array<{
    issue_id: string
    doctor_name: string
    issue_type: string
    status: 'Open' | 'In Progress' | 'Resolved' | string
    updated_at: string
  }>
  patient_journey_completion_rate_percent: number
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoDoctorWowFeaturesResponse {
  is_mock: boolean
  doctor_360_briefing: {
    title: string
    message: string
  }
  smart_referral_alerts: Array<{
    severity: 'high' | 'medium' | 'low' | string
    title: string
    message: string
  }>
  doctor_loyalty_program: {
    tiers: Array<{
      name: 'Silver' | 'Gold' | 'Platinum' | string
      qualifies: string[]
      criteria: string
    }>
  }
  table_reference: {
    doctor_profiles_count: number
    referral_logs_count: number
    daily_entries_count: number
    commission_configured_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientOverviewResponse {
  is_mock: boolean
  total_patients: number
  growth: {
    mom_percent: number
    yoy_percent: number
  }
  new_vs_returning: {
    new: number
    returning: number
  }
  patient_acquisition_cost: number
  patient_lifetime_value: number
  referral_source_analysis: Array<{
    source: string
    patients: number
  }>
  monthly_growth_trend: Array<{
    month: string
    patients: number
  }>
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientJourneyExperienceResponse {
  is_mock: boolean
  journey_funnel: Array<{
    stage: string
    value: number
  }>
  average_time_to_test_hours: number
  no_show_rate_percent: number
  average_tat_hours: number
  report_viewing_rate_percent: number
  patient_nps_score: number
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientRetentionLoyaltyResponse {
  is_mock: boolean
  retention_rate_percent: number
  churn_rate_percent: number
  repeat_visit_rate: number
  reactivation_rate_percent: number
  loyalty_program: {
    enrollment_rate_percent: number
    redemption_rate_percent: number
    repeat_visit_uplift_percent: number
  }
  patient_health_score: number
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientSegmentationHealthResponse {
  is_mock: boolean
  demographics: {
    age: Array<{ group: string; value: number }>
    gender: Array<{ group: string; value: number }>
    location: Array<{ group: string; value: number }>
  }
  segment_by_condition: Array<{ condition: string; patients: number }>
  segment_by_value: Array<{ segment: string; patients: number }>
  geographic_density: Array<{ zone: string; density_score: number }>
  population_health_insights: string[]
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientFinancialAnalyticsResponse {
  is_mock: boolean
  revenue_by_segment: Array<{ segment: string; revenue: number }>
  revenue_per_patient: number
  average_order_value: number
  payer_mix: Array<{ payer: string; value: number }>
  collection_effectiveness_percent: number
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientPredictiveInsightsResponse {
  is_mock: boolean
  churn_risk_patients: Array<{
    patient_id: string
    name: string
    risk_score: number
    reason: string
  }>
  plv_prediction_by_segment: Array<{
    segment: string
    predicted_plv: number
  }>
  automated_patient_briefing: string
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoPatientPredictiveWhatIfResponse {
  is_mock: boolean
  scenario: string
  inputs: {
    condition: string
    city: string
    discount_percent: number
  }
  projections: {
    projected_patient_volume_uplift_percent: number
    projected_revenue_impact_percent: number
    estimated_monthly_patient_delta: number
    estimated_monthly_revenue_delta: number
  }
  ai_summary: string
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
}

export interface CeoPatientWowFeaturesResponse {
  is_mock: boolean
  patient_360_profiles: Array<{
    patient_id: string
    name: string
    interactions: string[]
    tests: string[]
    reports: string[]
    feedback: string
    journey_timeline: Array<{
      date: string
      event: string
    }>
  }>
  voice_of_patient_feed: Array<{
    source: string
    message: string
    sentiment: 'positive' | 'neutral' | 'negative' | string
    time: string
  }>
  growth_opportunity_assistant: string[]
  table_reference: {
    daily_entries_count: number
    patient_profiles_count: number
    appointments_count: number
    lis_results_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryHealthScoreResponse {
  is_mock: boolean
  score: number
  stock_availability_rate_percent: number
  expiry_risk_dashboard: Array<{
    item_name: string
    branch: string
    batch_number: string
    days_to_expiry: number
    risk_level: string
    current_stock: number
  }>
  wastage: {
    rate_percent: number
    cost: number
  }
  inventory_turnover_ratio: number
  days_on_hand: number
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryStockConsumptionResponse {
  is_mock: boolean
  multi_location_stock_view: Array<{
    branch: string
    item_name: string
    current_stock: number
    reorder_point: number
  }>
  daily_consumption_monitoring: {
    high_value_items: Array<{ day: string; actual_usage: number; expected_usage: number }>
    fast_moving_items: Array<{ day: string; actual_usage: number; expected_usage: number }>
  }
  high_value_reagent_movement: Array<{
    reagent_name: string
    used_by: string
    used_on: string
    test_name: string
    quantity: number
    branch: string
  }>
  inventory_velocity_mix: Array<{
    category: string
    value: number
  }>
  stockout_alerts: Array<{
    item_name: string
    branch: string
    current_stock: number
    reorder_point: number
    severity: 'high' | 'medium' | 'low' | string
  }>
  min_max_stock_levels: Array<{
    item_name: string
    branch: string
    minimum_stock: number
    maximum_stock: number
    current_stock: number
  }>
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryProcurementVendorResponse {
  is_mock: boolean
  procurement_dashboard: Array<{
    po_number: string
    vendor_name: string
    branch: string
    status: string
    expected_delivery_date: string
    order_value: number
  }>
  vendor_performance_scorecard: Array<{
    vendor_name: string
    on_time_delivery_rate_percent: number
    rejection_rate_percent: number
    pricing_competitiveness_score: number
    responsiveness_score: number
  }>
  jit_reorder_suggestions: Array<{
    item_name: string
    suggested_reorder_qty: number
    confidence_percent: number
    reason: string
  }>
  supplier_diversification_risk: Array<{
    item_name: string
    criticality: string
    active_suppliers: number
    risk_level: string
  }>
  sku_rationalization: Array<{
    sku_group: string
    items_in_group: number
    recommended_action: string
    estimated_monthly_savings: number
  }>
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryLogisticsColdChainResponse {
  is_mock: boolean
  cold_chain_monitoring: {
    active_shipments: number
    within_range_percent: number
    temperature_alerts: Array<{
      shipment_id: string
      route: string
      current_temp_c: number
      allowed_range: string
      severity: 'high' | 'medium' | 'low' | string
    }>
  }
  sample_specimen_logistics: Array<{
    sample_id: string
    from_branch: string
    to_lab: string
    courier_status: string
    estimated_arrival: string
  }>
  branch_logistics_performance: Array<{
    branch: string
    avg_delivery_time_minutes: number
    sample_rejection_rate_percent: number
    courier_performance_score: number
  }>
  fleet_route_optimization: {
    status: string
    message: string
  }
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryFinancialImpactResponse {
  is_mock: boolean
  inventory_carrying_cost: number
  inventory_cost_per_test: number
  vendor_spend_analysis: Array<{
    vendor_name: string
    category: string
    branch: string
    spend: number
  }>
  procurement_savings_tracker: {
    savings_realized: number
    negotiation_savings: number
    bulk_purchase_savings: number
    sku_rationalization_savings: number
  }
  budget_vs_actual_inventory: Array<{
    month: string
    budget: number
    actual: number
  }>
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryComplianceQualityResponse {
  is_mock: boolean
  lot_batch_traceability: Array<{
    item_name: string
    lot_number: string
    received_on: string
    used_on: string
    branch: string
    used_for_test: string
  }>
  expiry_recall_management: {
    expiring_alerts: Array<{
      item_name: string
      branch: string
      days_to_expiry: number
      severity: 'high' | 'medium' | 'low' | string
    }>
    regulatory_recall_feed: Array<{
      recall_id: string
      item_name: string
      status: string
      advisory: string
    }>
  }
  supplier_item_certification_tracker: Array<{
    entity_type: string
    name: string
    certification: string
    status: string
    expiry_date: string
  }>
  audit_trail: Array<{
    timestamp: string
    activity_type: string
    item_name: string
    performed_by: string
    notes: string
  }>
  reagent_consumable_quality_tracking: Array<{
    item_name: string
    issue_type: string
    complaint_count: number
    last_reported_on: string
    status: string
  }>
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryPredictiveIntelligenceResponse {
  is_mock: boolean
  demand_forecasting: Array<{
    month: string
    pcr_reagent_demand: number
    edta_tube_demand: number
    contrast_media_demand: number
  }>
  expiry_prediction_prevention: Array<{
    item_name: string
    risk_score: number
    branch: string
    suggested_action: string
  }>
  supply_chain_risk_alerts: Array<{
    severity: 'high' | 'medium' | 'low' | string
    title: string
    message: string
  }>
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoInventoryPredictiveWhatIfResponse {
  is_mock: boolean
  scenario: string
  inputs: {
    current_supplier: string
    new_supplier: string
    item_category: string
  }
  projected_impact: {
    cost_change_percent: number
    availability_change_percent: number
    on_time_delivery_change_percent: number
    estimated_monthly_savings: number
  }
  ai_summary: string
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
}

export interface CeoInventoryWowFeaturesResponse {
  is_mock: boolean
  digital_control_tower: {
    overall_supply_chain_status: string
    active_alerts: number
    critical_stockouts: number
    in_transit_shipments: number
    expiring_within_7_days: number
    today_wastage_cost: number
  }
  zero_waste_ai_assistant: string[]
  supplier_health_scores: Array<{
    supplier_name: string
    health_score: number
    delivery_score: number
    quality_score: number
    financial_stability_score: number
  }>
  automated_inventory_briefing: string
  table_reference: {
    inventory_items_count: number
    branches_count: number
    daily_entries_count: number
    suppliers_count: number
    audit_logs_count: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceHealthScoreResponse {
  is_mock: boolean
  score: number
  status: string
  risk_exposure: 'Low' | 'Medium' | 'High' | string
  compliance_status_by_category: Array<{
    category: string
    score: number
    status: string
  }>
  score_trend: Array<{
    month: string
    score: number
  }>
  days_since_last_audit_by_branch: Array<{
    branch: string
    days_since_last_audit: number
  }>
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceLicenseAccreditationResponse {
  is_mock: boolean
  license_accreditation_dashboard: Array<{
    branch: string
    license_type: string
    license_id: string
    status: string
    expiry_date: string
    renewal_application_status: string
  }>
  auto_renewal_alerts: Array<{
    license_id: string
    branch: string
    days_to_expiry: number
    alert_window: string
    renewal_application_status: string
  }>
  nabl_accreditation_tracker: {
    current_status: string
    document_submission_date: string
    assessment_date: string
    non_conformance_resolution: string
    open_non_conformances: number
  }
  professional_license_tracking: Array<{
    name: string
    role: string
    license_number: string
    status: string
    expiry_date: string
  }>
  equipment_certification_calibration: Array<{
    equipment_name: string
    branch: string
    certification_status: string
    calibration_due_date: string
    last_calibrated_on: string
  }>
  document_repository: {
    status: string
    description: string
    placeholder_note: string
  }
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceRegulatoryStatutoryResponse {
  is_mock: boolean
  regulatory_compliance_dashboard: Array<{
    regulation: string
    compliance_percent: number
    status: string
  }>
  statutory_filing_tracker: Array<{
    filing_type: string
    period: string
    due_date: string
    status: string
  }>
  glp_compliance: {
    score: number
    status: string
    open_observations: number
    last_internal_review: string
  }
  biomedical_waste_management: {
    segregation_score: number
    storage_score: number
    disposal_score: number
    composite_status: string
  }
  regulatory_change_monitor: Array<{
    severity: 'high' | 'medium' | 'low' | string
    title: string
    impact: string
  }>
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceLegalContractResponse {
  is_mock: boolean
  contract_lifecycle_management: Array<{
    contract_id: string
    contract_type: string
    counterparty: string
    start_date: string
    expiry_date: string
    status: string
  }>
  auto_contract_renewal_alerts: Array<{
    contract_id: string
    days_to_expiry: number
    renewal_deadline: string
    status: string
  }>
  key_terms_extraction: Array<{
    contract_id: string
    termination_clause: string
    payment_terms: string
    liability_limit: string
    confidentiality: string
  }>
  legal_case_tracker: Array<{
    case_id: string
    matter: string
    counterparty: string
    stage: string
    next_hearing_or_action_date: string
    status: string
  }>
  policy_attestation_management: Array<{
    policy_name: string
    employees_targeted: number
    employees_signed: number
    attestation_percent: number
    status: string
  }>
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceIncidentRiskResponse {
  is_mock: boolean
  incident_dashboard: Array<{
    incident_id: string
    category: string
    severity: string
    branch: string
    status: string
    reported_at: string
  }>
  incident_severity_resolution_time: Array<{
    severity: string
    incident_count: number
    avg_resolution_hours: number
  }>
  whistleblower_hotline: {
    enabled: boolean
    mode: string
    channels: string[]
    note: string
  }
  risk_register: Array<{
    risk_id: string
    risk_name: string
    likelihood: string
    impact: string
    mitigation_status: string
  }>
  complaint_analysis_trends: {
    top_recurring_themes: Array<{
      theme: string
      share_percent: number
    }>
    ai_summary: string
  }
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceAuditReadinessResponse {
  is_mock: boolean
  audit_schedule_calendar: Array<{
    audit_name: string
    audit_type: string
    branch: string
    scheduled_date: string
    status: string
  }>
  audit_trail_evidence_log: Array<{
    event_time: string
    activity: string
    owner: string
    evidence_id: string
  }>
  non_conformance_corrective_action_tracker: Array<{
    nc_id: string
    finding: string
    corrective_action: string
    owner: string
    target_date: string
    status: string
  }>
  pre_audit_checklist: Array<{
    item: string
    status: string
  }>
  inspection_report_repository: Array<{
    report_id: string
    inspection_name: string
    branch: string
    report_date: string
    status: string
  }>
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceDataPrivacySecurityResponse {
  is_mock: boolean
  data_privacy_dashboard: {
    consent_management_percent: number
    data_access_logs_reviewed_percent: number
    breach_incidents_open: number
    privacy_training_completion_percent: number
  }
  regulation_compliance_tracker: Array<{
    regulation: string
    adherence_percent: number
    status: string
  }>
  data_breach_incident_log: Array<{
    incident_id: string
    branch: string
    severity: string
    reported_on: string
    resolution_status: string
  }>
  data_retention_disposal_policy: {
    adherence_percent: number
    overdue_disposals: number
    last_policy_review: string
    status: string
  }
  security_training_completion: {
    overall_completion_percent: number
    employees_completed: number
    employees_total: number
    overdue_learners: number
  }
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoCompliancePredictiveIntelligenceResponse {
  is_mock: boolean
  compliance_risk_prediction: Array<{
    risk_area: string
    predicted_risk_score: number
    horizon_days: number
    recommended_action: string
  }>
  regulatory_change_impact_analysis: Array<{
    regulation_update: string
    operational_impact: string
    compliance_impact: string
    recommended_response: string
  }>
  incident_trend_prediction: {
    next_quarter_incident_forecast: {
      low: number
      medium: number
      high: number
      critical: number
    }
    predicted_hotspots: string[]
    preventive_measures: string[]
  }
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoCompliancePredictiveWhatIfResponse {
  is_mock: boolean
  inputs: {
    target_state: string
    branch_model: string
  }
  simulation: {
    licensing_complexity: string
    regulatory_readiness_time_weeks: number
    projected_compliance_setup_cost: number
    key_implications: string[]
    recommended_first_actions: string[]
  }
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoComplianceWowFeaturesResponse {
  is_mock: boolean
  compliance_control_tower: {
    overall_compliance_score: number
    open_license_renewals: number
    upcoming_audits_30d: number
    open_incidents: number
    active_regulatory_alerts: number
    status: string
  }
  automated_compliance_briefing: {
    cadence: string
    brief: string
  }
  regulatory_radar: {
    monitoring_status: string
    last_scan_at: string
    recent_changes_detected: number
    auto_updated_checklist_items: number
    highlights: string[]
  }
  digital_compliance_twin: {
    simulation_status: string
    coverage_scope: string
    current_posture_score: number
    change_simulation_note: string
    recent_simulation: {
      scenario: string
      projected_posture_score: number
      risk_delta: string
      advisory: string
    }
  }
  table_reference: {
    branches: number
    licenses: number
    audit_logs: number
    incidents: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsBrandingResponse {
  is_mock: boolean
  company_profile: {
    company_name: string
    legal_name: string
    registration_number: string
    tagline: string
    description: string
    contact_information: {
      address: string
      phone: string
      email: string
      website: string
    }
    social_media_links: {
      facebook: string
      instagram: string
      linkedin: string
      x: string
    }
  }
  branding_asset_manager: {
    primary_logo_web: string
    primary_logo_app: string
    favicon: string
    app_icon: string
    background_banner: string
    email_template: string
    report_template: string
  }
  brand_color_palette: {
    primary_color: string
    secondary_color: string
    accent_color: string
  }
  white_label_configuration: {
    enabled: boolean
    branches: Array<{
      branch_name: string
      subdomain: string
      logo: string
      theme: string
    }>
  }
  default_language_locale: {
    language: string
    date_format: string
    timezone: string
    currency: string
  }
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsSecurityResponse {
  is_mock: boolean
  ceo_fortified_authentication: {
    biometric_login_enabled: boolean
    webauthn_fido2_enabled: boolean
    enrollment_status: string
    hardware_security_keys: Array<{
      key_name: string
      registered_on: string
      last_used_on: string
    }>
  }
  global_password_policy: {
    minimum_length: number
    require_uppercase: boolean
    require_lowercase: boolean
    require_numbers: boolean
    require_special_characters: boolean
    expiration_days: number
  }
  mfa_policy: {
    mode: string
    enforced_for_roles: string[]
    optional_for_roles: string[]
  }
  session_inactivity_management: {
    auto_sign_out_minutes: number
    max_concurrent_sessions: number
  }
  ip_allowlisting_restriction: {
    enabled: boolean
    allowed_ips: string[]
  }
  audit_log_immutable: CeoAuditLogRow[]
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsFeatureFlagsResponse {
  is_mock: boolean
  feature_flag_dashboard: Array<{
    feature_key: string
    label: string
    category: string
    enabled: boolean
  }>
  module_activation: Array<{
    module: string
    enabled: boolean
  }>
  flag_categories: Array<{
    category: string
    description: string
    flags_count: number
    enabled_count: number
  }>
  flag_change_audit: Array<{
    timestamp: string
    user_id: number
    feature_key: string
    old_value: boolean
    new_value: boolean
  }>
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsIntegrationsApiResponse {
  is_mock: boolean
  lis_integration: {
    enabled: boolean
    api_key: string
    endpoint: string
    data_mapping: string
  }
  analyzer_device_integration: Array<{
    device_name: string
    device_type: string
    connection_type: string
    status: string
  }>
  payment_gateway_configuration: Array<{
    gateway: string
    provider: string
    enabled: boolean
    merchant_id: string
  }>
  communication_gateways: {
    sms: { provider: string; sender_id: string; enabled: boolean }
    email: { provider: string; from_email: string; enabled: boolean }
    whatsapp: { provider: string; business_number: string; enabled: boolean }
  }
  api_key_management: Array<{
    key_name: string
    masked_key: string
    status: string
    created_at: string
    last_used_at: string
  }>
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsBranchLocalizationResponse {
  is_mock: boolean
  multi_branch_configuration: Array<{
    branch_id: number
    branch_name: string
    address: string
    phone: string
    operating_hours: string
    timezone: string
    status: string
  }>
  branch_level_pricing_discounts: Array<{
    branch_name: string
    test_code: string
    price: number
    discount_percent: number
    package_rule: string
  }>
  branch_level_staff_permissions: Array<{
    branch_name: string
    role: string
    permissions: string[]
  }>
  central_test_catalog: Array<{
    test_code: string
    test_name: string
    category: string
    active: boolean
  }>
  branch_switching: {
    current_view_branch: string
    available_branches: string[]
    quick_switch_enabled: boolean
  }
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsDataComplianceResponse {
  is_mock: boolean
  data_retention_policy: {
    patient_data_retention_years: number
    test_results_retention_years: number
    audit_logs_retention_years: number
    auto_purge_enabled: boolean
  }
  data_anonymization_rules: {
    enabled: boolean
    mask_phone: boolean
    mask_email: boolean
    hash_patient_identifier: boolean
    reporting_dataset_salt_rotation_days: number
  }
  consent_management: {
    default_consent_form_version: string
    require_digital_signature: boolean
    consent_expiry_days: number
    tracking_enabled: boolean
  }
  regulatory_compliance: {
    dpdp_mode: string
    gdpr_mode: string
    hipaa_mode: string
    cross_border_transfer_restriction: boolean
  }
  backup_disaster_recovery: {
    automated_backup_enabled: boolean
    backup_frequency: string
    backup_retention_days: number
    dr_drill_frequency: string
    last_successful_backup: string
  }
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsAiAutomationResponse {
  is_mock: boolean
  ai_auto_validation_rules: {
    enabled: boolean
    max_reference_range_deviation_percent: number
    critical_result_requires_manual_review: boolean
    minimum_confidence_threshold: number
  }
  ai_delta_check_alerts: {
    enabled: boolean
    delta_percent_threshold: number
    lookback_days: number
    alert_channels: string[]
  }
  automated_report_delivery: {
    enabled: boolean
    whatsapp_enabled: boolean
    sms_enabled: boolean
    email_enabled: boolean
    delivery_window: string
  }
  predictive_analytics_settings: {
    demand_forecasting_enabled: boolean
    patient_churn_model_enabled: boolean
    inventory_optimization_enabled: boolean
    model_refresh_frequency: string
    drift_monitoring_enabled: boolean
  }
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsUiExperienceResponse {
  is_mock: boolean
  default_theme: {
    theme: string
    allow_user_override: boolean
    default_density: string
  }
  ui_element_visibility: {
    footer: boolean
    billing_history: boolean
    support_buttons: boolean
    help_center_widget: boolean
    quick_action_fab: boolean
  }
  dashboard_customization: {
    personalized_layouts_enabled: boolean
    draggable_widgets_enabled: boolean
    layout_presets: Array<{
      name: string
      widgets: string[]
      default_for_roles: string[]
    }>
  }
  role_specific_dashboards: Array<{
    role: string
    default_dashboard: string
    key_modules: string[]
  }>
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsMaintenanceHealthResponse {
  is_mock: boolean
  system_status_dashboard: {
    overall_status: string
    active_branches: {
      online: number
      degraded: number
      offline: number
    }
    critical_integrations: Array<{
      name: string
      status: string
      latency_ms: number
    }>
    database_health: {
      status: string
      replication_lag_seconds: number
      connections_used_percent: number
    }
    backup_status: {
      status: string
      last_successful_backup: string
    }
    last_refreshed_at: string
  }
  scheduled_jobs_automations: Array<{
    job_name: string
    job_type: string
    status: string
    last_run_time: string
    next_run_time: string
  }>
  maintenance_mode: {
    enabled: boolean
    user_facing_message: string
    planned_window: string
  }
  error_incident_log: Array<{
    id: string
    severity: string
    component: string
    message: string
    status: string
    occurred_at: string
    resolved_at: string | null
  }>
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsImportExportMigrationResponse {
  is_mock: boolean
  bulk_data_import: {
    supported_entities: string[]
    supported_formats: string[]
    last_import_jobs: Array<{
      job_id: string
      entity: string
      format: string
      status: string
      processed_records: number
      failed_records: number
      completed_at: string
    }>
    template_downloads: Array<{
      entity: string
      template_path: string
    }>
  }
  bulk_data_export: {
    available_exports: string[]
    default_format: string
    last_export_jobs: Array<{
      job_id: string
      dataset: string
      format: string
      status: string
      rows_exported: number
      completed_at: string
    }>
  }
  data_migration_tools: {
    legacy_connectors: Array<{
      connector_name: string
      source_type: string
      status: string
    }>
    migration_runs: Array<{
      run_id: string
      source_system: string
      target_module: string
      status: string
      migrated_records: number
      run_at: string
    }>
    validation_checks_enabled: boolean
    rollback_supported: boolean
  }
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export interface CeoSettingsWowFeaturesResponse {
  is_mock: boolean
  digital_constitution_version_control: {
    current_version: string
    version_history: Array<{
      version: string
      changed_by: string
      changed_at: string
      change_summary: string
    }>
    rollback_allowed: boolean
  }
  configuration_push: {
    last_push_at: string
    last_push_by: string
    target_branches: number
    last_push_status: string
    pending_changes_count: number
  }
  zero_downtime_feature_rollout: {
    enabled: boolean
    default_rollout_percent: number
    active_rollouts: Array<{
      feature_key: string
      current_percent: number
      status: string
    }>
  }
  automated_system_health_report: {
    enabled: boolean
    cadence: string
    last_generated_at: string
    summary: string
    kpi_snapshot: {
      uptime_percent: number
      open_incidents: number
      backup_success_rate_percent: number
      avg_api_latency_ms: number
    }
  }
  table_reference: {
    branches: number
    users: number
    audit_logs: number
    policies: number
    generated_at: string
  }
  future_data_mapping: Record<string, string>
}

export async function analyzeCeoBehavior(payload: BehavioralMetricsPayload): Promise<BehavioralAnalyzeResponse> {
  const response = await axios.post(`${API_BASE}/api/ceo/auth/behavioral-analyze`, payload)
  return response.data
}

export async function getCeoDashboard(): Promise<CeoDashboardResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/dashboard`)
  return response.data
}

export async function askCeoAssistant(query: string): Promise<CeoAskNlpResponse> {
  const response = await axios.post(`${API_BASE}/api/ceo/ask-nlp`, { query })
  return response.data
}

export async function getCeoMasterData(): Promise<{ branches: CeoMasterDataBranch[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/master-data`)
  return response.data
}

export async function createCeoBranch(payload: { name: string; city: string; state: string; phone: string }): Promise<{ created: boolean; branch: CeoMasterDataBranch }> {
  const response = await axios.post(`${API_BASE}/api/ceo/master-data`, payload)
  return response.data
}

export async function getCeoApprovals(): Promise<{ items: CeoApprovalItem[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/approvals`)
  return response.data
}

export async function decideCeoApproval(approvalId: number, status: 'approved' | 'rejected'): Promise<{ updated: boolean; request_id: number; status: string }> {
  const response = await axios.put(`${API_BASE}/api/ceo/approvals/${approvalId}`, { status })
  return response.data
}

export async function getCeoExecutives(): Promise<{ items: CeoExecutiveItem[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/executives`)
  return response.data
}

export async function simulateCeo(payload: { target_city: string; initial_investment: number; projected_staff_count: number }): Promise<CeoSimulationResponse> {
  const response = await axios.post(`${API_BASE}/api/ceo/simulate`, payload)
  return response.data
}

export async function getCeoDailyBrief(): Promise<CeoDailyBriefResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/daily-brief`)
  return response.data
}

export async function getCeoBranding(): Promise<CeoBrandingResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/branding`)
  return response.data
}

export async function updateCeoBranding(payload: FormData): Promise<CeoBrandingResponse> {
  const response = await axios.put(`${API_BASE}/api/ceo/branding`, payload, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function changeCeoPassword(payload: { current_password: string; new_password: string }): Promise<{ updated: boolean; message: string }> {
  const response = await axios.post(`${API_BASE}/api/ceo/auth/change-password`, payload)
  return response.data
}

export async function getCeoMfaStatus(): Promise<CeoMfaStatusResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/auth/mfa/status`)
  return response.data
}

export async function toggleCeoMfa(enabled: boolean): Promise<CeoMfaStatusResponse & { updated: boolean }> {
  const response = await axios.post(`${API_BASE}/api/ceo/auth/mfa/toggle`, { enabled })
  return response.data
}

export async function getCeoSessions(): Promise<{ sessions: CeoSessionRow[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/sessions`)
  return response.data
}

export async function logoutCeoSession(sessionId: string): Promise<{ logged_out: boolean; session_id: string }> {
  const response = await axios.delete(`${API_BASE}/api/ceo/sessions/${encodeURIComponent(sessionId)}`)
  return response.data
}

export async function getCeoAuditLog(limit = 10): Promise<{ items: CeoAuditLogRow[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/audit-log`, { params: { limit } })
  return response.data
}

export async function getCeoRetentionPolicy(): Promise<CeoRetentionPolicyResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/privacy/retention`)
  return response.data
}

export async function updateCeoRetentionPolicy(payload: CeoRetentionPolicyResponse): Promise<{ updated: boolean } & CeoRetentionPolicyResponse> {
  const response = await axios.put(`${API_BASE}/api/ceo/privacy/retention`, payload)
  return response.data
}

export async function getCeoSystemHealth(): Promise<CeoSystemHealthResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/system-health`)
  return response.data
}

export async function getCeoGlobalSettings(): Promise<CeoGlobalSettingsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/global-settings`)
  return response.data
}

export async function updateCeoGlobalSettings(payload: CeoGlobalSettingsResponse): Promise<{ updated: boolean } & CeoGlobalSettingsResponse> {
  const response = await axios.put(`${API_BASE}/api/ceo/global-settings`, payload)
  return response.data
}

export async function getCeoPolicies(): Promise<{ items: CeoPolicyItem[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/policies`)
  return response.data
}

export async function createCeoPolicy(payload: { policy_type: string; title: string; content: string; effective_from?: string }): Promise<{ created: boolean; item: CeoPolicyItem }> {
  const response = await axios.post(`${API_BASE}/api/ceo/policies`, payload)
  return response.data
}

export async function updateCeoPolicy(policyId: number, payload: { policy_type: string; title: string; content: string; effective_from?: string }): Promise<{ updated: boolean; item: CeoPolicyItem }> {
  const response = await axios.put(`${API_BASE}/api/ceo/policies/${policyId}`, payload)
  return response.data
}

export async function deleteCeoPolicy(policyId: number): Promise<{ deleted: boolean; policy_id: number }> {
  const response = await axios.delete(`${API_BASE}/api/ceo/policies/${policyId}`)
  return response.data
}

export async function publishCeoPolicy(policyId: number): Promise<{ published: boolean; policy_id: number; notified_employees: number; signature_mode: string }> {
  const response = await axios.post(`${API_BASE}/api/ceo/policies/${policyId}/publish`)
  return response.data
}

export async function getCeoMasterSummary(): Promise<CeoMasterSummaryResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/master-summary`)
  return response.data
}

export async function getCeoUsers(search = ''): Promise<{ items: CeoUserDirectoryRow[] }> {
  const response = await axios.get(`${API_BASE}/api/ceo/users`, { params: search ? { search } : {} })
  return response.data
}

export async function getCeoProactiveInsights(): Promise<CeoProactiveInsightsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/proactive-insights`)
  return response.data
}

export async function getCeoPeopleHealthScore(): Promise<CeoPeopleHealthScoreResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/health-score`)
  return response.data
}

export async function getCeoPeopleTalentRetention(): Promise<CeoPeopleTalentRetentionResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/talent-retention`)
  return response.data
}

export async function getCeoPeopleEngagementCulture(): Promise<CeoPeopleEngagementCultureResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/engagement-culture`)
  return response.data
}

export async function getCeoPeopleLeadershipDevelopment(): Promise<CeoPeopleLeadershipDevelopmentResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/leadership-development`)
  return response.data
}

export async function getCeoPeopleWorkforceProductivity(): Promise<CeoPeopleWorkforceProductivityResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/workforce-productivity`)
  return response.data
}

export async function getCeoPeopleDei(): Promise<CeoPeopleDeiResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/dei`)
  return response.data
}

export async function getCeoPeopleWowFeatures(): Promise<CeoPeopleWowFeaturesResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/wow-features`)
  return response.data
}

export async function getCeoPeopleWhatIfSimulation(params: { role_name: string; salary_increase_percent: number }): Promise<CeoPeopleWhatIfResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/people/what-if-simulator`, { params })
  return response.data
}

export async function getCeoFinanceHealthScore(): Promise<CeoFinanceHealthScoreResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/health-score`)
  return response.data
}

export async function getCeoFinanceCashLiquidity(): Promise<CeoFinanceCashLiquidityResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/cash-liquidity`)
  return response.data
}

export async function getCeoFinanceProfitabilityRevenue(): Promise<CeoFinanceProfitabilityRevenueResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/profitability-revenue`)
  return response.data
}

export async function getCeoFinanceReceivablesCycle(): Promise<CeoFinanceReceivablesCycleResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/receivables-cycle`)
  return response.data
}

export async function getCeoFinanceCostControl(): Promise<CeoFinanceCostControlResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/cost-control`)
  return response.data
}

export async function getCeoFinanceComplianceTaxation(): Promise<CeoFinanceComplianceTaxationResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/compliance-taxation`)
  return response.data
}

export async function getCeoFinancePredictiveAnalytics(): Promise<CeoFinancePredictiveAnalyticsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/predictive-analytics`)
  return response.data
}

export async function getCeoFinanceDoctorReferralFinancials(): Promise<CeoFinanceDoctorReferralFinancialsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/doctor-referral-financials`)
  return response.data
}

export async function getCeoFinanceCfoBriefing(): Promise<CeoFinanceCfoBriefingResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/cfo-briefing`)
  return response.data
}

export async function getCeoFinanceBranchProfitabilityHeatmap(): Promise<CeoFinanceBranchProfitabilityHeatmapResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/branch-profitability-heatmap`)
  return response.data
}

export async function getCeoFinanceWhatIfSimulation(params: { city: string; discount_percent: number }): Promise<CeoFinanceWhatIfSimulatorResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/finance/what-if-simulator`, { params })
  return response.data
}

export async function getCeoDoctorNetworkHealth(): Promise<CeoDoctorNetworkHealthResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/network-health`)
  return response.data
}

export async function getCeoDoctorPerformanceAnalytics(): Promise<CeoDoctorPerformanceAnalyticsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/performance-analytics`)
  return response.data
}

export async function getCeoDoctorFinancialCommission(): Promise<CeoDoctorFinancialCommissionResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/financial-commission`)
  return response.data
}

export async function getCeoDoctorCommissionSimulation(params: { structure: string; base_commission_percent: number }): Promise<CeoDoctorCommissionSimulatorResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/commission-simulator`, { params })
  return response.data
}

export async function triggerCeoDoctorPayoutAutomation(): Promise<CeoDoctorPayoutAutomationResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/commission-payout-automation`)
  return response.data
}

export async function getCeoDoctorEngagementRelationship(): Promise<CeoDoctorEngagementRelationshipResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/engagement-relationship`)
  return response.data
}

export async function getCeoDoctorGrowthAcquisition(): Promise<CeoDoctorGrowthAcquisitionResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/growth-acquisition`)
  return response.data
}

export async function getCeoDoctorGrowthWhatIfSimulation(params: { specialty: string; commission_increase_percent: number }): Promise<CeoDoctorGrowthWhatIfResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/growth-what-if-simulator`, { params })
  return response.data
}

export async function getCeoDoctorOperationalExcellence(): Promise<CeoDoctorOperationalExcellenceResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/operational-excellence`)
  return response.data
}

export async function getCeoDoctorWowFeatures(): Promise<CeoDoctorWowFeaturesResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/doctors/wow-features`)
  return response.data
}

export async function getCeoPatientOverview(): Promise<CeoPatientOverviewResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/overview`)
  return response.data
}

export async function getCeoPatientJourneyExperience(): Promise<CeoPatientJourneyExperienceResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/journey-experience`)
  return response.data
}

export async function getCeoPatientRetentionLoyalty(): Promise<CeoPatientRetentionLoyaltyResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/retention-loyalty`)
  return response.data
}

export async function getCeoPatientSegmentationHealth(): Promise<CeoPatientSegmentationHealthResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/segmentation-health`)
  return response.data
}

export async function getCeoPatientFinancialAnalytics(): Promise<CeoPatientFinancialAnalyticsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/financial-analytics`)
  return response.data
}

export async function getCeoPatientPredictiveInsights(): Promise<CeoPatientPredictiveInsightsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/predictive-insights`)
  return response.data
}

export async function getCeoPatientPredictiveWhatIfSimulation(params: { condition: string; city: string; discount_percent: number }): Promise<CeoPatientPredictiveWhatIfResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/predictive-what-if-simulator`, { params })
  return response.data
}

export async function getCeoPatientWowFeatures(): Promise<CeoPatientWowFeaturesResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/patients/wow-features`)
  return response.data
}

export async function getCeoInventoryHealthScore(): Promise<CeoInventoryHealthScoreResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/health-score`)
  return response.data
}

export async function getCeoInventoryStockConsumptionAnalytics(): Promise<CeoInventoryStockConsumptionResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/stock-consumption-analytics`)
  return response.data
}

export async function getCeoInventoryProcurementVendorManagement(): Promise<CeoInventoryProcurementVendorResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/procurement-vendor-management`)
  return response.data
}

export async function getCeoInventoryLogisticsColdChain(): Promise<CeoInventoryLogisticsColdChainResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/logistics-cold-chain`)
  return response.data
}

export async function getCeoInventoryFinancialImpactCostControl(): Promise<CeoInventoryFinancialImpactResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/financial-impact-cost-control`)
  return response.data
}

export async function getCeoInventoryComplianceQualityControl(): Promise<CeoInventoryComplianceQualityResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/compliance-quality-control`)
  return response.data
}

export async function getCeoInventoryPredictiveIntelligence(): Promise<CeoInventoryPredictiveIntelligenceResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/predictive-intelligence`)
  return response.data
}

export async function getCeoInventoryPredictiveWhatIfSimulation(params: { current_supplier: string; new_supplier: string; item_category: string }): Promise<CeoInventoryPredictiveWhatIfResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/predictive-what-if-simulator`, { params })
  return response.data
}

export async function getCeoInventoryWowFeatures(): Promise<CeoInventoryWowFeaturesResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/inventory/wow-features`)
  return response.data
}

export async function getCeoComplianceHealthScore(): Promise<CeoComplianceHealthScoreResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/health-score`)
  return response.data
}

export async function getCeoComplianceLicenseAccreditationManagement(): Promise<CeoComplianceLicenseAccreditationResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/license-accreditation-management`)
  return response.data
}

export async function getCeoComplianceRegulatoryStatutory(): Promise<CeoComplianceRegulatoryStatutoryResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/regulatory-statutory`)
  return response.data
}

export async function getCeoComplianceLegalContractManagement(): Promise<CeoComplianceLegalContractResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/legal-contract-management`)
  return response.data
}

export async function getCeoComplianceIncidentRiskManagement(): Promise<CeoComplianceIncidentRiskResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/incident-risk-management`)
  return response.data
}

export async function getCeoComplianceAuditInspectionReadiness(): Promise<CeoComplianceAuditReadinessResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/audit-inspection-readiness`)
  return response.data
}

export async function getCeoComplianceDataPrivacySecurity(): Promise<CeoComplianceDataPrivacySecurityResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/data-privacy-security`)
  return response.data
}

export async function getCeoCompliancePredictiveIntelligence(): Promise<CeoCompliancePredictiveIntelligenceResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/predictive-intelligence`)
  return response.data
}

export async function getCeoCompliancePredictiveWhatIfSimulation(params: { target_state: string; branch_model: string }): Promise<CeoCompliancePredictiveWhatIfResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/predictive-what-if-simulator`, { params })
  return response.data
}

export async function getCeoComplianceWowFeatures(): Promise<CeoComplianceWowFeaturesResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/compliance/wow-features`)
  return response.data
}

export async function getCeoSettingsBranding(): Promise<CeoSettingsBrandingResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/branding`)
  return response.data
}

export async function updateCeoSettingsBranding(payload: CeoSettingsBrandingResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsBrandingResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/branding`, payload)
  return response.data
}

export async function getCeoSettingsSecurity(): Promise<CeoSettingsSecurityResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/security`)
  return response.data
}

export async function updateCeoSettingsSecurity(payload: CeoSettingsSecurityResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsSecurityResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/security`, payload)
  return response.data
}

export async function getCeoSettingsFeatureFlags(): Promise<CeoSettingsFeatureFlagsResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/feature-flags`)
  return response.data
}

export async function updateCeoSettingsFeatureFlags(payload: CeoSettingsFeatureFlagsResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsFeatureFlagsResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/feature-flags`, payload)
  return response.data
}

export async function getCeoSettingsIntegrationsApiManagement(): Promise<CeoSettingsIntegrationsApiResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/integrations-api-management`)
  return response.data
}

export async function updateCeoSettingsIntegrationsApiManagement(payload: CeoSettingsIntegrationsApiResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsIntegrationsApiResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/integrations-api-management`, payload)
  return response.data
}

export async function getCeoSettingsBranchLocalizationManagement(): Promise<CeoSettingsBranchLocalizationResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/branch-localization-management`)
  return response.data
}

export async function updateCeoSettingsBranchLocalizationManagement(payload: CeoSettingsBranchLocalizationResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsBranchLocalizationResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/branch-localization-management`, payload)
  return response.data
}

export async function getCeoSettingsDataComplianceManagement(): Promise<CeoSettingsDataComplianceResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/data-compliance-management`)
  return response.data
}

export async function updateCeoSettingsDataComplianceManagement(payload: CeoSettingsDataComplianceResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsDataComplianceResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/data-compliance-management`, payload)
  return response.data
}

export async function getCeoSettingsAiAutomationConfiguration(): Promise<CeoSettingsAiAutomationResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/ai-automation-configuration`)
  return response.data
}

export async function updateCeoSettingsAiAutomationConfiguration(payload: CeoSettingsAiAutomationResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsAiAutomationResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/ai-automation-configuration`, payload)
  return response.data
}

export async function getCeoSettingsUiExperience(): Promise<CeoSettingsUiExperienceResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/ui-experience`)
  return response.data
}

export async function updateCeoSettingsUiExperience(payload: CeoSettingsUiExperienceResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsUiExperienceResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/ui-experience`, payload)
  return response.data
}

export async function getCeoSettingsMaintenanceSystemHealth(): Promise<CeoSettingsMaintenanceHealthResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/maintenance-system-health`)
  return response.data
}

export async function updateCeoSettingsMaintenanceSystemHealth(payload: CeoSettingsMaintenanceHealthResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsMaintenanceHealthResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/maintenance-system-health`, payload)
  return response.data
}

export async function getCeoSettingsImportExportMigration(): Promise<CeoSettingsImportExportMigrationResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/import-export-migration`)
  return response.data
}

export async function updateCeoSettingsImportExportMigration(payload: CeoSettingsImportExportMigrationResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsImportExportMigrationResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/import-export-migration`, payload)
  return response.data
}

export async function getCeoSettingsWowFeatures(): Promise<CeoSettingsWowFeaturesResponse> {
  const response = await axios.get(`${API_BASE}/api/ceo/settings/wow-features`)
  return response.data
}

export async function updateCeoSettingsWowFeatures(payload: CeoSettingsWowFeaturesResponse): Promise<{ updated: boolean; section: string; saved_at: string; payload: CeoSettingsWowFeaturesResponse }> {
  const response = await axios.put(`${API_BASE}/api/ceo/settings/wow-features`, payload)
  return response.data
}