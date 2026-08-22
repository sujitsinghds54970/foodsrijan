import React, { useState, useEffect } from 'react'

interface LISProps {
  activeTab: string
}

interface MenuItemOrder {
  id: number
  order_number: string
  patient_id: number
  total_amount: number
  status: string
  order_date: string
  priority: string
}

interface LabMenuItem {
  id: number
  test_code: string
  test_name: string
  category: string
  sample_type: string
  base_price: number
  turnaround_time_hours: number
}

export default function LIS({ activeTab }: LISProps) {
  const [orders, setOrders] = useState<MenuItemOrder[]>([])
  const [menu_items, setMenuItems] = useState<LabMenuItem[]>([])
  const [loading, setLoading] = useState(false)
  const [showNewOrder, setShowNewOrder] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<MenuItemOrder | null>(null)

  useEffect(() => {
    if (activeTab === 'lis') {
      fetchOrders()
      fetchMenuItems()
    }
  }, [activeTab])

  const fetchOrders = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/lis/orders')
      const data = await response.json()
      if (data.success) {
        setOrders(data.orders || [])
      }
    } catch (error) {
      console.error('Error fetching orders:', error)
    }
    setLoading(false)
  }

  const fetchMenuItems = async () => {
    try {
      const response = await fetch('/api/lis/test-master')
      const data = await response.json()
      if (data.success) {
        setMenuItems(data.menu_items || [])
      }
    } catch (error) {
      console.error('Error fetching menu_items:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ordered': return 'bg-blue-100 text-blue-800'
      case 'sample_collected': return 'bg-yellow-100 text-yellow-800'
      case 'sample_received': return 'bg-orange-100 text-orange-800'
      case 'in_progress': return 'bg-purple-100 text-purple-800'
      case 'result_entered': return 'bg-indigo-100 text-indigo-800'
      case 'verified': return 'bg-teal-100 text-teal-800'
      case 'report_generated': return 'bg-green-100 text-green-800'
      case 'delivered': return 'bg-green-200 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  if (activeTab !== 'lis') return null

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">LIS - Laboratory Information System</h1>
          <p className="text-gray-600">Manage lab menu_items, orders, and results</p>
        </div>
        <div className="space-x-2">
          <button
            onClick={() => setShowNewOrder(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            + New MenuItem Order
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total Orders</div>
          <div className="text-2xl font-bold">{orders.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Pending</div>
          <div className="text-2xl font-bold text-yellow-600">
            {orders.filter(o => o.status === 'ordered').length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">In Progress</div>
          <div className="text-2xl font-bold text-blue-600">
            {orders.filter(o => ['sample_collected', 'sample_received', 'in_progress'].includes(o.status)).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Completed</div>
          <div className="text-2xl font-bold text-green-600">
            {orders.filter(o => o.status === 'delivered').length}
          </div>
        </div>
      </div>

      {/* MenuItem Categories */}
      <div className="bg-white rounded-lg shadow mb-6 p-4">
        <h2 className="text-lg font-semibold mb-4">Available MenuItem Categories</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {['Hematology', 'Biochemistry', 'Microbiology', 'Serology', 'Pathology', 'Radiology', 'Cardiology', 'Endocrinology'].map(cat => (
            <div key={cat} className="bg-gray-50 rounded-lg p-3 text-center">
              <div className="font-medium text-gray-700">{cat}</div>
              <div className="text-sm text-gray-500">{menu_items.filter(t => t.category === cat.toLowerCase()).length} menu_items</div>
            </div>
          ))}
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold">Recent MenuItem Orders</h2>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : orders.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No test orders found</div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Order #</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Customer ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Amount</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Priority</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Status</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Date</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.slice(0, 10).map(order => (
                <tr key={order.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{order.order_number}</td>
                  <td className="px-4 py-3">#{order.patient_id}</td>
                  <td className="px-4 py-3">₹{order.total_amount.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${order.priority === 'urgent' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
                      {order.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs ${getStatusColor(order.status)}`}>
                      {order.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(order.order_date).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setSelectedOrder(order)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

