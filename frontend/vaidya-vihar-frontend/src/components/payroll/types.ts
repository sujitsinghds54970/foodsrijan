export interface PayrollRunItem {
  id: number
  month: number
  year: number
  status: 'Draft' | 'Ready' | 'Approved' | 'Locked' | string
  total_gross_pay: number
  total_deductions: number
  total_net_pay: number
  approved_at?: string | null
}

export interface PayrollDashboardData {
  total_branch_payroll_this_month: number
  total_branch_payroll_last_month: number
  variance_percent: number
  department_wise_burn: Array<{ department: string; amount: number }>
  cost_to_income_ratio: number
}

export interface FundsCheckResponse {
  hasSufficientFunds: boolean
  required: number
  available: number
}

export interface PayslipItem {
  payroll_id: number
  month: number
  year: number
  status: string
  net_pay: number
  download_url: string
}
