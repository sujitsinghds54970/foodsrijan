export type TrendPoint = {
  date: string
  revenue: number
  expenses: number
  customers: number
}

export type MonthlyTrendPoint = {
  month: string
  revenue: number
  expenses: number
  customers: number
}

export type DashboardResponse = {
  branch_id: number
  period_start: string
  period_end: string
  kpis: {
    total_revenue: number
    total_expenses: number
    net_profit: number
    patient_count: number
    total_menu_items: number
    avg_bill_value: number
  }
  modality_split: {
    xray: number
    sonography: number
    pathology: number
    ct_mri: number
    other: number
  }
  department_tat: Array<{
    department: string
    avg_minutes: number
    avg_hours: number
    sample_size: number
  }>
}

export type TrendsResponse = {
  branch_id: number
  start_date: string
  end_date: string
  daily: TrendPoint[]
  monthly: MonthlyTrendPoint[]
}

export type TopReferrersResponse = {
  branch_id: number
  start_date: string
  end_date: string
  items: Array<{
    doctor_name: string
    patient_count: number
    total_revenue: number
  }>
}

export type ForecastResponse = {
  branch_id: number
  predicted_customers: number
  confidence_margin_percent: number
  lower_bound: number
  upper_bound: number
  series_used: Array<{
    month: string
    customers: number
  }>
}
