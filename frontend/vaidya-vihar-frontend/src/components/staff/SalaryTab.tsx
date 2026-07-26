import { useEffect, useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import QRCode from 'react-qr-code'
import toast from 'react-hot-toast'

import { getApiErrorMessage, resolveStaffMediaUrl, staffSelfApi } from './api'
import { StaffSalaryHistoryRow, StaffSalaryResponse, StaffSelfProfile } from './types'

const monthLabel = (month: number, year: number) => new Date(year, Math.max(month - 1, 0), 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })

export default function SalaryTab() {
  const [loading, setLoading] = useState(true)
  const [salary, setSalary] = useState<StaffSalaryResponse | null>(null)
  const [profile, setProfile] = useState<StaffSelfProfile | null>(null)
  const [selected, setSelected] = useState<StaffSalaryHistoryRow | null>(null)
  const payslipRef = useRef<HTMLDivElement>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const [data, me] = await Promise.all([staffSelfApi.getMySalary(), staffSelfApi.getMe()])
      setSalary(data)
      setProfile(me)
      setSelected(data.history[0] || null)
    } catch (error: any) {
      toast.error(getApiErrorMessage(error, 'Unable to load salary details'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const effective = useMemo(() => {
    if (selected) {
      return {
        basic: selected.basic,
        hra: selected.hra,
        allowances: selected.allowances,
        deductions: selected.deductions,
        net_pay: selected.net_pay,
      }
    }
    return salary?.current || null
  }, [salary, selected])

  const downloadPayslip = async () => {
    if (!payslipRef.current || !effective) return
    const canvas = await html2canvas(payslipRef.current, { scale: 2, backgroundColor: '#ffffff' })
    const img = canvas.toDataURL('image/png')
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageWidth = 190
    const pageHeight = (canvas.height * pageWidth) / canvas.width
    pdf.addImage(img, 'PNG', 10, 10, pageWidth, pageHeight)
    const suffix = selected ? `${selected.year}-${String(selected.month).padStart(2, '0')}` : 'current'
    pdf.save(`staff_payslip_${suffix}.pdf`)
  }

  const money = (value: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value || 0))
  const payPeriod = selected ? `${String(selected.month).padStart(2, '0')}/${selected.year}` : 'Current'
  const employeeId = profile?.staff_profile_id ? `ST${String(profile.staff_profile_id).padStart(7, '0')}` : '-'
  const dateOfJoining = '-'

  const earningsRows = [
    { label: 'Basic Salary', value: Number(effective?.basic || 0) },
    { label: 'DA', value: Number(effective?.basic || 0) * 0.1 },
    { label: 'HRA', value: Number(effective?.hra || 0) },
    { label: 'Shift Allowance', value: Number(effective?.allowances || 0) * 0.35 },
    { label: 'OT', value: Number(effective?.allowances || 0) * 0.3 },
    { label: 'Incentives', value: Math.max(0, Number(effective?.allowances || 0) * 0.35) },
    { label: 'Reimbursement', value: 0 },
  ]

  const deductionPool = Number(effective?.deductions || 0)
  const deductionRows = [
    { label: 'LOP', value: 0 },
    { label: 'PF', value: Number(effective?.basic || 0) * 0.12 },
    { label: 'ESI', value: Number(effective?.basic || 0) <= 21000 ? Number(effective?.basic || 0) * 0.0075 : 0 },
    { label: 'Professional Tax', value: Number(effective?.basic || 0) >= 25000 ? 200 : Number(effective?.basic || 0) >= 15000 ? 150 : Number(effective?.basic || 0) >= 10000 ? 75 : 0 },
    { label: 'TDS', value: Number(effective?.basic || 0) * 0.05 },
    { label: 'Statutory Deductions', value: 0 },
  ]
  const computedDeductionTotal = deductionRows.reduce((sum, row) => sum + row.value, 0)
  const adjustFactor = computedDeductionTotal > 0 ? deductionPool / computedDeductionTotal : 0
  const normalizedDeductionRows = deductionRows.map((row, index) => {
    if (index === deductionRows.length - 1) return { ...row, value: 0 }
    return { ...row, value: row.value * adjustFactor }
  })
  const normalizedDeductionSubtotal = normalizedDeductionRows.reduce((sum, row) => sum + row.value, 0)
  normalizedDeductionRows[normalizedDeductionRows.length - 1].value = Math.max(0, deductionPool - normalizedDeductionSubtotal)

  const grossPay = earningsRows.reduce((sum, row) => sum + row.value, 0)
  const totalDeductions = normalizedDeductionRows.reduce((sum, row) => sum + row.value, 0)
  const netPay = Number(effective?.net_pay || grossPay - totalDeductions)
  const qrValue = `PAYSLIP|EMP:${employeeId}|PERIOD:${payPeriod}|NET:${netPay}`

  if (loading) {
    return <div className="rounded-2xl bg-white/90 p-6 shadow-xl dark:bg-slate-900">Loading salary data...</div>
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl bg-emerald-50 p-4 shadow dark:bg-emerald-900/30"><p className="text-xs font-semibold uppercase text-emerald-700 dark:text-emerald-200">Basic</p><p className="mt-2 text-2xl font-extrabold text-emerald-900 dark:text-emerald-100">{effective?.basic || 0}</p></div>
        <div className="rounded-2xl bg-sky-50 p-4 shadow dark:bg-sky-900/30"><p className="text-xs font-semibold uppercase text-sky-700 dark:text-sky-200">HRA</p><p className="mt-2 text-2xl font-extrabold text-sky-900 dark:text-sky-100">{effective?.hra || 0}</p></div>
        <div className="rounded-2xl bg-amber-50 p-4 shadow dark:bg-amber-900/30"><p className="text-xs font-semibold uppercase text-amber-700 dark:text-amber-200">Deductions</p><p className="mt-2 text-2xl font-extrabold text-amber-900 dark:text-amber-100">{effective?.deductions || 0}</p></div>
        <div className="rounded-2xl bg-indigo-50 p-4 shadow dark:bg-indigo-900/30"><p className="text-xs font-semibold uppercase text-indigo-700 dark:text-indigo-200">Net Pay</p><p className="mt-2 text-2xl font-extrabold text-indigo-900 dark:text-indigo-100">{effective?.net_pay || 0}</p></div>
      </div>

      <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900/80">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Salary Management System</h2>
          <button onClick={downloadPayslip} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">Download Payslip</button>
        </div>

        <style>{`@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700;800&display=swap');`}</style>
        <div id="payslip-capture" ref={payslipRef} style={{ fontFamily: "'Noto Sans', sans-serif" }} className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-0 text-slate-800">

          <div className="relative">
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 text-white">
              <div className="flex items-start justify-between gap-4">
                <div className="h-16 w-16 overflow-hidden rounded-lg border border-white/40 bg-white/10 p-1">
                  {profile?.branch_logo_url ? (
                    <img src={resolveStaffMediaUrl(profile.branch_logo_url)} alt="Branch Logo" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-xs font-bold">LOGO</div>
                  )}
                </div>
                <div className="flex-1 text-right">
                  <p className="text-2xl font-bold">{profile?.branch_name || 'VaidyaVihar Diagnostic'}</p>
                  <p className="text-xs text-blue-100">{profile?.address || 'Branch Address'}</p>
                  <p className="text-xs text-blue-100">{profile?.mobile || '-'} • {profile?.email || '-'}</p>
                </div>
              </div>
              <p className="mt-4 text-center text-3xl font-extrabold tracking-[0.25em]">PAYSLIP</p>
            </div>

            <div className="space-y-5 p-6">
              <div className="grid grid-cols-2 gap-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
                <div className="space-y-1">
                  <p><span className="font-semibold text-slate-600">Employee Name:</span> {profile?.full_name || '-'}</p>
                  <p><span className="font-semibold text-slate-600">Employee ID:</span> {employeeId}</p>
                  <p><span className="font-semibold text-slate-600">Pay Period:</span> {payPeriod}</p>
                </div>
                <div className="space-y-1 text-right">
                  <p><span className="font-semibold text-slate-600">Department:</span> {profile?.department || '-'}</p>
                  <p><span className="font-semibold text-slate-600">Role:</span> {profile?.role || '-'}</p>
                  <p><span className="font-semibold text-slate-600">Date of Joining:</span> {dateOfJoining}</p>
                </div>
              </div>

              <div className="overflow-hidden rounded-xl border border-slate-200">
                <div className="grid grid-cols-2 bg-slate-100 text-sm font-bold text-slate-700">
                  <div className="border-r border-slate-200 px-4 py-2">Earnings</div>
                  <div className="px-4 py-2">Deductions</div>
                </div>
                {earningsRows.map((earning, index) => {
                  const deduction = normalizedDeductionRows[index]
                  return (
                    <div key={earning.label} className={`grid grid-cols-2 text-sm ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                      <div className="flex items-center justify-between border-r border-b border-slate-200 px-4 py-2">
                        <span>{earning.label}</span>
                        <span className="font-semibold">{money(earning.value)}</span>
                      </div>
                      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2">
                        <span>{deduction.label}</span>
                        <span className="font-semibold">{money(deduction.value)}</span>
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="rounded-xl border border-slate-300 bg-slate-100 p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-slate-700">Gross Pay</span>
                  <span className="font-bold">{money(grossPay)}</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-sm">
                  <span className="font-semibold text-slate-700">Total Deductions</span>
                  <span className="font-bold">{money(totalDeductions)}</span>
                </div>
                <div className="mt-3 border-t-2 border-gray-800 pt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-base font-bold text-slate-900">Net Pay</span>
                    <span className="text-3xl font-black text-blue-600">{money(netPay)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-end justify-between">
                <p className="text-xs text-slate-500">
                  Generated by VaidyaVihar Diagnostic. This is a computer-generated document.
                </p>
                <div className="rounded-lg border border-slate-300 bg-white p-2 text-center">
                  <QRCode value={qrValue} size={74} />
                  <p className="mt-1 text-[10px] font-semibold text-slate-600">Scan to Verify</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-700 dark:text-slate-300">
                <th className="py-2 pr-4">Month</th>
                <th className="py-2 pr-4">Basic</th>
                <th className="py-2 pr-4">Deductions</th>
                <th className="py-2 pr-4">Net Pay</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {(salary?.history || []).length === 0 ? (
                <tr><td colSpan={5} className="py-4 text-slate-500 dark:text-slate-400">No payslip history available.</td></tr>
              ) : (
                (salary?.history || []).map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="py-2 pr-4">{monthLabel(row.month, row.year)}</td>
                    <td className="py-2 pr-4">{row.basic}</td>
                    <td className="py-2 pr-4">{row.deductions}</td>
                    <td className="py-2 pr-4 font-bold text-indigo-600 dark:text-indigo-300">{row.net_pay}</td>
                    <td className="py-2">
                      <button onClick={() => setSelected(row)} className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800">View</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
