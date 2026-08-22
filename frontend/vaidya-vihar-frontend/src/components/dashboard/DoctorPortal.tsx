import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Cell, BarChart, Bar } from 'recharts'
import { Step } from 'react-joyride'
import { useAuth } from '../../contexts/AuthContext'
import StaffOnboardingTour from '../doctor/DoctorOnboardingTour'

type Tab = 'dashboard' | 'customers' | 'ordering' | 'communication' | 'analytics' | 'referrals' | 'ai' | 'loyalty' | 'cme' | 'white-label' | 'profile'

interface Customer {
  id: number
  patient_id: string
  name: string
  phone: string
  address: string
  blood_group?: string | null
  tags: string[]
}

interface MenuItemItem {
  id: number
  test_name: string
  category?: string | null
  base_price: number
  discounted_price: number
  turnaround_time_hours: number
}

interface Panel {
  id: number
  panel_name: string
  test_ids: number[]
}

interface TimelineEvent {
  type: string
  date?: string | null
  title: string
  details?: string | null
  report_url?: string | null
}

interface LabTeamMember {
  id: number
  name: string
  role: string
  branch_id: number
}

interface MessageItem {
  id: number
  sender_id: number
  receiver_id: number
  message: string
  read_at?: string | null
  created_at?: string | null
}

interface AlertItem {
  result_id: number
  patient_id: number
  patient_name: string
  test_name: string
  result_value: number
  unit?: string | null
  reference_range?: string | null
  severity: 'high' | 'low'
}

interface TrendItem {
  month: string
  orders: number
}

interface CommonMenuItem {
  test_name: string
  count: number
}

interface AnalyticsResponse {
  common_menu_items: CommonMenuItem[]
  demographics: {
    male: number
    female: number
    other: number
    age_groups: {
      '0-18': number
      '19-40': number
      '41-60': number
      '61+': number
    }
  }
  trends: TrendItem[]
}

interface ReferralSummary {
  total_referrals: number
  active_customers: number
  commission_earned: number
  commission_pending: number
}

interface CommissionRow {
  id: number
  order_id: number
  patient_id: number
  patient_name: string
  commission_amount: number
  status: string
  created_at?: string | null
  paid_at?: string | null
}

interface CommissionStatement {
  rows: CommissionRow[]
  totals: {
    earned: number
    pending: number
    total: number
  }
}

interface WalletSummary {
  total_referrals: number
  commission_total: number
  commission_earned: number
  commission_paid: number
  commission_pending: number
}

interface LoyaltyData {
  tier: 'Silver' | 'Gold' | 'Platinum' | string
  benefits: string[]
}

interface CMECourseItem {
  id: number
  title: string
  description: string
  duration: string
  link: string
}

interface WhiteLabelSettings {
  clinic_name: string
  clinic_address: string
  logo_url: string
}

interface AISymptomResponse {
  possible_conditions: string[]
  recommended_menu_items: string[]
  disclaimer: string
}

interface AIInterpretationResponse {
  report_id: number
  summary: string
}

interface AIPredictiveResponse {
  alerts: Array<{ patient_name: string; risk: string; message: string }>
  count: number
  disclaimer: string
}

interface AIGrowthResponse {
  insights: string[]
  summary: {
    total_referred_customers: number
    diabetic_customers: number
    diabetic_without_hba1c: number
  }
  disclaimer: string
}

const API_BASE = (process.env.REACT_APP_API_BASE_URL ||
  ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://127.0.0.1:8000'
    : window.location.origin))

const PIE_COLORS = ['#0f766e', '#0891b2', '#ca8a04']

function formatMonth(value: string): string {
  const [year, month] = value.split('-')
  if (!year || !month) return value
  const date = new Date(Number(year), Number(month) - 1, 1)
  return date.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
}

export default function StaffPortal() {
  const { token, user } = useAuth()
  const [tab, setTab] = useState<Tab>('dashboard')
  const [profile, setProfile] = useState<any>(null)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [menu_items, setMenuItems] = useState<MenuItemItem[]>([])
  const [panels, setPanels] = useState<Panel[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [selectedMenuItemIds, setSelectedMenuItemIds] = useState<number[]>([])
  const [selectedPanelIds, setSelectedPanelIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [labTeam, setLabTeam] = useState<LabTeamMember[]>([])
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [chatUserId, setChatUserId] = useState<number | null>(null)
  const [messageDraft, setMessageDraft] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null)
  const [referrals, setReferrals] = useState<ReferralSummary | null>(null)
  const [commissionStatement, setCommissionStatement] = useState<CommissionStatement | null>(null)
  const [wallet, setWallet] = useState<WalletSummary | null>(null)
  const [loyalty, setLoyalty] = useState<LoyaltyData | null>(null)
  const [courses, setCourses] = useState<CMECourseItem[]>([])

  const [symptomsInput, setSymptomsInput] = useState('fever, fatigue')
  const [aiSymptom, setAiSymptom] = useState<AISymptomResponse | null>(null)
  const [reportIdInput, setOrderIdInput] = useState('')
  const [aiInterpretation, setAiInterpretation] = useState<AIInterpretationResponse | null>(null)
  const [aiPredictive, setAiPredictive] = useState<AIPredictiveResponse | null>(null)
  const [aiGrowth, setAiGrowth] = useState<AIGrowthResponse | null>(null)
  const [aiBusy, setAiBusy] = useState(false)
  const [lastErrorTime, setLastErrorTime] = useState(0)

  const [whiteLabelClinicName, setWhiteLabelClinicName] = useState('')
  const [whiteLabelClinicAddress, setWhiteLabelClinicAddress] = useState('')
  const [whiteLabelLogo, setWhiteLabelLogo] = useState('')
  const [whiteLabelSaving, setWhiteLabelSaving] = useState(false)
  const [tourRun, setTourRun] = useState(false)
  const initialLoadRanRef = useRef(false)
  const lastErrorTimeRef = useRef(0)
  const hasSeededChatUserRef = useRef(false)

  const requestConfig = useMemo(() => ({ headers: token ? { Authorization: `Bearer ${token}` } : {} }), [token])
  const doctorTourStorageKey = useMemo(
    () => `doctor-portal-tour-seen-${profile?.doctor_id || profile?.id || user?.id || 'default'}`,
    [profile?.doctor_id, profile?.id, user?.id],
  )
  useEffect(() => {
    lastErrorTimeRef.current = lastErrorTime
  }, [lastErrorTime])
  const tourSteps = useMemo<Step[]>(() => [
    {
      target: '[data-tour="doctor-header"]',
      content: 'Welcome to your Staff Portal. This area gives you a branch-aligned clinical view.',
      disableBeacon: true,
    },
    {
      target: '[data-tour="doctor-tabs"]',
      content: 'Use these tabs to switch quickly between customers, ordering, communication, and insights.',
    },
    {
      target: '[data-tour="doctor-tab-ordering"]',
      content: 'Start here to place new test orders for your selected patient.',
    },
    {
      target: '[data-tour="doctor-tab-analytics"]',
      content: 'Analytics helps you spot trends, common menu_items, and risk patterns.',
    },
    {
      target: '[data-tour="doctor-tab-whitelabel"]',
      content: 'White-label settings brand patient-facing orders with your clinic identity.',
    },
  ], [])

  const completeTour = useCallback(() => {
    window.localStorage.setItem(doctorTourStorageKey, '1')
    setTourRun(false)
  }, [doctorTourStorageKey])

  const loadFoundation = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const [
        profileRes,
        customersRes,
        catalogRes,
        panelsRes,
        ordersRes,
        alertsRes,
        messagesRes,
        analyticsRes,
        referralsRes,
        commissionRes,
        walletRes,
        loyaltyRes,
        cmeRes,
        whiteLabelRes,
      ] = await Promise.all([
        axios.get(`${API_BASE}/api/doctor/profile`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/customers`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/test-catalog`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/panels`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/orders`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/alerts/critical`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/messages`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/analytics`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/referral-tracker`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/commission/statement`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/wallet`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/loyalty`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/cme-courses`, requestConfig),
        axios.get(`${API_BASE}/api/doctor/white-label`, requestConfig),
      ])
      setProfile(profileRes.data)
      setCustomers(customersRes.data.customers || [])
      setMenuItems(catalogRes.data.menu_items || [])
      setPanels(panelsRes.data.panels || [])
      setOrders(ordersRes.data.orders || [])
      setAlerts(alertsRes.data.alerts || [])
      setLabTeam(messagesRes.data.lab_team || [])
      const receivedMessages = messagesRes.data.messages || []
      setMessages(receivedMessages)
      if (!hasSeededChatUserRef.current && receivedMessages.length) {
        const latestMessage = receivedMessages[receivedMessages.length - 1]
        const counterpart = latestMessage.sender_id === user?.id
          ? latestMessage.receiver_id
          : latestMessage.sender_id
        setChatUserId(counterpart)
        hasSeededChatUserRef.current = true
      }
      setAnalytics(analyticsRes.data)
      setReferrals(referralsRes.data)
      setCommissionStatement(commissionRes.data)
      setWallet(walletRes.data)
      setLoyalty(loyaltyRes.data)
      setCourses(cmeRes.data.courses || [])

      const whiteLabel: WhiteLabelSettings = {
        clinic_name: whiteLabelRes.data?.clinic_name || '',
        clinic_address: whiteLabelRes.data?.clinic_address || '',
        logo_url: whiteLabelRes.data?.logo_url || '',
      }
      setWhiteLabelClinicName(whiteLabel.clinic_name)
      setWhiteLabelClinicAddress(whiteLabel.clinic_address)
      setWhiteLabelLogo(whiteLabel.logo_url)

      const keyPrefix = `doctor-whitelabel-${profileRes.data?.doctor_id || profileRes.data?.id || user?.id || 'default'}`
      if (!whiteLabel.clinic_name) {
        setWhiteLabelClinicName(window.localStorage.getItem(`${keyPrefix}-clinic-name`) || '')
      }
      if (!whiteLabel.clinic_address) {
        setWhiteLabelClinicAddress(window.localStorage.getItem(`${keyPrefix}-clinic-address`) || '')
      }
      if (!whiteLabel.logo_url) {
        setWhiteLabelLogo(window.localStorage.getItem(`${keyPrefix}-logo`) || '')
      }
    } catch (error: any) {
      const now = Date.now()
      if (now - lastErrorTimeRef.current >= 5000) {
        lastErrorTimeRef.current = now
        setLastErrorTime(now)
        toast.error(error?.response?.data?.detail || 'Unable to load doctor portal')
      }
    } finally {
      setLoading(false)
    }
  }, [requestConfig, token, user?.id])

  useEffect(() => {
    if (!token || initialLoadRanRef.current) return
    initialLoadRanRef.current = true
    void loadFoundation()
  }, [loadFoundation, token])

  useEffect(() => {
    if (loading) return
    const hasSeenTour = window.localStorage.getItem(doctorTourStorageKey) === '1'
    if (!hasSeenTour) {
      setTourRun(true)
    }
  }, [doctorTourStorageKey, loading])

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      if (!token) return
      try {
        const response = await axios.get(`${API_BASE}/api/doctor/customers`, {
          ...requestConfig,
          params: { search, tag: tagFilter || undefined, date: dateFilter || undefined },
        })
        setCustomers(response.data.customers || [])
      } catch {
        // Keep current list visible if optional search call fails.
      }
    }, 250)
    return () => window.clearTimeout(timer)
  }, [dateFilter, requestConfig, search, tagFilter, token])

  useEffect(() => {
    if (!token) {
      initialLoadRanRef.current = false
      hasSeededChatUserRef.current = false
      lastErrorTimeRef.current = 0
      setLastErrorTime(0)
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    const interval = window.setInterval(() => {
      void (async () => {
        try {
          const [alertsRes, messagesRes, referralsRes, commissionRes, walletRes] = await Promise.all([
            axios.get(`${API_BASE}/api/doctor/alerts/critical`, requestConfig),
            axios.get(`${API_BASE}/api/doctor/messages`, requestConfig),
            axios.get(`${API_BASE}/api/doctor/referral-tracker`, requestConfig),
            axios.get(`${API_BASE}/api/doctor/commission/statement`, requestConfig),
            axios.get(`${API_BASE}/api/doctor/wallet`, requestConfig),
          ])
          setAlerts(alertsRes.data.alerts || [])
          setLabTeam(messagesRes.data.lab_team || [])
          setMessages(messagesRes.data.messages || [])
          setReferrals(referralsRes.data)
          setCommissionStatement(commissionRes.data)
          setWallet(walletRes.data)
        } catch {
          // Silent polling failure to avoid UX interruption.
        }
      })()
    }, 30000)
    return () => window.clearInterval(interval)
  }, [requestConfig, token])

  const openCustomer = async (patient: Customer) => {
    setSelectedCustomer(patient)
    try {
      const response = await axios.get(`${API_BASE}/api/doctor/customers/${patient.id}/timeline`, requestConfig)
      setTimeline(response.data.events || [])
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to load patient timeline')
    }
  }

  const updateTag = async (tag: string, action: 'add' | 'remove') => {
    if (!selectedCustomer) return
    try {
      const response = await axios.post(`${API_BASE}/api/doctor/customers/${selectedCustomer.id}/tags`, { tag, action }, requestConfig)
      const updated = { ...selectedCustomer, tags: response.data.tags || [] }
      setSelectedCustomer(updated)
      setCustomers(current => current.map(patient => patient.id === updated.id ? updated : patient))
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to update patient tag')
    }
  }

  const submitOrder = async () => {
    if (!selectedCustomer || (!selectedMenuItemIds.length && !selectedPanelIds.length)) {
      toast.error('Select a patient and at least one test or panel')
      return
    }
    setSaving(true)
    try {
      await axios.post(`${API_BASE}/api/doctor/orders`, {
        patient_id: selectedCustomer.id,
        test_ids: selectedMenuItemIds,
        panel_ids: selectedPanelIds,
      }, requestConfig)
      toast.success('Order sent to the lab')
      setSelectedMenuItemIds([])
      setSelectedPanelIds([])
      await loadFoundation()
      setTab('dashboard')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to send order')
    } finally {
      setSaving(false)
    }
  }

  const sendMessage = async () => {
    if (!chatUserId) {
      toast.error('Select a lab team member first')
      return
    }
    const trimmed = messageDraft.trim()
    if (!trimmed) return
    setSendingMessage(true)
    try {
      await axios.post(`${API_BASE}/api/doctor/messages`, {
        receiver_id: chatUserId,
        message: trimmed,
      }, requestConfig)
      setMessageDraft('')
      const response = await axios.get(`${API_BASE}/api/doctor/messages`, {
        ...requestConfig,
        params: { with_user_id: chatUserId },
      })
      setMessages(response.data.messages || [])
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to send message')
    } finally {
      setSendingMessage(false)
    }
  }

  const runSymptomChecker = async () => {
    const symptoms = symptomsInput.split(',').map(item => item.trim()).filter(Boolean)
    if (!symptoms.length) {
      toast.error('Enter at least one symptom')
      return
    }
    setAiBusy(true)
    try {
      const response = await axios.post(`${API_BASE}/api/doctor/ai/symptom-checker`, { symptoms }, requestConfig)
      setAiSymptom(response.data)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run symptom checker')
    } finally {
      setAiBusy(false)
    }
  }

  const runOrderInterpretation = async () => {
    const reportId = Number(reportIdInput)
    if (!reportId) {
      toast.error('Enter a valid report ID')
      return
    }
    setAiBusy(true)
    try {
      const response = await axios.post(`${API_BASE}/api/doctor/ai/report-interpretation`, { report_id: reportId }, requestConfig)
      setAiInterpretation(response.data)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run report interpretation')
    } finally {
      setAiBusy(false)
    }
  }

  const runPredictiveAlert = async () => {
    setAiBusy(true)
    try {
      const response = await axios.post(`${API_BASE}/api/doctor/ai/predictive-alert`, {}, requestConfig)
      setAiPredictive(response.data)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run predictive alert')
    } finally {
      setAiBusy(false)
    }
  }

  const runGrowthInsights = async () => {
    setAiBusy(true)
    try {
      const response = await axios.post(`${API_BASE}/api/doctor/ai/growth-insights`, { include_window_days: 180 }, requestConfig)
      setAiGrowth(response.data)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to run growth insights')
    } finally {
      setAiBusy(false)
    }
  }

  const saveWhiteLabel = async () => {
    setWhiteLabelSaving(true)
    const keyPrefix = `doctor-whitelabel-${profile?.doctor_id || profile?.id || user?.id || 'default'}`
    try {
      await axios.put(`${API_BASE}/api/doctor/white-label`, {
        clinic_name: whiteLabelClinicName,
        clinic_address: whiteLabelClinicAddress,
        logo_url: whiteLabelLogo,
      }, requestConfig)
      window.localStorage.setItem(`${keyPrefix}-clinic-name`, whiteLabelClinicName)
      window.localStorage.setItem(`${keyPrefix}-clinic-address`, whiteLabelClinicAddress)
      window.localStorage.setItem(`${keyPrefix}-logo`, whiteLabelLogo)
      toast.success('White-label settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to save white-label settings')
    } finally {
      setWhiteLabelSaving(false)
    }
  }

  const toggleMenuItem = (id: number) => setSelectedMenuItemIds(current => current.includes(id) ? current.filter(testId => testId !== id) : [...current, id])
  const togglePanel = (panel: Panel) => {
    setSelectedPanelIds(current => current.includes(panel.id) ? current.filter(panelId => panelId !== panel.id) : [...current, panel.id])
  }

  const filteredMessages = useMemo(() => {
    if (!chatUserId || !user?.id) return messages
    return messages.filter(message => (
      (message.sender_id === user.id && message.receiver_id === chatUserId)
      || (message.receiver_id === user.id && message.sender_id === chatUserId)
    ))
  }, [chatUserId, messages, user?.id])

  const demographicsPie = useMemo(() => {
    if (!analytics) return []
    return [
      { name: 'Male', value: analytics.demographics.male },
      { name: 'Female', value: analytics.demographics.female },
      { name: 'Other', value: analytics.demographics.other },
    ]
  }, [analytics])

  const ageBars = useMemo(() => {
    if (!analytics) return []
    return [
      { group: '0-18', customers: analytics.demographics.age_groups['0-18'] },
      { group: '19-40', customers: analytics.demographics.age_groups['19-40'] },
      { group: '41-60', customers: analytics.demographics.age_groups['41-60'] },
      { group: '61+', customers: analytics.demographics.age_groups['61+'] },
    ]
  }, [analytics])

  if (loading) {
    return <div className="p-6 text-sm font-semibold text-slate-600">Loading Staff Portal...</div>
  }

  return (
    <div className="min-h-full bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl">
        <StaffOnboardingTour run={tourRun} steps={tourSteps} onFinish={completeTour} />

        <header data-tour="doctor-header" className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-600">Staff Platform</p>
            <h1 className="mt-1 text-2xl font-black text-slate-900 sm:text-3xl">Good day, {profile?.name || user?.first_name || 'Staff'}</h1>
            <p className="mt-1 text-sm text-slate-500">Clinical history, communication, analytics, and referral performance in one place.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <span className="w-fit rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">{profile?.loyalty_tier || 'Silver'} tier</span>
            <span className={`w-fit rounded-full px-3 py-1 text-xs font-bold ${alerts.length ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'}`}>
              Critical alerts: {alerts.length}
            </span>
          </div>
        </header>

        <nav data-tour="doctor-tabs" className="mb-6 overflow-x-auto rounded-2xl bg-white p-2 shadow-sm">
          <div className="flex min-w-max gap-2">
          {([
            ['dashboard', 'Dashboard'],
            ['customers', 'Customers'],
            ['ordering', 'Order menu_items'],
            ['communication', 'Communication'],
            ['analytics', 'Analytics'],
            ['referrals', 'Referrals'],
            ['ai', 'AI Assistant'],
            ['loyalty', 'Loyalty'],
            ['cme', 'CME'],
            ['white-label', 'White-label'],
            ['profile', 'My profile'],
          ] as [Tab, string][]).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setTab(value)}
              data-tour={
                value === 'ordering'
                  ? 'doctor-tab-ordering'
                  : value === 'analytics'
                    ? 'doctor-tab-analytics'
                    : value === 'white-label'
                      ? 'doctor-tab-whitelabel'
                      : undefined
              }
              className={`whitespace-nowrap rounded-xl px-3 py-2 text-sm font-bold transition sm:px-4 ${tab === value ? 'bg-teal-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
            >
              {label}
            </button>
          ))}
          </div>
        </nav>

        {tab === 'dashboard' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <Metric label="Customers" value={customers.length} />
              <Metric label="Pending orders" value={orders.filter(order => order.status !== 'Completed').length} />
              <Metric label="Critical alerts" value={alerts.length} tone="rose" />
              <Metric label="Pending commission" value={Math.round(referrals?.commission_pending || 0)} tone="amber" />
            </div>
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-lg font-black text-slate-900">Critical lab alerts</h2>
                <button onClick={() => setTab('analytics')} className="text-sm font-bold text-teal-600">Open analytics</button>
              </div>
              <AlertsList alerts={alerts.slice(0, 5)} />
            </section>
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-3">
                <h2 className="text-lg font-black text-slate-900">Recent customers</h2>
                <button onClick={() => setTab('customers')} className="text-sm font-bold text-teal-600">View all</button>
              </div>
              <CustomerList customers={customers.slice(0, 5)} onSelect={openCustomer} />
            </section>
          </div>
        )}

        {tab === 'customers' && (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="text-lg font-black text-slate-900">Customer search</h2>
                <div className="grid w-full gap-2 sm:max-w-xl sm:grid-cols-3">
                  <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Name, ID, or mobile" className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-teal-500" />
                  <input value={tagFilter} onChange={event => setTagFilter(event.target.value)} placeholder="Tag" className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-teal-500" />
                  <input type="date" value={dateFilter} onChange={event => setDateFilter(event.target.value)} className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-teal-500" />
                </div>
              </div>
              <CustomerList customers={customers} onSelect={openCustomer} />
            </section>
            <CustomerDetails patient={selectedCustomer} timeline={timeline} onTag={updateTag} />
          </div>
        )}

        {tab === 'ordering' && (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">Choose patient</h2>
              <CustomerList customers={customers} onSelect={openCustomer} selectedId={selectedCustomer?.id} />
              <div className="mt-5 border-t border-slate-100 pt-5">
                <h3 className="mb-3 font-bold text-slate-800">Your panels</h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {panels.map(panel => (
                    <label key={panel.id} className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
                      <input type="checkbox" checked={selectedPanelIds.includes(panel.id)} onChange={() => togglePanel(panel)} />
                      {panel.panel_name}
                    </label>
                  ))}
                </div>
              </div>
            </section>
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">MenuItem catalog</h2>
              <div className="max-h-[28rem] space-y-2 overflow-auto">
                {menu_items.map(test => (
                  <label key={test.id} className="flex items-start gap-3 rounded-xl border border-slate-200 p-3">
                    <input type="checkbox" checked={selectedMenuItemIds.includes(test.id)} onChange={() => toggleMenuItem(test.id)} className="mt-1" />
                    <span className="min-w-0 flex-1">
                      <strong className="block text-sm text-slate-800">{test.test_name}</strong>
                      <span className="text-xs text-slate-500">{test.category || 'General'} · {test.turnaround_time_hours}h · INR {test.discounted_price || test.base_price}</span>
                    </span>
                  </label>
                ))}
              </div>
              <button disabled={saving} onClick={() => void submitOrder()} className="mt-5 w-full rounded-xl bg-teal-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-50">
                {saving ? 'Sending...' : `Send order${selectedCustomer ? ` for ${selectedCustomer.name}` : ''}`}
              </button>
            </section>
          </div>
        )}

        {tab === 'communication' && (
          <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
            <section className="rounded-2xl bg-white p-4 shadow-sm sm:p-5">
              <h2 className="mb-3 text-lg font-black text-slate-900">Lab team</h2>
              <div className="space-y-2">
                {labTeam.map(member => (
                  <button
                    key={member.id}
                    onClick={() => setChatUserId(member.id)}
                    className={`w-full rounded-xl border px-3 py-2 text-left ${chatUserId === member.id ? 'border-teal-500 bg-teal-50' : 'border-slate-200 hover:border-teal-300'}`}
                  >
                    <p className="text-sm font-bold text-slate-900">{member.name}</p>
                    <p className="text-xs text-slate-500">{member.role}</p>
                  </button>
                ))}
                {!labTeam.length && <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500">No branch lab users found.</p>}
              </div>
            </section>
            <section className="flex min-h-[28rem] flex-col rounded-2xl bg-white p-4 shadow-sm sm:p-5">
              <h2 className="mb-3 text-lg font-black text-slate-900">Secure messaging</h2>
              <div className="flex-1 space-y-2 overflow-auto rounded-xl bg-slate-50 p-3">
                {filteredMessages.map(message => {
                  const mine = message.sender_id === user?.id
                  return (
                    <div key={message.id} className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${mine ? 'ml-auto bg-teal-600 text-white' : 'bg-white text-slate-700'}`}>
                      <p>{message.message}</p>
                      <p className={`mt-1 text-[11px] ${mine ? 'text-teal-100' : 'text-slate-400'}`}>
                        {message.created_at ? new Date(message.created_at).toLocaleString() : ''}
                      </p>
                    </div>
                  )
                })}
                {!filteredMessages.length && <p className="text-sm text-slate-500">No messages yet. Start a conversation with the selected team member.</p>}
              </div>
              <div className="mt-3 flex gap-2">
                <input
                  value={messageDraft}
                  onChange={event => setMessageDraft(event.target.value)}
                  placeholder="Type your message"
                  className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-teal-500"
                />
                <button disabled={sendingMessage || !chatUserId} onClick={() => void sendMessage()} className="rounded-xl bg-teal-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
                  {sendingMessage ? 'Sending...' : 'Send'}
                </button>
              </div>
            </section>
          </div>
        )}

        {tab === 'analytics' && (
          <div className="space-y-6">
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">Order trend (last 6 months)</h2>
              <div className="h-72 w-full">
                <ResponsiveContainer>
                  <AreaChart data={(analytics?.trends || []).map(item => ({ ...item, month: formatMonth(item.month) }))}>
                    <defs>
                      <linearGradient id="ordersGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0f766e" stopOpacity={0.45} />
                        <stop offset="95%" stopColor="#0f766e" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Area type="monotone" dataKey="orders" stroke="#0f766e" fill="url(#ordersGradient)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </section>
            <div className="grid gap-6 lg:grid-cols-2">
              <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
                <h2 className="mb-4 text-lg font-black text-slate-900">Customer demographics</h2>
                <div className="h-64 w-full">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={demographicsPie} dataKey="value" nameKey="name" outerRadius={90}>
                        {demographicsPie.map((entry, index) => (
                          <Cell key={`${entry.name}-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </section>
              <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
                <h2 className="mb-4 text-lg font-black text-slate-900">Age groups</h2>
                <div className="h-64 w-full">
                  <ResponsiveContainer>
                    <BarChart data={ageBars}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="group" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="customers" fill="#0f766e" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </section>
            </div>
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">Most requested menu_items</h2>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {(analytics?.common_menu_items || []).map(test => (
                  <div key={test.test_name} className="rounded-xl border border-slate-200 p-3">
                    <p className="text-sm font-bold text-slate-800">{test.test_name}</p>
                    <p className="text-xs text-slate-500">Requested {test.count} times</p>
                  </div>
                ))}
                {!analytics?.common_menu_items?.length && <p className="text-sm text-slate-500">No request trends available yet.</p>}
              </div>
            </section>
          </div>
        )}

        {tab === 'referrals' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <Metric label="Total referrals" value={wallet?.total_referrals || referrals?.total_referrals || 0} />
              <Metric label="Commission total" value={Math.round(wallet?.commission_total || 0)} tone="teal" />
              <Metric label="Commission paid" value={Math.round(wallet?.commission_paid || 0)} tone="emerald" />
              <Metric label="Commission pending" value={Math.round(wallet?.commission_pending || referrals?.commission_pending || 0)} tone="amber" />
            </div>
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">Staff wallet</h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                <TotalCard label="Referrals" value={wallet?.total_referrals || 0} tone="teal" isCurrency={false} />
                <TotalCard label="Earned" value={wallet?.commission_earned || 0} tone="emerald" />
                <TotalCard label="Paid" value={wallet?.commission_paid || 0} tone="emerald" />
                <TotalCard label="Pending" value={wallet?.commission_pending || 0} tone="amber" />
              </div>
            </section>
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">Commission statement</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Date</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Customer</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Order</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Amount</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(commissionStatement?.rows || []).map(row => (
                      <tr key={row.id}>
                        <td className="px-3 py-2 text-slate-600">{row.created_at ? new Date(row.created_at).toLocaleDateString() : '-'}</td>
                        <td className="px-3 py-2 text-slate-800">{row.patient_name}</td>
                        <td className="px-3 py-2 text-slate-600">#{row.order_id}</td>
                        <td className="px-3 py-2 font-semibold text-slate-800">INR {row.commission_amount.toFixed(2)}</td>
                        <td className="px-3 py-2">
                          <span className={`rounded-full px-2 py-1 text-xs font-bold ${row.status === 'Paid' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {!commissionStatement?.rows?.length && (
                      <tr>
                        <td colSpan={5} className="px-3 py-6 text-center text-slate-500">No commission rows yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <TotalCard label="Total" value={commissionStatement?.totals.total || 0} />
                <TotalCard label="Earned" value={commissionStatement?.totals.earned || 0} tone="emerald" />
                <TotalCard label="Pending" value={commissionStatement?.totals.pending || 0} tone="amber" />
              </div>
            </section>
          </div>
        )}

        {tab === 'ai' && (
          <div className="space-y-6">
            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h2 className="mb-4 text-lg font-black text-slate-900">AI Symptom Checker</h2>
              <div className="flex gap-2">
                <input value={symptomsInput} onChange={event => setSymptomsInput(event.target.value)} className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="fever, cough, fatigue" />
                <button disabled={aiBusy} onClick={() => void runSymptomChecker()} className="rounded-xl bg-teal-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Run</button>
              </div>
              {aiSymptom && (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 p-3">
                    <p className="text-xs font-bold uppercase text-slate-500">Possible conditions</p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-700">{aiSymptom.possible_conditions.map(item => <li key={item}>• {item}</li>)}</ul>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-3">
                    <p className="text-xs font-bold uppercase text-slate-500">Recommended menu_items</p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-700">{aiSymptom.recommended_menu_items.map(item => <li key={item}>• {item}</li>)}</ul>
                  </div>
                </div>
              )}
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
                <h3 className="text-lg font-black text-slate-900">Order Interpretation</h3>
                <div className="mt-3 flex gap-2">
                  <input value={reportIdInput} onChange={event => setOrderIdInput(event.target.value)} className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="Order ID" />
                  <button disabled={aiBusy} onClick={() => void runOrderInterpretation()} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Summarize</button>
                </div>
                {aiInterpretation && <p className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700">{aiInterpretation.summary}</p>}
              </div>

              <div className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
                <h3 className="text-lg font-black text-slate-900">Predictive Alerts</h3>
                <button disabled={aiBusy} onClick={() => void runPredictiveAlert()} className="mt-3 rounded-xl bg-rose-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Analyze risk</button>
                {aiPredictive && (
                  <div className="mt-3 space-y-2">
                    {aiPredictive.alerts.slice(0, 5).map((item, idx) => <div key={`${item.patient_name}-${idx}`} className="rounded-xl bg-rose-50 p-3 text-sm text-rose-900"><strong>{item.patient_name}</strong>: {item.message}</div>)}
                    {!aiPredictive.alerts.length && <p className="text-sm text-slate-500">No risk alerts from current records.</p>}
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
              <h3 className="text-lg font-black text-slate-900">Growth Insights</h3>
              <button disabled={aiBusy} onClick={() => void runGrowthInsights()} className="mt-3 rounded-xl bg-amber-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Generate insights</button>
              {aiGrowth && (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 p-3">
                    <p className="text-xs font-bold uppercase text-slate-500">Insights</p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-700">{aiGrowth.insights.map(item => <li key={item}>• {item}</li>)}</ul>
                  </div>
                  <div className="rounded-xl border border-slate-200 p-3">
                    <p className="text-xs font-bold uppercase text-slate-500">Panel summary</p>
                    <p className="mt-2 text-sm text-slate-700">Total referred customers: {aiGrowth.summary.total_referred_customers}</p>
                    <p className="text-sm text-slate-700">Diabetic customers: {aiGrowth.summary.diabetic_customers}</p>
                    <p className="text-sm text-slate-700">No HbA1c in records: {aiGrowth.summary.diabetic_without_hba1c}</p>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}

        {tab === 'loyalty' && (
          <section className="space-y-6 rounded-2xl bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-black text-slate-900">Loyalty Program</h2>
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">{loyalty?.tier || profile?.loyalty_tier || 'Silver'} Tier</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(loyalty?.benefits || []).map(item => <div key={item} className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm font-semibold text-slate-700">{item}</div>)}
              {!(loyalty?.benefits || []).length && <p className="text-sm text-slate-500">Benefits will appear after loyalty profile sync.</p>}
            </div>
          </section>
        )}

        {tab === 'cme' && (
          <section className="space-y-4 rounded-2xl bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-black text-slate-900">CME Portal</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {courses.map(course => (
                <div key={course.id} className="rounded-xl border border-slate-200 p-4">
                  <p className="text-sm font-black text-slate-900">{course.title}</p>
                  <p className="mt-1 text-xs text-slate-500">{course.duration}</p>
                  <p className="mt-2 text-sm text-slate-700">{course.description}</p>
                  <a href={course.link} target="_blank" rel="noreferrer" className="mt-3 inline-block rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-bold text-white">Open Course</a>
                </div>
              ))}
              {!courses.length && <p className="text-sm text-slate-500">No active CME courses available right now.</p>}
            </div>
          </section>
        )}

        {tab === 'white-label' && (
          <section className="space-y-4 rounded-2xl bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-black text-slate-900">White-labeling (Placeholder)</h2>
            <p className="text-sm text-slate-500">Applied to patient-facing portal and report header metadata. Values are saved to your doctor profile.</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-semibold text-slate-700">Clinic name
                <input value={whiteLabelClinicName} onChange={event => setWhiteLabelClinicName(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2" />
              </label>
              <label className="text-sm font-semibold text-slate-700">Clinic address
                <input value={whiteLabelClinicAddress} onChange={event => setWhiteLabelClinicAddress(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2" />
              </label>
              <label className="sm:col-span-2 text-sm font-semibold text-slate-700">Clinic logo
                <input type="file" accept="image/*" className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2" onChange={event => {
                  const file = event.target.files?.[0]
                  if (!file) return
                  const reader = new FileReader()
                  reader.onload = () => setWhiteLabelLogo(String(reader.result || ''))
                  reader.readAsDataURL(file)
                }} />
              </label>
            </div>
            <button disabled={whiteLabelSaving} onClick={() => void saveWhiteLabel()} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{whiteLabelSaving ? 'Saving...' : 'Save White-label'}</button>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase text-slate-500">Preview</p>
              <div className="mt-2 flex items-center gap-3">
                {whiteLabelLogo ? <img src={whiteLabelLogo} alt="Clinic logo" className="h-12 w-12 rounded-full object-cover" /> : <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-200 text-xs text-slate-500">Logo</div>}
                <div>
                  <p className="text-sm font-bold text-slate-900">{whiteLabelClinicName || 'Clinic Name'}</p>
                  <p className="text-xs text-slate-500">{whiteLabelClinicAddress || 'Clinic Address'}</p>
                </div>
              </div>
            </div>
          </section>
        )}

        {tab === 'profile' && <ProfileCard profile={profile} requestConfig={requestConfig} onSaved={loadFoundation} />}
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  tone = 'teal',
}: {
  label: string
  value: number
  tone?: 'teal' | 'rose' | 'amber' | 'emerald'
}) {
  const toneClass = {
    teal: 'border-teal-100 bg-teal-50',
    rose: 'border-rose-100 bg-rose-50',
    amber: 'border-amber-100 bg-amber-50',
    emerald: 'border-emerald-100 bg-emerald-50',
  }[tone]
  return (
    <div className={`rounded-2xl border p-5 ${toneClass}`}>
      <p className="text-sm font-semibold text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-black text-slate-900">{value}</p>
    </div>
  )
}

function TotalCard({
  label,
  value,
  tone = 'teal',
  isCurrency = true,
}: {
  label: string
  value: number
  tone?: 'teal' | 'amber' | 'emerald'
  isCurrency?: boolean
}) {
  const textClass = {
    teal: 'text-teal-700',
    amber: 'text-amber-700',
    emerald: 'text-emerald-700',
  }[tone]
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-black ${textClass}`}>{isCurrency ? `INR ${value.toFixed(2)}` : value}</p>
    </div>
  )
}

function AlertsList({ alerts }: { alerts: AlertItem[] }) {
  if (!alerts.length) return <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No critical lab alerts right now.</p>
  return (
    <div className="space-y-2">
      {alerts.map(alert => (
        <div key={alert.result_id} className={`rounded-xl border p-3 ${alert.severity === 'high' ? 'border-rose-200 bg-rose-50' : 'border-amber-200 bg-amber-50'}`}>
          <p className="text-sm font-bold text-slate-900">{alert.patient_name} · {alert.test_name}</p>
          <p className="text-xs text-slate-600">
            Value: {alert.result_value} {alert.unit || ''}
            {alert.reference_range ? ` · Ref: ${alert.reference_range}` : ''}
          </p>
        </div>
      ))}
    </div>
  )
}

function CustomerList({
  customers,
  onSelect,
  selectedId,
}: {
  customers: Customer[]
  onSelect: (patient: Customer) => void
  selectedId?: number
}) {
  if (!customers.length) return <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No customers found.</p>
  return (
    <div className="space-y-2">
      {customers.map(patient => (
        <button
          key={patient.id}
          onClick={() => onSelect(patient)}
          className={`flex w-full items-center justify-between gap-3 rounded-xl border p-3 text-left transition ${selectedId === patient.id ? 'border-teal-500 bg-teal-50' : 'border-slate-200 hover:border-teal-300'}`}
        >
          <span className="min-w-0">
            <strong className="block truncate text-sm text-slate-900">{patient.name}</strong>
            <span className="text-xs text-slate-500">{patient.patient_id} · {patient.phone}</span>
          </span>
          <span className="text-xs font-bold text-teal-600">Open</span>
        </button>
      ))}
    </div>
  )
}

function CustomerDetails({
  patient,
  timeline,
  onTag,
}: {
  patient: Customer | null
  timeline: TimelineEvent[]
  onTag: (tag: string, action: 'add' | 'remove') => void
}) {
  if (!patient) return <section className="rounded-2xl bg-white p-6 text-sm text-slate-500 shadow-sm">Select a patient to view the clinical timeline.</section>
  return (
    <section className="rounded-2xl bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-black text-slate-900">{patient.name}</h2>
      <p className="mt-1 text-sm text-slate-500">{patient.patient_id} · {patient.phone}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {patient.tags.map(tag => (
          <button key={tag} onClick={() => onTag(tag, 'remove')} className="rounded-full bg-rose-100 px-2 py-1 text-xs font-bold text-rose-700">{tag} ×</button>
        ))}
        <button onClick={() => onTag('High Risk', 'add')} className="rounded-full border border-dashed border-slate-300 px-2 py-1 text-xs font-bold text-slate-500">+ High Risk</button>
      </div>
      <div className="mt-6 space-y-4 border-l-2 border-teal-100 pl-4">
        {timeline.map((event, index) => (
          <div key={`${event.type}-${index}`}>
            <p className="text-xs font-bold uppercase tracking-wide text-teal-600">{event.type}</p>
            <p className="font-bold text-slate-800">{event.title}</p>
            <p className="text-sm text-slate-500">{event.details || 'No additional details'}</p>
            {event.report_url ? (
              <iframe
                title={`${event.title} report`}
                src={event.report_url.startsWith('http') ? event.report_url : `${API_BASE}${event.report_url}`}
                className="mt-3 h-48 w-full rounded-xl border border-slate-200 sm:h-56"
              />
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}

function ProfileCard({
  profile,
  requestConfig,
  onSaved,
}: {
  profile: any
  requestConfig: any
  onSaved: () => Promise<void>
}) {
  const [upiId, setUpiId] = useState(profile?.upi_id || '')
  const [bankAccount, setBankAccount] = useState(profile?.bank_account || '')
  const [ifsc, setIfsc] = useState(profile?.ifsc || '')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      await axios.put(`${API_BASE}/api/doctor/profile`, { upi_id: upiId, bank_account: bankAccount, ifsc }, requestConfig)
      toast.success('Profile updated')
      await onSaved()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to update profile')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="max-w-2xl rounded-2xl bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-black text-slate-900">Professional profile</h2>
      <p className="mt-1 text-sm text-slate-500">{profile?.qualification} · {profile?.specialization}</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <label className="text-sm font-semibold text-slate-700">
          UPI ID
          <input value={upiId} onChange={event => setUpiId(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 font-normal outline-none focus:border-teal-500" />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Bank account
          <input value={bankAccount} onChange={event => setBankAccount(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 font-normal outline-none focus:border-teal-500" />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          IFSC
          <input value={ifsc} onChange={event => setIfsc(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 font-normal outline-none focus:border-teal-500" />
        </label>
      </div>
      <button disabled={saving} onClick={() => void save()} className="mt-6 rounded-xl bg-teal-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-50">
        {saving ? 'Saving...' : 'Save profile'}
      </button>
    </section>
  )
}
