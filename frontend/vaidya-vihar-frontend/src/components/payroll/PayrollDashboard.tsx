import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useAuth } from '../../contexts/AuthContext'

import { payrollApi } from './api'
import PayrollRunList from './PayrollRunList'
import { PayrollDashboardData, PayrollRunItem } from './types'

const COLORS = ['#2563eb', '#0f766e', '#ea580c', '#7c3aed', '#1d4ed8', '#b45309']

export default function PayrollDashboard() {
  const { user } = useAuth()
  const [dashboard, setDashboard] = useState<PayrollDashboardData | null>(null)
  const [runs, setRuns] = useState<PayrollRunItem[]>([])
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1)
  const [year, setYear] = useState<number>(new Date().getFullYear())
  const [simPct, setSimPct] = useState<number>(10)
  const [simResult, setSimResult] = useState<{ current_cost: number; projected_cost: number; delta: number } | null>(null)
  const [fundsAlert, setFundsAlert] = useState<{ required: number; available: number } | null>(null)

  const load = async () => {
    try {
      const [dash, list] = await Promise.all([payrollApi.getDashboard(), payrollApi.listRuns()])
      setDashboard(dash)
      setRuns(list)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to load payroll dashboard')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const branchName = useMemo(() => {
    const fromAuthBranch = ((user as any)?.branch?.name || '').trim()
    const fromAuthName = ((user as any)?.branch_name || '').trim()
    const fromSelected = (localStorage.getItem('selectedBranchName') || '').trim()
    const fromLocal = (localStorage.getItem('branchName') || '').trim()
    const candidate = fromAuthBranch || fromAuthName || fromSelected || fromLocal
    if (!candidate || candidate.toLowerCase() === 'branch') {
      return 'Diagnostic Center'
    }
    return candidate
  }, [user])

  const activePayrollRun = useMemo(() => {
    return runs.find((run) => (run.status || '').toLowerCase() !== 'locked') || null
  }, [runs])

  useEffect(() => {
    const checkCurrentRunFunds = async () => {
      if (!activePayrollRun) {
        setFundsAlert(null)
        return
      }
      try {
        const funds = await payrollApi.checkFunds(activePayrollRun.id)
        if (!funds.hasSufficientFunds) {
          setFundsAlert({ required: funds.required || 0, available: funds.available || 0 })
          return
        }
      } catch {
        // Keep dashboard usable even if funds check fails.
      }
      setFundsAlert(null)
    }

    void checkCurrentRunFunds()
  }, [activePayrollRun])

  const departmentBurnData = useMemo(() => {
    const source = dashboard?.department_wise_burn || []
    if (!source.length) {
      return [
        { department: 'Radiology', amount: 42, percentage: 42 },
        { department: 'Phlebotomy', amount: 33, percentage: 33 },
        { department: 'Admin', amount: 25, percentage: 25 },
      ]
    }
    const total = source.reduce((sum, entry) => sum + Number(entry.amount || 0), 0)
    if (total <= 0) {
      return source.map((entry) => ({
        department: entry.department,
        amount: Number(entry.amount || 0),
        percentage: 0,
      }))
    }
    return source.map((entry) => {
      const amount = Number(entry.amount || 0)
      return {
        department: entry.department,
        amount,
        percentage: Number(((amount / total) * 100).toFixed(1)),
      }
    })
  }, [dashboard?.department_wise_burn])

  const generateRun = async () => {
    try {
      await payrollApi.generate(month, year)
      toast.success('Payroll generated')
      await load()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Payroll generation failed')
    }
  }

  const approveRun = async (run: PayrollRunItem) => {
    try {
      const funds = await payrollApi.checkFunds(run.id)
      if (!funds.hasSufficientFunds) {
        toast.error(`Zero-Balance Alert: Required INR ${funds.required.toLocaleString()} | Available INR ${funds.available.toLocaleString()}`)
        return
      }
      await payrollApi.approve(run.id)
      toast.success('Payroll approved and locked')
      await load()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Approval failed')
    }
  }

  const runSimulation = async () => {
    try {
      const response = await payrollApi.simulate(simPct)
      setSimResult(response)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Simulation failed')
    }
  }

  return (
    <div className="space-y-6">
      {fundsAlert && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-red-800 shadow-lg">
          <p className="text-sm font-bold">
            ⚠️ Alert: Account Balance (INR {fundsAlert.available.toLocaleString()}) is insufficient for the current Payroll Run (INR {fundsAlert.required.toLocaleString()}). Please arrange funds before approving.
          </p>
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
        <h2 className="text-2xl font-black text-slate-900">{branchName} Payroll Dashboard</h2>
        <p className="mt-1 text-sm text-slate-600">Branch-level payroll analytics, burn split, and approval readiness.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <p className="text-xs uppercase text-slate-500">{branchName} Payroll This Month</p>
          <p className="mt-1 text-2xl font-black text-slate-900">INR {(dashboard?.total_branch_payroll_this_month || 0).toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <p className="text-xs uppercase text-slate-500">{branchName} Last Month</p>
          <p className="mt-1 text-2xl font-black text-slate-900">INR {(dashboard?.total_branch_payroll_last_month || 0).toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <p className="text-xs uppercase text-slate-500">{branchName} Variance %</p>
          <p className="mt-1 text-2xl font-black text-slate-900">{(dashboard?.variance_percent || 0).toFixed(2)}%</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <p className="text-xs uppercase text-slate-500">{branchName} Cost-to-Income Ratio</p>
          <p className="mt-1 text-2xl font-black text-slate-900">{(dashboard?.cost_to_income_ratio || 0).toFixed(2)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
          <h3 className="text-base font-bold text-slate-900">Department-wise Burn</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={departmentBurnData}
                  dataKey="amount"
                  nameKey="department"
                  innerRadius={56}
                  outerRadius={92}
                  paddingAngle={2}
                >
                  {departmentBurnData.map((entry, index) => (
                    <Cell key={entry.department} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: any) => `INR ${Number(value).toLocaleString()}`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-2">
            {departmentBurnData.map((entry, index) => (
              <div key={entry.department} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
                <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span>{entry.department}</span>
                </div>
                <div className="text-right text-xs text-slate-600">
                  <div>{entry.percentage.toFixed(1)}%</div>
                  <div>INR {entry.amount.toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
          <h3 className="text-base font-bold text-slate-900">What-if Simulation</h3>
          <p className="mt-1 text-sm text-slate-600">Estimate monthly payroll impact for a hypothetical salary hike.</p>

          <div className="mt-4">
            <label htmlFor="sim-hike" className="mb-2 block text-sm font-semibold text-slate-700">Simulate Salary Hike (%)</label>
            <div className="flex items-center gap-3">
              <input
                id="sim-hike"
                type="number"
                value={simPct}
                onChange={(e) => setSimPct(Number(e.target.value || 0))}
                className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm outline-none ring-0 transition focus:border-blue-500"
              />
              <button
                type="button"
                onClick={() => void runSimulation()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-700"
              >
                Run Simulation
              </button>
            </div>
          </div>

          {simResult && (
            <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              Current: <span className="font-semibold">INR {simResult.current_cost.toLocaleString()}</span> |
              {' '}Projected: <span className="font-semibold">INR {simResult.projected_cost.toLocaleString()}</span> |
              {' '}Delta: <span className="font-semibold">INR {simResult.delta.toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-lg">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-bold text-slate-900">Payroll Run List</h3>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={12}
              value={month}
              onChange={(e) => setMonth(Number(e.target.value || 1))}
              className="w-16 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            />
            <input
              type="number"
              min={2000}
              max={2200}
              value={year}
              onChange={(e) => setYear(Number(e.target.value || new Date().getFullYear()))}
              className="w-20 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            />
            <button
              type="button"
              onClick={() => void generateRun()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-700"
            >
              Generate
            </button>
          </div>
        </div>
        <PayrollRunList runs={runs} onApprove={(run) => void approveRun(run)} />
      </div>
    </div>
  )
}
