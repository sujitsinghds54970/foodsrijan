import { useEffect, useMemo, useState } from 'react'
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

  const grossPay = useMemo(
    () =>
      Number(form.basic || 0) +
      Number(form.da || 0) +
      Number(form.hra || 0) +
      Number(form.shift_allowance || 0) +
      Number(form.ot || 0) +
      Number(form.incentives || 0),
    [form.basic, form.da, form.hra, form.shift_allowance, form.ot, form.incentives],
  )

  const totalDeductions = useMemo(
    () => Number(form.lop || 0) + Number(form.statutory_deductions || 0),
    [form.lop, form.statutory_deductions],
  )

  const netPay = useMemo(() => grossPay - totalDeductions, [grossPay, totalDeductions])

  const save = async () => {
    setSaving(true)
    try {
      const payload = {
        ...form,
        allowances:
          Number(form.da || 0) +
          Number(form.shift_allowance || 0) +
          Number(form.ot || 0) +
          Number(form.incentives || 0),
        deductions: Number(form.lop || 0) + Number(form.statutory_deductions || 0),
        net_pay: netPay,
      }
      console.log('PAYLOAD SENT:', payload)
      const updated = await staffApi.updateSalary(staffProfileId, payload)
      console.log('BACKEND RESPONSE:', updated)
      onUpdated(updated)
      window.dispatchEvent(new CustomEvent('staff-salary-updated', { detail: { staffProfileId, salary: updated } }))
      toast.success('Salary details updated')
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Failed to update salary'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-bold text-slate-900">Salary & Bank</h3>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>Basic Salary</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter Basic Salary" value={form.basic} onChange={(e) => setForm({ ...form, basic: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>DA (Dearness Allowance)</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter DA Amount" value={Number(form.da || 0)} onChange={(e) => setForm({ ...form, da: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>HRA (House Rent Allowance)</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter HRA Amount" value={form.hra} onChange={(e) => setForm({ ...form, hra: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>Shift Allowance</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter Shift Allowance" value={Number(form.shift_allowance || 0)} onChange={(e) => setForm({ ...form, shift_allowance: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>OT (Overtime)</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter Overtime Amount" value={Number(form.ot || 0)} onChange={(e) => setForm({ ...form, ot: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>LOP (Loss of Pay)</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter LOP Amount" value={Number(form.lop || 0)} onChange={(e) => setForm({ ...form, lop: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>Incentives / Bonuses</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter Incentives / Bonuses" value={Number(form.incentives || 0)} onChange={(e) => setForm({ ...form, incentives: Number(e.target.value || 0) })} />
        </label>
        <label className="space-y-1 text-xs font-semibold text-slate-700">
          <span>Statutory Deductions (PF/ESI/TDS)</span>
          <input type="number" className="w-full rounded border px-2 py-1.5 text-sm font-normal" placeholder="Enter Statutory Deductions" value={Number(form.statutory_deductions || 0)} onChange={(e) => setForm({ ...form, statutory_deductions: Number(e.target.value || 0) })} />
        </label>
      </div>

      <div className="mt-2 grid grid-cols-1 gap-1 text-xs font-semibold text-slate-700 md:grid-cols-3">
        <p>Gross Pay: {grossPay.toFixed(2)}</p>
        <p>Deductions: {totalDeductions.toFixed(2)}</p>
        <p className="text-emerald-700">Net Pay: {netPay.toFixed(2)}</p>
      </div>

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
