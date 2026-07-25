import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { getApiErrorMessage, staffApi } from './api'
import { StaffSalary } from './types'

interface SalarySectionProps {
  staffProfileId: number
  salary: StaffSalary
  onUpdated: (next: StaffSalary) => void
}

export default function SalarySection({ staffProfileId, salary, onUpdated }: SalarySectionProps) {
  const [form, setForm] = useState<StaffSalary>(salary)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setForm(salary)
  }, [salary])

  const save = async () => {
    setSaving(true)
    try {
      const payload = {
        ...form,
        net_pay: Number(form.basic || 0) + Number(form.hra || 0) + Number(form.allowances || 0) - Number(form.deductions || 0),
      }
      const updated = await staffApi.updateSalary(staffProfileId, payload)
      onUpdated(updated)
      toast.success('Salary details updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to update salary'))
    } finally {
      setSaving(false)
    }
  }

  const net = Number(form.basic || 0) + Number(form.hra || 0) + Number(form.allowances || 0) - Number(form.deductions || 0)

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-bold text-slate-900">Salary & Bank</h3>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <input type="number" className="rounded border px-2 py-1.5 text-sm" placeholder="Basic" value={form.basic} onChange={(e) => setForm({ ...form, basic: Number(e.target.value || 0) })} />
        <input type="number" className="rounded border px-2 py-1.5 text-sm" placeholder="HRA" value={form.hra} onChange={(e) => setForm({ ...form, hra: Number(e.target.value || 0) })} />
        <input type="number" className="rounded border px-2 py-1.5 text-sm" placeholder="Allowances" value={form.allowances} onChange={(e) => setForm({ ...form, allowances: Number(e.target.value || 0) })} />
        <input type="number" className="rounded border px-2 py-1.5 text-sm" placeholder="Deductions" value={form.deductions} onChange={(e) => setForm({ ...form, deductions: Number(e.target.value || 0) })} />
      </div>

      <p className="mt-2 text-xs font-semibold text-emerald-700">Net Pay: {net.toFixed(2)}</p>

      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        <input className="rounded border px-2 py-1.5 text-sm" placeholder="Bank Name" value={form.bank_name || ''} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
        <input className="rounded border px-2 py-1.5 text-sm" placeholder="Account Number" value={form.account_number || ''} onChange={(e) => setForm({ ...form, account_number: e.target.value })} />
        <input className="rounded border px-2 py-1.5 text-sm" placeholder="IFSC" value={form.ifsc_code || ''} onChange={(e) => setForm({ ...form, ifsc_code: e.target.value })} />
        <input className="rounded border px-2 py-1.5 text-sm" placeholder="UPI ID" value={form.upi_id || ''} onChange={(e) => setForm({ ...form, upi_id: e.target.value })} />
      </div>

      <button onClick={save} disabled={saving} className="mt-3 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
        {saving ? 'Saving...' : 'Save Salary'}
      </button>
    </div>
  )
}
