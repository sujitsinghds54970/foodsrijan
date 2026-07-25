import axios from 'axios'

import {
  AlertsPayload,
  ConsumptionHistoryRow,
  Department,
  EquipmentItem,
  InventoryItem,
  Supplier,
} from './types'

const API_BASE = 'http://127.0.0.1:8000'

export async function listInventoryByDepartment(department: Department): Promise<InventoryItem[]> {
  const response = await axios.get(`${API_BASE}/api/inventory`, {
    params: { department },
  })
  return response.data as InventoryItem[]
}

export async function createInventoryItem(payload: Record<string, unknown>): Promise<InventoryItem> {
  const response = await axios.post(`${API_BASE}/api/inventory`, payload)
  return response.data as InventoryItem
}

export async function updateInventoryItem(itemId: number, payload: Record<string, unknown>): Promise<InventoryItem> {
  const response = await axios.put(`${API_BASE}/api/inventory/${itemId}`, payload)
  return response.data as InventoryItem
}

export async function addStock(itemId: number, quantity: number, notes?: string): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/${itemId}/add-stock`, { quantity, notes })
}

export async function consumeStock(itemId: number, quantity: number, notes?: string): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/${itemId}/consume`, { quantity, notes })
}

export async function deleteInventoryItem(itemId: number): Promise<void> {
  await axios.delete(`${API_BASE}/api/inventory/${itemId}`)
}

export async function listSuppliers(): Promise<Supplier[]> {
  const response = await axios.get(`${API_BASE}/api/inventory/suppliers`)
  return response.data as Supplier[]
}

export async function createSupplier(payload: Record<string, unknown>): Promise<Supplier> {
  const response = await axios.post(`${API_BASE}/api/inventory/suppliers`, payload)
  return response.data as Supplier
}

export async function listEquipment(department: Department): Promise<EquipmentItem[]> {
  const response = await axios.get(`${API_BASE}/api/inventory/equipment`, { params: { department } })
  return response.data as EquipmentItem[]
}

export async function createEquipment(payload: Record<string, unknown>): Promise<EquipmentItem> {
  const response = await axios.post(`${API_BASE}/api/inventory/equipment`, payload)
  return response.data as EquipmentItem
}

export async function logEquipmentService(equipmentId: number, payload: { service_date: string; notes?: string }): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/equipment/${equipmentId}/service-log`, payload)
}

export async function getConsumptionHistory(): Promise<ConsumptionHistoryRow[]> {
  const response = await axios.get(`${API_BASE}/api/inventory/consumption-history`)
  return response.data as ConsumptionHistoryRow[]
}

export async function getInventoryAlerts(): Promise<AlertsPayload> {
  const response = await axios.get(`${API_BASE}/api/inventory/alerts`)
  return response.data as AlertsPayload
}

export async function submitManualAudit(payload: { item_id: number; physical_qty: number; notes?: string }): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/audit`, payload)
}
