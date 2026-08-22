import axios from 'axios'

import { DashboardResponse, ForecastResponse, TopReferrersResponse, TrendsResponse } from './types'

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000'

function authHeader(token?: string) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetchAnalyticsDashboard(branchId: number, token?: string): Promise<DashboardResponse> {
  const response = await axios.get(`${API_BASE}/api/analytics/dashboard/branch/${branchId}`, {
    headers: authHeader(token),
  })
  return response.data as DashboardResponse
}

export async function fetchAnalyticsTrends(branchId: number, startDate: string, endDate: string, token?: string): Promise<TrendsResponse> {
  const response = await axios.get(`${API_BASE}/api/analytics/trends`, {
    params: { branch_id: branchId, start_date: startDate, end_date: endDate },
    headers: authHeader(token),
  })
  return response.data as TrendsResponse
}

export async function fetchTopReferrers(branchId: number, startDate: string, endDate: string, token?: string): Promise<TopReferrersResponse> {
  const response = await axios.get(`${API_BASE}/api/analytics/staff/top-referrers`, {
    params: { branch_id: branchId, start_date: startDate, end_date: endDate, limit: 10 },
    headers: authHeader(token),
  })
  return response.data as TopReferrersResponse
}

export async function fetchNextMonthForecast(branchId: number, token?: string): Promise<ForecastResponse> {
  const response = await axios.get(`${API_BASE}/api/analytics/forecast/next-month`, {
    params: { branch_id: branchId },
    headers: authHeader(token),
  })
  return response.data as ForecastResponse
}
