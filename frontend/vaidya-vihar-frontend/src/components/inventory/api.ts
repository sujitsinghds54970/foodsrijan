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

export async function listInventoryByDepartment(department: Department, branchId?: number): Promise<InventoryItem[]> {
  const response = await axios.get(`${API_BASE}/api/inventory`, {
    params: { department, ...(branchId ? { branch_id: branchId } : {}) },
  })
  return response.data as InventoryItem[]
}

export async function createInventoryItem(payload: Record<string, unknown>, branchId?: number): Promise<InventoryItem> {
  const response = await axios.post(`${API_BASE}/api/inventory`, {
    ...payload,
    ...(branchId ? { branch_id: branchId } : {}),
  })
  return response.data as InventoryItem
}

export async function updateInventoryItem(itemId: number, payload: Record<string, unknown>, branchId?: number): Promise<InventoryItem> {
  const response = await axios.put(`${API_BASE}/api/inventory/${itemId}`, {
    ...payload,
    ...(branchId ? { branch_id: branchId } : {}),
  })
  return response.data as InventoryItem
}

export async function addStock(itemId: number, quantity: number, notes?: string, branchId?: number): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/${itemId}/add-stock`, {
    quantity,
    notes,
    ...(branchId ? { branch_id: branchId } : {}),
  })
}

export async function consumeStock(itemId: number, quantity: number, notes?: string, branchId?: number): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/${itemId}/consume`, {
    quantity,
    notes,
    ...(branchId ? { branch_id: branchId } : {}),
  })
}

export async function deleteInventoryItem(itemId: number, branchId?: number): Promise<void> {
  await axios.delete(`${API_BASE}/api/inventory/${itemId}`, {
    params: branchId ? { branch_id: branchId } : {},
  })
}

export async function listSuppliers(branchId?: number): Promise<Supplier[]> {
  const response = await axios.get(`${API_BASE}/api/inventory/suppliers`, {
    params: branchId ? { branch_id: branchId } : {},
  })
  return response.data as Supplier[]
}

export async function createSupplier(payload: Record<string, unknown>, branchId?: number): Promise<Supplier> {
  const response = await axios.post(`${API_BASE}/api/inventory/suppliers`, {
    ...payload,
    ...(branchId ? { branch_id: branchId } : {}),
  })
  return response.data as Supplier
}

export async function listEquipment(department: Department, branchId?: number): Promise<EquipmentItem[]> {
  const response = await axios.get(`${API_BASE}/api/inventory/equipment`, {
    params: { department, ...(branchId ? { branch_id: branchId } : {}) },
  })
  return response.data as EquipmentItem[]
}

export async function createEquipment(payload: Record<string, unknown>, branchId?: number): Promise<EquipmentItem> {
  const response = await axios.post(`${API_BASE}/api/inventory/equipment`, {
    ...payload,
    ...(branchId ? { branch_id: branchId } : {}),
  })
  return response.data as EquipmentItem
}

export async function logEquipmentService(
  equipmentId: number,
  payload: { service_date: string; notes?: string },
  branchId?: number,
): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/equipment/${equipmentId}/service-log`, {
    ...payload,
    ...(branchId ? { branch_id: branchId } : {}),
  })
}

export async function getConsumptionHistory(branchId?: number): Promise<ConsumptionHistoryRow[]> {
  const response = await axios.get(`${API_BASE}/api/inventory/consumption-history`, {
    params: branchId ? { branch_id: branchId } : {},
  })
  return response.data as ConsumptionHistoryRow[]
}

export async function getInventoryAlerts(branchId?: number): Promise<AlertsPayload> {
  const response = await axios.get(`${API_BASE}/api/inventory/alerts`, {
    params: branchId ? { branch_id: branchId } : {},
  })
  return response.data as AlertsPayload
}

export async function submitManualAudit(
  payload: { item_id: number; physical_qty: number; notes?: string },
  branchId?: number,
): Promise<void> {
  await axios.post(`${API_BASE}/api/inventory/audit`, {
    ...payload,
    ...(branchId ? { branch_id: branchId } : {}),
  })
}
