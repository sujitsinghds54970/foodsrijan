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