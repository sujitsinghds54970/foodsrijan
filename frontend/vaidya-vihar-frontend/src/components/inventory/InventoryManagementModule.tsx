import { useCallback, useEffect, useMemo, useState } from 'react'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'
import Barcode from 'react-barcode'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'
import {
  addStock,
  consumeStock,
  createEquipment,
  createInventoryItem,
  createSupplier,
  deleteInventoryItem,
  getConsumptionHistory,
  getInventoryAlerts,
  listEquipment,
  listInventoryByDepartment,
  listSuppliers,
  logEquipmentService,
  submitManualAudit,
  updateInventoryItem,
} from './api'
import { AlertsPayload, ConsumptionHistoryRow, Department, EquipmentItem, InventoryItem, Supplier } from './types'

const DEPARTMENTS: Department[] = [
  'X-Ray',
  'Sonography',
  'Pathology',
  'CT Scan',
  'MRI',
  'Other Consumables',
]

type TopTab = Department | 'Dashboard' | 'Consumption History'
type ActionMode = 'add' | 'consume' | 'edit'

const columnHelper = createColumnHelper<InventoryItem>()

export default function InventoryManagementModule() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<TopTab>('Dashboard')
  const [items, setItems] = useState<InventoryItem[]>([])
  const [equipment, setEquipment] = useState<EquipmentItem[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [alerts, setAlerts] = useState<AlertsPayload | null>(null)
  const [history, setHistory] = useState<ConsumptionHistoryRow[]>([])
  const [loading, setLoading] = useState(false)

  const [showItemForm, setShowItemForm] = useState(false)
  const [showSupplierForm, setShowSupplierForm] = useState(false)
  const [showEquipmentForm, setShowEquipmentForm] = useState(false)
  const [showAuditForm, setShowAuditForm] = useState(false)

  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null)
  const [actionMode, setActionMode] = useState<ActionMode>('add')
  const [actionQty, setActionQty] = useState(1)
  const [actionNotes, setActionNotes] = useState('')

  const isManager = user?.role === 'branch_admin' || user?.role === 'branch_director' || user?.role === 'super_admin'

  const loadSuppliers = useCallback(async () => {
    const rows = await listSuppliers()
    setSuppliers(rows)
  }, [])

  const loadAlerts = useCallback(async () => {
    const payload = await getInventoryAlerts()
    setAlerts(payload)
  }, [])

  const loadHistory = useCallback(async () => {
    const rows = await getConsumptionHistory()
    setHistory(rows)
  }, [])

  const loadDepartmentData = useCallback(async (department: Department) => {
    setLoading(true)
    try {
      const [itemRows, equipmentRows] = await Promise.all([
        listInventoryByDepartment(department),
        listEquipment(department),
      ])
      setItems(itemRows)
      setEquipment(equipmentRows)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!isManager) {
      return
    }

    loadSuppliers().catch(() => toast.error('Failed to load suppliers'))
    loadAlerts().catch(() => toast.error('Failed to load inventory alerts'))
    loadHistory().catch(() => toast.error('Failed to load consumption history'))
  }, [isManager, loadAlerts, loadHistory, loadSuppliers])

  useEffect(() => {
    if (!isManager) {
      return
    }
    if (DEPARTMENTS.includes(activeTab as Department)) {
      loadDepartmentData(activeTab as Department).catch(() => toast.error('Failed to load department inventory'))
    }
  }, [activeTab, isManager, loadDepartmentData])

  const columns = useMemo(
    () => [
      columnHelper.accessor('item_name', {
        header: 'Item Name',
        cell: (ctx) => (
          <div>
            <div className="font-semibold text-slate-900">{ctx.getValue()}</div>
            <div className="text-xs text-slate-500">{ctx.row.original.category || 'Uncategorized'}</div>
          </div>
        ),
      }),
      columnHelper.accessor('current_qty', {
        header: 'Stock',
        cell: (ctx) => (
          <span className={ctx.row.original.is_low_stock ? 'text-rose-600 font-semibold' : 'text-slate-700'}>
            {ctx.getValue()} {ctx.row.original.unit}
          </span>
        ),
      }),
      columnHelper.accessor('min_threshold', { header: 'Min Threshold' }),
      columnHelper.accessor('expiry_date', {
        header: 'Expiry',
        cell: (ctx) =>
          ctx.getValue() ? (
            <span className={ctx.row.original.is_expiring_soon ? 'text-amber-600 font-semibold' : 'text-slate-700'}>
              {ctx.getValue()}
            </span>
          ) : (
            'N/A'
          ),
      }),
      columnHelper.accessor('unit_cost', {
        header: 'Unit Cost',
        cell: (ctx) => `Rs ${ctx.getValue()}`,
      }),
      columnHelper.accessor('total_value', {
        header: 'Total Value',
        cell: (ctx) => `Rs ${ctx.getValue().toFixed(2)}`,
      }),
      columnHelper.accessor('supplier_name', {
        header: 'Supplier',
        cell: (ctx) => ctx.getValue() || 'Unassigned',
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Actions',
        cell: (ctx) => (
          <div className="flex gap-2">
            <button
              onClick={() => openAction(ctx.row.original, 'add')}
              className="px-2 py-1 text-xs rounded bg-emerald-100 text-emerald-700"
            >
              Add Stock
            </button>
            <button
              onClick={() => openAction(ctx.row.original, 'consume')}
              className="px-2 py-1 text-xs rounded bg-amber-100 text-amber-700"
            >
              Consume
            </button>
            <button
              onClick={() => openEdit(ctx.row.original)}
              className="px-2 py-1 text-xs rounded bg-sky-100 text-sky-700"
            >
              Edit
            </button>
          </div>
        ),
      }),
    ],
    []
  )

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  function openAction(item: InventoryItem, mode: ActionMode) {
    setSelectedItem(item)
    setActionMode(mode)
    setActionQty(1)
    setActionNotes('')
    setShowItemForm(false)
  }

  function openEdit(item: InventoryItem) {
    setSelectedItem(item)
    setActionMode('edit')
    setShowItemForm(true)
  }

  async function submitStockAction() {
    if (!selectedItem) return
    try {
      if (actionMode === 'add') {
        await addStock(selectedItem.id, actionQty, actionNotes)
        toast.success('Stock added')
      } else {
        await consumeStock(selectedItem.id, actionQty, actionNotes)
        toast.success('Stock consumed')
      }
      if (DEPARTMENTS.includes(activeTab as Department)) {
        await loadDepartmentData(activeTab as Department)
      }
      await loadAlerts()
      setSelectedItem(null)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Stock action failed')
    }
  }

  async function handleDelete(itemId: number) {
    if (!window.confirm('Delete this item?')) return
    try {
      await deleteInventoryItem(itemId)
      toast.success('Item deleted')
      if (DEPARTMENTS.includes(activeTab as Department)) {
        await loadDepartmentData(activeTab as Department)
      }
      await loadAlerts()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Delete failed')
    }
  }

  if (!isManager) {
    return <div className="p-6 text-red-600">Inventory access is restricted to Branch Admin and Branch Director.</div>
  }

  return (
    <div className="grid grid-cols-12 gap-6">
      <aside className="col-span-12 md:col-span-3 xl:col-span-2 bg-white rounded-xl p-4 shadow-sm h-fit">
        <h2 className="text-sm font-bold text-slate-500 uppercase mb-3">Inventory Tabs</h2>
        <nav className="space-y-2">
          {(['Dashboard', ...DEPARTMENTS, 'Consumption History'] as TopTab[]).map((tabName) => (
            <button
              key={tabName}
              onClick={() => setActiveTab(tabName)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm ${
                activeTab === tabName ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {tabName}
            </button>
          ))}
        </nav>
      </aside>

      <section className="col-span-12 md:col-span-9 xl:col-span-10 space-y-4">
        {activeTab === 'Dashboard' && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold text-slate-900">Inventory Alerts & Control Center</h1>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-white rounded-xl p-4 border border-rose-100">
                <h3 className="font-semibold text-rose-700">Low Stock Alerts ({alerts?.low_stock_count || 0})</h3>
                <ul className="mt-2 space-y-1 text-sm text-slate-700">
                  {(alerts?.low_stock || []).slice(0, 8).map((row) => (
                    <li key={row.item_id}>{row.item_name}: {row.current_qty} / min {row.min_threshold}</li>
                  ))}
                </ul>
              </div>
              <div className="bg-white rounded-xl p-4 border border-amber-100">
                <h3 className="font-semibold text-amber-700">Expiry Alerts ({alerts?.expiring_soon_count || 0})</h3>
                <ul className="mt-2 space-y-1 text-sm text-slate-700">
                  {(alerts?.expiring_soon || []).slice(0, 8).map((row) => (
                    <li key={row.item_id}>{row.item_name}: {row.expiry_date}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setShowSupplierForm(true)} className="px-3 py-2 rounded bg-indigo-600 text-white text-sm">Add Supplier</button>
              <button onClick={() => setShowAuditForm(true)} className="px-3 py-2 rounded bg-slate-800 text-white text-sm">Manual Audit</button>
              <button onClick={() => setActiveTab('X-Ray')} className="px-3 py-2 rounded bg-emerald-600 text-white text-sm">Open Department View</button>
            </div>
          </div>
        )}

        {activeTab === 'Consumption History' && (
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <h1 className="text-xl font-bold mb-4">Consumption History</h1>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b">
                    <th className="py-2">Patient ID</th>
                    <th className="py-2">Test</th>
                    <th className="py-2">Item Deducted</th>
                    <th className="py-2">Quantity</th>
                    <th className="py-2">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((row) => (
                    <tr key={row.id} className="border-b border-slate-100">
                      <td className="py-2">{row.patient_identifier || '-'}</td>
                      <td className="py-2">{row.test_name || '-'}</td>
                      <td className="py-2">{row.item_deducted || '-'}</td>
                      <td className="py-2">{row.quantity}</td>
                      <td className="py-2">{new Date(row.consumed_on).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {DEPARTMENTS.includes(activeTab as Department) && (
          <div className="space-y-4">
            <div className="flex flex-wrap justify-between gap-2">
              <h1 className="text-2xl font-bold text-slate-900">{activeTab} Inventory</h1>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => { setSelectedItem(null); setShowItemForm(true) }} className="px-3 py-2 rounded bg-slate-900 text-white text-sm">Add Item</button>
                <button onClick={() => setShowEquipmentForm(true)} className="px-3 py-2 rounded bg-cyan-700 text-white text-sm">Add Machine</button>
                <button onClick={() => setShowSupplierForm(true)} className="px-3 py-2 rounded bg-indigo-600 text-white text-sm">Add Supplier</button>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-sm overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id} className="border-b text-left text-slate-500">
                      {headerGroup.headers.map((header) => (
                        <th key={header.id} className="py-2 pr-3">
                          {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td className="py-4" colSpan={columns.length}>Loading...</td>
                    </tr>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <tr key={row.id} className="border-b border-slate-100 align-top">
                        {row.getVisibleCells().map((cell) => (
                          <td key={cell.id} className="py-2 pr-3">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                        ))}
                        <td>
                          <button onClick={() => handleDelete(row.original.id)} className="text-xs text-rose-600">Delete</button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-sm">
              <h2 className="text-lg font-semibold mb-2">Equipment / Machine Management</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500 border-b">
                      <th className="py-2">Machine Name</th>
                      <th className="py-2">Brand/Model</th>
                      <th className="py-2">Serial Number</th>
                      <th className="py-2">Last Service</th>
                      <th className="py-2">Next Service Due</th>
                      <th className="py-2">Alert</th>
                      <th className="py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {equipment.map((m) => (
                      <tr key={m.id} className="border-b border-slate-100">
                        <td className="py-2">{m.machine_name}</td>
                        <td className="py-2">{m.brand_model || '-'}</td>
                        <td className="py-2">{m.serial_number || '-'}</td>
                        <td className="py-2">{m.last_service_date || '-'}</td>
                        <td className="py-2">{m.next_service_due_date || '-'}</td>
                        <td className="py-2">
                          {m.is_service_due_soon ? <span className="px-2 py-1 rounded bg-rose-100 text-rose-700">Due in 7 days</span> : '-'}
                        </td>
                        <td className="py-2">
                          <button
                            onClick={async () => {
                              const serviceDate = window.prompt('Service date (YYYY-MM-DD):', new Date().toISOString().slice(0, 10))
                              if (!serviceDate) return
                              const notes = window.prompt('Service notes:', '') || ''
                              await logEquipmentService(m.id, { service_date: serviceDate, notes })
                              toast.success('Service log saved')
                              await loadDepartmentData(activeTab as Department)
                            }}
                            className="text-xs px-2 py-1 rounded bg-slate-800 text-white"
                          >
                            Log Service
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {selectedItem && selectedItem.barcode_number && (
              <div className="bg-white rounded-xl p-4 shadow-sm inline-block">
                <h2 className="font-semibold mb-2">Generate Barcode</h2>
                <Barcode value={selectedItem.barcode_number} />
              </div>
            )}
          </div>
        )}
      </section>

      {selectedItem && (actionMode === 'add' || actionMode === 'consume') && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl p-4 w-full max-w-md space-y-3">
            <h3 className="text-lg font-semibold">{actionMode === 'add' ? 'Add Stock' : 'Consume Stock'}: {selectedItem.item_name}</h3>
            <input type="number" value={actionQty} onChange={(e) => setActionQty(Number(e.target.value))} className="w-full border rounded p-2" />
            <textarea value={actionNotes} onChange={(e) => setActionNotes(e.target.value)} placeholder="Notes" className="w-full border rounded p-2" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setSelectedItem(null)} className="px-3 py-2 rounded bg-slate-100">Cancel</button>
              <button onClick={submitStockAction} className="px-3 py-2 rounded bg-slate-900 text-white">Submit</button>
            </div>
          </div>
        </div>
      )}

      {showItemForm && (
        <ItemFormModal
          department={(DEPARTMENTS.includes(activeTab as Department) ? (activeTab as Department) : 'X-Ray')}
          suppliers={suppliers}
          item={selectedItem}
          onClose={() => {
            setShowItemForm(false)
            setSelectedItem(null)
          }}
          onSaved={async () => {
            setShowItemForm(false)
            setSelectedItem(null)
            if (DEPARTMENTS.includes(activeTab as Department)) {
              await loadDepartmentData(activeTab as Department)
            }
            await loadAlerts()
          }}
        />
      )}

      {showSupplierForm && (
        <SupplierModal
          onClose={() => setShowSupplierForm(false)}
          onSaved={async () => {
            setShowSupplierForm(false)
            await loadSuppliers()
          }}
        />
      )}

      {showEquipmentForm && DEPARTMENTS.includes(activeTab as Department) && (
        <EquipmentModal
          department={activeTab as Department}
          onClose={() => setShowEquipmentForm(false)}
          onSaved={async () => {
            setShowEquipmentForm(false)
            await loadDepartmentData(activeTab as Department)
          }}
        />
      )}

      {showAuditForm && (
        <AuditModal
          items={items}
          onClose={() => setShowAuditForm(false)}
          onSaved={async () => {
            setShowAuditForm(false)
            if (DEPARTMENTS.includes(activeTab as Department)) {
              await loadDepartmentData(activeTab as Department)
            }
            await loadAlerts()
          }}
        />
      )}
    </div>
  )
}

function ItemFormModal({
  department,
  suppliers,
  item,
  onClose,
  onSaved,
}: {
  department: Department
  suppliers: Supplier[]
  item: InventoryItem | null
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [form, setForm] = useState({
    department,
    item_name: item?.item_name || '',
    category: item?.category || '',
    current_qty: item?.current_qty || 0,
    min_threshold: item?.min_threshold || 0,
    expiry_date: item?.expiry_date || '',
    unit_cost: item?.unit_cost || 0,
    unit: item?.unit || 'units',
    supplier_id: item?.supplier_id || '',
    barcode_number: item?.barcode_number || '',
  })

  async function submit() {
    try {
      const payload = {
        ...form,
        supplier_id: form.supplier_id ? Number(form.supplier_id) : null,
      }
      if (item) {
        await updateInventoryItem(item.id, payload)
        toast.success('Item updated')
      } else {
        await createInventoryItem(payload)
        toast.success('Item created')
      }
      await onSaved()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save item')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-4 w-full max-w-xl space-y-3">
        <h3 className="text-lg font-semibold">{item ? 'Edit Inventory Item' : `Add Inventory Item (${department})`}</h3>
        <div className="grid md:grid-cols-2 gap-2">
          <input value={form.item_name} onChange={(e) => setForm({ ...form, item_name: e.target.value })} placeholder="Item name" className="border rounded p-2" />
          <input value={form.category || ''} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Category" className="border rounded p-2" />
          <input type="number" value={form.current_qty} onChange={(e) => setForm({ ...form, current_qty: Number(e.target.value) })} placeholder="Current qty" className="border rounded p-2" />
          <input type="number" value={form.min_threshold} onChange={(e) => setForm({ ...form, min_threshold: Number(e.target.value) })} placeholder="Min threshold" className="border rounded p-2" />
          <input type="date" value={form.expiry_date || ''} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} className="border rounded p-2" />
          <input type="number" value={form.unit_cost} onChange={(e) => setForm({ ...form, unit_cost: Number(e.target.value) })} placeholder="Unit cost" className="border rounded p-2" />
          <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} placeholder="Unit" className="border rounded p-2" />
          <select value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} className="border rounded p-2">
            <option value="">Select supplier</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <input value={form.barcode_number || ''} onChange={(e) => setForm({ ...form, barcode_number: e.target.value })} placeholder="Barcode number" className="border rounded p-2 md:col-span-2" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-2 rounded bg-slate-100">Cancel</button>
          <button onClick={submit} className="px-3 py-2 rounded bg-slate-900 text-white">Save</button>
        </div>
      </div>
    </div>
  )
}

function SupplierModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => Promise<void> }) {
  const [form, setForm] = useState({ name: '', contact_person: '', phone: '', email: '', address: '', gstin: '' })

  async function submit() {
    try {
      await createSupplier(form)
      toast.success('Supplier created')
      await onSaved()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to create supplier')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-4 w-full max-w-xl space-y-3">
        <h3 className="text-lg font-semibold">Add Supplier / Dealer</h3>
        <div className="grid md:grid-cols-2 gap-2">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Supplier Name" className="border rounded p-2" />
          <input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} placeholder="Contact Person" className="border rounded p-2" />
          <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Phone" className="border rounded p-2" />
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email" className="border rounded p-2" />
          <input value={form.gstin} onChange={(e) => setForm({ ...form, gstin: e.target.value })} placeholder="GSTIN" className="border rounded p-2" />
          <input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Address" className="border rounded p-2" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-2 rounded bg-slate-100">Cancel</button>
          <button onClick={submit} className="px-3 py-2 rounded bg-indigo-600 text-white">Save Supplier</button>
        </div>
      </div>
    </div>
  )
}

function EquipmentModal({
  department,
  onClose,
  onSaved,
}: {
  department: Department
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [form, setForm] = useState({
    department,
    machine_name: '',
    brand_model: '',
    serial_number: '',
    purchase_date: '',
    warranty_end_date: '',
    amc_company: '',
    dealer_contact: '',
    last_service_date: '',
    next_service_due_date: '',
  })

  async function submit() {
    try {
      await createEquipment(form)
      toast.success('Machine saved')
      await onSaved()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save machine')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-4 w-full max-w-2xl space-y-3">
        <h3 className="text-lg font-semibold">Add Equipment ({department})</h3>
        <div className="grid md:grid-cols-2 gap-2">
          <input value={form.machine_name} onChange={(e) => setForm({ ...form, machine_name: e.target.value })} placeholder="Machine Name" className="border rounded p-2" />
          <input value={form.brand_model} onChange={(e) => setForm({ ...form, brand_model: e.target.value })} placeholder="Brand / Model" className="border rounded p-2" />
          <input value={form.serial_number} onChange={(e) => setForm({ ...form, serial_number: e.target.value })} placeholder="Serial Number" className="border rounded p-2" />
          <input type="date" value={form.purchase_date} onChange={(e) => setForm({ ...form, purchase_date: e.target.value })} className="border rounded p-2" />
          <input type="date" value={form.warranty_end_date} onChange={(e) => setForm({ ...form, warranty_end_date: e.target.value })} className="border rounded p-2" />
          <input value={form.amc_company} onChange={(e) => setForm({ ...form, amc_company: e.target.value })} placeholder="AMC Company" className="border rounded p-2" />
          <input value={form.dealer_contact} onChange={(e) => setForm({ ...form, dealer_contact: e.target.value })} placeholder="Dealer Contact" className="border rounded p-2" />
          <input type="date" value={form.last_service_date} onChange={(e) => setForm({ ...form, last_service_date: e.target.value })} className="border rounded p-2" />
          <input type="date" value={form.next_service_due_date} onChange={(e) => setForm({ ...form, next_service_due_date: e.target.value })} className="border rounded p-2" />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-2 rounded bg-slate-100">Cancel</button>
          <button onClick={submit} className="px-3 py-2 rounded bg-cyan-700 text-white">Save</button>
        </div>
      </div>
    </div>
  )
}

function AuditModal({
  items,
  onClose,
  onSaved,
}: {
  items: InventoryItem[]
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [itemId, setItemId] = useState('')
  const [physicalQty, setPhysicalQty] = useState(0)
  const [notes, setNotes] = useState('')

  async function submit() {
    if (!itemId) {
      toast.error('Select an item first')
      return
    }

    try {
      await submitManualAudit({ item_id: Number(itemId), physical_qty: physicalQty, notes })
      toast.success('Audit logged')
      await onSaved()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Audit failed')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl p-4 w-full max-w-lg space-y-3">
        <h3 className="text-lg font-semibold">Manual Stock Audit</h3>
        <select value={itemId} onChange={(e) => setItemId(e.target.value)} className="w-full border rounded p-2">
          <option value="">Select item</option>
          {items.map((item) => (
            <option key={item.id} value={item.id}>{item.item_name}</option>
          ))}
        </select>
        <input type="number" value={physicalQty} onChange={(e) => setPhysicalQty(Number(e.target.value))} className="w-full border rounded p-2" placeholder="Physical count" />
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full border rounded p-2" placeholder="Notes" />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-3 py-2 rounded bg-slate-100">Cancel</button>
          <button onClick={submit} className="px-3 py-2 rounded bg-slate-900 text-white">Save Audit</button>
        </div>
      </div>
    </div>
  )
}
