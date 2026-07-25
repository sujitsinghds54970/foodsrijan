import React, { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

import {
  addFamilyMember,
  getPatientDashboard,
  getPatientReports,
  getReportDownloadUrl,
  notifyPatientReport,
  patientLogin,
  redeemWallet,
} from './api'

interface PatientDashboardProps {
  active: boolean
}

const STORAGE_KEY = 'patient_portal_token'
const SESSION_EVENT = 'patient-portal-session-changed'

interface Branding {
  clinic_name?: string
  clinic_address?: string
  logo_url?: string
  report_header?: {
    title?: string
    subtitle?: string
    logo_url?: string
  }
}

export default function PatientDashboard({ active }: PatientDashboardProps) {
  const [token, setToken] = useState<string | null>(localStorage.getItem(STORAGE_KEY))
  const [loading, setLoading] = useState(false)
  const [dashboard, setDashboard] = useState<any>(null)
  const [reportsData, setReportsData] = useState<any>({ reports: [], total: 0, page: 1, page_size: 10 })

  const [loginMode, setLoginMode] = useState<'otp' | 'password'>('otp')
  const [mobile, setMobile] = useState('')
  const [otp, setOtp] = useState('123456')
  const [patientCode, setPatientCode] = useState('')
  const [password, setPassword] = useState('')

  const [familyName, setFamilyName] = useState('')
  const [familyRelation, setFamilyRelation] = useState('')
  const [familyMobile, setFamilyMobile] = useState('')
  const [redeemAmount, setRedeemAmount] = useState('')

  const kpis = useMemo(() => dashboard?.kpis || {}, [dashboard])
  const branding = useMemo<Branding>(() => dashboard?.branding || {}, [dashboard])
  const brandTitle = branding?.clinic_name || 'Vaidya Vihar Diagnostic'
  const brandSubtitle = branding?.clinic_address || 'Trusted diagnostics and patient care portal'

  const loadPortal = useCallback(async (portalToken: string) => {
    setLoading(true)
    try {
      const [dash, reports] = await Promise.all([
        getPatientDashboard(portalToken),
        getPatientReports(portalToken, reportsData.page || 1, reportsData.page_size || 10),
      ])
      setDashboard(dash)
      setReportsData(reports)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to load patient portal data')
    } finally {
      setLoading(false)
    }
  }, [reportsData.page, reportsData.page_size])

  useEffect(() => {
    if (!active || !token) return
    loadPortal(token)
  }, [active, token, loadPortal])

  const onLogin = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    try {
      const session =
        loginMode === 'otp'
          ? await patientLogin({ mode: 'otp', mobile, otp })
          : await patientLogin({ mode: 'password', patient_id: patientCode, password })

      localStorage.setItem(STORAGE_KEY, session.access_token)
      setToken(session.access_token)
      window.dispatchEvent(new Event(SESSION_EVENT))
      toast.success(`Welcome ${session.patient.full_name}`)
      await loadPortal(session.access_token)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const onLogout = () => {
    localStorage.removeItem(STORAGE_KEY)
    setToken(null)
    window.dispatchEvent(new Event(SESSION_EVENT))
    setDashboard(null)
    setReportsData({ reports: [], total: 0, page: 1, page_size: 10 })
  }

  const onDownloadReport = async (reportId: number) => {
    if (!token) return
    try {
      const data = await getReportDownloadUrl(token, reportId)
      window.open(`http://127.0.0.1:8000${data.download_url}`, '_blank')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to download report')
    }
  }

  const onNotify = async (reportId: number, channel: 'whatsapp' | 'email') => {
    if (!token) return
    try {
      const data = await notifyPatientReport(token, reportId, channel)
      if (data.channel_url) {
        window.open(data.channel_url, '_blank')
      }
      toast.success(`Share link prepared for ${channel}`)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to prepare share link')
    }
  }

  const onAddFamily = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!token) return
    try {
      await addFamilyMember(token, {
        name: familyName,
        relation: familyRelation,
        mobile: familyMobile || undefined,
      })
      setFamilyName('')
      setFamilyRelation('')
      setFamilyMobile('')
      toast.success('Family member added')
      await loadPortal(token)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to add family member')
    }
  }

  const onRedeem = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!token) return
    const value = Number(redeemAmount)
    if (!value) {
      toast.error('Enter redeem amount')
      return
    }
    try {
      await redeemWallet(token, value)
      setRedeemAmount('')
      toast.success('Wallet redeemed')
      await loadPortal(token)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to redeem wallet')
    }
  }

  if (!active) return null

  if (!token) {
    return (
      <div className="rounded-3xl border border-emerald-100 bg-gradient-to-br from-white via-cyan-50 to-emerald-50 p-8 shadow-xl">
        <h2 className="text-3xl font-black text-slate-900">Patient Portal Login</h2>
        <p className="mt-2 text-slate-600">Use OTP login or patient ID with password.</p>

        <div className="mt-6 inline-flex rounded-xl border border-cyan-200 bg-white p-1">
          <button
            className={`rounded-lg px-4 py-2 text-sm font-semibold ${loginMode === 'otp' ? 'bg-cyan-600 text-white' : 'text-slate-700'}`}
            onClick={() => setLoginMode('otp')}
          >
            OTP Login
          </button>
          <button
            className={`rounded-lg px-4 py-2 text-sm font-semibold ${loginMode === 'password' ? 'bg-emerald-600 text-white' : 'text-slate-700'}`}
            onClick={() => setLoginMode('password')}
          >
            Patient ID Login
          </button>
        </div>

        <form className="mt-6 grid gap-4 md:grid-cols-2" onSubmit={onLogin}>
          {loginMode === 'otp' ? (
            <>
              <input
                className="rounded-xl border border-cyan-200 px-4 py-3"
                placeholder="Mobile number"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                required
              />
              <input
                className="rounded-xl border border-cyan-200 px-4 py-3"
                placeholder="OTP (use 123456)"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                required
              />
            </>
          ) : (
            <>
              <input
                className="rounded-xl border border-emerald-200 px-4 py-3"
                placeholder="Patient ID"
                value={patientCode}
                onChange={(e) => setPatientCode(e.target.value)}
                required
              />
              <input
                className="rounded-xl border border-emerald-200 px-4 py-3"
                placeholder="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="md:col-span-2 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 px-5 py-3 font-semibold text-white"
          >
            {loading ? 'Please wait...' : 'Continue to Portal'}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-cyan-100 bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 p-6 text-white shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {branding?.logo_url ? (
              <img src={branding.logo_url} alt={`${brandTitle} logo`} className="h-14 w-14 rounded-2xl border border-white/30 object-cover" />
            ) : null}
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-50">{brandTitle}</p>
              <p className="text-xs text-cyan-100">{brandSubtitle}</p>
            </div>
          </div>
          <div>
            <h2 className="text-3xl font-black">My Health Dashboard</h2>
            <p className="mt-1 text-cyan-50">Reports, wallet, family account, and care tracking in one place.</p>
          </div>
          <button onClick={onLogout} className="rounded-xl bg-white/20 px-4 py-2 font-semibold">
            Logout
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Total Reports</p>
          <p className="mt-2 text-2xl font-black text-slate-900">{kpis.total_reports || 0}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Completed</p>
          <p className="mt-2 text-2xl font-black text-emerald-700">{kpis.completed_reports || 0}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Pending</p>
          <p className="mt-2 text-2xl font-black text-amber-600">{kpis.pending_reports || 0}</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Wallet Balance</p>
          <p className="mt-2 text-2xl font-black text-cyan-700">Rs. {Number(kpis.wallet_balance || 0).toFixed(2)}</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-5 py-4">
            <h3 className="text-lg font-bold text-slate-900">Reports</h3>
            <p className="mt-1 text-xs text-slate-500">Header branding will follow {brandTitle} for shared/downloaded reports.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left">Patient ID</th>
                  <th className="px-4 py-3 text-left">Test</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(reportsData.reports || []).map((report: any) => (
                  <tr className="border-t border-slate-100" key={report.id}>
                    <td className="px-4 py-3 font-medium">{report.patient_id}</td>
                    <td className="px-4 py-3">{report.test_name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-semibold ${
                          report.status === 'Completed' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {report.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button onClick={() => onDownloadReport(report.id)} className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white">
                          Download
                        </button>
                        <button onClick={() => onNotify(report.id, 'whatsapp')} className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white">
                          WhatsApp
                        </button>
                        <button onClick={() => onNotify(report.id, 'email')} className="rounded-lg bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white">
                          Email
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-lg font-bold text-slate-900">Health Wallet</h3>
            <p className="mt-1 text-sm text-slate-500">Cashback: {kpis.cashback_percent || 0}%</p>
            <form className="mt-4 space-y-3" onSubmit={onRedeem}>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2"
                placeholder="Redeem amount"
                value={redeemAmount}
                onChange={(e) => setRedeemAmount(e.target.value)}
              />
              <button className="w-full rounded-xl bg-emerald-600 px-4 py-2.5 font-semibold text-white" type="submit">
                Redeem Wallet
              </button>
            </form>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-lg font-bold text-slate-900">Family Account</h3>
            <form className="mt-3 space-y-2" onSubmit={onAddFamily}>
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2"
                placeholder="Name"
                value={familyName}
                onChange={(e) => setFamilyName(e.target.value)}
                required
              />
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2"
                placeholder="Relation"
                value={familyRelation}
                onChange={(e) => setFamilyRelation(e.target.value)}
                required
              />
              <input
                className="w-full rounded-xl border border-slate-200 px-3 py-2"
                placeholder="Mobile (optional)"
                value={familyMobile}
                onChange={(e) => setFamilyMobile(e.target.value)}
              />
              <button className="w-full rounded-xl bg-cyan-600 px-4 py-2.5 font-semibold text-white" type="submit">
                Add Member
              </button>
            </form>
            <div className="mt-3 space-y-2">
              {(dashboard?.family_members || []).map((member: any) => (
                <div key={member.id} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{member.name}</p>
                  <p className="text-slate-500">{member.relation}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="text-lg font-bold text-slate-900">Sample Tracking</h3>
            <div className="mt-3 space-y-2">
              {(dashboard?.sample_tracking || []).map((item: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <span className="text-sm font-medium text-slate-700">{item.step}</span>
                  <span className={`text-xs font-semibold ${item.done ? 'text-emerald-700' : 'text-slate-500'}`}>
                    {item.done ? 'Done' : 'Waiting'}
                  </span>
                </div>
              ))}
            </div>
            <button className="mt-4 w-full rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 px-4 py-2.5 font-semibold text-white">
              Book Appointment
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
