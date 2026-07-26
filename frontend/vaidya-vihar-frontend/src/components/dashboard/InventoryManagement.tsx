import InventoryManagementModule from '../inventory/InventoryManagementModule'

interface InventoryManagementProps {
  branchId?: number
}

export default function InventoryManagement({ branchId }: InventoryManagementProps) {
  return <InventoryManagementModule branchId={branchId} />
}
