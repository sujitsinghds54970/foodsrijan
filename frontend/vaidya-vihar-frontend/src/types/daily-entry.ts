export interface Customer {
  id: number;
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  address?: string;
}

export interface Staff {
  id: number;
  first_name: string;
  last_name: string;
  specialization: string;
  phone?: string;
}

export interface DailyEntryRow {
  id?: number;
  patient_id: number;
  patient_name: string;
  patient_phone: string;
  doctor_id: number;
  doctor_name: string;
  visit_date: string;
  consultation_fee: number;
  test_fee: number;
  total_amount: number;
  test_type: string;
  notes: string;
  payment_status: 'paid' | 'pending' | 'partial';
  branch_id: number;
  history_count?: number; // Customer visit history
}

export interface GridApiResponse {
  entries: DailyEntryRow[];
  customers: Customer[];
  staff: Staff[];
  summary: {
    total_customers: number;
    total_revenue: number;
    pending_amount: number;
  };
}

