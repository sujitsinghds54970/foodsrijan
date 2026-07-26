import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  CeoComplianceAuditReadinessResponse,
  CeoComplianceDataPrivacySecurityResponse,
  CeoComplianceHealthScoreResponse,
  CeoComplianceIncidentRiskResponse,
  CeoComplianceLegalContractResponse,
  CeoCompliancePredictiveIntelligenceResponse,
  CeoCompliancePredictiveWhatIfResponse,
  CeoComplianceWowFeaturesResponse,
  CeoComplianceLicenseAccreditationResponse,
  CeoComplianceRegulatoryStatutoryResponse,
  getCeoComplianceAuditInspectionReadiness,
  getCeoComplianceDataPrivacySecurity,
  getCeoComplianceHealthScore,
  getCeoComplianceIncidentRiskManagement,
  getCeoComplianceLegalContractManagement,
  getCeoComplianceLicenseAccreditationManagement,
  getCeoCompliancePredictiveIntelligence,
  getCeoCompliancePredictiveWhatIfSimulation,
  getCeoComplianceRegulatoryStatutory,
  getCeoComplianceWowFeatures,
} from './api'

const CARD_CLASS = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm'

const CeoComplianceLegal = () => {
  const [loading, setLoading] = useState(true)
  const [health, setHealth] = useState<CeoComplianceHealthScoreResponse | null>(null)
  const [licenses, setLicenses] = useState<CeoComplianceLicenseAccreditationResponse | null>(null)
  const [regulatory, setRegulatory] = useState<CeoComplianceRegulatoryStatutoryResponse | null>(null)
  const [legal, setLegal] = useState<CeoComplianceLegalContractResponse | null>(null)
  const [incidentRisk, setIncidentRisk] = useState<CeoComplianceIncidentRiskResponse | null>(null)
  const [auditReadiness, setAuditReadiness] = useState<CeoComplianceAuditReadinessResponse | null>(null)
  const [privacySecurity, setPrivacySecurity] = useState<CeoComplianceDataPrivacySecurityResponse | null>(null)
  const [predictive, setPredictive] = useState<CeoCompliancePredictiveIntelligenceResponse | null>(null)
  const [whatIfResult, setWhatIfResult] = useState<CeoCompliancePredictiveWhatIfResponse | null>(null)
  const [wowFeatures, setWowFeatures] = useState<CeoComplianceWowFeaturesResponse | null>(null)
  const [whatIfState, setWhatIfState] = useState('Maharashtra')
  const [whatIfModel, setWhatIfModel] = useState('Full-Service')
  const [whatIfLoading, setWhatIfLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [healthResp, licenseResp, regulatoryResp, legalResp, incidentResp, auditResp, privacyResp, predictiveResp, whatIfResp, wowResp] = await Promise.all([
          getCeoComplianceHealthScore(),
          getCeoComplianceLicenseAccreditationManagement(),
          getCeoComplianceRegulatoryStatutory(),
          getCeoComplianceLegalContractManagement(),
          getCeoComplianceIncidentRiskManagement(),
          getCeoComplianceAuditInspectionReadiness(),
          getCeoComplianceDataPrivacySecurity(),
          getCeoCompliancePredictiveIntelligence(),
          getCeoCompliancePredictiveWhatIfSimulation({ target_state: 'Maharashtra', branch_model: 'Full-Service' }),
          getCeoComplianceWowFeatures(),
        ])
        setHealth(healthResp)
        setLicenses(licenseResp)
        setRegulatory(regulatoryResp)
        setLegal(legalResp)
        setIncidentRisk(incidentResp)
        setAuditReadiness(auditResp)
        setPrivacySecurity(privacyResp)
        setPredictive(predictiveResp)
        setWhatIfResult(whatIfResp)
        setWowFeatures(wowResp)
      } catch (error: any) {
        toast.error(error?.response?.data?.detail || 'Unable to load Compliance & Legal dashboard')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const healthGaugeData = useMemo(() => {
    const value = Math.max(0, Math.min(health?.score || 0, 100))
    return [{ name: 'Compliance Health', value, fill: value >= 80 ? '#16a34a' : value >= 60 ? '#f59e0b' : '#ef4444' }]
  }, [health])

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading Compliance &amp; Legal dashboard...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">Compliance &amp; Legal</h1>
        <p className="mt-1 text-sm text-slate-600">Regulatory readiness, statutory controls, contract governance, and legal-risk visibility for super-admin oversight.</p>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">WOW Features</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Compliance Control Tower</p>
            <p className="mt-2 text-xs uppercase text-slate-500">Overall Compliance Score</p>
            <p className="text-4xl font-black text-emerald-700">{wowFeatures?.compliance_control_tower.overall_compliance_score || 0}</p>
            <p className="mt-1 text-sm text-slate-600">{wowFeatures?.compliance_control_tower.status || 'N/A'}</p>
            <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
              <div className="rounded-md bg-slate-50 p-2 text-xs text-slate-700">Renewals: <span className="font-bold">{wowFeatures?.compliance_control_tower.open_license_renewals || 0}</span></div>
              <div className="rounded-md bg-slate-50 p-2 text-xs text-slate-700">Audits (30d): <span className="font-bold">{wowFeatures?.compliance_control_tower.upcoming_audits_30d || 0}</span></div>
              <div className="rounded-md bg-slate-50 p-2 text-xs text-slate-700">Incidents: <span className="font-bold">{wowFeatures?.compliance_control_tower.open_incidents || 0}</span></div>
              <div className="rounded-md bg-slate-50 p-2 text-xs text-slate-700">Alerts: <span className="font-bold">{wowFeatures?.compliance_control_tower.active_regulatory_alerts || 0}</span></div>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Automated Compliance Briefing</p>
            <p className="mt-2 text-xs uppercase text-slate-500">{wowFeatures?.automated_compliance_briefing.cadence || 'Daily'}</p>
            <p className="mt-2 rounded-md bg-indigo-50 p-3 text-sm text-slate-700">{wowFeatures?.automated_compliance_briefing.brief}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Regulatory Radar</p>
            <div className="mt-2 space-y-1 text-sm text-slate-700">
              <p><span className="font-semibold text-slate-800">Status:</span> {wowFeatures?.regulatory_radar.monitoring_status || 'N/A'}</p>
              <p><span className="font-semibold text-slate-800">Changes Detected:</span> {wowFeatures?.regulatory_radar.recent_changes_detected || 0}</p>
              <p><span className="font-semibold text-slate-800">Checklist Auto-updates:</span> {wowFeatures?.regulatory_radar.auto_updated_checklist_items || 0}</p>
            </div>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-600">
              {(wowFeatures?.regulatory_radar.highlights || []).map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Digital Compliance Twin</p>
            <p className="mt-2 text-sm text-slate-700">{wowFeatures?.digital_compliance_twin.change_simulation_note}</p>
            <div className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 p-3 text-sm text-slate-700">
              <p><span className="font-semibold text-slate-800">Recent Scenario:</span> {wowFeatures?.digital_compliance_twin.recent_simulation.scenario}</p>
              <p><span className="font-semibold text-slate-800">Projected Posture:</span> {wowFeatures?.digital_compliance_twin.recent_simulation.projected_posture_score}</p>
              <p><span className="font-semibold text-slate-800">Risk Delta:</span> {wowFeatures?.digital_compliance_twin.recent_simulation.risk_delta}</p>
              <p className="mt-1 text-xs">{wowFeatures?.digital_compliance_twin.recent_simulation.advisory}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Compliance Health Scorecard (The Pulse of Protection)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Overall Compliance Health Score</p>
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
              <p className="text-xs uppercase text-slate-500">{health?.status || 'Unknown'}</p>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-3`}>
            <p className="text-xs uppercase text-slate-500">Risk Exposure Level</p>
            <p className={`mt-2 text-3xl font-black ${health?.risk_exposure === 'Low' ? 'text-emerald-700' : health?.risk_exposure === 'Medium' ? 'text-amber-700' : 'text-rose-700'}`}>
              {health?.risk_exposure || 'N/A'}
            </p>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Days Since Last Audit / Inspection</p>
            <div className="mt-3 space-y-2">
              {(health?.days_since_last_audit_by_branch || []).map((item) => (
                <div key={item.branch} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                  <span className="text-sm font-semibold text-slate-800">{item.branch}</span>
                  <span className="text-sm text-slate-700">{item.days_since_last_audit} days</span>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Compliance Status by Category</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={health?.compliance_status_by_category || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" interval={0} angle={-12} textAnchor="end" height={70} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="score" fill="#4f46e5" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Compliance Score Trend</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={health?.score_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#0ea5e9" strokeWidth={3} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">License &amp; Accreditation Management (The Permission Slips)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">License &amp; Accreditation Dashboard</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">License Type</th><th className="pb-2 pr-4">License ID</th><th className="pb-2 pr-4">Status</th><th className="pb-2 pr-4">Expiry Date</th><th className="pb-2">Renewal Application</th>
                  </tr>
                </thead>
                <tbody>
                  {(licenses?.license_accreditation_dashboard || []).map((row) => (
                    <tr key={row.license_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 font-semibold text-slate-800">{row.license_type}</td><td className="py-2 pr-4 text-slate-700">{row.license_id}</td><td className="py-2 pr-4 text-slate-700">{row.status}</td><td className="py-2 pr-4 text-slate-700">{row.expiry_date}</td><td className="py-2 text-slate-700">{row.renewal_application_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Auto-Renewal Alerts</p>
            <div className="mt-3 space-y-2">
              {(licenses?.auto_renewal_alerts || []).map((alert) => (
                <div key={alert.license_id} className={`rounded-md border px-3 py-2 ${alert.days_to_expiry <= 30 ? 'border-rose-200 bg-rose-50' : alert.days_to_expiry <= 60 ? 'border-amber-200 bg-amber-50' : 'border-cyan-200 bg-cyan-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{alert.license_id} · {alert.branch}</p>
                  <p className="text-xs text-slate-700">Expires in {alert.days_to_expiry} days ({alert.alert_window})</p>
                  <p className="text-xs text-slate-600">Renewal: {alert.renewal_application_status}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">NABL Accreditation Tracker</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p><span className="font-semibold text-slate-800">Status:</span> {licenses?.nabl_accreditation_tracker.current_status}</p>
              <p><span className="font-semibold text-slate-800">Document Submission:</span> {licenses?.nabl_accreditation_tracker.document_submission_date}</p>
              <p><span className="font-semibold text-slate-800">Assessment Date:</span> {licenses?.nabl_accreditation_tracker.assessment_date}</p>
              <p><span className="font-semibold text-slate-800">NC Resolution:</span> {licenses?.nabl_accreditation_tracker.non_conformance_resolution}</p>
              <p><span className="font-semibold text-slate-800">Open NCs:</span> {licenses?.nabl_accreditation_tracker.open_non_conformances}</p>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Professional License Tracking</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Name</th><th className="pb-2 pr-4">Role</th><th className="pb-2 pr-4">License #</th><th className="pb-2 pr-4">Status</th><th className="pb-2">Expiry</th></tr></thead>
                <tbody>
                  {(licenses?.professional_license_tracking || []).map((row) => (
                    <tr key={row.license_number} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.name}</td><td className="py-2 pr-4 text-slate-700">{row.role}</td><td className="py-2 pr-4 font-semibold text-slate-800">{row.license_number}</td><td className="py-2 pr-4 text-slate-700">{row.status}</td><td className="py-2 text-slate-700">{row.expiry_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Equipment Certification &amp; Calibration</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Equipment</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Certification</th><th className="pb-2 pr-4">Calibration Due</th><th className="pb-2">Last Calibrated</th></tr></thead>
                <tbody>
                  {(licenses?.equipment_certification_calibration || []).map((row, idx) => (
                    <tr key={`${row.equipment_name}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.equipment_name}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 text-slate-700">{row.certification_status}</td><td className="py-2 pr-4 text-slate-700">{row.calibration_due_date}</td><td className="py-2 text-slate-700">{row.last_calibrated_on}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Document Repository</p>
            <div className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 p-4 text-sm text-slate-700">
              <p className="font-semibold text-cyan-800">{licenses?.document_repository.description}</p>
              <p className="mt-1">{licenses?.document_repository.placeholder_note}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Regulatory &amp; Statutory Compliance (The Rulebook)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Regulatory Compliance Dashboard</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={regulatory?.regulatory_compliance_dashboard || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="regulation" interval={0} angle={-12} textAnchor="end" height={80} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="compliance_percent" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">GLP Compliance (Schedule L-1)</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p><span className="font-semibold text-slate-800">Score:</span> {regulatory?.glp_compliance.score || 0}</p>
              <p><span className="font-semibold text-slate-800">Status:</span> {regulatory?.glp_compliance.status || 'N/A'}</p>
              <p><span className="font-semibold text-slate-800">Open Observations:</span> {regulatory?.glp_compliance.open_observations || 0}</p>
              <p><span className="font-semibold text-slate-800">Last Internal Review:</span> {regulatory?.glp_compliance.last_internal_review || 'N/A'}</p>
            </div>
            <div className="mt-4 rounded-md bg-emerald-50 p-3 text-sm text-slate-700">
              <p className="font-semibold text-emerald-700">Biomedical Waste Management</p>
              <p>Segregation: {regulatory?.biomedical_waste_management.segregation_score || 0}%</p>
              <p>Storage: {regulatory?.biomedical_waste_management.storage_score || 0}%</p>
              <p>Disposal: {regulatory?.biomedical_waste_management.disposal_score || 0}%</p>
              <p>Status: {regulatory?.biomedical_waste_management.composite_status || 'N/A'}</p>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Statutory Filing Tracker</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Filing Type</th><th className="pb-2 pr-4">Period</th><th className="pb-2 pr-4">Due Date</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(regulatory?.statutory_filing_tracker || []).map((row, idx) => (
                    <tr key={`${row.filing_type}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.filing_type}</td><td className="py-2 pr-4 text-slate-700">{row.period}</td><td className="py-2 pr-4 text-slate-700">{row.due_date}</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Regulatory Change Monitor</p>
            <div className="mt-3 space-y-2">
              {(regulatory?.regulatory_change_monitor || []).map((item, idx) => (
                <div key={idx} className={`rounded-md border px-3 py-2 ${item.severity === 'high' ? 'border-rose-200 bg-rose-50' : item.severity === 'medium' ? 'border-amber-200 bg-amber-50' : 'border-cyan-200 bg-cyan-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{item.title}</p>
                  <p className="text-xs text-slate-700">{item.impact}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Legal &amp; Contract Management (The Protection)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Contract Lifecycle Management</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Contract ID</th><th className="pb-2 pr-4">Type</th><th className="pb-2 pr-4">Counterparty</th><th className="pb-2 pr-4">Start</th><th className="pb-2 pr-4">Expiry</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(legal?.contract_lifecycle_management || []).map((row) => (
                    <tr key={row.contract_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.contract_id}</td><td className="py-2 pr-4 text-slate-700">{row.contract_type}</td><td className="py-2 pr-4 text-slate-700">{row.counterparty}</td><td className="py-2 pr-4 text-slate-700">{row.start_date}</td><td className="py-2 pr-4 text-slate-700">{row.expiry_date}</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Auto-Contract Renewal Alerts</p>
            <div className="mt-3 space-y-2">
              {(legal?.auto_contract_renewal_alerts || []).map((row) => (
                <div key={row.contract_id} className={`rounded-md border px-3 py-2 ${row.days_to_expiry <= 60 ? 'border-amber-200 bg-amber-50' : 'border-cyan-200 bg-cyan-50'}`}>
                  <p className="text-sm font-semibold text-slate-800">{row.contract_id}</p>
                  <p className="text-xs text-slate-700">Days to expiry: {row.days_to_expiry} · Deadline: {row.renewal_deadline}</p>
                  <p className="text-xs text-slate-600">{row.status}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Key Terms Extraction</p>
            <div className="mt-3 space-y-2">
              {(legal?.key_terms_extraction || []).map((row) => (
                <div key={row.contract_id} className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">
                  <p className="font-semibold text-slate-800">{row.contract_id}</p>
                  <p>Termination: {row.termination_clause}</p>
                  <p>Payment: {row.payment_terms}</p>
                  <p>Liability: {row.liability_limit}</p>
                  <p>Confidentiality: {row.confidentiality}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Legal Case Tracker</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Case ID</th><th className="pb-2 pr-4">Matter</th><th className="pb-2 pr-4">Counterparty</th><th className="pb-2 pr-4">Stage</th><th className="pb-2 pr-4">Next Action</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(legal?.legal_case_tracker || []).map((row) => (
                    <tr key={row.case_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.case_id}</td><td className="py-2 pr-4 text-slate-700">{row.matter}</td><td className="py-2 pr-4 text-slate-700">{row.counterparty}</td><td className="py-2 pr-4 text-slate-700">{row.stage}</td><td className="py-2 pr-4 text-slate-700">{row.next_hearing_or_action_date}</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Policy Attestation Management</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Policy</th><th className="pb-2 pr-4">Signed/Target</th><th className="pb-2 pr-4">Attestation</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(legal?.policy_attestation_management || []).map((row) => (
                    <tr key={row.policy_name} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.policy_name}</td><td className="py-2 pr-4 text-slate-700">{row.employees_signed}/{row.employees_targeted}</td><td className="py-2 pr-4 text-slate-700">{row.attestation_percent.toFixed(1)}%</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Incident &amp; Risk Management (The Early Warning System)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Incident Dashboard</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Incident ID</th><th className="pb-2 pr-4">Category</th><th className="pb-2 pr-4">Severity</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Status</th><th className="pb-2">Reported At</th></tr></thead>
                <tbody>
                  {(incidentRisk?.incident_dashboard || []).map((row) => (
                    <tr key={row.incident_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.incident_id}</td><td className="py-2 pr-4 text-slate-700">{row.category}</td><td className="py-2 pr-4 text-slate-700">{row.severity}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 text-slate-700">{row.status}</td><td className="py-2 text-slate-700">{row.reported_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Incident Severity &amp; Resolution Time</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={incidentRisk?.incident_severity_resolution_time || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="severity" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="incident_count" fill="#8b5cf6" name="Incident Count" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="avg_resolution_hours" fill="#f97316" name="Avg Resolution (hrs)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Anonymous Whistleblower Hotline</p>
            <p className="mt-2 text-xs text-slate-600">{incidentRisk?.whistleblower_hotline.note}</p>
            <form
              className="mt-3 space-y-2"
              onSubmit={(event) => {
                event.preventDefault()
                toast.success('Mock whistleblower report submitted for demo.')
              }}
            >
              <input className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Concern category" />
              <textarea className="h-24 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Describe concern anonymously" />
              <button type="submit" className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Submit Anonymous Report</button>
            </form>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Risk Register</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Risk ID</th><th className="pb-2 pr-4">Risk</th><th className="pb-2 pr-4">Likelihood</th><th className="pb-2 pr-4">Impact</th><th className="pb-2">Mitigation Status</th></tr></thead>
                <tbody>
                  {(incidentRisk?.risk_register || []).map((row) => (
                    <tr key={row.risk_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.risk_id}</td><td className="py-2 pr-4 text-slate-700">{row.risk_name}</td><td className="py-2 pr-4 text-slate-700">{row.likelihood}</td><td className="py-2 pr-4 text-slate-700">{row.impact}</td><td className="py-2 text-slate-700">{row.mitigation_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Complaint Analysis &amp; Trends</p>
            <div className="mt-3 space-y-2">
              {(incidentRisk?.complaint_analysis_trends.top_recurring_themes || []).map((row) => (
                <div key={row.theme} className="rounded-md bg-slate-50 px-3 py-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-semibold text-slate-800">{row.theme}</span>
                    <span className="text-slate-700">{row.share_percent}%</span>
                  </div>
                </div>
              ))}
              <p className="rounded-md border border-cyan-100 bg-cyan-50 p-3 text-xs text-slate-700">{incidentRisk?.complaint_analysis_trends.ai_summary}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Audit &amp; Inspection Readiness (The Proof)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Audit Schedule &amp; Calendar</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Audit</th><th className="pb-2 pr-4">Type</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Scheduled Date</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(auditReadiness?.audit_schedule_calendar || []).map((row, idx) => (
                    <tr key={`${row.audit_name}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.audit_name}</td><td className="py-2 pr-4 text-slate-700">{row.audit_type}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 text-slate-700">{row.scheduled_date}</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Audit Trail &amp; Evidence Log</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Event Time</th><th className="pb-2 pr-4">Activity</th><th className="pb-2 pr-4">Owner</th><th className="pb-2">Evidence ID</th></tr></thead>
                <tbody>
                  {(auditReadiness?.audit_trail_evidence_log || []).map((row) => (
                    <tr key={row.evidence_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.event_time}</td><td className="py-2 pr-4 text-slate-700">{row.activity}</td><td className="py-2 pr-4 text-slate-700">{row.owner}</td><td className="py-2 font-semibold text-slate-800">{row.evidence_id}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Pre-Audit Checklist</p>
            <div className="mt-3 space-y-2">
              {(auditReadiness?.pre_audit_checklist || []).map((row) => (
                <div key={row.item} className={`rounded-md border px-3 py-2 text-sm ${row.status === 'Done' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : row.status === 'In Progress' ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-slate-200 bg-slate-50 text-slate-700'}`}>
                  <p className="font-semibold">{row.item}</p>
                  <p className="text-xs">Status: {row.status}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Non-Conformance &amp; Corrective Action Tracker</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">NC ID</th><th className="pb-2 pr-4">Finding</th><th className="pb-2 pr-4">Corrective Action</th><th className="pb-2 pr-4">Owner</th><th className="pb-2 pr-4">Target Date</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(auditReadiness?.non_conformance_corrective_action_tracker || []).map((row) => (
                    <tr key={row.nc_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.nc_id}</td><td className="py-2 pr-4 text-slate-700">{row.finding}</td><td className="py-2 pr-4 text-slate-700">{row.corrective_action}</td><td className="py-2 pr-4 text-slate-700">{row.owner}</td><td className="py-2 pr-4 text-slate-700">{row.target_date}</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Inspection Report Repository</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Report ID</th><th className="pb-2 pr-4">Inspection</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Report Date</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(auditReadiness?.inspection_report_repository || []).map((row) => (
                    <tr key={row.report_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.report_id}</td><td className="py-2 pr-4 text-slate-700">{row.inspection_name}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 text-slate-700">{row.report_date}</td><td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">Data Privacy &amp; Security (The Trust)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">Data Privacy Dashboard</p>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Consent Mgmt</p><p className="text-2xl font-black text-slate-900">{privacySecurity?.data_privacy_dashboard.consent_management_percent || 0}%</p></div>
              <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Access Logs Reviewed</p><p className="text-2xl font-black text-slate-900">{privacySecurity?.data_privacy_dashboard.data_access_logs_reviewed_percent || 0}%</p></div>
              <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Open Breaches</p><p className="text-2xl font-black text-rose-700">{privacySecurity?.data_privacy_dashboard.breach_incidents_open || 0}</p></div>
              <div className="rounded-md bg-slate-50 p-3"><p className="text-xs text-slate-500">Privacy Training</p><p className="text-2xl font-black text-slate-900">{privacySecurity?.data_privacy_dashboard.privacy_training_completion_percent || 0}%</p></div>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Security Training Completion</p>
            <p className="mt-2 text-4xl font-black text-emerald-700">{privacySecurity?.security_training_completion.overall_completion_percent || 0}%</p>
            <p className="mt-2 text-sm text-slate-700">
              {privacySecurity?.security_training_completion.employees_completed || 0}/{privacySecurity?.security_training_completion.employees_total || 0} completed
            </p>
            <p className="text-xs text-slate-600">Overdue learners: {privacySecurity?.security_training_completion.overdue_learners || 0}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">GDPR / HIPAA / DPDP Compliance</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={privacySecurity?.regulation_compliance_tracker || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="regulation" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="adherence_percent" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Data Retention &amp; Disposal Policy</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p><span className="font-semibold text-slate-800">Adherence:</span> {privacySecurity?.data_retention_disposal_policy.adherence_percent || 0}%</p>
              <p><span className="font-semibold text-slate-800">Overdue Disposals:</span> {privacySecurity?.data_retention_disposal_policy.overdue_disposals || 0}</p>
              <p><span className="font-semibold text-slate-800">Last Policy Review:</span> {privacySecurity?.data_retention_disposal_policy.last_policy_review || 'N/A'}</p>
              <p><span className="font-semibold text-slate-800">Status:</span> {privacySecurity?.data_retention_disposal_policy.status || 'N/A'}</p>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Data Breach Incident Log</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Incident ID</th><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Severity</th><th className="pb-2 pr-4">Reported On</th><th className="pb-2">Resolution Status</th></tr></thead>
                <tbody>
                  {(privacySecurity?.data_breach_incident_log || []).map((row) => (
                    <tr key={row.incident_id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.incident_id}</td><td className="py-2 pr-4 text-slate-700">{row.branch}</td><td className="py-2 pr-4 text-slate-700">{row.severity}</td><td className="py-2 pr-4 text-slate-700">{row.reported_on}</td><td className="py-2 text-slate-700">{row.resolution_status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-bold text-slate-900">AI-Powered Predictive Intelligence (The Brain)</h2>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Compliance Risk Prediction</p>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={predictive?.compliance_risk_prediction || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="risk_area" interval={0} angle={-12} textAnchor="end" height={90} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="predicted_risk_score" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Incident Trend Analysis &amp; Prediction</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p className="font-semibold text-slate-800">Next quarter forecast</p>
              <p>Low: {predictive?.incident_trend_prediction.next_quarter_incident_forecast.low || 0}</p>
              <p>Medium: {predictive?.incident_trend_prediction.next_quarter_incident_forecast.medium || 0}</p>
              <p>High: {predictive?.incident_trend_prediction.next_quarter_incident_forecast.high || 0}</p>
              <p>Critical: {predictive?.incident_trend_prediction.next_quarter_incident_forecast.critical || 0}</p>
            </div>
            <div className="mt-3 rounded-md bg-slate-50 p-3 text-xs text-slate-700">
              <p className="font-semibold text-slate-800">Predicted Hotspots</p>
              <ul className="mt-1 list-disc space-y-1 pl-4">
                {(predictive?.incident_trend_prediction.predicted_hotspots || []).map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Regulatory Change Impact Analysis</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Regulatory Update</th><th className="pb-2 pr-4">Operational Impact</th><th className="pb-2 pr-4">Compliance Impact</th><th className="pb-2">Recommended Response</th></tr></thead>
                <tbody>
                  {(predictive?.regulatory_change_impact_analysis || []).map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.regulation_update}</td><td className="py-2 pr-4 text-slate-700">{row.operational_impact}</td><td className="py-2 pr-4 text-slate-700">{row.compliance_impact}</td><td className="py-2 text-slate-700">{row.recommended_response}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">What-If Scenario Simulator</p>
            <form
              className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-4"
              onSubmit={async (event) => {
                event.preventDefault()
                try {
                  setWhatIfLoading(true)
                  const result = await getCeoCompliancePredictiveWhatIfSimulation({
                    target_state: whatIfState,
                    branch_model: whatIfModel,
                  })
                  setWhatIfResult(result)
                  toast.success('Compliance what-if simulation completed.')
                } catch (error: any) {
                  toast.error(error?.response?.data?.detail || 'Failed to run simulation')
                } finally {
                  setWhatIfLoading(false)
                }
              }}
            >
              <input value={whatIfState} onChange={(e) => setWhatIfState(e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Target state" />
              <select value={whatIfModel} onChange={(e) => setWhatIfModel(e.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
                <option>Full-Service</option>
                <option>Collection-Center</option>
              </select>
              <button disabled={whatIfLoading} type="submit" className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-70">
                {whatIfLoading ? 'Simulating...' : 'Run Simulation'}
              </button>
            </form>
            {whatIfResult && (
              <div className="mt-3 rounded-md border border-cyan-100 bg-cyan-50 p-3 text-sm text-slate-700">
                <p><span className="font-semibold text-slate-800">Licensing Complexity:</span> {whatIfResult.simulation.licensing_complexity}</p>
                <p><span className="font-semibold text-slate-800">Readiness Time:</span> {whatIfResult.simulation.regulatory_readiness_time_weeks} weeks</p>
                <p><span className="font-semibold text-slate-800">Projected Setup Cost:</span> ₹{whatIfResult.simulation.projected_compliance_setup_cost.toLocaleString()}</p>
                <p className="mt-2 font-semibold text-slate-800">Key Implications</p>
                <ul className="list-disc space-y-1 pl-4">
                  {whatIfResult.simulation.key_implications.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

export default CeoComplianceLegal
