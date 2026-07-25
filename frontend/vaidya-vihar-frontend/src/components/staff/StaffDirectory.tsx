import { useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { StaffCreatePayload, StaffSummary } from './types'

interface StaffDirectoryProps {
  items: StaffSummary[]
  selectedId: number | null
  selectedIds: number[]
  loading: boolean
  onSelect: (id: number) => void
  onToggleSelect: (id: number) => void
  onToggleSelectAll: (checked: boolean) => void
  onCreate: (payload: StaffCreatePayload) => Promise<void>
  onBulkToggleDailyOps: (canAccess: boolean) => Promise<void>
  onSearch: (value: string) => void
}

export default function StaffDirectory({
  items,
  selectedId,
  selectedIds,
  loading,
  onSelect,
  onToggleSelect,
  onToggleSelectAll,
  onCreate,
  onBulkToggleDailyOps,
  onSearch,
}: StaffDirectoryProps) {
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<StaffCreatePayload>({
    first_name: '',
    last_name: '',
    email: '',
    mobile: '',
    department: '',
    designation: 'staff',
  })

  const activeCount = useMemo(() => items.filter((x) => x.status === 'active').length, [items])
  const allSelected = items.length > 0 && selectedIds.length === items.length

  const submit = async () => {
    if (!form.first_name || !form.last_name || !form.email || !form.mobile) {
      toast.error('Please fill first name, last name, email and mobile')
      return
    }
    await onCreate(form)
    setForm({
      first_name: '',
      last_name: '',
      email: '',
      mobile: '',
      department: '',
      designation: 'staff',
    })
    setShowCreate(false)
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Staff Directory</h2>
          <p className="text-xs text-slate-500">{activeCount} active of {items.length}</p>
        </div>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
        >
          {showCreate ? 'Close' : 'Add Staff'}
        </button>
      </div>

      <input
        type="text"
        placeholder="Search by name, email, username"
        className="mb-3 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
        onChange={(e) => onSearch(e.target.value)}
      />

      <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
        <label className="mb-2 flex items-center gap-2 text-xs text-slate-700">
          <input type="checkbox" checked={allSelected} onChange={(e) => onToggleSelectAll(e.target.checked)} />
          Select all visible staff
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => void onBulkToggleDailyOps(true)}
            disabled={selectedIds.length === 0}
            className="rounded bg-cyan-600 px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
          >
            Bulk Allow Daily Ops
          </button>
          <button
            onClick={() => void onBulkToggleDailyOps(false)}
            disabled={selectedIds.length === 0}
            className="rounded bg-rose-600 px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
          >
            Bulk Revoke Daily Ops
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="grid grid-cols-2 gap-2">
            <input className="rounded border px-2 py-1.5 text-sm" placeholder="First name" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            <input className="rounded border px-2 py-1.5 text-sm" placeholder="Last name" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            <input className="rounded border px-2 py-1.5 text-sm" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <input className="rounded border px-2 py-1.5 text-sm" placeholder="Mobile" value={form.mobile} onChange={(e) => setForm({ ...form, mobile: e.target.value })} />
            <input className="rounded border px-2 py-1.5 text-sm" placeholder="Department" value={form.department || ''} onChange={(e) => setForm({ ...form, department: e.target.value })} />
            <input className="rounded border px-2 py-1.5 text-sm" placeholder="Designation" value={form.designation || ''} onChange={(e) => setForm({ ...form, designation: e.target.value })} />
          </div>
          <button onClick={submit} className="mt-2 w-full rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700">Create Staff</button>
        </div>
      )}

      <div className="max-h-[65vh] space-y-2 overflow-auto pr-1">
        {loading ? (
          <div className="rounded border border-dashed p-3 text-sm text-slate-500">Loading staff...</div>
        ) : items.length === 0 ? (
          <div className="rounded border border-dashed p-3 text-sm text-slate-500">No staff found for this branch.</div>
        ) : (
          items.map((item) => (
            <div
              key={item.staff_profile_id}
              className={`w-full rounded-xl border p-3 text-left transition ${selectedId === item.staff_profile_id ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200 bg-white hover:border-slate-300'}`}
            >
              <div className="mb-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(item.staff_profile_id)}
                  onChange={() => onToggleSelect(item.staff_profile_id)}
                />
                <button onClick={() => onSelect(item.staff_profile_id)} className="flex-1 text-left">
                  <p className="text-sm font-semibold text-slate-900">{item.full_name}</p>
                  <p className="text-xs text-slate-500">{item.staff_id} • {item.username}</p>
                </button>
              </div>
              <p className="text-xs text-slate-500">{item.department || 'No department'} • {item.status}</p>
              <p className="mt-1 text-[11px] font-semibold text-slate-600">
                Daily Ops: {item.can_access_daily_ops ? 'Allowed' : 'Blocked'}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
