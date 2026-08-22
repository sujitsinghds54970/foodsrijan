export interface PendingActionItem {
  title: string
  count: number
}

export interface BranchPayrollRunSummary {
  id: number
  month: number
  year: number
  status: string
  tx_count?: number
}

export interface BranchPayrollHealthScore {
  health_score: number
  health_band: 'Green' | 'Yellow' | 'Red' | string
  cost_to_income_ratio: number
  total_branch_payroll: number
  mom_variance_percent: number
  yoy_variance_percent: number
  payroll_run_status: string
  payroll_run: BranchPayrollRunSummary | null
  pending_actions: PendingActionItem[]
}

export interface DepartmentBurnItem {
  department: string
  amount: number
  percentage: number
}

export interface PayrollTrendItem {
  label: string
  month: number
  year: number
  payroll_cost: number
  employee_count: number
}

export interface OvertimeAllowanceBreakdown {
  overtime: number
  allowances: number
  incentives: number
  reimbursements: number
}

export interface TopEarnerItem {
  staff_profile_id: number
  employee_name: string
  department: string
  net_pay: number
  basic: number
  incentives: number
  deductions: number
}

export interface BranchPayrollAnalytics {
  department_wise_burn: DepartmentBurnItem[]
  payroll_trend_12m: PayrollTrendItem[]
  employee_count_vs_payroll_cost: PayrollTrendItem[]
  overtime_allowance_breakdown: OvertimeAllowanceBreakdown
  top_earners: TopEarnerItem[]
}

export interface BranchPayrollGridRow {
  staff_profile_id: number
  employee_name: string
  department: string
  basic: number
  da: number
  hra: number
  shift_allowance: number
  ot: number
  lop: number
  incentives: number
  statutory_deductions: number
  net_pay: number
}

export interface BranchPayrollStaffUpdatePayload {
  payroll_run_id: number
  basic: number
  da: number
  hra: number
  shift_allowance: number
  ot: number
  lop: number
  incentives: number
  statutory_deductions: number
}

export interface BranchPayrollProcessSelectedResponse {
  message: string
  payroll_run_id: number
  processed_count: number
  emails_sent: number
  email_failures: Array<{ staff_id: string; email: string }>
}

export interface BranchPayrollGenerateResponse {
  message: string
  payroll_run: {
    id: number
    month: number
    year: number
    status: string
    total_gross_pay: number
    total_deductions: number
    total_net_pay: number
  }
  grid_rows: BranchPayrollGridRow[]
}

export interface BranchPayrollPreviewResponse {
  payroll_run: {
    id: number
    month: number
    year: number
    status: string
    total_gross_pay: number
    total_deductions: number
    total_net_pay: number
  }
  summary: {
    employee_count: number
    total_net_pay: number
  }
  grid_rows: BranchPayrollGridRow[]
}

export interface BranchPayrollSimulationResponse {
  department: string
  hike_percentage: number
  current_total_cost: number
  projected_total_cost: number
  projected_delta: number
  current_health_score: number
  projected_health_score: number
  health_score_impact: number
}

export interface StatutoryContributionItem {
  department: string
  pf: number
  esi: number
  pt: number
  tds: number
  total: number
}

export interface BranchPayrollStatutoryOrder {
  payroll_run_id: number
  month: number
  year: number
  contributions: StatutoryContributionItem[]
  totals: {
    pf: number
    esi: number
    pt: number
    tds: number
    total: number
  }
}

export interface BranchPayrollReadiness {
  readiness_score: number
  attendance_completeness_percent: number
  leave_approval_percent: number
  can_generate: boolean
  reasons: string[]
}

export interface PayrollAnomalyItem {
  staff_profile_id: number
  employee_name: string
  department: string
  previous_overtime_hours: number
  current_overtime_hours: number
  increase_percent: number
  message: string
}

export interface PayrollWellnessData {
  average_salary: number
  salary_distribution: Array<{ bucket: string; count: number }>
  financial_stress: {
    high_advance_requests: number
    pending_advance_requests: number
  }
}

export interface PayrollTwoFactorState {
  two_factor_enabled: boolean
}
