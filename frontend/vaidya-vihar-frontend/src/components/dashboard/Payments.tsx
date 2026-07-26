import React, { useState, useEffect } from 'react'

interface PaymentsProps {
  activeTab: string
  branchId?: number
}

interface Invoice {
  id: number
  invoice_number: string
  patient_id: number
  total_amount: number
  final_amount: number
  status: string
  payment_status: string
  created_at: string
}

interface Payment {
  id: number
  transaction_id: string
  amount: number
  payment_mode: string
  status: string
  created_at: string
}

export default function Payments({ activeTab, branchId }: PaymentsProps) {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(false)
  const [activeView, setActiveView] = useState<'invoices' | 'payments'>('invoices')

  useEffect(() => {
    if (activeTab === 'payments') {
      fetchInvoices()
      fetchPayments()
    }
  }, [activeTab])

  const fetchInvoices = async () => {
    setLoading(true)
    try {
      const query = branchId ? `?branch_id=${branchId}` : ''
      const response = await fetch(`/api/payments/invoices${query}`)
      const data = await response.json()
      if (data.success) {
        setInvoices(data.invoices || [])
      }
    } catch (error) {
      console.error('Error fetching invoices:', error)
    }
    setLoading(false)
  }

  const fetchPayments = async () => {
    try {
      const query = branchId ? `?branch_id=${branchId}` : ''
      const response = await fetch(`/api/payments/payments${query}`)
      const data = await response.json()
      if (data.success) {
        setPayments(data.payments || [])
      }
    } catch (error) {
      console.error('Error fetching payments:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid': return 'bg-green-100 text-green-800'
      case 'partial': return 'bg-yellow-100 text-yellow-800'
      case 'pending': return 'bg-gray-100 text-gray-800'
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (activeTab !== 'payments') return null

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Payment Management</h1>
          <p className="text-gray-600">Manage invoices, payments, and payment gateways</p>
        </div>
        <div className="space-x-2">
          <button
            onClick={() => setActiveView('invoices')}
            className={`px-4 py-2 rounded-lg ${activeView === 'invoices' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Invoices
          </button>
          <button
            onClick={() => setActiveView('payments')}
            className={`px-4 py-2 rounded-lg ${activeView === 'payments' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
          >
            Payments
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Invoices</div>
          <div className="text-2xl font-bold">{invoices.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Amount</div>
          <div className="text-2xl font-bold text-green-600">
            ₹{invoices.reduce((sum, inv) => sum + inv.final_amount, 0).toFixed(2)}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Pending Payments</div>
          <div className="text-2xl font-bold text-yellow-600">
            {invoices.filter(inv => inv.payment_status === 'pending').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Transactions</div>
          <div className="text-2xl font-bold">{payments.length}</div>
        </div>
      </div>

      {/* Payment Gateways */}
      <div className="bg-white rounded-lg shadow mb-6 p-4">
        <h2 className="text-lg font-semibold mb-4">Payment Gateways</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="border rounded-lg p-4 text-center">
            <div className="font-bold text-xl mb-2">Razorpay</div>
            <div className="text-sm text-green-600">● Active</div>
          </div>
          <div className="border rounded-lg p-4 text-center">
            <div className="font-bold text-xl mb-2">PayU</div>
            <div className="text-sm text-gray-500">● Not configured</div>
          </div>
          <div className="border rounded-lg p-4 text-center">
            <div className="font-bold text-xl mb-2">Cash</div>
            <div className="text-sm text-green-600">● Active</div>
          </div>
          <div className="border rounded-lg p-4 text-center">
            <div className="font-bold text-xl mb-2">UPI</div>
            <div className="text-sm text-green-600">● Active</div>
          </div>
        </div>
      </div>

      {/* Invoices Table */}
      {activeView === 'invoices' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Recent Invoices</h2>
          </div>
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading...</div>
          ) : invoices.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No invoices found</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Invoice #</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Patient ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Payment</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Date</th>
                </tr>
              </thead>
              <tbody>
                {invoices.slice(0, 10).map(invoice => (
                  <tr key={invoice.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{invoice.invoice_number}</td>
                    <td className="px-4 py-3">#{invoice.patient_id}</td>
                    <td className="px-4 py-3">₹{invoice.final_amount.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(invoice.status)}`}>
                        {invoice.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(invoice.payment_status)}`}>
                        {invoice.payment_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(invoice.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Payments Table */}
      {activeView === 'payments' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Recent Payments</h2>
          </div>
          {payments.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No payments found</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Transaction ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Amount</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Mode</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Date</th>
                </tr>
              </thead>
              <tbody>
                {payments.slice(0, 10).map(payment => (
                  <tr key={payment.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-sm">{payment.transaction_id}</td>
                    <td className="px-4 py-3">₹{payment.amount.toFixed(2)}</td>
                    <td className="px-4 py-3">{payment.payment_mode}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(payment.status)}`}>
                        {payment.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(payment.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
