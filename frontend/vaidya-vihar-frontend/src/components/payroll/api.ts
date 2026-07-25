import axios from 'axios'
import { FundsCheckResponse, PayrollDashboardData, PayrollRunItem, PayslipItem } from './types'

const API_BASE =
  (process as any).env.REACT_APP_API_BASE_URL ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

export const payrollApi = {
  async getDashboard(): Promise<PayrollDashboardData> {
    const response = await axios.get(`${API_BASE}/api/payroll/dashboard`)
    return response.data
  },

  async listRuns(): Promise<PayrollRunItem[]> {
    const response = await axios.get(`${API_BASE}/api/payroll/runs`)
    return response.data?.items || []
  },

  async generate(month: number, year: number): Promise<PayrollRunItem> {
    const response = await axios.post(`${API_BASE}/api/payroll/generate`, { month, year })
    return response.data?.payroll_run
  },

  async checkFunds(payrollId: number): Promise<FundsCheckResponse> {
    const response = await axios.get(`${API_BASE}/api/payroll/${payrollId}/check-funds`)
    return response.data
  },

  async approve(payrollId: number): Promise<{ message: string; status: string }> {
    const response = await axios.post(`${API_BASE}/api/payroll/${payrollId}/approve`, { force_lock: true })
    return response.data
  },

  async simulate(percentage: number): Promise<{ current_cost: number; projected_cost: number; delta: number }> {
    const response = await axios.post(`${API_BASE}/api/payroll/simulate`, { percentage })
    return response.data
  },

  async listMyPayslips(): Promise<PayslipItem[]> {
    const response = await axios.get(`${API_BASE}/api/payroll/my/payslips`)
    return response.data?.items || []
  },

  async downloadPayslip(downloadUrl: string, filename?: string): Promise<void> {
    const absoluteUrl = downloadUrl.startsWith('http') ? downloadUrl : `${API_BASE}${downloadUrl}`
    const response = await axios.get(absoluteUrl, { responseType: 'blob' })

    const blob = new Blob([response.data], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'payslip.pdf'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  },

  payslipDownloadUrl(payrollId: number, staffId: number): string {
    return `${API_BASE}/api/payroll/${payrollId}/payslip/${staffId}`
  },
}
