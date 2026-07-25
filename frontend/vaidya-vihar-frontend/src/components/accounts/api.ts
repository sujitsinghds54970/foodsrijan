import axios from 'axios'
import {
  FinanceExpense,
  FinanceInvoice,
  FinanceTransaction,
  FinanceTransactionType,
  GstReport,
  ProfitLossReport,
} from './types'

const API_BASE = 'http://127.0.0.1:8000'

export async function listTransactions(params: {
  branch_id?: number
  start?: string
  end?: string
  type?: FinanceTransactionType | ''
}): Promise<FinanceTransaction[]> {
  const response = await axios.get(`${API_BASE}/api/transactions`, { params })
  return response.data as FinanceTransaction[]
}

export async function createTransaction(payload: {
  branch_id?: number
  date?: string
  type: FinanceTransactionType
  amount: number
  description?: string
  reference_id?: string
  category?: string
  payment_method?: string
}): Promise<FinanceTransaction> {
  const response = await axios.post(`${API_BASE}/api/transactions`, payload)
  return response.data as FinanceTransaction
}

export async function listInvoices(params: { branch_id?: number; status?: string }): Promise<FinanceInvoice[]> {
  const response = await axios.get(`${API_BASE}/api/invoices`, { params })
  return response.data as FinanceInvoice[]
}

export async function createInvoice(payload: {
  branch_id?: number
  patient_id?: number
  patient_name?: string
  date?: string
  total_amount: number
  tax_amount?: number
  gst_rate?: number
  status?: 'pending' | 'paid' | 'cancelled'
  due_date?: string
  pdf_url?: string
  reference_id?: string
}): Promise<FinanceInvoice> {
  const response = await axios.post(`${API_BASE}/api/invoices`, payload)
  return response.data as FinanceInvoice
}

export async function markInvoicePaid(invoiceId: number): Promise<FinanceInvoice> {
  const response = await axios.put(`${API_BASE}/api/invoices/${invoiceId}/mark-paid`)
  return response.data as FinanceInvoice
}

export async function generateInvoicePdf(invoiceId: number): Promise<{ message: string; pdf_url: string }> {
  const response = await axios.get(`${API_BASE}/api/invoices/${invoiceId}/generate-pdf`)
  return response.data as { message: string; pdf_url: string }
}

export async function sendInvoice(invoiceId: number, channel: 'email' | 'whatsapp'): Promise<{
  message: string
  channel_url?: string
  pdf_url?: string
}> {
  const response = await axios.post(`${API_BASE}/api/invoices/${invoiceId}/send`, null, { params: { channel } })
  return response.data as { message: string; channel_url?: string; pdf_url?: string }
}

export async function listExpenses(params: { branch_id?: number; status?: string }): Promise<FinanceExpense[]> {
  const response = await axios.get(`${API_BASE}/api/expenses`, { params })
  return response.data as FinanceExpense[]
}

export async function createExpense(payload: {
  branch_id?: number
  date?: string
  category: string
  amount: number
  description?: string
  status?: string
  payment_method?: string
  reference_id?: string
  attachment?: File | null
}): Promise<FinanceExpense> {
  const form = new FormData()
  if (payload.branch_id) form.append('branch_id', String(payload.branch_id))
  if (payload.date) form.append('date', payload.date)
  form.append('category', payload.category)
  form.append('amount', String(payload.amount))
  if (payload.description) form.append('description', payload.description)
  if (payload.status) form.append('status', payload.status)
  if (payload.payment_method) form.append('payment_method', payload.payment_method)
  if (payload.reference_id) form.append('reference_id', payload.reference_id)
  if (payload.attachment) form.append('attachment', payload.attachment)

  const response = await axios.post(`${API_BASE}/api/expenses`, form, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data as FinanceExpense
}

export async function approveExpense(expenseId: number): Promise<FinanceExpense> {
  const response = await axios.put(`${API_BASE}/api/expenses/${expenseId}/approve`)
  return response.data as FinanceExpense
}

export async function getProfitLoss(params: {
  start: string
  end: string
  branch_id?: number
}): Promise<ProfitLossReport> {
  const response = await axios.get(`${API_BASE}/api/reports/profit-loss`, { params })
  return response.data as ProfitLossReport
}

export async function getGstReport(params: {
  month: number
  year: number
  branch_id?: number
}): Promise<GstReport> {
  const response = await axios.get(`${API_BASE}/api/reports/gst`, { params })
  return response.data as GstReport
}
