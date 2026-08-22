export interface StaffItem {
  id: number
  full_name: string
  mobile: string
  email?: string
  address?: string
  city?: string
  specialization?: string
  degree?: string
  hospital_clinic_affiliation?: string
  years_of_experience?: number
  bank_account_number?: string
  ifsc_code?: string
  upi_id?: string
  commission_percentage: number
  latitude?: number
  longitude?: number
  portal_username?: string
  monthly_referrals?: number
  monthly_revenue?: number
  monthly_commission?: number
}

export interface PerformanceItem {
  doctor_id: number
  doctor_name: string
  specialization?: string
  referrals: number
  revenue: number
  commission_percentage: number
  commission: number
}

export interface PerformanceResponse {
  month: number
  year: number
  top_5_referring_staff: PerformanceItem[]
  doctor_performance: PerformanceItem[]
  total_revenue_from_referrals: number
  total_commission_payable: number
  pending_orders_to_send: number
}

export interface ShareResultItem {
  doctor_id: number
  doctor_name: string
  email?: string
  mobile?: string
  share_links: string[]
  email_link?: string
  whatsapp_link?: string
  expires_at: string
}
