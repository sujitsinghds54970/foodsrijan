import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  CeoInventoryComplianceQualityResponse,
  CeoInventoryFinancialImpactResponse,
  CeoInventoryHealthScoreResponse,
  CeoInventoryLogisticsColdChainResponse,
  CeoInventoryPredictiveIntelligenceResponse,
  CeoInventoryPredictiveWhatIfResponse,
  CeoInventoryProcurementVendorResponse,
  CeoInventoryStockConsumptionResponse,
  CeoInventoryWowFeaturesResponse,
  getCeoInventoryComplianceQualityControl,
  getCeoInventoryFinancialImpactCostControl,
  getCeoInventoryHealthScore,
  getCeoInventoryLogisticsColdChain,
  getCeoInventoryPredictiveIntelligence,
  getCeoInventoryPredictiveWhatIfSimulation,
  getCeoInventoryProcurementVendorManagement,
  getCeoInventoryStockConsumptionAnalytics,
  getCeoInventoryWowFeatures,
} from './api'

const CARD_CLASS = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm'
const PIE_COLORS = ['#4f46e5', '#0ea5e9', '#22c55e', '#f59e0b', '#ef4444']

const toCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

const CeoInventorySupply = () => {
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<CeoInventoryHealthScoreResponse | null>(null)
  const [liveView, setLiveView] = useState<CeoInventoryStockConsumptionResponse | null>(null)
  const [procurement, setProcurement] = useState<CeoInventoryProcurementVendorResponse | null>(null)
  const [logistics, setLogistics] = useState<CeoInventoryLogisticsColdChainResponse | null>(null)
  const [financialImpact, setFinancialImpact] = useState<CeoInventoryFinancialImpactResponse | null>(null)
  const [compliance, setCompliance] = useState<CeoInventoryComplianceQualityResponse | null>(null)
  const [predictive, setPredictive] = useState<CeoInventoryPredictiveIntelligenceResponse | null>(null)
  const [wow, setWow] = useState<CeoInventoryWowFeaturesResponse | null>(null)
  const [whatIfCurrentSupplier, setWhatIfCurrentSupplier] = useState('MedChem Reagents Pvt Ltd')
  const [whatIfNewSupplier, setWhatIfNewSupplier] = useState('NovaBio Supplies')
  const [whatIfItemCategory, setWhatIfItemCategory] = useState('Reagents')
  const [whatIfResult, setWhatIfResult] = useState<CeoInventoryPredictiveWhatIfResponse | null>(null)
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [inventoryLoadError, setInventoryLoadError] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setInventoryLoadError(false)
      try {
        const results = await Promise.allSettled([
          getCeoInventoryHealthScore(),
          getCeoInventoryStockConsumptionAnalytics(),
          getCeoInventoryProcurementVendorManagement(),
          getCeoInventoryLogisticsColdChain(),
          getCeoInventoryFinancialImpactCostControl(),
          getCeoInventoryComplianceQualityControl(),
          getCeoInventoryPredictiveIntelligence(),
          getCeoInventoryWowFeatures(),
        ])
        const healthResp = results[0].status === 'fulfilled' ? results[0].value : null
        const liveViewResp = results[1].status === 'fulfilled' ? results[1].value : null
        const procurementResp = results[2].status === 'fulfilled' ? results[2].value : null
        const logisticsResp = results[3].status === 'fulfilled' ? results[3].value : null
        const financialResp = results[4].status === 'fulfilled' ? results[4].value : null
        const complianceResp = results[5].status === 'fulfilled' ? results[5].value : null
        const predictiveResp = results[6].status === 'fulfilled' ? results[6].value : null
        const wowResp = results[7].status === 'fulfilled' ? results[7].value : null

        if (healthResp) setHealth(healthResp)
        if (liveViewResp) setLiveView(liveViewResp)
        if (procurementResp) setProcurement(procurementResp)
        if (logisticsResp) setLogistics(logisticsResp)
        if (financialResp) setFinancialImpact(financialResp)
        if (complianceResp) setCompliance(complianceResp)
        if (predictiveResp) setPredictive(predictiveResp)
        if (wowResp) setWow(wowResp)
        setInventoryLoadError(results.some((item) => item.status === 'rejected'))
      } catch {
        setInventoryLoadError(true)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const runWhatIf = async () => {
    setWhatIfLoading(true)
    try {
      const result = await getCeoInventoryPredictiveWhatIfSimulation({
        current_supplier: whatIfCurrentSupplier.trim() || 'MedChem Reagents Pvt Ltd',
        new_supplier: whatIfNewSupplier.trim() || 'NovaBio Supplies',
        item_category: whatIfItemCategory.trim() || 'Reagents',
      })
      setWhatIfResult(result)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run what-if simulation')
    } finally {
      setWhatIfLoading(false)
    }
  }

  const healthGaugeData = useMemo(() => {
    const value = Math.max(0, Math.min(health?.score || 0, 100))
    return [{ name: 'Inventory Health', value, fill: value >= 80 ? '#16a34a' : value >= 60 ? '#f59e0b' : '#ef4444' }]
  }, [health])

  const combinedConsumptionTrend = useMemo(() => {
    const highValue = liveView?.daily_consumption_monitoring.high_value_items || []
    const fastMoving = liveView?.daily_consumption_monitoring.fast_moving_items || []
    return highValue.map((point, index) => ({
      day: point.day,
      highValueActual: point.actual_usage,
      highValueExpected: point.expected_usage,
      fastMovingActual: fastMoving[index]?.actual_usage || 0,
      fastMovingExpected: fastMoving[index]?.expected_usage || 0,
    }))
  }, [liveView])

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading Inventory &amp; Supply Chain dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {inventoryLoadError && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">Inventory dashboard data is partially unavailable</p>
          <p className="mt-1 text-xs text-amber-700">Some inventory widgets are showing fallback values while data services recover.</p>
        </section>
      )}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">Inventory &amp; Supply Chain</h1>
        <p className="mt-1 text-sm text-slate-600">Real-time visibility into inventory health, sourcing, logistics, compliance, and predictive intelligence across branches.</p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Out-of-the-Box AI "Wow" Features</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">The Digital Control Tower</p>
            <p className="mt-1 text-xs text-slate-500">{wow?.digital_control_tower.overall_supply_chain_status || 'N/A'}</p>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
              <div className="rounded-md bg-indigo-50 p-3"><p className="text-xs uppercase text-indigo-700">Active Alerts</p><p className="text-2xl font-black text-indigo-800">{wow?.digital_control_tower.active_alerts || 0}</p></div>
              <div className="rounded-md bg-rose-50 p-3"><p className="text-xs uppercase text-rose-700">Critical Stockouts</p><p className="text-2xl font-black text-rose-800">{wow?.digital_control_tower.critical_stockouts || 0}</p></div>
              <div className="rounded-md bg-cyan-50 p-3"><p className="text-xs uppercase text-cyan-700">In-Transit Shipments</p><p className="text-2xl font-black text-cyan-800">{wow?.digital_control_tower.in_transit_shipments || 0}</p></div>
              <div className="rounded-md bg-amber-50 p-3"><p className="text-xs uppercase text-amber-700">Expiring in 7 Days</p><p className="text-2xl font-black text-amber-800">{wow?.digital_control_tower.expiring_within_7_days || 0}</p></div>
              <div className="rounded-md bg-emerald-50 p-3"><p className="text-xs uppercase text-emerald-700">Today's Wastage Cost</p><p className="text-2xl font-black text-emerald-800">{toCurrency(wow?.digital_control_tower.today_wastage_cost || 0)}</p></div>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Automated Inventory Briefing</p>
            <div className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 p-4 text-sm text-slate-700">
              {wow?.automated_inventory_briefing || 'No briefing available.'}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">The Zero-Waste AI Assistant</p>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
              {(wow?.zero_waste_ai_assistant || []).map((tip, idx) => <li key={idx}>{tip}</li>)}
            </ul>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Supplier Health Scores</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Supplier</th><th className="pb-2 pr-4">Health</th><th className="pb-2 pr-4">Delivery</th><th className="pb-2 pr-4">Quality</th><th className="pb-2">Financial</th></tr></thead>
                <tbody>
                  {(wow?.supplier_health_scores || []).map((row) => (
                    <tr key={row.supplier_name} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.supplier_name}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.health_score}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.delivery_score}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.quality_score}</td>
                      <td className="py-2 text-slate-700">{row.financial_stability_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Inventory Health Scorecard (The Pulse)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Overall Inventory Health Score</p>
            <div className="mt-3 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={healthGaugeData} innerRadius="68%" outerRadius="100%" barSize={22} startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-96px] text-center">
              <p className="text-4xl font-black text-slate-900">{health?.score || 0}</p>
              <p className="text-xs uppercase text-slate-500">AI Composite Score</p>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4 lg:col-span-2`}>
            <p className="text-xs uppercase text-slate-500">Stock Availability</p>
            <p className="mt-2 text-3xl font-black text-emerald-700">{Number(health?.stock_availability_rate_percent || 0).toFixed(1)}%</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4 lg:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Wastage Rate</p>
            <p className="mt-2 text-3xl font-black text-rose-700">{Number(health?.wastage.rate_percent || 0).toFixed(1)}%</p>
            <p className="text-xs text-slate-600">Cost Impact: {toCurrency(health?.wastage.cost || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4 lg:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Turnover Ratio</p>
            <p className="mt-2 text-3xl font-black text-indigo-700">{Number(health?.inventory_turnover_ratio || 0).toFixed(1)}x</p>
            <p className="mt-3 text-xs uppercase text-slate-500">Days on Hand</p>
            <p className="text-2xl font-black text-cyan-700">{Number(health?.days_on_hand || 0).toFixed(0)} days</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Expiry Risk Dashboard</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-2 pr-4">Item</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Batch</th><th className="pb-2 pr-4">Days to Expiry</th><th className="pb-2 pr-4">Risk Level</th><th className="pb-2">Current Stock</th>
                  </tr>
                </thead>
                <tbody>
                  {(health?.expiry_risk_dashboard || []).map((item, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{item.item_name}</td>
                      <td className="py-2 pr-4 text-slate-700">{item.branch}</td>
                      <td className="py-2 pr-4 text-slate-700">{item.batch_number}</td>
                      <td className="py-2 pr-4 text-slate-700">{item.days_to_expiry}</td>
                      <td className="py-2 pr-4"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.days_to_expiry <= 7 ? 'bg-rose-100 text-rose-700' : 'bg-amber-100 text-amber-700'}`}>{item.risk_level}</span></td>
                      <td className="py-2 text-slate-700">{item.current_stock}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Real-Time Stock &amp; Consumption Analytics (The Live View)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Multi-Location Stock View (Critical Item)</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={liveView?.multi_location_stock_view || []}>
                  <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="branch" /><YAxis /><Tooltip /><Legend />
                  <Bar dataKey="current_stock" name="Current Stock" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="reorder_point" name="Reorder Point" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Fast vs Slow Moving Mix</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={liveView?.inventory_velocity_mix || []} dataKey="value" nameKey="category" outerRadius={110} label>
                    {(liveView?.inventory_velocity_mix || []).map((entry, idx) => <Cell key={entry.category} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip /><Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Daily Consumption Monitoring (Actual vs Expected)</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={combinedConsumptionTrend}>
                  <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="day" /><YAxis /><Tooltip /><Legend />
                  <Line type="monotone" dataKey="highValueActual" name="High-Value Actual" stroke="#4f46e5" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="highValueExpected" name="High-Value Expected" stroke="#6366f1" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="fastMovingActual" name="Fast-Moving Actual" stroke="#0ea5e9" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="fastMovingExpected" name="Fast-Moving Expected" stroke="#06b6d4" strokeDasharray="4 4" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">High-Value Reagent Movement</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Reagent</th><th className="pb-2 pr-4">Used By</th><th className="pb-2 pr-4">Used On</th><th className="pb-2 pr-4">Test</th><th className="pb-2 pr-4">Qty</th><th className="pb-2">Branch</th></tr></thead>
                <tbody>
                  {(liveView?.high_value_reagent_movement || []).map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.reagent_name}</td><td className="py-2 pr-4 text-slate-700">{row.used_by}</td><td className="py-2 pr-4 text-slate-700">{row.used_on}</td><td className="py-2 pr-4 text-slate-700">{row.test_name}</td><td className="py-2 pr-4 text-slate-700">{row.quantity}</td><td className="py-2 text-slate-700">{row.branch}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Stockout Alerts</p>
            <div className="mt-3 space-y-2">
              {(liveView?.stockout_alerts || []).map((alert, idx) => (
                <div key={idx} className={`rounded-md border px-3 py-2 ${alert.severity === 'high' ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{alert.item_name} · {alert.branch}</p>
                  <p className="text-xs text-slate-700">Current: {alert.current_stock} | Reorder Point: {alert.reorder_point}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Minimum &amp; Maximum Stock Levels</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Item</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Min Stock</th><th className="pb-2 pr-4">Max Stock</th><th className="pb-2">Current Stock</th></tr></thead>
                <tbody>
                  {(liveView?.min_max_stock_levels || []).map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.item_name}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 text-slate-700">{row.minimum_stock}</td><td className="py-2 pr-4 text-slate-700">{row.maximum_stock}</td><td className="py-2 text-slate-700">{row.current_stock}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Procurement &amp; Vendor Management (The Sourcing Engine)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Procurement Dashboard</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">PO Number</th><th className="pb-2 pr-4">Vendor</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Status</th><th className="pb-2 pr-4">Expected Delivery</th><th className="pb-2">Order Value</th></tr></thead>
                <tbody>
                  {(procurement?.procurement_dashboard || []).map((po) => (
                    <tr key={po.po_number} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{po.po_number}</td><td className="py-2 pr-4 text-slate-700">{po.vendor_name}</td><td className="py-2 pr-4 text-slate-700">{po.branch}</td><td className="py-2 pr-4 text-slate-700">{po.status}</td><td className="py-2 pr-4 text-slate-700">{po.expected_delivery_date}</td><td className="py-2 text-slate-700">{toCurrency(po.order_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Vendor Performance Scorecard</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Vendor</th><th className="pb-2 pr-4">On-time Delivery</th><th className="pb-2 pr-4">Rejection Rate</th><th className="pb-2 pr-4">Pricing Score</th><th className="pb-2">Responsiveness</th></tr></thead>
                <tbody>
                  {(procurement?.vendor_performance_scorecard || []).map((vendor) => (
                    <tr key={vendor.vendor_name} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{vendor.vendor_name}</td><td className="py-2 pr-4 text-slate-700">{vendor.on_time_delivery_rate_percent}%</td><td className="py-2 pr-4 text-slate-700">{vendor.rejection_rate_percent}%</td><td className="py-2 pr-4 text-slate-700">{vendor.pricing_competitiveness_score}</td><td className="py-2 text-slate-700">{vendor.responsiveness_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Centralized Procurement &amp; JIT Reordering</p>
            <div className="mt-3 space-y-2">
              {(procurement?.jit_reorder_suggestions || []).map((item) => (
                <div key={item.item_name} className="rounded-md border border-indigo-100 bg-indigo-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{item.item_name}</p>
                  <p className="text-xs text-indigo-700">Suggested Reorder: {item.suggested_reorder_qty} units · Confidence: {item.confidence_percent}%</p>
                  <p className="text-xs text-slate-600">{item.reason}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Supplier Diversification Risk</p>
            <div className="mt-3 space-y-2">
              {(procurement?.supplier_diversification_risk || []).map((item, idx) => (
                <div key={`${item.item_name}-${idx}`} className={`rounded-md border px-3 py-2 ${item.risk_level === 'High' ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{item.item_name}</p>
                  <p className="text-xs text-slate-700">Suppliers: {item.active_suppliers} · Criticality: {item.criticality} · Risk: {item.risk_level}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">SKU Rationalization Suggestions</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">SKU Group</th><th className="pb-2 pr-4">Count</th><th className="pb-2 pr-4">Action</th><th className="pb-2">Savings</th></tr></thead>
                <tbody>
                  {(procurement?.sku_rationalization || []).map((sku) => (
                    <tr key={sku.sku_group} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{sku.sku_group}</td><td className="py-2 pr-4 text-slate-700">{sku.items_in_group}</td><td className="py-2 pr-4 text-slate-700">{sku.recommended_action}</td><td className="py-2 text-slate-700">{toCurrency(sku.estimated_monthly_savings)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Logistics &amp; Cold Chain Management (The Delivery Engine)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Cold Chain Monitoring Dashboard</p>
            <p className="mt-2 text-xs text-slate-600">Active Shipments: {logistics?.cold_chain_monitoring.active_shipments || 0} · In Range: {logistics?.cold_chain_monitoring.within_range_percent || 0}%</p>
            <div className="mt-3 space-y-2">
              {(logistics?.cold_chain_monitoring.temperature_alerts || []).map((alert) => (
                <div key={alert.shipment_id} className={`rounded-md border px-3 py-2 ${alert.severity === 'high' ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{alert.shipment_id} · {alert.route}</p>
                  <p className="text-xs text-slate-700">Current: {alert.current_temp_c}°C | Allowed: {alert.allowed_range}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Branch-wise Logistics Performance</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={logistics?.branch_logistics_performance || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="branch" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="avg_delivery_time_minutes" name="Delivery Time (min)" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="sample_rejection_rate_percent" name="Rejection Rate (%)" fill="#ef4444" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="courier_performance_score" name="Courier Score" fill="#22c55e" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Sample &amp; Specimen Logistics</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Sample</th><th className="pb-2 pr-4">Route</th><th className="pb-2 pr-4">Status</th><th className="pb-2">ETA</th></tr></thead>
                <tbody>
                  {(logistics?.sample_specimen_logistics || []).map((item) => (
                    <tr key={item.sample_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{item.sample_id}</td><td className="py-2 pr-4 text-slate-700">{item.from_branch} → {item.to_lab}</td><td className="py-2 pr-4 text-slate-700">{item.courier_status}</td><td className="py-2 text-slate-700">{item.estimated_arrival}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Fleet &amp; Route Optimization</p>
            <div className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 p-4 text-sm text-slate-700">
              {logistics?.fleet_route_optimization.message || 'Optimization insights will appear here.'}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Financial Impact &amp; Cost Control (The Bottom Line)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-6 lg:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Inventory Carrying Cost</p>
            <p className="mt-2 text-3xl font-black text-rose-700">{toCurrency(financialImpact?.inventory_carrying_cost || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-6 lg:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Cost per Test (Inventory)</p>
            <p className="mt-2 text-3xl font-black text-indigo-700">{toCurrency(financialImpact?.inventory_cost_per_test || 0)}</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Procurement Savings Tracker</p>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div className="rounded-md bg-emerald-50 p-3"><p className="text-xs uppercase text-emerald-700">Total Savings</p><p className="text-xl font-black text-emerald-800">{toCurrency(financialImpact?.procurement_savings_tracker.savings_realized || 0)}</p></div>
              <div className="rounded-md bg-indigo-50 p-3"><p className="text-xs uppercase text-indigo-700">Negotiation</p><p className="text-xl font-black text-indigo-800">{toCurrency(financialImpact?.procurement_savings_tracker.negotiation_savings || 0)}</p></div>
              <div className="rounded-md bg-cyan-50 p-3"><p className="text-xs uppercase text-cyan-700">Bulk Purchase</p><p className="text-xl font-black text-cyan-800">{toCurrency(financialImpact?.procurement_savings_tracker.bulk_purchase_savings || 0)}</p></div>
              <div className="rounded-md bg-amber-50 p-3"><p className="text-xs uppercase text-amber-700">SKU Rationalization</p><p className="text-xl font-black text-amber-800">{toCurrency(financialImpact?.procurement_savings_tracker.sku_rationalization_savings || 0)}</p></div>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Vendor Spend Analysis</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={financialImpact?.vendor_spend_analysis || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="vendor_name" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Bar dataKey="spend" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Budget vs Actual (Inventory)</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={financialImpact?.budget_vs_actual_inventory || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Legend />
                  <Bar dataKey="budget" fill="#22c55e" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="actual" fill="#ef4444" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Compliance &amp; Quality Control (The Risk Shield)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Lot &amp; Batch Traceability</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Item</th><th className="pb-2 pr-4">Lot/Batch</th><th className="pb-2 pr-4">Received</th><th className="pb-2 pr-4">Used</th><th className="pb-2 pr-4">Branch</th><th className="pb-2">Test</th></tr></thead>
                <tbody>
                  {(compliance?.lot_batch_traceability || []).map((row, idx) => (
                    <tr key={`${row.lot_number}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.item_name}</td><td className="py-2 pr-4 text-slate-700">{row.lot_number}</td><td className="py-2 pr-4 text-slate-700">{row.received_on}</td><td className="py-2 pr-4 text-slate-700">{row.used_on}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 text-slate-700">{row.used_for_test}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Expiry &amp; Recall Management</p>
            <div className="mt-3 space-y-2">
              {(compliance?.expiry_recall_management.expiring_alerts || []).map((item, idx) => (
                <div key={idx} className={`rounded-md border px-3 py-2 ${item.severity === 'high' ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{item.item_name} · {item.branch}</p>
                  <p className="text-xs text-slate-700">Expires in {item.days_to_expiry} days</p>
                </div>
              ))}
              {(compliance?.expiry_recall_management.regulatory_recall_feed || []).map((recall) => (
                <div key={recall.recall_id} className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{recall.recall_id} · {recall.item_name}</p>
                  <p className="text-xs text-slate-700">{recall.advisory}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Supplier &amp; Item Certification Tracker</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Type</th><th className="pb-2 pr-4">Name</th><th className="pb-2 pr-4">Certification</th><th className="pb-2 pr-4">Status</th><th className="pb-2">Expiry</th></tr></thead>
                <tbody>
                  {(compliance?.supplier_item_certification_tracker || []).map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.entity_type}</td><td className="py-2 pr-4 font-semibold text-slate-800">{row.name}</td><td className="py-2 pr-4 text-slate-700">{row.certification}</td><td className="py-2 pr-4 text-slate-700">{row.status}</td><td className="py-2 text-slate-700">{row.expiry_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Audit Trail</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Timestamp</th><th className="pb-2 pr-4">Activity</th><th className="pb-2 pr-4">Item</th><th className="pb-2 pr-4">Performed By</th><th className="pb-2">Notes</th></tr></thead>
                <tbody>
                  {(compliance?.audit_trail || []).map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.timestamp}</td><td className="py-2 pr-4 font-semibold text-slate-800">{row.activity_type}</td><td className="py-2 pr-4 text-slate-700">{row.item_name}</td><td className="py-2 pr-4 text-slate-700">{row.performed_by}</td><td className="py-2 text-slate-700">{row.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Reagent &amp; Consumable Quality Tracking</p>
            <div className="mt-3 space-y-2">
              {(compliance?.reagent_consumable_quality_tracking || []).map((row, idx) => (
                <div key={idx} className="rounded-md border border-slate-200 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{row.item_name}</p>
                  <p className="text-xs text-slate-700">{row.issue_type} · Complaints: {row.complaint_count}</p>
                  <p className="text-xs text-slate-600">Last Reported: {row.last_reported_on} · Status: {row.status}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">AI-Powered Predictive Analytics &amp; Intelligence (The Brain)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Demand Forecasting</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={predictive?.demand_forecasting || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="pcr_reagent_demand" name="PCR Reagent" stroke="#4f46e5" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="edta_tube_demand" name="EDTA Tube" stroke="#0ea5e9" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="contrast_media_demand" name="Contrast Media" stroke="#22c55e" strokeWidth={2.5} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Expiry Prediction &amp; Prevention</p>
            <div className="mt-3 space-y-2">
              {(predictive?.expiry_prediction_prevention || []).map((row, idx) => (
                <div key={idx} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{row.item_name} · {row.branch}</p>
                  <p className="text-xs text-amber-700">Risk Score: {row.risk_score}</p>
                  <p className="text-xs text-slate-700">{row.suggested_action}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Supply Chain Risk Alerts</p>
            <div className="mt-3 space-y-2">
              {(predictive?.supply_chain_risk_alerts || []).map((alert, idx) => (
                <div key={idx} className={`rounded-md border px-3 py-2 ${alert.severity === 'high' ? 'border-rose-200 bg-rose-50' : alert.severity === 'medium' ? 'border-amber-200 bg-amber-50' : 'border-cyan-200 bg-cyan-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{alert.title}</p>
                  <p className="text-xs text-slate-700">{alert.message}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">What-If Scenario Simulator</p>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-4">
              <input value={whatIfCurrentSupplier} onChange={(e) => setWhatIfCurrentSupplier(e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Current Supplier" />
              <input value={whatIfNewSupplier} onChange={(e) => setWhatIfNewSupplier(e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="New Supplier" />
              <input value={whatIfItemCategory} onChange={(e) => setWhatIfItemCategory(e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Item Category" />
              <button type="button" onClick={() => void runWhatIf()} disabled={whatIfLoading} className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300">
                {whatIfLoading ? 'Running...' : 'Run Simulation'}
              </button>
            </div>
            {whatIfResult && (
              <div className="mt-4 rounded-md border border-indigo-100 bg-indigo-50 p-4 text-sm text-slate-700">
                <p className="font-semibold text-indigo-800">{whatIfResult.scenario}</p>
                <p>Cost Change: {whatIfResult.projected_impact.cost_change_percent.toFixed(2)}%</p>
                <p>Availability Change: {whatIfResult.projected_impact.availability_change_percent.toFixed(2)}%</p>
                <p>On-Time Delivery Change: {whatIfResult.projected_impact.on_time_delivery_change_percent.toFixed(2)}%</p>
                <p>Estimated Monthly Savings: {toCurrency(whatIfResult.projected_impact.estimated_monthly_savings)}</p>
                <p className="mt-1 text-xs text-slate-600">{whatIfResult.ai_summary}</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

export default CeoInventorySupply
