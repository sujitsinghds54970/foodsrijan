import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Funnel,
  FunnelChart,
  LabelList,
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
  CeoCustomerFinancialAnalyticsResponse,
  CeoCustomerJourneyExperienceResponse,
  CeoCustomerOverviewResponse,
  CeoCustomerPredictiveInsightsResponse,
  CeoCustomerPredictiveWhatIfResponse,
  CeoCustomerRetentionLoyaltyResponse,
  CeoCustomerSegmentationHealthResponse,
  CeoCustomerWowFeaturesResponse,
  getCeoCustomerFinancialAnalytics,
  getCeoCustomerJourneyExperience,
  getCeoCustomerOverview,
  getCeoCustomerPredictiveInsights,
  getCeoCustomerPredictiveWhatIfSimulation,
  getCeoCustomerRetentionLoyalty,
  getCeoCustomerSegmentationHealth,
  getCeoCustomerWowFeatures,
} from './api'

const CARD_CLASS = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm'
const PIE_COLORS = ['#4f46e5', '#0ea5e9', '#22c55e', '#f59e0b', '#ef4444']

const toCurrency = (value: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value || 0)

const CeoCustomerInsights = () => {
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<CeoCustomerOverviewResponse | null>(null)
  const [journey, setJourney] = useState<CeoCustomerJourneyExperienceResponse | null>(null)
  const [retention, setRetention] = useState<CeoCustomerRetentionLoyaltyResponse | null>(null)
  const [segmentation, setSegmentation] = useState<CeoCustomerSegmentationHealthResponse | null>(null)
  const [financial, setFinancial] = useState<CeoCustomerFinancialAnalyticsResponse | null>(null)
  const [predictive, setPredictive] = useState<CeoCustomerPredictiveInsightsResponse | null>(null)
  const [wow, setWow] = useState<CeoCustomerWowFeaturesResponse | null>(null)
  const [whatIfCondition, setWhatIfCondition] = useState('Diabetes')
  const [whatIfCity, setWhatIfCity] = useState('Mumbai')
  const [whatIfDiscount, setWhatIfDiscount] = useState(10)
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [whatIfResult, setWhatIfResult] = useState<CeoCustomerPredictiveWhatIfResponse | null>(null)
  const [isCustomer360Open, setIsCustomer360Open] = useState(false)
  const [patientSearch, setCustomerSearch] = useState('')
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [overviewResp, journeyResp, retentionResp, segmentationResp, financialResp, predictiveResp, wowResp] = await Promise.all([
          getCeoCustomerOverview(),
          getCeoCustomerJourneyExperience(),
          getCeoCustomerRetentionLoyalty(),
          getCeoCustomerSegmentationHealth(),
          getCeoCustomerFinancialAnalytics(),
          getCeoCustomerPredictiveInsights(),
          getCeoCustomerWowFeatures(),
        ])
        setOverview(overviewResp)
        setJourney(journeyResp)
        setRetention(retentionResp)
        setSegmentation(segmentationResp)
        setFinancial(financialResp)
        setPredictive(predictiveResp)
        setWow(wowResp)
        setSelectedCustomerId(wowResp.patient_360_profiles[0]?.patient_id || null)
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Unable to load Customer Insights dashboard')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const runWhatIf = async () => {
    setWhatIfLoading(true)
    try {
      const result = await getCeoCustomerPredictiveWhatIfSimulation({
        condition: whatIfCondition.trim() || 'Diabetes',
        city: whatIfCity.trim() || 'Mumbai',
        discount_percent: whatIfDiscount,
      })
      setWhatIfResult(result)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run scenario simulation')
    } finally {
      setWhatIfLoading(false)
    }
  }

  const npsGaugeData = useMemo(() => {
    const value = Math.max(0, Math.min(journey?.patient_nps_score || 0, 100))
    return [{ name: 'Customer NPS', value, fill: value >= 70 ? '#16a34a' : value >= 50 ? '#f59e0b' : '#ef4444' }]
  }, [journey])

  const healthScoreGaugeData = useMemo(() => {
    const value = Math.max(0, Math.min(retention?.patient_health_score || 0, 100))
    return [{ name: 'Customer Health Score', value, fill: value >= 75 ? '#16a34a' : value >= 55 ? '#f59e0b' : '#ef4444' }]
  }, [retention])

  const patient360List = useMemo(() => {
    const list = wow?.patient_360_profiles || []
    const q = patientSearch.trim().toLowerCase()
    if (!q) return list
    return list.filter((item) => item.name.toLowerCase().includes(q) || item.patient_id.toLowerCase().includes(q))
  }, [wow, patientSearch])

  const selectedCustomer360 = useMemo(
    () => (wow?.patient_360_profiles || []).find((item) => item.patient_id === selectedCustomerId) || null,
    [wow, selectedCustomerId]
  )

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading Customer Insights dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">Customer Insights</h1>
        <p className="mt-1 text-sm text-slate-600">Acquisition, journey, retention, segmentation, and predictive patient analytics for super admin decisions.</p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Customer Acquisition &amp; Growth (The Top of Funnel)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Total Customer Base</p>
            <p className="mt-1 text-4xl font-black text-slate-900">{overview?.total_customers || 0}</p>
            <p className="mt-2 text-xs font-semibold text-emerald-700">MoM: +{Number(overview?.growth.mom_percent || 0).toFixed(1)}%</p>
            <p className="text-xs font-semibold text-indigo-700">YoY: +{Number(overview?.growth.yoy_percent || 0).toFixed(1)}%</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Customer Acquisition Cost (PAC)</p>
            <p className="mt-1 text-3xl font-black text-rose-700">{toCurrency(overview?.patient_acquisition_cost || 0)}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Customer Lifetime Value (PLV)</p>
            <p className="mt-1 text-3xl font-black text-emerald-700">{toCurrency(overview?.patient_lifetime_value || 0)}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">New vs Returning Customers</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'New', value: overview?.new_vs_returning.new || 0 },
                      { name: 'Returning', value: overview?.new_vs_returning.returning || 0 },
                    ]}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={110}
                    label
                  >
                    <Cell fill="#4f46e5" />
                    <Cell fill="#22c55e" />
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Referral Source Analysis</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview?.referral_source_analysis || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="source" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="customers" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Customer Base Growth Trend</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={overview?.monthly_growth_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="customers" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Customer Journey &amp; Experience (The Middle of Funnel)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Customer Journey Funnel</p>
            <div className="mt-3 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <FunnelChart>
                  <Tooltip />
                  <Funnel dataKey="value" data={journey?.journey_funnel || []} isAnimationActive>
                    <LabelList position="right" fill="#334155" stroke="none" dataKey="stage" />
                    {(journey?.journey_funnel || []).map((_, idx) => (
                      <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                    ))}
                  </Funnel>
                </FunnelChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Customer Satisfaction (NPS)</p>
            <div className="mt-3 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={npsGaugeData} innerRadius="68%" outerRadius="100%" barSize={22} startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-96px] text-center">
              <p className="text-4xl font-black text-slate-900">{journey?.patient_nps_score || 0}</p>
              <p className="text-xs uppercase text-slate-500">NPS Score</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Average Time to MenuItem</p>
            <p className="mt-2 text-3xl font-black text-indigo-700">{Number(journey?.average_time_to_test_hours || 0).toFixed(1)} hrs</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">No-Show Rate</p>
            <p className="mt-2 text-3xl font-black text-rose-700">{Number(journey?.no_show_rate_percent || 0).toFixed(1)}%</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Average TAT</p>
            <p className="mt-2 text-3xl font-black text-emerald-700">{Number(journey?.average_tat_hours || 0).toFixed(1)} hrs</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-xs uppercase text-slate-500">Order Viewing Rate</p>
            <div className="mt-2">
              <div className="mb-1 flex items-center justify-between text-xs font-semibold text-slate-600">
                <span>Online Order View Rate</span>
                <span>{journey?.report_viewing_rate_percent || 0}%</span>
              </div>
              <div className="h-3 rounded-full bg-slate-100">
                <div className="h-3 rounded-full bg-gradient-to-r from-cyan-500 to-indigo-500" style={{ width: `${Math.min(Math.max(journey?.report_viewing_rate_percent || 0, 0), 100)}%` }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Customer Retention &amp; Loyalty (The Bottom of Funnel)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}><p className="text-xs uppercase text-slate-500">Retention Rate</p><p className="mt-2 text-3xl font-black text-emerald-700">{Number(retention?.retention_rate_percent || 0).toFixed(1)}%</p></div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}><p className="text-xs uppercase text-slate-500">Churn Rate</p><p className="mt-2 text-3xl font-black text-rose-700">{Number(retention?.churn_rate_percent || 0).toFixed(1)}%</p></div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}><p className="text-xs uppercase text-slate-500">Repeat Visit Rate</p><p className="mt-2 text-3xl font-black text-indigo-700">{Number(retention?.repeat_visit_rate || 0).toFixed(1)}x</p></div>
          <div className={`${CARD_CLASS} col-span-12 md:col-span-3`}><p className="text-xs uppercase text-slate-500">Reactivation Rate</p><p className="mt-2 text-3xl font-black text-cyan-700">{Number(retention?.reactivation_rate_percent || 0).toFixed(1)}%</p></div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Loyalty Program Performance</p>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-md bg-indigo-50 p-3"><p className="text-xs uppercase text-indigo-700">Enrollment Rate</p><p className="text-2xl font-black text-indigo-800">{Number(retention?.loyalty_program.enrollment_rate_percent || 0).toFixed(1)}%</p></div>
              <div className="rounded-md bg-emerald-50 p-3"><p className="text-xs uppercase text-emerald-700">Redemption Rate</p><p className="text-2xl font-black text-emerald-700">{Number(retention?.loyalty_program.redemption_rate_percent || 0).toFixed(1)}%</p></div>
              <div className="rounded-md bg-cyan-50 p-3"><p className="text-xs uppercase text-cyan-700">Repeat Visit Uplift</p><p className="text-2xl font-black text-cyan-700">+{Number(retention?.loyalty_program.repeat_visit_uplift_percent || 0).toFixed(1)}%</p></div>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Customer Health Score</p>
            <div className="mt-3 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={healthScoreGaugeData} innerRadius="68%" outerRadius="100%" barSize={22} startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background dataKey="value" cornerRadius={12} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-[-96px] text-center"><p className="text-4xl font-black text-slate-900">{retention?.patient_health_score || 0}</p><p className="text-xs uppercase text-slate-500">Return Likelihood</p></div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Customer Segmentation &amp; Population Health (The Granular View)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Demographics by Age</p>
            <div className="mt-3 h-64"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={segmentation?.demographics.age || []} dataKey="value" nameKey="group" outerRadius={95} label>{(segmentation?.demographics.age || []).map((item, idx) => <Cell key={item.group} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Demographics by Gender</p>
            <div className="mt-3 h-64"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={segmentation?.demographics.gender || []} dataKey="value" nameKey="group" outerRadius={95} label>{(segmentation?.demographics.gender || []).map((item, idx) => <Cell key={item.group} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Demographics by Location</p>
            <div className="mt-3 h-64"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={segmentation?.demographics.location || []} dataKey="value" nameKey="group" outerRadius={95} label>{(segmentation?.demographics.location || []).map((item, idx) => <Cell key={item.group} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Segmentation by Condition</p>
            <div className="mt-3 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={segmentation?.segment_by_condition || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="condition" /><YAxis /><Tooltip /><Bar dataKey="customers" fill="#4f46e5" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Segmentation by Lifetime Value</p>
            <div className="mt-3 h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={segmentation?.segment_by_value || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="segment" /><YAxis /><Tooltip /><Bar dataKey="customers" fill="#0ea5e9" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Geographic Customer Density Map</p>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
              {(segmentation?.geographic_density || []).map((zone) => (
                <div key={zone.zone} className="rounded-lg border border-slate-200 p-3 text-center" style={{ backgroundColor: `rgba(14, 165, 233, ${Math.max(0.2, Math.min(zone.density_score / 100, 0.9))})` }}>
                  <p className="text-xs font-semibold text-white">{zone.zone}</p><p className="mt-1 text-2xl font-black text-white">{zone.density_score}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Population Health Insights</p>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">{(segmentation?.population_health_insights || []).map((insight, idx) => <li key={idx}>{insight}</li>)}</ul>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Financial &amp; Revenue Analytics (The Bottom Line)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">Revenue by Customer Segment</p>
            <div className="mt-3 h-80"><ResponsiveContainer width="100%" height="100%"><BarChart data={financial?.revenue_by_segment || []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="segment" interval={0} angle={-12} textAnchor="end" height={70} /><YAxis /><Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} /><Bar dataKey="revenue" fill="#22c55e" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-xs uppercase text-slate-500">Revenue per Customer</p><p className="mt-2 text-3xl font-black text-emerald-700">{toCurrency(financial?.revenue_per_patient || 0)}</p>
            <p className="mt-4 text-xs uppercase text-slate-500">Average Order Value (AOV)</p><p className="mt-1 text-3xl font-black text-indigo-700">{toCurrency(financial?.average_order_value || 0)}</p>
            <p className="mt-4 text-xs uppercase text-slate-500">Collection Effectiveness</p><p className="mt-1 text-3xl font-black text-cyan-700">{Number(financial?.collection_effectiveness_percent || 0).toFixed(1)}%</p>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Payer Mix</p>
            <div className="mt-3 h-72"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={financial?.payer_mix || []} dataKey="value" nameKey="payer" outerRadius={110} label>{(financial?.payer_mix || []).map((entry, idx) => <Cell key={entry.payer} fill={PIE_COLORS[idx % PIE_COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer></div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">AI-Powered Predictive Insights (The Brain)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Customer Churn Prediction</p>
            <div className="mt-3 space-y-2">
              {(predictive?.churn_risk_customers || []).map((item) => (
                <div key={item.patient_id} className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2">
                  <p className="text-sm font-semibold text-slate-800">{item.name} ({item.patient_id})</p>
                  <p className="text-xs text-rose-700">Risk Score: {item.risk_score}</p>
                  <p className="text-xs text-slate-600">{item.reason}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">PLV Prediction by Segment</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={predictive?.plv_prediction_by_segment || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="segment" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip formatter={(value: any) => toCurrency(Number(value || 0))} />
                  <Bar dataKey="predicted_plv" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">What-If Scenario Simulator</p>
            <div className="mt-3 space-y-3">
              <input value={whatIfCondition} onChange={(e) => setWhatIfCondition(e.target.value)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Condition (e.g., Diabetes)" />
              <input value={whatIfCity} onChange={(e) => setWhatIfCity(e.target.value)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="City (e.g., Mumbai)" />
              <input type="number" min={0} max={50} value={whatIfDiscount} onChange={(e) => setWhatIfDiscount(Number(e.target.value || 0))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Discount %" />
              <button type="button" onClick={() => void runWhatIf()} disabled={whatIfLoading} className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300">
                {whatIfLoading ? 'Running...' : 'Run Simulation'}
              </button>
              {whatIfResult && (
                <div className="rounded-md border border-indigo-100 bg-indigo-50 p-3 text-sm text-slate-700">
                  <p className="font-semibold text-indigo-800">{whatIfResult.scenario}</p>
                  <p>Customer Volume Uplift: {whatIfResult.projections.projected_patient_volume_uplift_percent.toFixed(2)}%</p>
                  <p>Revenue Impact: {whatIfResult.projections.projected_revenue_impact_percent.toFixed(2)}%</p>
                  <p>Monthly Customer Delta: {whatIfResult.projections.estimated_monthly_patient_delta}</p>
                  <p>Monthly Revenue Delta: {toCurrency(whatIfResult.projections.estimated_monthly_revenue_delta)}</p>
                </div>
              )}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Automated Customer Insights Briefing</p>
            <div className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 p-4 text-sm leading-relaxed text-slate-700">
              {predictive?.automated_patient_briefing || 'No briefing available.'}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Out-of-the-Box "Wow" Features</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-700">Customer 360 View</p>
              <button type="button" onClick={() => setIsCustomer360Open(true)} className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-700">
                Open
              </button>
            </div>
            <p className="mt-3 text-sm text-slate-600">Searchable modal aggregating interactions, menu_items, orders, and feedback.</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Voice of the Customer Feed</p>
            <div className="mt-3 space-y-2">
              {(wow?.voice_of_patient_feed || []).map((item, idx) => (
                <div key={idx} className="rounded-md border border-slate-200 px-3 py-2">
                  <p className="text-xs font-semibold text-slate-700">{item.source} · {item.time}</p>
                  <p className="text-sm text-slate-600">{item.message}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Growth Opportunity AI Assistant</p>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700">
              {(wow?.growth_opportunity_assistant || []).map((item, idx) => <li key={idx}>{item}</li>)}
            </ul>
          </div>
        </div>
      </section>

      {isCustomer360Open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-5xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between">
              <h3 className="text-xl font-bold text-slate-900">Customer 360 View</h3>
              <button type="button" onClick={() => setIsCustomer360Open(false)} className="rounded-md bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
                Close
              </button>
            </div>
            <div className="mt-4 grid grid-cols-12 gap-4">
              <div className="col-span-12 lg:col-span-4">
                <input value={patientSearch} onChange={(e) => setCustomerSearch(e.target.value)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Search patient by name or ID" />
                <div className="mt-3 max-h-80 space-y-2 overflow-auto">
                  {patient360List.map((patient) => (
                    <button key={patient.patient_id} type="button" onClick={() => setSelectedCustomerId(patient.patient_id)} className={`w-full rounded-md border px-3 py-2 text-left ${selectedCustomerId === patient.patient_id ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 bg-white'}`}>
                      <p className="text-sm font-semibold text-slate-800">{patient.name}</p>
                      <p className="text-xs text-slate-500">{patient.patient_id}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="col-span-12 lg:col-span-8">
                {selectedCustomer360 ? (
                  <div className="space-y-3">
                    <div className="rounded-md border border-slate-200 p-3">
                      <p className="text-sm font-semibold text-slate-800">{selectedCustomer360.name} ({selectedCustomer360.patient_id})</p>
                      <p className="text-xs text-slate-600">{selectedCustomer360.feedback}</p>
                    </div>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                      <div className="rounded-md bg-slate-50 p-3"><p className="text-xs font-semibold uppercase text-slate-500">Interactions</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-700">{selectedCustomer360.interactions.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                      <div className="rounded-md bg-slate-50 p-3"><p className="text-xs font-semibold uppercase text-slate-500">MenuItems</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-700">{selectedCustomer360.menu_items.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                      <div className="rounded-md bg-slate-50 p-3"><p className="text-xs font-semibold uppercase text-slate-500">Orders</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-700">{selectedCustomer360.orders.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                    </div>
                    <div className="rounded-md border border-slate-200 p-3">
                      <p className="text-sm font-semibold text-slate-700">Customer Health Journey Timeline</p>
                      <div className="mt-3 space-y-2">
                        {selectedCustomer360.journey_timeline.map((event, idx) => (
                          <div key={idx} className="flex items-center gap-3">
                            <div className="h-2 w-2 rounded-full bg-indigo-500" />
                            <p className="text-xs font-semibold text-slate-700">{event.date}</p>
                            <p className="text-xs text-slate-600">{event.event}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">Select a patient to view the 360 profile.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CeoCustomerInsights
