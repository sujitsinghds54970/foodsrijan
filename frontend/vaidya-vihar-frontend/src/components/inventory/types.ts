export type Department =
  | 'X-Ray'
  | 'Sonography'
  | 'Pathology'
  | 'CT Scan'
  | 'MRI'
  | 'Other Consumables'

export interface Supplier {
  id: number
  branch_id: number
  name: string
  contact_person?: string | null
  phone?: string | null
  email?: string | null
  address?: string | null
  gstin?: string | null
  is_active: boolean
}

export interface InventoryItem {
  id: number
  branch_id: number
  department: Department
  item_name: string
  category?: string | null
  current_qty: number
  min_threshold: number
  expiry_date?: string | null
  unit_cost: number
  unit: string
  supplier_id?: number | null
  supplier_name?: string | null
  barcode_number?: string | null
  total_value: number
  is_low_stock: boolean
  is_expiring_soon: boolean
}

export interface EquipmentItem {
  id: number
  branch_id: number
  department: Department
  machine_name: string
  brand_model?: string | null
  serial_number?: string | null
  purchase_date?: string | null
  warranty_end_date?: string | null
  amc_company?: string | null
  dealer_contact?: string | null
  last_service_date?: string | null
  next_service_due_date?: string | null
  is_service_due_soon: boolean
}

export interface ConsumptionHistoryRow {
  id: number
  daily_entry_id?: number | null
  patient_identifier?: string | null
  test_name?: string | null
  item_deducted?: string | null
  quantity: number
  consumed_on: string
}

export interface AlertsPayload {
  low_stock_count: number
  expiring_soon_count: number
  low_stock: Array<{
    item_id: number
    item_name: string
    current_qty: number
    min_threshold: number
  }>
  expiring_soon: Array<{
    item_id: number
    item_name: string
    expiry_date: string
  }>
}
