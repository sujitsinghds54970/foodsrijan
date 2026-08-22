import React, { useState } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import axios from 'axios'

export default function Orders() {
  const { user } = useAuth()
  const [reportType, setOrderType] = useState('daily')
  const [dateRange, setDateRange] = useState({
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0]
  })
  const [loading, setLoading] = useState(false)
  const [reportData, setOrderData] = useState<any[]>([])

  const reportTypes = [
    { value: 'daily', label: 'Daily Entry Order', description: 'Customer visits and fees for specific dates' },
    { value: 'monthly', label: 'Monthly Summary', description: 'Monthly patient statistics and revenue' },
    { value: 'patient-history', label: 'Customer History', description: 'Complete patient visit history' },
    { value: 'revenue', label: 'Revenue Order', description: 'Financial summary and analysis' },
    { value: 'staff-performance', label: 'Staff Performance', description: 'Staff consultation statistics' }
  ]

  const generateOrder = async () => {
    try {
      setLoading(true)
      
      let endpoint = ''
      let params: any = {
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
        branch_id: user?.branch_id
      }

      switch (reportType) {
        case 'daily':
          endpoint = '/api/export/daily-entries'
          break
        case 'monthly':
          endpoint = '/api/export/monthly-summary'
          break
        case 'patient-history':
          endpoint = '/api/export/patient-history'
          break
        case 'revenue':
          endpoint = '/api/export/revenue'
          break
        case 'staff-performance':
          endpoint = '/api/export/staff-performance'
          break
      }

      const response = await axios.get(endpoint, { params })
      setOrderData(response.data || [])
      
    } catch (error) {
      console.error('Error generating report:', error)
      alert('Error generating report. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const exportToExcel = async () => {
    try {
      const endpointMap: { [key: string]: string } = {
        daily: '/api/export/daily-entries',
        monthly: '/api/export/monthly-summary',
        'patient-history': '/api/export/patient-history',
        revenue: '/api/export/revenue',
        'staff-performance': '/api/export/staff-performance'
      }

      const endpoint = endpointMap[reportType]
      const params = {
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
        branch_id: user?.branch_id,
        format: 'excel'
      }

      const response = await axios.get(endpoint, {
        params,
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${reportType}-report-${dateRange.start_date}-to-${dateRange.end_date}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      alert('Order exported successfully!')
      
    } catch (error) {
      console.error('Error exporting report:', error)
      alert('Error exporting report. Please try again.')
    }
  }

  const exportToPDF = async () => {
    try {
      const endpointMap: { [key: string]: string } = {
        daily: '/api/export/daily-entries',
        monthly: '/api/export/monthly-summary',
        'patient-history': '/api/export/patient-history',
        revenue: '/api/export/revenue',
        'staff-performance': '/api/export/staff-performance'
      }

      const endpoint = endpointMap[reportType]
      const params = {
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
        branch_id: user?.branch_id,
        format: 'pdf'
      }

      const response = await axios.get(endpoint, {
        params,
        responseType: 'blob'
      })
      
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${reportType}-report-${dateRange.start_date}-to-${dateRange.end_date}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      alert('PDF report exported successfully!')
      
    } catch (error) {
      console.error('Error exporting PDF:', error)
      alert('Error exporting PDF. Please try again.')
    }
  }

  const getCurrentMonth = () => {
    const now = new Date()
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)
    
    setDateRange({
      start_date: firstDay.toISOString().split('T')[0],
      end_date: lastDay.toISOString().split('T')[0]
    })
  }

  const getLastMonth = () => {
    const now = new Date()
    const firstDay = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const lastDay = new Date(now.getFullYear(), now.getMonth(), 0)
    
    setDateRange({
      start_date: firstDay.toISOString().split('T')[0],
      end_date: lastDay.toISOString().split('T')[0]
    })
  }

  const getThisYear = () => {
    const now = new Date()
    const firstDay = new Date(now.getFullYear(), 0, 1)
    const lastDay = new Date(now.getFullYear(), 11, 31)
    
    setDateRange({
      start_date: firstDay.toISOString().split('T')[0],
      end_date: lastDay.toISOString().split('T')[0]
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Orders & Analytics</h1>
            <p className="text-gray-600 mt-1">Generate and export comprehensive orders</p>
          </div>
        </div>
      </div>

      {/* Order Configuration */}
      <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Order Configuration</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Order Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Order Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setOrderType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {reportTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
            <p className="text-sm text-gray-500 mt-1">
              {reportTypes.find(t => t.value === reportType)?.description}
            </p>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Date Range
            </label>
            <div className="space-y-3">
              <div className="flex space-x-3">
                <input
                  type="date"
                  value={dateRange.start_date}
                  onChange={(e) => setDateRange({ ...dateRange, start_date: e.target.value })}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="date"
                  value={dateRange.end_date}
                  onChange={(e) => setDateRange({ ...dateRange, end_date: e.target.value })}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              {/* Quick Date Buttons */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setDateRange({
                    start_date: new Date().toISOString().split('T')[0],
                    end_date: new Date().toISOString().split('T')[0]
                  })}
                  className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200"
                >
                  Today
                </button>
                <button
                  onClick={getCurrentMonth}
                  className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200"
                >
                  This Month
                </button>
                <button
                  onClick={getLastMonth}
                  className="px-3 py-1 text-xs bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200"
                >
                  Last Month
                </button>
                <button
                  onClick={getThisYear}
                  className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded-full hover:bg-yellow-200"
                >
                  This Year
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-3 mt-6">
          <button
            onClick={generateOrder}
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-2"
          >
            {loading ? (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            )}
            <span>{loading ? 'Generating...' : 'Generate Order'}</span>
          </button>
          
          <button
            onClick={exportToExcel}
            className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Export Excel</span>
          </button>
          
          <button
            onClick={exportToPDF}
            className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Export PDF</span>
          </button>
        </div>
      </div>

      {/* Order Preview */}
      {reportData.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Order Preview</h2>
            <p className="text-sm text-gray-500">
              {reportTypes.find(t => t.value === reportType)?.label} - {dateRange.start_date} to {dateRange.end_date}
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Customers
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Revenue
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reportData.map((row, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {row.date || row.visit_date || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {row.patient_count || row.total_customers || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{(row.total_revenue || row.revenue || 0).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        Generated
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quick Orders */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-white text-lg">📊</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Today's Summary</h3>
              <p className="text-sm text-gray-500">Quick overview of today's activities</p>
            </div>
          </div>
          <button 
            onClick={() => {
              setOrderType('daily')
              setDateRange({
                start_date: new Date().toISOString().split('T')[0],
                end_date: new Date().toISOString().split('T')[0]
              })
              generateOrder()
            }}
            className="w-full mt-4 bg-blue-50 text-blue-700 py-2 rounded-lg hover:bg-blue-100 transition-colors"
          >
            Generate
          </button>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-green-500 rounded-lg flex items-center justify-center">
              <span className="text-white text-lg">📈</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Monthly Order</h3>
              <p className="text-sm text-gray-500">Complete monthly analysis</p>
            </div>
          </div>
          <button 
            onClick={() => {
              setOrderType('monthly')
              getCurrentMonth()
              generateOrder()
            }}
            className="w-full mt-4 bg-green-50 text-green-700 py-2 rounded-lg hover:bg-green-100 transition-colors"
          >
            Generate
          </button>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center">
              <span className="text-white text-lg">💰</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Revenue Analysis</h3>
              <p className="text-sm text-gray-500">Financial performance tracking</p>
            </div>
          </div>
          <button 
            onClick={() => {
              setOrderType('revenue')
              getCurrentMonth()
              generateOrder()
            }}
            className="w-full mt-4 bg-purple-50 text-purple-700 py-2 rounded-lg hover:bg-purple-100 transition-colors"
          >
            Generate
          </button>
        </div>
      </div>
    </div>
  )
}
