import axios from 'axios'
import {
  BranchPayrollAnalytics,
  BranchPayrollGenerateResponse,
  BranchPayrollHealthScore,
  BranchPayrollPreviewResponse,
  BranchPayrollProcessSelectedResponse,
  BranchPayrollReadiness,
  BranchPayrollStaffUpdatePayload,
  BranchPayrollSimulationResponse,
  BranchPayrollStatutoryOrder,
  PayrollAnomalyItem,
  PayrollTwoFactorState,
  PayrollWellnessData,
} from './branchPayrollTypes'

const API_BASE =
  (process as any).env.REACT_APP_API_BASE_URL ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8000'
    : window.location.origin)

export const branchPayrollApi = {
  async getHealthScore(month: number, year: number): Promise<BranchPayrollHealthScore> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/health-score`, {
      params: { month, year },
    })
    return response.data
  },

  async getAnalytics(month: number, year: number): Promise<BranchPayrollAnalytics> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/analytics`, {
      params: { month, year },
    })
    return response.data
  },

  async generate(month: number, year: number, step: 'fetch_data' | 'review' | 'freeze'): Promise<BranchPayrollGenerateResponse> {
    const response = await axios.post(`${API_BASE}/api/branch/payroll/generate`, { month, year, step })
    return response.data
  },

  async adjust(payload: {
    payroll_run_id: number
    adjustment_type: 'percent' | 'fixed'
    value: number
    target_department?: string
    unlock_reason?: string
  }): Promise<{ message: string; affected_employees: number; total_net_pay: number; grid_rows: any[] }> {
    const response = await axios.put(`${API_BASE}/api/branch/payroll/adjust`, payload)
    return response.data
  },

  async preview(payroll_run_id: number): Promise<BranchPayrollPreviewResponse> {
    const response = await axios.post(`${API_BASE}/api/branch/payroll/preview`, { payroll_run_id })
    return response.data
  },

  async approve(payroll_run_id: number): Promise<{ message: string; status: string; payslips_emailed?: number }> {
    const response = await axios.post(`${API_BASE}/api/branch/payroll/approve`, { payroll_run_id, force_lock: true })
    return response.data
  },

  async updateStaffPayrollRow(staff_profile_id: number, payload: BranchPayrollStaffUpdatePayload): Promise<{ message: string; net_pay: number }> {
    const response = await axios.put(`${API_BASE}/api/branch/payroll/staff/${staff_profile_id}`, payload)
    return response.data
  },

  async processSelected(staff_ids: number[], payroll_run_id?: number): Promise<BranchPayrollProcessSelectedResponse> {
    const response = await axios.post(`${API_BASE}/api/branch/payroll/process-selected`, {
      staff_ids,
      payroll_run_id,
    })
    return response.data
  },

  async simulate(department: string, hike_percentage: number): Promise<BranchPayrollSimulationResponse> {
    const response = await axios.post(`${API_BASE}/api/branch/payroll/simulate`, { department, hike_percentage })
    return response.data
  },

  async getStatutoryOrder(payroll_run_id?: number): Promise<BranchPayrollStatutoryOrder> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/orders/statutory`, {
      params: payroll_run_id ? { payroll_run_id } : {},
    })
    return response.data
  },

  async getReadiness(month: number, year: number): Promise<BranchPayrollReadiness> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/readiness`, { params: { month, year } })
    return response.data
  },

  async getAnomalies(month: number, year: number): Promise<{ anomalies: PayrollAnomalyItem[] }> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/anomalies`, { params: { month, year } })
    return response.data
  },

  async getWellness(payroll_run_id?: number): Promise<PayrollWellnessData> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/wellness`, {
      params: payroll_run_id ? { payroll_run_id } : {},
    })
    return response.data
  },

  async getTwoFactorState(): Promise<PayrollTwoFactorState> {
    const response = await axios.get(`${API_BASE}/api/branch/payroll/security/two-factor`)
    return response.data
  },

  async setTwoFactorState(enabled: boolean): Promise<PayrollTwoFactorState> {
    const response = await axios.post(`${API_BASE}/api/branch/payroll/security/two-factor`, { enabled })
    return response.data
  },

  payrollOrderUrl(format: 'pdf' | 'excel' | 'csv', payroll_run_id?: number): string {
    const query = payroll_run_id ? `?format=${format}&payroll_run_id=${payroll_run_id}` : `?format=${format}`
    return `${API_BASE}/api/branch/payroll/orders/payroll${query}`
  },

  bankFileUrl(payroll_run_id?: number): string {
    const query = payroll_run_id ? `?payroll_run_id=${payroll_run_id}` : ''
    return `${API_BASE}/api/branch/payroll/orders/bank-file${query}`
  },
}
