import { useCallback, useEffect, useMemo, useState } from 'react'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'
import {
  approveExpense,
  createExpense,
  createInvoice,
  createTransaction,
  generateInvoicePdf,
  getGstReport,
  getProfitLoss,
  listExpenses,
  listInvoices,
  listTransactions,
  markInvoicePaid,
  sendInvoice,
} from './api'
import { FinanceExpense, FinanceInvoice, FinanceTransaction, FinanceTransactionType } from './types'

const txColumnHelper = createColumnHelper<FinanceTransaction>()

function toIsoDate(value: Date): string {
  return value.toISOString().slice(0, 10)
}

function formatMoney(amount: number): string {
  return `Rs ${Number(amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

interface AccountsModuleProps {
  branchId?: number
}

export default function AccountsModule({ branchId }: AccountsModuleProps) {
  const { user } = useAuth()
  const forcedBranchId = Number(branchId)
  const effectiveBranchId = Number.isFinite(forcedBranchId) && forcedBranchId > 0
    ? forcedBranchId
    : user?.role === 'super_admin'
      ? undefined
      : (user?.branch_id ? Number(user.branch_id) : undefined)
  const [transactions, setTransactions] = useState<FinanceTransaction[]>([])
  const [invoices, setInvoices] = useState<FinanceInvoice[]>([])
  const [expenses, setExpenses] = useState<FinanceExpense[]>([])

  const [loading, setLoading] = useState(false)
  const [activeView, setActiveView] = useState<'dashboard' | 'transactions' | 'invoices' | 'expenses'>('dashboard')

  const [startDate, setStartDate] = useState<string>(toIsoDate(new Date(Date.now() - 29 * 24 * 3600 * 1000)))
  const [endDate, setEndDate] = useState<string>(toIsoDate(new Date()))
  const [transactionType, setTransactionType] = useState<FinanceTransactionType | ''>('')

  const [plSummary, setPlSummary] = useState<{ revenue: number; expense: number; net_profit: number } | null>(null)
  const [gstSummary, setGstSummary] = useState<{ invoice_count: number; taxable_amount: number; gst_amount: number } | null>(null)

  const [newTx, setNewTx] = useState({
    type: 'revenue' as FinanceTransactionType,
    amount: '',
    description: '',
    category: '',
    payment_method: 'cash',
  })

  const [newInvoice, setNewInvoice] = useState({
    patient_name: '',
    total_amount: '',
    tax_amount: '',
    gst_rate: '0',
    status: 'pending' as 'pending' | 'paid' | 'cancelled',
    due_date: '',
  })

  const [newExpense, setNewExpense] = useState({
    category: '',
    amount: '',
    description: '',
    status: 'pending',
    payment_method: 'cash',
    attachment: null as File | null,
  })

  const loadAllData = useCallback(async () => {
    try {
      setLoading(true)
      const [txData, invData, expData] = await Promise.all([
        listTransactions({ branch_id: effectiveBranchId, start: `${startDate}T00:00:00`, end: `${endDate}T23:59:59`, type: transactionType || undefined }),
        listInvoices({ branch_id: effectiveBranchId }),
        listExpenses({ branch_id: effectiveBranchId }),
      ])

      setTransactions(txData)
      setInvoices(invData)
      setExpenses(expData)

      const month = new Date().getMonth() + 1
      const year = new Date().getFullYear()

      const [pl, gst] = await Promise.all([
        getProfitLoss({ start: `${startDate}T00:00:00`, end: `${endDate}T23:59:59`, branch_id: effectiveBranchId }),
        getGstReport({ month, year, branch_id: effectiveBranchId }),
      ])

      setPlSummary(pl)
      setGstSummary(gst)
    } catch (error) {
      toast.error('Failed to load accounts data')
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, transactionType, effectiveBranchId])

  useEffect(() => {
    loadAllData().catch(() => {
      toast.error('Failed to initialize accounts module')
    })
  }, [loadAllData])

  useEffect(() => {
    if (activeView === 'transactions' || activeView === 'dashboard') {
      loadAllData().catch(() => {
        toast.error('Failed to refresh accounts data')
      })
    }
  }, [activeView, loadAllData])

  const kpis = useMemo(() => {
    const revenue = transactions.filter((t) => t.type === 'revenue').reduce((sum, item) => sum + Number(item.amount), 0)
    const expense = transactions.filter((t) => t.type === 'expense').reduce((sum, item) => sum + Number(item.amount), 0)
    const pendingInvoices = invoices.filter((item) => item.status === 'pending').length
    const pendingExpenses = expenses.filter((item) => item.status === 'pending').length

    return {
      revenue,
      expense,
      net: revenue - expense,
      pendingInvoices,
      pendingExpenses,
    }
  }, [transactions, invoices, expenses])

  const trendData = useMemo(() => {
    const map = new Map<string, { date: string; revenue: number; expense: number }>()

    transactions.forEach((tx) => {
      const key = tx.date.slice(0, 10)
      if (!map.has(key)) {
        map.set(key, { date: key, revenue: 0, expense: 0 })
      }
      const slot = map.get(key)
      if (!slot) return
      if (tx.type === 'revenue') slot.revenue += Number(tx.amount)
      if (tx.type === 'expense') slot.expense += Number(tx.amount)
    })

    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
  }, [transactions])

  const txColumns = useMemo(
    () => [
      txColumnHelper.accessor('date', {
        header: 'Date',
        cell: (info) => new Date(info.getValue()).toLocaleString(),
      }),
      txColumnHelper.accessor('type', {
        header: 'Type',
        cell: (info) => (
          <span
            className={`rounded px-2 py-1 text-xs font-semibold ${
              info.getValue() === 'revenue' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
            }`}
          >
            {info.getValue()}
          </span>
        ),
      }),
      txColumnHelper.accessor('amount', {
        header: 'Amount',
        cell: (info) => <span className="font-semibold">{formatMoney(Number(info.getValue()))}</span>,
      }),
      txColumnHelper.accessor('category', {
        header: 'Category',
      }),
      txColumnHelper.accessor('payment_method', {
        header: 'Payment',
      }),
      txColumnHelper.accessor('description', {
        header: 'Description',
      }),
      txColumnHelper.accessor('reference_id', {
        header: 'Reference',
      }),
    ],
    []
  )

  const txTable = useReactTable({
    data: transactions,
    columns: txColumns,
    getCoreRowModel: getCoreRowModel(),
  })

  async function onCreateTransaction() {
    try {
      if (!newTx.amount) {
        toast.error('Amount is required')
        return
      }

      await createTransaction({
        branch_id: effectiveBranchId,
        type: newTx.type,
        amount: Number(newTx.amount),
        description: newTx.description,
        category: newTx.category,
        payment_method: newTx.payment_method,
      })

      setNewTx({ type: 'revenue', amount: '', description: '', category: '', payment_method: 'cash' })
      toast.success('Transaction created')
      await loadAllData()
    } catch {
      toast.error('Failed to create transaction')
    }
  }

  async function onCreateInvoice() {
    try {
      if (!newInvoice.total_amount) {
        toast.error('Invoice total is required')
        return
      }

      await createInvoice({
        branch_id: effectiveBranchId,
        patient_name: newInvoice.patient_name || undefined,
        total_amount: Number(newInvoice.total_amount),
        tax_amount: Number(newInvoice.tax_amount || 0),
        gst_rate: Number(newInvoice.gst_rate || 0),
        status: newInvoice.status,
        due_date: newInvoice.due_date ? `${newInvoice.due_date}T00:00:00` : undefined,
      })

      setNewInvoice({
        patient_name: '',
        total_amount: '',
        tax_amount: '',
        gst_rate: '0',
        status: 'pending',
        due_date: '',
      })
      toast.success('Invoice created')
      await loadAllData()
    } catch {
      toast.error('Failed to create invoice')
    }
  }

  async function onCreateExpense() {
    try {
      if (!newExpense.category || !newExpense.amount) {
        toast.error('Category and amount are required')
        return
      }

      await createExpense({
        branch_id: effectiveBranchId,
        category: newExpense.category,
        amount: Number(newExpense.amount),
        description: newExpense.description,
        status: newExpense.status,
        payment_method: newExpense.payment_method,
        attachment: newExpense.attachment,
      })

      setNewExpense({
        category: '',
        amount: '',
        description: '',
        status: 'pending',
        payment_method: 'cash',
        attachment: null,
      })
      toast.success('Expense created')
      await loadAllData()
    } catch {
      toast.error('Failed to create expense')
    }
  }

  if (!user) return null

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-800">Accounts</h1>
          <p className="text-slate-500">Finance operations, invoices, expenses, and reporting</p>
        </div>
        <div className="flex gap-2">
          {(['dashboard', 'transactions', 'invoices', 'expenses'] as const).map((view) => (
            <button
              key={view}
              onClick={() => setActiveView(view)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
                activeView === view ? 'bg-slate-800 text-white' : 'bg-white text-slate-700 hover:bg-slate-100'
              }`}
            >
              {view[0].toUpperCase() + view.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {activeView === 'dashboard' && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-5">
            <KpiCard title="Revenue" value={formatMoney(kpis.revenue)} tone="emerald" />
            <KpiCard title="Expense" value={formatMoney(kpis.expense)} tone="rose" />
            <KpiCard title="Net Profit" value={formatMoney(kpis.net)} tone={kpis.net >= 0 ? 'teal' : 'amber'} />
            <KpiCard title="Pending Invoices" value={String(kpis.pendingInvoices)} tone="indigo" />
            <KpiCard title="Pending Expenses" value={String(kpis.pendingExpenses)} tone="orange" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-2xl bg-white p-5 shadow-sm lg:col-span-2">
              <h3 className="mb-4 text-lg font-semibold text-slate-800">Revenue vs Expense Trend</h3>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Area type="monotone" dataKey="revenue" stroke="#0f766e" fill="#5eead4" fillOpacity={0.5} />
                    <Area type="monotone" dataKey="expense" stroke="#be123c" fill="#fda4af" fillOpacity={0.45} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl bg-white p-5 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-slate-800">Tax Snapshot</h3>
              <div className="space-y-3 text-sm">
                <InfoRow label="P/L Revenue" value={formatMoney(plSummary?.revenue || 0)} />
                <InfoRow label="P/L Expense" value={formatMoney(plSummary?.expense || 0)} />
                <InfoRow label="P/L Net" value={formatMoney(plSummary?.net_profit || 0)} />
                <InfoRow label="Invoices (Month)" value={String(gstSummary?.invoice_count || 0)} />
                <InfoRow label="Taxable Amount" value={formatMoney(gstSummary?.taxable_amount || 0)} />
                <InfoRow label="GST Amount" value={formatMoney(gstSummary?.gst_amount || 0)} />
              </div>
            </div>
          </div>
        </>
      )}

      {activeView === 'transactions' && (
        <div className="space-y-4 rounded-2xl bg-white p-5 shadow-sm">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded border border-slate-300 px-3 py-2"
            />
            <select
              value={transactionType}
              onChange={(e) => setTransactionType(e.target.value as FinanceTransactionType | '')}
              className="rounded border border-slate-300 px-3 py-2"
            >
              <option value="">All Types</option>
              <option value="revenue">Revenue</option>
              <option value="expense">Expense</option>
              <option value="transfer">Transfer</option>
            </select>
            <button onClick={() => loadAllData()} className="rounded bg-slate-800 px-4 py-2 text-white">
              Apply Filters
            </button>
            <button
              onClick={() => {
                setStartDate(toIsoDate(new Date(Date.now() - 29 * 24 * 3600 * 1000)))
                setEndDate(toIsoDate(new Date()))
                setTransactionType('')
              }}
              className="rounded bg-slate-100 px-4 py-2 text-slate-700"
            >
              Reset
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 p-4 md:grid-cols-5">
            <select
              value={newTx.type}
              onChange={(e) => setNewTx((s) => ({ ...s, type: e.target.value as FinanceTransactionType }))}
              className="rounded border border-slate-300 px-3 py-2"
            >
              <option value="revenue">Revenue</option>
              <option value="expense">Expense</option>
              <option value="transfer">Transfer</option>
            </select>
            <input
              value={newTx.amount}
              onChange={(e) => setNewTx((s) => ({ ...s, amount: e.target.value }))}
              placeholder="Amount"
              type="number"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newTx.category}
              onChange={(e) => setNewTx((s) => ({ ...s, category: e.target.value }))}
              placeholder="Category"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newTx.description}
              onChange={(e) => setNewTx((s) => ({ ...s, description: e.target.value }))}
              placeholder="Description"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <button onClick={onCreateTransaction} className="rounded bg-emerald-600 px-4 py-2 font-semibold text-white">
              Add Transaction
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                {txTable.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id} className="border-b border-slate-200 bg-slate-50">
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-3 py-2 text-left font-semibold text-slate-700">
                        {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {txTable.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2 text-slate-700">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeView === 'invoices' && (
        <div className="space-y-4 rounded-2xl bg-white p-5 shadow-sm">
          <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 p-4 md:grid-cols-7">
            <input
              value={newInvoice.patient_name}
              onChange={(e) => setNewInvoice((s) => ({ ...s, patient_name: e.target.value }))}
              placeholder="Patient name"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newInvoice.total_amount}
              onChange={(e) => setNewInvoice((s) => ({ ...s, total_amount: e.target.value }))}
              placeholder="Total"
              type="number"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newInvoice.tax_amount}
              onChange={(e) => setNewInvoice((s) => ({ ...s, tax_amount: e.target.value }))}
              placeholder="Tax"
              type="number"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newInvoice.gst_rate}
              onChange={(e) => setNewInvoice((s) => ({ ...s, gst_rate: e.target.value }))}
              placeholder="GST %"
              type="number"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              type="date"
              value={newInvoice.due_date}
              onChange={(e) => setNewInvoice((s) => ({ ...s, due_date: e.target.value }))}
              className="rounded border border-slate-300 px-3 py-2"
            />
            <select
              value={newInvoice.status}
              onChange={(e) => setNewInvoice((s) => ({ ...s, status: e.target.value as 'pending' | 'paid' | 'cancelled' }))}
              className="rounded border border-slate-300 px-3 py-2"
            >
              <option value="pending">Pending</option>
              <option value="paid">Paid</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <button onClick={onCreateInvoice} className="rounded bg-indigo-600 px-4 py-2 font-semibold text-white">
              Create Invoice
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left">Invoice #</th>
                  <th className="px-3 py-2 text-left">Patient</th>
                  <th className="px-3 py-2 text-left">Total</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Due</th>
                  <th className="px-3 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-semibold">{invoice.invoice_number}</td>
                    <td className="px-3 py-2">{invoice.patient_name || '-'}</td>
                    <td className="px-3 py-2">{formatMoney(Number(invoice.total_amount))}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-1 text-xs font-semibold ${
                          invoice.status === 'paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {invoice.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">{invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : '-'}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={async () => {
                            try {
                              const result = await generateInvoicePdf(invoice.id)
                              toast.success('PDF generated')
                              const pdfHref = result.pdf_url.startsWith('http') ? result.pdf_url : `http://127.0.0.1:8000${result.pdf_url}`
                              window.open(pdfHref, '_blank', 'noopener,noreferrer')
                              await loadAllData()
                            } catch {
                              toast.error('Failed to generate PDF')
                            }
                          }}
                          className="rounded bg-slate-100 px-2 py-1 text-xs"
                        >
                          Generate PDF
                        </button>
                        {invoice.pdf_url && (
                          <a
                            href={invoice.pdf_url.startsWith('http') ? invoice.pdf_url : `http://127.0.0.1:8000${invoice.pdf_url}`}
                            target="_blank"
                            rel="noreferrer"
                            className="rounded bg-slate-200 px-2 py-1 text-xs text-slate-700"
                          >
                            View PDF
                          </a>
                        )}
                        <button
                          onClick={async () => {
                            try {
                              const result = await sendInvoice(invoice.id, 'whatsapp')
                              if (result.channel_url) {
                                window.open(result.channel_url, '_blank', 'noopener,noreferrer')
                              }
                              toast.success('WhatsApp link ready')
                            } catch {
                              toast.error('Failed to prepare WhatsApp link')
                            }
                          }}
                          className="rounded bg-teal-100 px-2 py-1 text-xs text-teal-700"
                        >
                          WhatsApp
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              const result = await sendInvoice(invoice.id, 'email')
                              if (result.channel_url) {
                                window.open(result.channel_url, '_blank', 'noopener,noreferrer')
                              }
                              toast.success('Email link ready')
                            } catch {
                              toast.error('Failed to prepare Email link')
                            }
                          }}
                          className="rounded bg-cyan-100 px-2 py-1 text-xs text-cyan-700"
                        >
                          Email
                        </button>
                        {invoice.status !== 'paid' && (
                          <button
                            onClick={async () => {
                              try {
                                await markInvoicePaid(invoice.id)
                                toast.success('Invoice marked paid')
                                await loadAllData()
                              } catch {
                                toast.error('Failed to mark paid')
                              }
                            }}
                            className="rounded bg-emerald-600 px-2 py-1 text-xs text-white"
                          >
                            Mark Paid
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeView === 'expenses' && (
        <div className="space-y-4 rounded-2xl bg-white p-5 shadow-sm">
          <div className="grid grid-cols-1 gap-3 rounded-xl border border-slate-200 p-4 md:grid-cols-7">
            <input
              value={newExpense.category}
              onChange={(e) => setNewExpense((s) => ({ ...s, category: e.target.value }))}
              placeholder="Category"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newExpense.amount}
              onChange={(e) => setNewExpense((s) => ({ ...s, amount: e.target.value }))}
              placeholder="Amount"
              type="number"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <input
              value={newExpense.description}
              onChange={(e) => setNewExpense((s) => ({ ...s, description: e.target.value }))}
              placeholder="Description"
              className="rounded border border-slate-300 px-3 py-2"
            />
            <select
              value={newExpense.status}
              onChange={(e) => setNewExpense((s) => ({ ...s, status: e.target.value }))}
              className="rounded border border-slate-300 px-3 py-2"
            >
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
            <select
              value={newExpense.payment_method}
              onChange={(e) => setNewExpense((s) => ({ ...s, payment_method: e.target.value }))}
              className="rounded border border-slate-300 px-3 py-2"
            >
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="card">Card</option>
              <option value="bank_transfer">Bank Transfer</option>
            </select>
            <input
              type="file"
              onChange={(e) => setNewExpense((s) => ({ ...s, attachment: e.target.files?.[0] || null }))}
              className="rounded border border-slate-300 px-3 py-2"
            />
            <button onClick={onCreateExpense} className="rounded bg-rose-600 px-4 py-2 font-semibold text-white">
              Add Expense
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Category</th>
                  <th className="px-3 py-2 text-left">Amount</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-left">Receipt</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Action</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((expense) => (
                  <tr key={expense.id} className="border-b border-slate-100">
                    <td className="px-3 py-2">{new Date(expense.date).toLocaleDateString()}</td>
                    <td className="px-3 py-2">{expense.category}</td>
                    <td className="px-3 py-2 font-semibold">{formatMoney(Number(expense.amount))}</td>
                    <td className="px-3 py-2">{expense.description || '-'}</td>
                    <td className="px-3 py-2">
                      {expense.attachment_url ? (
                        <a href={`http://127.0.0.1:8000${expense.attachment_url}`} target="_blank" rel="noreferrer" className="text-cyan-700 underline">
                          View
                        </a>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-1 text-xs font-semibold ${
                          expense.status === 'approved' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {expense.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {expense.status !== 'approved' && (
                        <button
                          onClick={async () => {
                            try {
                              await approveExpense(expense.id)
                              toast.success('Expense approved')
                              await loadAllData()
                            } catch {
                              toast.error('Failed to approve expense')
                            }
                          }}
                          className="rounded bg-emerald-600 px-2 py-1 text-xs text-white"
                        >
                          Approve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {loading && <div className="text-sm text-slate-500">Loading accounts data...</div>}
    </div>
  )
}

function KpiCard({ title, value, tone }: { title: string; value: string; tone: 'emerald' | 'rose' | 'teal' | 'indigo' | 'orange' | 'amber' }) {
  const toneMap: Record<string, string> = {
    emerald: 'from-emerald-500 to-teal-600',
    rose: 'from-rose-500 to-red-600',
    teal: 'from-teal-500 to-cyan-600',
    indigo: 'from-indigo-500 to-blue-600',
    orange: 'from-orange-500 to-amber-600',
    amber: 'from-amber-500 to-yellow-600',
  }

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
      <p className={`mt-2 bg-gradient-to-r ${toneMap[tone]} bg-clip-text text-2xl font-black text-transparent`}>{value}</p>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold text-slate-700">{value}</span>
    </div>
  )
}
