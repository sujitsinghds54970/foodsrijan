import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

export type CustomerLoginPayload =
  | { mode: 'otp'; mobile: string; otp: string }
  | { mode: 'password'; patient_id: string; password: string }

export interface CustomerSession {
  access_token: string
  token_type: string
  patient: {
    id: number
    patient_code: string
    full_name: string
    mobile: string
    wallet_balance: number
    cashback_percent: number
  }
}

export async function patientLogin(payload: CustomerLoginPayload): Promise<CustomerSession> {
  const response = await axios.post(`${API_BASE}/api/patient/login`, payload)
  return response.data as CustomerSession
}

function patientHeaders(token: string) {
  return { Authorization: `Bearer ${token}` }
}

export async function getCustomerDashboard(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/dashboard`, {
    headers: patientHeaders(token),
  })
  return response.data
}

export async function getCustomerOrders(token: string, page = 1, pageSize = 10) {
  const response = await axios.get(`${API_BASE}/api/patient/orders`, {
    headers: patientHeaders(token),
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function getOrderDownloadUrl(token: string, reportId: number) {
  const response = await axios.get(`${API_BASE}/api/patient/orders/${reportId}/download`, {
    headers: patientHeaders(token),
  })
  return response.data as {
    report_id: number
    download_url: string
    report_header?: {
      title?: string
      subtitle?: string
      logo_url?: string
    }
    branding?: {
      clinic_name?: string
      clinic_address?: string
      logo_url?: string
    }
  }
}

export async function notifyCustomerOrder(token: string, reportId: number, channel: 'whatsapp' | 'email') {
  const response = await axios.post(
    `${API_BASE}/api/patient/notify`,
    { report_id: reportId, channel },
    { headers: patientHeaders(token) }
  )
  return response.data as { success: boolean; channel_url: string; download_url: string }
}

export async function addFamilyMember(token: string, payload: { name: string; relation: string; age?: number; mobile?: string }) {
  const response = await axios.post(`${API_BASE}/api/patient/family-members`, payload, {
    headers: patientHeaders(token),
  })
  return response.data
}

export async function redeemWallet(token: string, amount: number) {
  const response = await axios.post(
    `${API_BASE}/api/patient/wallet/redeem`,
    { amount },
    { headers: patientHeaders(token) }
  )
  return response.data as { wallet_balance: number; redeemed: number }
}
