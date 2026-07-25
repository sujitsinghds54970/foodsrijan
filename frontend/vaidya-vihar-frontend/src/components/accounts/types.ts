export type FinanceTransactionType = 'revenue' | 'expense' | 'transfer'

export interface FinanceTransaction {
  id: number
  branch_id: number
  date: string
  type: FinanceTransactionType
  amount: number
  description?: string
  reference_id?: string
  category?: string
  payment_method?: string
  created_by: number
}

export interface FinanceInvoice {
  id: number
  invoice_number: string
  patient_id?: number | null
  patient_name?: string | null
  branch_id: number
  date: string
  total_amount: number
  tax_amount: number
  gst_rate: number
  status: 'pending' | 'paid' | 'cancelled'
  due_date?: string | null
  pdf_url?: string | null
  reference_id?: string | null
}

export interface FinanceExpense {
  id: number
  branch_id: number
  date: string
  category: string
  amount: number
  description?: string
  attachment_url?: string
  approved_by?: number | null
  status: 'pending' | 'approved' | 'rejected'
  payment_method?: string
  reference_id?: string
}

export interface ProfitLossReport {
  branch_id: number
  start: string
  end: string
  revenue: number
  expense: number
  net_profit: number
}

export interface GstReport {
  branch_id: number
  month: number
  year: number
  invoice_count: number
  taxable_amount: number
  gst_amount: number
}
