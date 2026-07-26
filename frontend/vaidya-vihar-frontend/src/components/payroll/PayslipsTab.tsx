import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'

import { payrollApi } from './api'
import { PayslipItem } from './types'

export default function PayslipsTab() {
  const [items, setItems] = useState<PayslipItem[]>([])
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null)
  const lastErrorAtRef = useRef(0)

  const handleDownload = async (item: PayslipItem) => {
    const key = `${item.payroll_id}-${item.month}-${item.year}`
    if (downloadingKey === key) return

    try {
      setDownloadingKey(key)
      const fileName = `payslip_${String(item.month).padStart(2, '0')}_${item.year}.pdf`
      await payrollApi.downloadPayslip(item.download_url, fileName)
    } catch (error: any) {
      const now = Date.now()
      if (now - lastErrorAtRef.current >= 5000) {
        toast.error(error?.response?.data?.detail || 'Unable to download payslip PDF')
        lastErrorAtRef.current = now
      }
    } finally {
      setDownloadingKey(null)
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        setItems(await payrollApi.listMyPayslips())
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Unable to load payslips')
      }
    }
    void load()
  }, [])

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-bold text-slate-900">Payslips</h3>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-600">
            <tr>
              <th className="px-3 py-2">Month</th>
              <th className="px-3 py-2">Year</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Net Pay</th>
              <th className="px-3 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-slate-500" colSpan={5}>No payslips generated yet.</td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={`${item.payroll_id}-${item.month}-${item.year}`} className="border-t border-slate-100">
                  <td className="px-3 py-2">{String(item.month).padStart(2, '0')}</td>
                  <td className="px-3 py-2">{item.year}</td>
                  <td className="px-3 py-2">{item.status}</td>
                  <td className="px-3 py-2">INR {item.net_pay.toLocaleString()}</td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => void handleDownload(item)}
                      disabled={downloadingKey === `${item.payroll_id}-${item.month}-${item.year}`}
                      className="rounded bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-700"
                    >
                      {downloadingKey === `${item.payroll_id}-${item.month}-${item.year}` ? 'Downloading...' : 'Download PDF'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">Payslip PDFs include QR verification and password protection.</p>
    </div>
  )
}
