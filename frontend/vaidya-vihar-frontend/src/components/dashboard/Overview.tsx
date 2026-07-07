import React, { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'

export default function Overview() {
  const { user } = useAuth()
  const [stats, setStats] = useState({
    totalPatients: 0,
    todayVisits: 0,
    totalStaff: 0,
    revenue: 0
  })

  useEffect(() => {
    // Fetch dashboard statistics
    const fetchStats = async () => {
      try {
        // This would typically call your API
        // const response = await fetch('/api/dashboard/stats')
        // const data = await response.json()
        
        // For now, using mock data
        setStats({
          totalPatients: 1247,
          todayVisits: 23,
          totalStaff: 15,
          revenue: 45680
        })
      } catch (error) {
        console.error('Error fetching stats:', error)
      }
    }

    fetchStats()
  }, [])

  const statCards = [
    { 
      title: 'Total Patients', 
      value: stats.totalPatients, 
      icon: '👥', 
      gradient: 'from-blue-500 to-cyan-500',
      bgGradient: 'from-blue-50 to-cyan-50'
    },
    { 
      title: "Today's Visits", 
      value: stats.todayVisits, 
      icon: '📅', 
      gradient: 'from-emerald-500 to-teal-500',
      bgGradient: 'from-emerald-50 to-teal-50'
    },
    { 
      title: 'Total Staff', 
      value: stats.totalStaff, 
      icon: '👨‍⚕️', 
      gradient: 'from-purple-500 to-pink-500',
      bgGradient: 'from-purple-50 to-pink-50'
    },
    { 
      title: 'Monthly Revenue', 
      value: `₹${stats.revenue.toLocaleString()}`, 
      icon: '💰', 
      gradient: 'from-amber-500 to-orange-500',
      bgGradient: 'from-amber-50 to-orange-50'
    },
  ]

  const quickActions = [
    {
      title: 'Daily Entry',
      description: 'Record patient visits',
      icon: '📝',
      gradient: 'from-blue-500 to-cyan-500',
      bgColor: 'bg-blue-50'
    },
    {
      title: 'Add Patient',
      description: 'Register new patient',
      icon: '👥',
      gradient: 'from-emerald-500 to-teal-500',
      bgColor: 'bg-emerald-50'
    },
    {
      title: 'View Reports',
      description: 'Export monthly data',
      icon: '📊',
      gradient: 'from-purple-500 to-pink-500',
      bgColor: 'bg-purple-50'
    },
  ]

  const recentActivities = [
    { text: 'New patient registered: John Doe', time: '2 minutes ago', color: 'bg-blue-500' },
    { text: 'Daily entry completed for 15 patients', time: '1 hour ago', color: 'bg-emerald-500' },
    { text: 'Monthly report generated', time: '3 hours ago', color: 'bg-amber-500' },
  ]

  return (
    <div className="space-y-8">
      {/* Welcome Section - Premium */}
      <div className="premium-card p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-purple-200/30 to-pink-200/30 rounded-full blur-3xl -mr-32 -mt-32" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-blue-200/30 to-cyan-200/30 rounded-full blur-3xl -ml-24 -mb-24" />
        
        <div className="relative flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-black mb-2">
              <span className="gradient-text">Welcome back, {user?.first_name}!</span>
            </h1>
            <p className="text-lg text-slate-600 font-medium">
              Here's what's happening at <span className="font-bold text-purple-600">VaidyaVihar Diagnostic</span> today.
            </p>
          </div>
          <div className="text-right bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-purple-100">
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Current Branch</p>
            <p className="text-2xl font-black bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              {user?.branch_id ? `Branch #${user.branch_id}` : 'Main Branch'}
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards - Premium */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => (
          <div key={index} className="stats-card group cursor-pointer">
            <div className="flex items-center justify-between mb-4">
              <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300`}>
                <span className="text-3xl">{stat.icon}</span>
              </div>
            </div>
            <p className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-2">{stat.title}</p>
            <p className="text-4xl font-black bg-gradient-to-r ${stat.gradient} bg-clip-text text-transparent">
              {stat.value}
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-emerald-600">
              <span className="mr-1">↗</span>
              <span>+12% from last month</span>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions - Premium */}
      <div className="premium-card p-8">
        <div className="flex items-center mb-6">
          <h2 className="text-2xl font-black gradient-text">Quick Actions</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quickActions.map((action, index) => (
            <button 
              key={index}
              className="group relative overflow-hidden rounded-2xl p-6 bg-gradient-to-br from-white to-slate-50 border-2 border-transparent hover:border-purple-200 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1"
            >
              <div className="absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity duration-300" style={{
                backgroundImage: `linear-gradient(135deg, var(--brand-purple), var(--brand-pink))`
              }} />
              <div className="relative flex items-center space-x-4">
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${action.gradient} flex items-center justify-center shadow-lg transform group-hover:scale-110 group-hover:rotate-6 transition-all duration-300`}>
                  <span className="text-2xl">{action.icon}</span>
                </div>
                <div className="text-left flex-1">
                  <p className="font-black text-lg text-slate-900 mb-1">{action.title}</p>
                  <p className="text-sm text-slate-600 font-medium">{action.description}</p>
                </div>
                <svg className="w-6 h-6 text-slate-400 group-hover:text-purple-600 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Activity - Premium */}
      <div className="premium-card p-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-black gradient-text">Recent Activity</h2>
          <button className="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white text-sm font-bold hover:shadow-lg transition-all hover:-translate-y-0.5">
            View All
          </button>
        </div>
        <div className="space-y-4">
          {recentActivities.map((activity, index) => (
            <div 
              key={index}
              className="group flex items-center space-x-4 p-4 rounded-xl bg-gradient-to-r from-slate-50 to-white border border-slate-100 hover:border-purple-200 hover:shadow-lg transition-all duration-300 cursor-pointer"
            >
              <div className={`w-3 h-3 ${activity.color} rounded-full shadow-lg group-hover:scale-125 transition-transform`} />
              <div className="flex-1">
                <p className="text-sm font-semibold text-slate-900">{activity.text}</p>
                <p className="text-xs text-slate-500 font-medium mt-1">{activity.time}</p>
              </div>
              <svg className="w-5 h-5 text-slate-300 group-hover:text-purple-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Metrics - Premium */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="premium-card p-8">
          <h3 className="text-xl font-black gradient-text mb-6">Performance Metrics</h3>
          <div className="space-y-4">
            {[
              { label: 'Patient Satisfaction', value: 95, color: 'from-emerald-500 to-teal-500' },
              { label: 'Staff Efficiency', value: 88, color: 'from-blue-500 to-cyan-500' },
              { label: 'Revenue Growth', value: 76, color: 'from-purple-500 to-pink-500' },
            ].map((metric, index) => (
              <div key={index}>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-bold text-slate-700">{metric.label}</span>
                  <span className="text-sm font-black text-purple-600">{metric.value}%</span>
                </div>
                <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className={`h-full bg-gradient-to-r ${metric.color} rounded-full transition-all duration-1000 ease-out`}
                    style={{ width: `${metric.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="premium-card p-8">
          <h3 className="text-xl font-black gradient-text mb-6">System Status</h3>
          <div className="space-y-4">
            {[
              { label: 'Database', status: 'Operational', color: 'emerald' },
              { label: 'API Services', status: 'Operational', color: 'emerald' },
              { label: 'Backup System', status: 'Operational', color: 'emerald' },
            ].map((system, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-xl bg-gradient-to-r from-slate-50 to-white border border-slate-100">
                <span className="text-sm font-bold text-slate-700">{system.label}</span>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 bg-${system.color}-500 rounded-full animate-pulse`} />
                  <span className={`text-xs font-bold text-${system.color}-600 uppercase tracking-wider`}>{system.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
