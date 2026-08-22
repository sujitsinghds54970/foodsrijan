import React, { useCallback, useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { useAuth } from '../../contexts/AuthContext'
import {
  addAppointmentConsent,
  askCustomerChatbot,
  createOrUpdateCustomerGoal,
  createCustomerReferral,
  createB2CAppointment,
  getB2CProfile,
  getCustomerHealthScore,
  getCustomerReminders,
  getCustomerOrderSummary,
  getCustomerOrdersPhase2,
  getCustomerTrends,
  getCustomerWallet,
  getB2CMenuItemCatalog,
  getUpcomingAppointments,
  requestCustomerOtp,
  verifyCustomerOtp,
} from './b2cApi'

interface CustomerB2CPhase1Props {
  active: boolean
}

export default function CustomerB2CPhase1({ active }: CustomerB2CPhase1Props) {
  const { token } = useAuth()
  const patientToken = typeof window !== 'undefined' ? localStorage.getItem('patient_portal_token') : null
  const apiToken = patientToken || token

  const [loading, setLoading] = useState(false)
  const [mobile, setMobile] = useState('')
  const [otp, setOtp] = useState('')

  const [profile, setProfile] = useState<any>(null)
  const [menu_items, setMenuItems] = useState<any[]>([])
  const [upcoming, setUpcoming] = useState<any[]>([])
  const [selectedMenuItems, setSelectedMenuItems] = useState<number[]>([])
  const [appointmentType, setAppointmentType] = useState<'Home' | 'Center'>('Center')
  const [scheduledTime, setScheduledTime] = useState('')
  const [orders, setOrders] = useState<any[]>([])
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null)
  const [reportSummary, setOrderSummary] = useState<{ ai_summary: string; abnormal_flags: Record<string, string> } | null>(null)
  const [showSummaryModal, setShowSummaryModal] = useState(false)
  const [healthScore, setHealthScore] = useState<{ score: number; band: string } | null>(null)
  const [reminders, setReminders] = useState<any[]>([])
  const [trendBiomarker, setTrendBiomarker] = useState('HbA1c')
  const [trendPoints, setTrendPoints] = useState<Array<{ date: string; value: number }>>([])
  const [chatOpen, setChatOpen] = useState(false)
  const [chatQuery, setChatQuery] = useState('')
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'assistant'; text: string }>>([
    {
      role: 'assistant',
      text: 'Hello. I can help with report explanations, fasting prep, and follow-up reminders.',
    },
  ])
  const [consentText, setConsentText] = useState(
    'I consent to sample collection, processing, and diagnostic report generation for selected menu_items.'
  )
  const [consentAppointmentId, setConsentAppointmentId] = useState('')
  const [wallet, setWallet] = useState<{
    available_points: number
    payment_history: Array<{ id: number; points: number; transaction_type: string; description: string; created_at: string }>
    payment_options: Array<{ type: string; label: string }>
  } | null>(null)
  const [referralCode, setReferralCode] = useState('')
  const [referralLink, setReferralLink] = useState('')
  const [goals, setGoals] = useState<Array<{ id: number; goal_type: string; target_date: string; status: string; reward_points: number }>>([])
  const [goalType, setGoalType] = useState('Lower HbA1c below 7 for 3 months')
  const [goalTargetDate, setGoalTargetDate] = useState('')
  const [goalStatus, setGoalStatus] = useState('In Progress')
  const [insuranceEnabled, setInsuranceEnabled] = useState(false)
  const [insuranceProvider, setInsuranceProvider] = useState('')
  const [insurancePolicy, setInsurancePolicy] = useState('')
  const [corporateId, setCorporateId] = useState('')
  const [insuranceFileName, setInsuranceFileName] = useState('')

  const recommendation = useMemo(() => {
    if (!menu_items.length) return null
    const basic = menu_items.find((item) => item.name.toLowerCase().includes('cbc'))
    const thyroid = menu_items.find((item) => item.name.toLowerCase().includes('thyroid'))
    const lipid = menu_items.find((item) => item.name.toLowerCase().includes('lipid'))
    const picks = [basic, thyroid, lipid].filter(Boolean)
    if (!picks.length) return null

    const total = picks.reduce((sum: number, item: any) => sum + Number(item.price || 0), 0)
    const discounted = Math.round(total * 0.9)
    return {
      menu_items: picks,
      total,
      discounted,
      title: 'AI Recommended Vital Screening',
    }
  }, [menu_items])

  const loadPhase1 = useCallback(async () => {
    if (!apiToken) return
    setLoading(true)
    try {
      const [profileData, testCatalog, upcomingData] = await Promise.all([
        getB2CProfile(apiToken),
        getB2CMenuItemCatalog(apiToken),
        getUpcomingAppointments(apiToken),
      ])
      const [ordersData, scoreData, reminderData, trendData, walletData] = await Promise.all([
        getCustomerOrdersPhase2(apiToken),
        getCustomerHealthScore(apiToken),
        getCustomerReminders(apiToken),
        getCustomerTrends(apiToken, trendBiomarker),
        getCustomerWallet(apiToken),
      ])
      setProfile(profileData)
      setMenuItems(testCatalog.menu_items || [])
      setUpcoming(upcomingData.appointments || [])
      setOrders(ordersData.orders || [])
      setHealthScore({ score: scoreData.score, band: scoreData.band })
      setReminders(reminderData.reminders || [])
      setTrendPoints((trendData.points || []).map((item) => ({ date: item.date, value: item.value })))
      setWallet(walletData)
      if (!mobile && profileData.mobile) {
        setMobile(profileData.mobile)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to load Phase 1 patient portal')
    } finally {
      setLoading(false)
    }
  }, [apiToken, mobile, trendBiomarker])

  useEffect(() => {
    if (!active || !apiToken) return
    loadPhase1()
  }, [active, apiToken, loadPhase1])

  const onRequestOtp = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      const result = await requestCustomerOtp(mobile)
      if (result.otp_for_dev) {
        toast.success(`OTP generated: ${result.otp_for_dev}`)
      } else {
        toast.success(result.message)
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to request OTP')
    }
  }

  const onVerifyOtp = async (event: React.FormEvent) => {
    event.preventDefault()
    try {
      const result = await verifyCustomerOtp(mobile, otp)
      toast.success(result.message)
      await loadPhase1()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to verify OTP')
    }
  }

  const onToggleMenuItem = (testId: number) => {
    setSelectedMenuItems((prev) =>
      prev.includes(testId) ? prev.filter((id) => id !== testId) : [...prev, testId]
    )
  }

  const onBookAppointment = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!apiToken) return

    if (!selectedMenuItems.length) {
      toast.error('Select at least one test')
      return
    }

    if (!scheduledTime) {
      toast.error('Select appointment date and time')
      return
    }

    try {
      await createB2CAppointment(apiToken, {
        test_ids: selectedMenuItems,
        appointment_type: appointmentType,
        scheduled_time: new Date(scheduledTime).toISOString(),
      })
      toast.success('Appointment booked successfully')
      setSelectedMenuItems([])
      await loadPhase1()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to create appointment')
    }
  }

  const onSignConsent = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!apiToken) return

    const appointmentId = Number(consentAppointmentId)
    if (!appointmentId) {
      toast.error('Enter a valid appointment id')
      return
    }

    try {
      await addAppointmentConsent(apiToken, appointmentId, consentText)
      toast.success('Consent signed successfully')
      setConsentAppointmentId('')
      await loadPhase1()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to sign consent')
    }
  }

  const onAskAiSummary = async (report: any) => {
    if (!apiToken) return
    try {
      const summary = await getCustomerOrderSummary(apiToken, report.id)
      setSelectedOrder(report)
      setOrderSummary({ ai_summary: summary.ai_summary, abnormal_flags: summary.abnormal_flags || {} })
      setShowSummaryModal(true)
      if (summary.critical_alert_required) {
        window.dispatchEvent(new Event('patient-critical-alert'))
        toast.error('Critical alert dispatched to patient and doctor')
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to fetch AI summary')
    }
  }

  const onTrendChange = async (biomarker: string) => {
    if (!apiToken) return
    try {
      setTrendBiomarker(biomarker)
      const trendData = await getCustomerTrends(apiToken, biomarker)
      setTrendPoints((trendData.points || []).map((item) => ({ date: item.date, value: item.value })))
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to load trend data')
    }
  }

  const onSendChat = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!apiToken) return
    const query = chatQuery.trim()
    if (!query) return

    setChatMessages((prev) => [...prev, { role: 'user', text: query }])
    setChatQuery('')
    try {
      const result = await askCustomerChatbot(apiToken, query)
      setChatMessages((prev) => [...prev, { role: 'assistant', text: result.response }])
    } catch (error: any) {
      const fallback = error?.response?.data?.detail || 'AI assistant is currently unavailable'
      setChatMessages((prev) => [...prev, { role: 'assistant', text: fallback }])
    }
  }

  const onGenerateReferral = async () => {
    if (!apiToken) return
    try {
      const data = await createCustomerReferral(apiToken)
      setReferralCode(data.referral_code)
      setReferralLink(data.referral_link)
      toast.success('Referral link generated')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to generate referral link')
    }
  }

  const onCopyReferral = async () => {
    if (!referralLink) return
    try {
      await navigator.clipboard.writeText(referralLink)
      toast.success('Referral link copied')
    } catch {
      toast.error('Unable to copy link automatically')
    }
  }

  const onSaveGoal = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!apiToken) return
    if (!goalTargetDate) {
      toast.error('Select a target date for your goal')
      return
    }
    try {
      const saved = await createOrUpdateCustomerGoal(apiToken, {
        goal_type: goalType,
        target_date: new Date(goalTargetDate).toISOString(),
        status: goalStatus,
      })
      setGoals((prev) => {
        const filtered = prev.filter((item) => item.id !== saved.id && item.goal_type !== saved.goal_type)
        return [saved, ...filtered]
      })
      toast.success('Goal challenge saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to save challenge')
    }
  }

  const onSaveInsurance = (event: React.FormEvent) => {
    event.preventDefault()
    if (!insuranceEnabled) {
      toast.success('Corporate/insurance billing disabled')
      return
    }
    if (!insuranceProvider || !insurancePolicy) {
      toast.error('Enter insurance provider and policy details')
      return
    }
    toast.success('Insurance details captured for billing desk verification')
  }

  if (!active) return null

  return (
    <div className="space-y-5">
      <section className="relative overflow-hidden rounded-3xl border border-[#f6d8c8] bg-gradient-to-br from-[#fff5ef] via-[#fef9f2] to-[#fffef9] p-5 shadow-sm">
        <div className="absolute -right-14 -top-14 h-36 w-36 rounded-full bg-[#f8c29a]/25" />
        <div className="absolute -bottom-16 -left-16 h-40 w-40 rounded-full bg-[#8db7a8]/15" />
        <div className="relative">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[#9a6a4f]">Customer B2C Phase 1</p>
          <h2 className="mt-1 text-2xl font-black text-[#2f2a24]">Mobile-first Health Journey</h2>
          <p className="mt-2 max-w-2xl text-sm text-[#5d5348]">
            Secure OTP verification, test discovery, bookings, digital consent, and family context in one patient-safe flow.
          </p>
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-3">
        <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm lg:col-span-1">
          <h3 className="text-base font-bold text-[#2f2a24]">Health Score</h3>
          <div className="mt-3 rounded-2xl bg-gradient-to-br from-[#2f7d6b] to-[#194d43] p-4 text-white">
            <p className="text-xs uppercase tracking-[0.14em] text-[#c5e8de]">AI Wellness Index</p>
            <p className="mt-2 text-4xl font-black">{healthScore?.score ?? '--'}</p>
            <p className="mt-1 text-sm text-[#d9f2eb]">{healthScore?.band || 'Calculating...'}</p>
          </div>
          <div className="mt-4 space-y-2">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d7b66]">Smart Reminders</p>
            {reminders.slice(0, 3).map((item) => (
              <div key={item.id} className="rounded-xl border border-[#eadfce] bg-[#fffaf4] p-3 text-sm text-[#5d5348]">
                <p className="font-semibold text-[#2f2a24]">{item.test_name}</p>
                <p>{item.message}</p>
              </div>
            ))}
            {!reminders.length && <p className="text-sm text-[#7f6f5f]">No reminders right now.</p>}
          </div>
        </section>

        <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm lg:col-span-1">
          <h3 className="text-base font-bold text-[#2f2a24]">OTP Verification</h3>
          <form className="mt-3 space-y-3" onSubmit={onRequestOtp}>
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              placeholder="Mobile number"
              value={mobile}
              onChange={(event) => setMobile(event.target.value)}
              required
            />
            <button className="w-full rounded-xl bg-[#c96f3f] px-4 py-2 text-sm font-semibold text-white" type="submit">
              Request OTP
            </button>
          </form>

          <form className="mt-3 space-y-3" onSubmit={onVerifyOtp}>
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              placeholder="Enter OTP"
              value={otp}
              onChange={(event) => setOtp(event.target.value)}
              required
            />
            <button className="w-full rounded-xl bg-[#2f7d6b] px-4 py-2 text-sm font-semibold text-white" type="submit">
              Verify OTP
            </button>
          </form>

          <div className="mt-4 rounded-xl bg-[#faf3e9] p-3 text-sm text-[#5d5348]">
            <p className="font-semibold">Verification status</p>
            <p>{profile?.otp_verification ? 'Verified' : 'Pending verification'}</p>
          </div>
        </section>

        <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm lg:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-bold text-[#2f2a24]">Profile + Family Switching</h3>
            <button
              className="rounded-lg border border-[#d7c7b4] px-3 py-1 text-xs font-semibold text-[#5d5348]"
              onClick={loadPhase1}
              type="button"
            >
              Refresh
            </button>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-[#fcf8f2] p-3 text-sm">
              <p className="text-[#7f6f5f]">Customer ID</p>
              <p className="font-semibold text-[#2f2a24]">{profile?.patient_id || 'N/A'}</p>
            </div>
            <div className="rounded-xl bg-[#fcf8f2] p-3 text-sm">
              <p className="text-[#7f6f5f]">Name</p>
              <p className="font-semibold text-[#2f2a24]">{profile?.full_name || 'N/A'}</p>
            </div>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#8d7b66]">Family Members</p>
            <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
              {(profile?.family_members || []).map((member: any) => (
                <div key={member.id} className="min-w-[180px] rounded-xl border border-[#e8dccf] bg-white p-3 text-sm">
                  <p className="font-semibold text-[#2f2a24]">{member.name}</p>
                  <p className="text-[#7f6f5f]">{member.relation}</p>
                  <p className="text-[#7f6f5f]">{member.mobile || 'No mobile'}</p>
                </div>
              ))}
              {(!profile?.family_members || profile.family_members.length === 0) && (
                <div className="rounded-xl border border-dashed border-[#d9c9b6] bg-[#fcf8f2] p-3 text-sm text-[#7f6f5f]">
                  No family members added yet.
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-base font-bold text-[#2f2a24]">Order Viewer</h3>
          <p className="text-xs text-[#7f6f5f]">Open report link, then tap Ask AI for plain-English highlights.</p>
        </div>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {orders.map((report) => (
            <div key={report.id} className="rounded-xl border border-[#eadfce] bg-[#fffdf9] p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-[#2f2a24]">{report.test_name}</p>
                  <p className="text-xs text-[#7f6f5f]">{report.created_at ? new Date(report.created_at).toLocaleString() : 'No date'}</p>
                </div>
                <span className="rounded-full bg-[#f4ede1] px-2 py-1 text-xs font-semibold text-[#6d604f]">{report.status}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {report.download_url ? (
                  <a
                    className="rounded-lg bg-[#1f6f5f] px-3 py-1.5 text-xs font-semibold text-white"
                    href={`http://127.0.0.1:8000${report.download_url}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View Order
                  </a>
                ) : null}
                <button
                  className="rounded-lg bg-[#c96f3f] px-3 py-1.5 text-xs font-semibold text-white"
                  onClick={() => onAskAiSummary(report)}
                  type="button"
                >
                  Ask AI
                </button>
              </div>
            </div>
          ))}
          {!orders.length && <p className="text-sm text-[#7f6f5f]">No orders available yet.</p>}
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-bold text-[#2f2a24]">Digital Wallet & Loyalty</h3>
            <span className="rounded-full bg-[#eaf7f2] px-3 py-1 text-xs font-bold text-[#236b5a]">Points</span>
          </div>
          <div className="mt-3 rounded-2xl bg-gradient-to-br from-[#2f7d6b] to-[#1f5d51] p-4 text-white">
            <p className="text-xs uppercase tracking-[0.14em] text-[#c5e8de]">Available Balance</p>
            <p className="mt-2 text-4xl font-black">{wallet?.available_points ?? 0}</p>
            <p className="mt-1 text-sm text-[#d9f2eb]">Redeem points for discounts on your next test booking.</p>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d7b66]">Payment Options</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {(wallet?.payment_options || []).map((opt) => (
                <span key={opt.type} className="rounded-full bg-[#f3ede4] px-3 py-1 text-xs font-semibold text-[#5d5348]">{opt.label}</span>
              ))}
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d7b66]">Recent Loyalty Activity</p>
            {(wallet?.payment_history || []).slice(0, 4).map((item) => (
              <div key={item.id} className="rounded-xl border border-[#eadfce] bg-[#fffaf4] p-3 text-sm text-[#5d5348]">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-[#2f2a24]">{item.transaction_type}</p>
                  <p className="font-bold text-[#236b5a]">{item.transaction_type === 'Redemption' ? '-' : '+'}{item.points} pts</p>
                </div>
                <p>{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
          <h3 className="text-base font-bold text-[#2f2a24]">Referral Bonus Program</h3>
          <p className="mt-1 text-sm text-[#7f6f5f]">Invite friends. If they book a test, both of you receive bonus points.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="rounded-xl bg-[#c96f3f] px-4 py-2 text-sm font-semibold text-white" onClick={onGenerateReferral} type="button">
              Share With Friends
            </button>
            <button className="rounded-xl border border-[#d7c7b4] px-4 py-2 text-sm font-semibold text-[#5d5348]" onClick={onCopyReferral} type="button" disabled={!referralLink}>
              Copy Link
            </button>
          </div>
          <div className="mt-4 rounded-xl bg-[#fcf8f2] p-3 text-sm text-[#5d5348]">
            <p><span className="font-semibold">Referral Code:</span> {referralCode || 'Not generated yet'}</p>
            <p className="break-all"><span className="font-semibold">Referral Link:</span> {referralLink || 'Generate a referral link first'}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-base font-bold text-[#2f2a24]">Health Trends</h3>
            <div className="flex gap-2 text-xs">
              {['HbA1c', 'FBS', 'LDL'].map((item) => (
                <button
                  key={item}
                  className={`rounded-full px-3 py-1 font-semibold ${
                    trendBiomarker === item ? 'bg-[#2f7d6b] text-white' : 'bg-[#f3ede4] text-[#5d5348]'
                  }`}
                  onClick={() => onTrendChange(item)}
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendPoints}>
                <defs>
                  <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2f7d6b" stopOpacity={0.7} />
                    <stop offset="95%" stopColor="#2f7d6b" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ece4d8" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="#2f7d6b" fill="url(#trendFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
          <h3 className="text-base font-bold text-[#2f2a24]">Health Journey</h3>
          <div className="mt-3 space-y-3">
            <div className="rounded-xl border border-[#eadfce] bg-[#fff9f1] p-3 text-sm">
              <p className="font-semibold text-[#2f2a24]">Your Diabetes Journey</p>
              <p className="text-[#5d5348]">Focus for today: 30-minute post-meal walk and hydration target of 2.5L.</p>
            </div>
            <div className="rounded-xl border border-[#eadfce] bg-[#f4fbf8] p-3 text-sm">
              <p className="font-semibold text-[#2f2a24]">Daily Tip</p>
              <p className="text-[#5d5348]">Pair carbohydrates with protein for steadier blood glucose response.</p>
            </div>
            <div className="rounded-xl border border-[#eadfce] bg-[#fff6f6] p-3 text-sm">
              <p className="font-semibold text-[#2f2a24]">Education</p>
              <p className="text-[#5d5348]">Learn how HbA1c trends reflect long-term sugar control, not just a single day reading.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
          <h3 className="text-base font-bold text-[#2f2a24]">Gamification: Health Goals</h3>
          <form className="mt-3 space-y-3" onSubmit={onSaveGoal}>
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              value={goalType}
              onChange={(event) => setGoalType(event.target.value)}
              placeholder="Goal type"
              required
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                className="rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
                type="date"
                value={goalTargetDate}
                onChange={(event) => setGoalTargetDate(event.target.value)}
                required
              />
              <select
                className="rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
                value={goalStatus}
                onChange={(event) => setGoalStatus(event.target.value)}
              >
                <option>In Progress</option>
                <option>Achieved</option>
                <option>Paused</option>
              </select>
            </div>
            <button className="rounded-xl bg-[#2f7d6b] px-4 py-2 text-sm font-semibold text-white" type="submit">
              Save Challenge
            </button>
          </form>

          <div className="mt-4 space-y-2">
            <div className="rounded-xl border border-[#e8d8a6] bg-[#fff4d1] p-3 text-sm text-[#5e4a25]">
              <p className="font-semibold">Default Challenge</p>
              <p>Earn 500 points by maintaining your HbA1c below 7 for 3 months.</p>
            </div>
            {goals.map((goal) => (
              <div key={goal.id} className="rounded-xl border border-[#eadfce] bg-[#fffaf4] p-3 text-sm text-[#5d5348]">
                <p className="font-semibold text-[#2f2a24]">{goal.goal_type}</p>
                <p>Target: {new Date(goal.target_date).toLocaleDateString()}</p>
                <p>Status: {goal.status}</p>
                <p className="font-bold text-[#236b5a]">Reward: {goal.reward_points} points</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
          <h3 className="text-base font-bold text-[#2f2a24]">Corporate/Insurance Billing</h3>
          <form className="mt-3 space-y-3" onSubmit={onSaveInsurance}>
            <label className="flex items-center gap-2 text-sm font-semibold text-[#5d5348]">
              <input
                type="checkbox"
                checked={insuranceEnabled}
                onChange={(event) => setInsuranceEnabled(event.target.checked)}
              />
              Enable corporate health insurance billing
            </label>
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              placeholder="Insurance provider"
              value={insuranceProvider}
              onChange={(event) => setInsuranceProvider(event.target.value)}
              disabled={!insuranceEnabled}
            />
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              placeholder="Policy number"
              value={insurancePolicy}
              onChange={(event) => setInsurancePolicy(event.target.value)}
              disabled={!insuranceEnabled}
            />
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              placeholder="Corporate/Employee ID"
              value={corporateId}
              onChange={(event) => setCorporateId(event.target.value)}
              disabled={!insuranceEnabled}
            />
            <label className="block rounded-xl border border-dashed border-[#d7c7b4] bg-[#fcf8f2] px-3 py-3 text-sm text-[#7f6f5f]">
              Upload policy document (PDF/Image)
              <input
                type="file"
                className="mt-2 block text-xs"
                disabled={!insuranceEnabled}
                onChange={(event) => setInsuranceFileName(event.target.files?.[0]?.name || '')}
              />
            </label>
            {insuranceFileName ? <p className="text-xs text-[#7f6f5f]">Selected file: {insuranceFileName}</p> : null}
            <button className="rounded-xl bg-[#1f6f5f] px-4 py-2 text-sm font-semibold text-white" type="submit">
              Save Billing Preference
            </button>
          </form>
        </div>
      </section>

      <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
        <h3 className="text-base font-bold text-[#2f2a24]">Book MenuItems & Appointments</h3>
        <form className="mt-3 grid gap-4 lg:grid-cols-3" onSubmit={onBookAppointment}>
          <div className="lg:col-span-2">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d7b66]">MenuItem Catalog</p>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {menu_items.map((test) => (
                <label
                  key={test.id}
                  className={`cursor-pointer rounded-xl border p-3 text-sm ${
                    selectedMenuItems.includes(test.id)
                      ? 'border-[#2f7d6b] bg-[#ebf7f3]'
                      : 'border-[#e9ddcf] bg-[#fffdfb]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-[#2f2a24]">{test.name}</p>
                      <p className="text-[#7f6f5f]">{test.category}</p>
                      <p className="mt-1 text-xs text-[#7f6f5f]">{test.preparation_instructions || 'No special prep'}</p>
                    </div>
                    <input
                      type="checkbox"
                      className="mt-1"
                      checked={selectedMenuItems.includes(test.id)}
                      onChange={() => onToggleMenuItem(test.id)}
                    />
                  </div>
                  <p className="mt-2 text-sm font-bold text-[#c96f3f]">Rs {test.price}</p>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <select
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              value={appointmentType}
              onChange={(event) => setAppointmentType(event.target.value as 'Home' | 'Center')}
            >
              <option value="Center">Center Visit</option>
              <option value="Home">Home Collection</option>
            </select>
            <input
              className="w-full rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
              type="datetime-local"
              value={scheduledTime}
              onChange={(event) => setScheduledTime(event.target.value)}
              required
            />
            <button className="w-full rounded-xl bg-[#1f6f5f] px-4 py-2 text-sm font-semibold text-white" type="submit">
              Book Appointment
            </button>
          </div>
        </form>
      </section>

      {recommendation && (
        <section className="rounded-2xl border border-[#e8d8a6] bg-gradient-to-r from-[#fff4d1] to-[#ffefd6] p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-[#8d6c23]">AI Package Card</p>
          <h3 className="mt-1 text-lg font-black text-[#45371d]">{recommendation.title}</h3>
          <p className="mt-1 text-sm text-[#5e4a25]">
            Includes {recommendation.menu_items.map((item: any) => item.name).join(', ')}
          </p>
          <p className="mt-2 text-sm text-[#5e4a25]">
            Bundle Price: <span className="line-through">Rs {recommendation.total}</span>{' '}
            <span className="font-bold text-[#9a5a19]">Rs {recommendation.discounted}</span>
          </p>
        </section>
      )}

      <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
        <h3 className="text-base font-bold text-[#2f2a24]">Upcoming Appointments</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-[#efe5d8] text-left text-[#7f6f5f]">
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">Type</th>
                <th className="px-2 py-2">Scheduled</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">MenuItems</th>
              </tr>
            </thead>
            <tbody>
              {upcoming.map((item) => (
                <tr key={item.id} className="border-b border-[#f4ecdf]">
                  <td className="px-2 py-2 font-semibold">{item.id}</td>
                  <td className="px-2 py-2">{item.appointment_type}</td>
                  <td className="px-2 py-2">{new Date(item.scheduled_time).toLocaleString()}</td>
                  <td className="px-2 py-2">{item.status}</td>
                  <td className="px-2 py-2">{(item.test_ids || []).join(', ')}</td>
                </tr>
              ))}
              {!upcoming.length && (
                <tr>
                  <td className="px-2 py-3 text-[#7f6f5f]" colSpan={5}>
                    No upcoming appointments yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-2xl border border-[#eadfce] bg-white p-4 shadow-sm">
        <h3 className="text-base font-bold text-[#2f2a24]">Digital Consent</h3>
        <form className="mt-3 grid gap-3 md:grid-cols-3" onSubmit={onSignConsent}>
          <input
            className="rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
            placeholder="Appointment ID"
            value={consentAppointmentId}
            onChange={(event) => setConsentAppointmentId(event.target.value)}
            required
          />
          <input
            className="md:col-span-2 rounded-xl border border-[#decdb9] px-3 py-2 text-sm"
            placeholder="Consent statement"
            value={consentText}
            onChange={(event) => setConsentText(event.target.value)}
            required
          />
          <button className="md:col-span-3 rounded-xl bg-[#c96f3f] px-4 py-2 text-sm font-semibold text-white" type="submit">
            Sign Consent
          </button>
        </form>
      </section>

      {showSummaryModal && reportSummary && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-2xl rounded-2xl bg-white p-5 shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-[#8d7b66]">Ask AI Summary</p>
                <h4 className="text-lg font-bold text-[#2f2a24]">{selectedOrder?.test_name || 'Order'}</h4>
              </div>
              <button
                className="rounded-lg border border-[#eadfce] px-3 py-1 text-sm"
                onClick={() => setShowSummaryModal(false)}
                type="button"
              >
                Close
              </button>
            </div>
            <p className="mt-4 text-sm text-[#4f463c]">{reportSummary.ai_summary}</p>
            <div className="mt-4">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#8d7b66]">Key Flags</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.values(reportSummary.abnormal_flags || {}).map((value, index) => (
                  <span key={`${value}-${index}`} className="rounded-full bg-[#fff0e6] px-3 py-1 text-xs font-semibold text-[#9a5a3b]">
                    {value}
                  </span>
                ))}
                {!Object.keys(reportSummary.abnormal_flags || {}).length && (
                  <span className="rounded-full bg-[#edf7f3] px-3 py-1 text-xs font-semibold text-[#236b5a]">No major flags detected</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <button
        className="fixed bottom-5 right-5 z-40 rounded-full bg-[#2f7d6b] px-5 py-3 text-sm font-semibold text-white shadow-xl"
        onClick={() => setChatOpen((prev) => !prev)}
        type="button"
      >
        Ask the AI
      </button>

      {chatOpen && (
        <div className="fixed bottom-20 right-5 z-40 flex h-[460px] w-[340px] flex-col overflow-hidden rounded-2xl border border-[#d8c9b8] bg-white shadow-2xl">
          <div className="bg-[#2f7d6b] px-4 py-3 text-white">
            <p className="text-xs uppercase tracking-[0.12em] text-[#c7ece2]">24/7 Assistant</p>
            <p className="font-semibold">Health Query Copilot</p>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto bg-[#fcfaf6] p-3">
            {chatMessages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  message.role === 'user'
                    ? 'ml-auto bg-[#2f7d6b] text-white'
                    : 'mr-auto bg-white text-[#3b342c] border border-[#e8ddcf]'
                }`}
              >
                {message.text}
              </div>
            ))}
          </div>
          <form className="flex gap-2 border-t border-[#eee5da] p-3" onSubmit={onSendChat}>
            <input
              className="flex-1 rounded-xl border border-[#dbcab8] px-3 py-2 text-sm"
              placeholder="Ask about orders, fasting, HbA1c..."
              value={chatQuery}
              onChange={(event) => setChatQuery(event.target.value)}
            />
            <button className="rounded-xl bg-[#c96f3f] px-3 py-2 text-sm font-semibold text-white" type="submit">
              Send
            </button>
          </form>
        </div>
      )}

      {loading && <p className="text-sm text-[#7f6f5f]">Loading patient B2C data...</p>}
    </div>
  )
}
