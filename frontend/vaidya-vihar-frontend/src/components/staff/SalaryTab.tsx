import { useEffect, useMemo, useRef, useState } from 'react'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import toast from 'react-hot-toast'

import { getApiErrorMessage, staffSelfApi } from './api'
import { StaffSalaryHistoryRow, StaffSalaryResponse } from './types'

const monthLabel = (month: number, year: number) => new Date(year, Math.max(month - 1, 0), 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })

export default function SalaryTab() {
  const [loading, setLoading] = useState(true)
  const [salary, setSalary] = useState<StaffSalaryResponse | null>(null)
  const [selected, setSelected] = useState<StaffSalaryHistoryRow | null>(null)
  const payslipRef = useRef<HTMLDivElement>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await staffSelfApi.getMySalary()
      setSalary(data)
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
    pdf.addImage(img, 'PNG', 10, 10, 190, 110)
    const suffix = selected ? `${selected.year}-${String(selected.month).padStart(2, '0')}` : 'current'
    pdf.save(`staff_payslip_${suffix}.pdf`)
  }

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

        <div ref={payslipRef} className="rounded-2xl border border-indigo-100 bg-gradient-to-br from-white to-indigo-50 p-5 dark:border-indigo-900 dark:from-slate-900 dark:to-slate-800">
          <p className="text-lg font-bold text-slate-900 dark:text-slate-100">Payslip {selected ? monthLabel(selected.month, selected.year) : 'Current'}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-xl bg-white p-3 dark:bg-slate-900"><p className="text-xs text-slate-500 dark:text-slate-400">Basic</p><p className="text-lg font-bold text-slate-900 dark:text-slate-100">{effective?.basic || 0}</p></div>
            <div className="rounded-xl bg-white p-3 dark:bg-slate-900"><p className="text-xs text-slate-500 dark:text-slate-400">Allowances</p><p className="text-lg font-bold text-slate-900 dark:text-slate-100">{effective?.allowances || 0}</p></div>
            <div className="rounded-xl bg-white p-3 dark:bg-slate-900"><p className="text-xs text-slate-500 dark:text-slate-400">Deductions</p><p className="text-lg font-bold text-slate-900 dark:text-slate-100">{effective?.deductions || 0}</p></div>
            <div className="rounded-xl bg-white p-3 dark:bg-slate-900"><p className="text-xs text-slate-500 dark:text-slate-400">Net Pay</p><p className="text-lg font-bold text-indigo-700 dark:text-indigo-300">{effective?.net_pay || 0}</p></div>
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
