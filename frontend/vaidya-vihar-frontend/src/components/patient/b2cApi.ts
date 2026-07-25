import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` }
}

export interface B2CProfile {
  id: number
  patient_id: string
  full_name: string
  mobile: string
  email?: string
  otp_verification: boolean
  referring_doctor_id?: number
  family_members: Array<{
    id: number
    name: string
    relation: string
    mobile?: string
    age?: number
  }>
  family_members_json: Array<Record<string, unknown>>
}

export interface B2CTestItem {
  id: number
  name: string
  category: string
  price: number
  preparation_instructions?: string
}

export interface B2CAppointment {
  id: number
  test_ids: number[]
  appointment_type: 'Home' | 'Center'
  scheduled_time: string
  status: string
}

export interface PatientReport {
  id: number
  patient_id: string
  test_name: string
  status: string
  amount: number
  created_at?: string
  download_url?: string
}

export interface PatientWallet {
  available_points: number
  payment_history: Array<{
    id: number
    points: number
    transaction_type: string
    description: string
    created_at: string
  }>
  payment_options: Array<{
    type: string
    label: string
  }>
}

export interface PatientFamilyProfile {
  patient_id: number
  patient_code: string
  family_group?: string | null
  headline: string
  summary: string
  primary_member: {
    id: number
    full_name: string
    mobile: string
    email?: string | null
  }
  members: Array<{
    id: number
    name: string
    relation: string
    mobile?: string | null
    age?: number | null
    linked_profile_id?: number | null
  }>
}

export interface HomeCollectionMapResponse {
  patient_location: { lat: number; lng: number; label: string }
  phlebotomist_location: { lat: number; lng: number; label: string; status: string }
  eta_minutes: number
  route_points: Array<{ lat: number; lng: number; label?: string }>
  status: string
  message: string
}

export interface PatientVaultDocumentItem {
  id: number
  original_filename: string
  file_url: string
  extracted_text: string
  document_label?: string | null
  file_size: number
  mime_type?: string | null
  created_at: string
}

export interface EmergencyAlertItem {
  id: number
  report_id?: number | null
  alert_type: string
  triggered_at: string
  delivery_channels: string[]
  doctor_notified: boolean
  note?: string | null
}

export interface SecondOpinionRequestItem {
  id: number
  report_id: number
  status: string
  payment_reference?: string | null
  specialist_panel: string
  premium_amount: number
  payment_url?: string
  message?: string
}

export interface WearableSyncItem {
  id: number
  provider: string
  status: string
  last_synced_at: string
}

export async function requestPatientOtp(mobile: string) {
  const response = await axios.post(`${API_BASE}/api/patient/auth/otp`, { mobile })
  return response.data as { success: boolean; message: string; otp_for_dev?: string }
}

export async function verifyPatientOtp(mobile: string, otp: string) {
  const response = await axios.post(`${API_BASE}/api/patient/auth/verify`, { mobile, otp })
  return response.data as { success: boolean; message: string }
}

export async function getB2CProfile(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/profile`, {
    headers: authHeaders(token),
  })
  return response.data as B2CProfile
}

export async function getB2CTestCatalog(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/test-catalog`, {
    headers: authHeaders(token),
  })
  return response.data as { tests: B2CTestItem[] }
}

export async function createB2CAppointment(
  token: string,
  payload: {
    test_ids: number[]
    appointment_type: 'Home' | 'Center'
    scheduled_time: string
  }
) {
  const response = await axios.post(`${API_BASE}/api/patient/appointments`, payload, {
    headers: authHeaders(token),
  })
  return response.data as B2CAppointment
}

export async function addAppointmentConsent(token: string, appointmentId: number, consentText: string) {
  const response = await axios.post(
    `${API_BASE}/api/patient/appointments/${appointmentId}/consent`,
    { consent_text: consentText },
    { headers: authHeaders(token) }
  )
  return response.data as { id: number; appointment_id: number; signed_at: string }
}

export async function getUpcomingAppointments(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/appointments/upcoming`, {
    headers: authHeaders(token),
  })
  return response.data as { appointments: B2CAppointment[] }
}

export async function getPatientReportsPhase2(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/reports`, {
    headers: authHeaders(token),
  })
  return response.data as { reports: PatientReport[] }
}

export async function getPatientReportSummary(token: string, reportId: number) {
  const response = await axios.get(`${API_BASE}/api/patient/reports/${reportId}/summary`, {
    headers: authHeaders(token),
  })
  return response.data as {
    report_id: number
    summary_id: number
    ai_summary: string
    abnormal_flags: Record<string, string>
    critical_alert_required?: boolean
    emergency_alert?: {
      id: number
      alert_type: string
      triggered_at: string
      delivery_channels: string[]
    } | null
  }
}

export async function getPatientTrends(token: string, biomarker: string) {
  const response = await axios.get(`${API_BASE}/api/patient/trends/${encodeURIComponent(biomarker)}`, {
    headers: authHeaders(token),
  })
  return response.data as {
    biomarker: string
    points: Array<{ date: string; value: number; graph_data?: Record<string, unknown> }>
  }
}

export async function getPatientHealthScore(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/health-score`, {
    headers: authHeaders(token),
  })
  return response.data as {
    score: number
    last_calculated: string
    band: string
  }
}

export async function getPatientReminders(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/reminders`, {
    headers: authHeaders(token),
  })
  return response.data as {
    reminders: Array<{
      id: number
      test_name: string
      next_due_date: string
      status: string
      message: string
    }>
  }
}

export async function askPatientChatbot(token: string, query: string) {
  const response = await axios.post(
    `${API_BASE}/api/patient/chatbot`,
    { query },
    { headers: authHeaders(token) }
  )
  return response.data as {
    query: string
    response: string
  }
}

export async function getPatientWallet(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/wallet`, {
    headers: authHeaders(token),
  })
  return response.data as PatientWallet
}

export async function createPatientReferral(token: string) {
  const response = await axios.post(`${API_BASE}/api/patient/referral`, {}, {
    headers: authHeaders(token),
  })
  return response.data as {
    referral_code: string
    referral_link: string
    message: string
  }
}

export async function createOrUpdatePatientGoal(
  token: string,
  payload: { goal_type: string; target_date: string; status: string }
) {
  const response = await axios.post(`${API_BASE}/api/patient/goals`, payload, {
    headers: authHeaders(token),
  })
  return response.data as {
    id: number
    patient_id: number
    goal_type: string
    target_date: string
    status: string
    reward_points: number
  }
}

export async function getPatientFamilyProfile(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/family-profile`, {
    headers: authHeaders(token),
  })
  return response.data as PatientFamilyProfile
}

export async function getPatientHomeCollectionMap(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/home-collection/map`, {
    headers: authHeaders(token),
  })
  return response.data as HomeCollectionMapResponse
}

export async function getPatientVaultDocuments(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/vault`, {
    headers: authHeaders(token),
  })
  return response.data as { items: PatientVaultDocumentItem[]; headline: string }
}

export async function uploadPatientVaultDocument(token: string, file: File, documentLabel?: string) {
  const formData = new FormData()
  formData.append('file', file)
  if (documentLabel) {
    formData.append('document_label', documentLabel)
  }
  const response = await axios.post(`${API_BASE}/api/patient/vault/upload`, formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data as { document: PatientVaultDocumentItem; message: string }
}

export async function triggerPatientCriticalAlert(token: string, payload: { report_id: number; alert_type?: string; note?: string }) {
  const response = await axios.post(`${API_BASE}/api/patient/alerts/critical`, payload, {
    headers: authHeaders(token),
  })
  return response.data as { id: number; alert_type: string; triggered_at: string; channels: string[]; message: string }
}

export async function getPatientEmergencyAlerts(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/emergency-alerts`, {
    headers: authHeaders(token),
  })
  return response.data as { items: EmergencyAlertItem[] }
}

export async function requestPatientSecondOpinion(
  token: string,
  payload: { report_id: number; specialist_panel: string }
) {
  const response = await axios.post(`${API_BASE}/api/patient/second-opinion`, payload, {
    headers: authHeaders(token),
  })
  return response.data as SecondOpinionRequestItem
}

export async function getPatientSecondOpinionRequests(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/second-opinion`, {
    headers: authHeaders(token),
  })
  return response.data as { items: SecondOpinionRequestItem[] }
}

export async function getPatientWearables(token: string) {
  const response = await axios.get(`${API_BASE}/api/patient/wearables`, {
    headers: authHeaders(token),
  })
  return response.data as { items: WearableSyncItem[]; headline: string }
}

export async function connectPatientWearable(
  token: string,
  payload: { provider: 'Apple Health' | 'Google Fit' | 'Fitbit'; token?: string }
) {
  const response = await axios.post(`${API_BASE}/api/patient/wearables/connect`, payload, {
    headers: authHeaders(token),
  })
  return response.data as { id: number; provider: string; status: string; message: string }
}
