import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable,
} from '@tanstack/react-table'
import {
  CeoAskNlpResponse,
  CeoAuditLogRow,
  CeoBrandingResponse,
  CeoDailyBriefResponse,
  CeoGlobalSettingsResponse,
  CeoMasterSummaryResponse,
  CeoPolicyItem,
  CeoProactiveInsightsResponse,
  CeoRetentionPolicyResponse,
  CeoSessionRow,
  CeoSimulationResponse,
  CeoSystemHealthResponse,
  CeoUserDirectoryRow,
  askCeoAssistant,
  changeCeoPassword,
  createCeoPolicy,
  deleteCeoPolicy,
  getCeoAuditLog,
  getCeoBranding,
  getCeoGlobalSettings,
  getCeoDailyBrief,
  getCeoMfaStatus,
  getCeoMasterSummary,
  getCeoPolicies,
  getCeoRetentionPolicy,
  getCeoSessions,
  getCeoSystemHealth,
  getCeoUsers,
  getCeoProactiveInsights,
  logoutCeoSession,
  publishCeoPolicy,
  simulateCeo,
  toggleCeoMfa,
  updateCeoBranding,
  updateCeoGlobalSettings,
  updateCeoPolicy,
  updateCeoRetentionPolicy,
} from './api'

type BrandingFormValues = {
  company_name: string
  legal_name: string
  registration_number: string
  tagline: string
  description: string
  contact_address: string
  contact_phone: string
  contact_email: string
  contact_website: string
  social_facebook: string
  social_instagram: string
  social_linkedin: string
  social_x: string
}

type PasswordFormValues = {
  current_password: string
  new_password: string
  confirm_password: string
}

type PolicyFormValues = {
  policy_type: 'leave_attendance' | 'expense' | 'data_privacy'
  title: string
  content: string
  effective_from: string
}

type ChiefOfStaffMessage = {
  id: number
  sender: 'user' | 'ai'
  text: string
}

const INPUT_CLASS =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100'

const CARD_CLASS = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm'

const formatDateTime = (value: string | null) => {
  if (!value) return '—'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return '—'
  return dt.toLocaleString()
}

export default function CeoOverview() {
  const navigate = useNavigate()
  const [branding, setBranding] = useState<CeoBrandingResponse | null>(null)
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [sessions, setSessions] = useState<CeoSessionRow[]>([])
  const [auditRows, setAuditRows] = useState<CeoAuditLogRow[]>([])
  const [systemHealth, setSystemHealth] = useState<CeoSystemHealthResponse | null>(null)
  const [masterSummary, setMasterSummary] = useState<CeoMasterSummaryResponse | null>(null)
  const [userDirectory, setUserDirectory] = useState<CeoUserDirectoryRow[]>([])
  const [userSearch, setUserSearch] = useState('')
  const [insights, setInsights] = useState<CeoProactiveInsightsResponse | null>(null)
  const [simForm, setSimForm] = useState({ target_city: '', initial_investment: '', projected_staff_count: '' })
  const [simulating, setSimulating] = useState(false)
  const [simulationResult, setSimulationResult] = useState<CeoSimulationResponse | null>(null)
  const [dailyBrief, setDailyBrief] = useState<CeoDailyBriefResponse | null>(null)
  const [isBriefPlaying, setIsBriefPlaying] = useState(false)
  const [briefProgress, setBriefProgress] = useState(0)
  const [isChiefOpen, setIsChiefOpen] = useState(false)
  const [chiefInput, setChiefInput] = useState('')
  const [chiefMessages, setChiefMessages] = useState<ChiefOfStaffMessage[]>([
    {
      id: 1,
      sender: 'ai',
      text: 'Hello CEO. I am your Virtual AI Chief of Staff. Ask for summaries, risks, or action plans.',
    },
  ])
  const [chiefThinking, setChiefThinking] = useState(false)
  const [globalSettings, setGlobalSettings] = useState<CeoGlobalSettingsResponse | null>(null)
  const [policies, setPolicies] = useState<CeoPolicyItem[]>([])
  const [retention, setRetention] = useState<CeoRetentionPolicyResponse>({ enabled: false, retention_days: 365 })
  const [savingBranding, setSavingBranding] = useState(false)
  const [savingGlobalSettings, setSavingGlobalSettings] = useState(false)
  const [savingPolicy, setSavingPolicy] = useState(false)
  const [publishingPolicyId, setPublishingPolicyId] = useState<number | null>(null)
  const [deletingPolicyId, setDeletingPolicyId] = useState<number | null>(null)
  const [changingPassword, setChangingPassword] = useState(false)
  const [togglingMfa, setTogglingMfa] = useState(false)
  const [savingRetention, setSavingRetention] = useState(false)
  const [editingPolicyId, setEditingPolicyId] = useState<number | null>(null)
  const [assetFiles, setAssetFiles] = useState<Record<string, File | null>>({
    primary_logo: null,
    favicon: null,
    app_icon: null,
    background_banner: null,
  })
  const [overviewLoadError, setOverviewLoadError] = useState(false)

  const brandingForm = useForm<BrandingFormValues>({
    defaultValues: {
      company_name: '',
      legal_name: '',
      registration_number: '',
      tagline: '',
      description: '',
      contact_address: '',
      contact_phone: '',
      contact_email: '',
      contact_website: '',
      social_facebook: '',
      social_instagram: '',
      social_linkedin: '',
      social_x: '',
    },
  })

  const passwordForm = useForm<PasswordFormValues>({
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  const policyForm = useForm<PolicyFormValues>({
    defaultValues: {
      policy_type: 'leave_attendance',
      title: '',
      content: '',
      effective_from: '',
    },
  })

  const assetPreview = useMemo(() => {
    return {
      primary_logo: branding?.assets?.primary_logo_url || '',
      favicon: branding?.assets?.favicon_url || '',
      app_icon: branding?.assets?.app_icon_url || '',
      background_banner: branding?.assets?.background_banner_url || '',
    }
  }, [branding])

  const userColumns = useMemo<ColumnDef<CeoUserDirectoryRow>[]>(
    () => [
      { accessorKey: 'name', header: 'Name' },
      { accessorKey: 'username', header: 'Username/ID' },
      { accessorKey: 'role', header: 'Role' },
      { accessorKey: 'branch', header: 'Branch' },
      { accessorKey: 'status', header: 'Status' },
    ],
    []
  )

  const userTable = useReactTable({
    data: userDirectory,
    columns: userColumns,
    state: {
      globalFilter: userSearch,
    },
    onGlobalFilterChange: setUserSearch,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const loadOverviewData = async () => {
    setOverviewLoadError(false)
    try {
      const results = await Promise.allSettled([
        getCeoBranding(),
        getCeoMfaStatus(),
        getCeoSessions(),
        getCeoAuditLog(10),
        getCeoRetentionPolicy(),
        getCeoSystemHealth(),
        getCeoGlobalSettings(),
        getCeoPolicies(),
        getCeoMasterSummary(),
        getCeoUsers(),
        getCeoProactiveInsights(),
        getCeoDailyBrief(),
      ])

      const brandingResp = results[0].status === 'fulfilled' ? results[0].value : null
      const mfaResp = results[1].status === 'fulfilled' ? results[1].value : null
      const sessionsResp = results[2].status === 'fulfilled' ? results[2].value : null
      const auditResp = results[3].status === 'fulfilled' ? results[3].value : null
      const retentionResp = results[4].status === 'fulfilled' ? results[4].value : null
      const systemHealthResp = results[5].status === 'fulfilled' ? results[5].value : null
      const globalSettingsResp = results[6].status === 'fulfilled' ? results[6].value : null
      const policiesResp = results[7].status === 'fulfilled' ? results[7].value : null
      const masterSummaryResp = results[8].status === 'fulfilled' ? results[8].value : null
      const usersResp = results[9].status === 'fulfilled' ? results[9].value : null
      const insightsResp = results[10].status === 'fulfilled' ? results[10].value : null
      const dailyBriefResp = results[11].status === 'fulfilled' ? results[11].value : null

      if (brandingResp) {
        setBranding(brandingResp)
        brandingForm.reset({
          company_name: brandingResp.company_name || '',
          legal_name: brandingResp.legal_name || '',
          registration_number: brandingResp.registration_number || '',
          tagline: brandingResp.tagline || '',
          description: brandingResp.description || '',
          contact_address: brandingResp.contact_info?.address || '',
          contact_phone: brandingResp.contact_info?.phone || '',
          contact_email: brandingResp.contact_info?.email || '',
          contact_website: brandingResp.contact_info?.website || '',
          social_facebook: brandingResp.social_media_links?.facebook || '',
          social_instagram: brandingResp.social_media_links?.instagram || '',
          social_linkedin: brandingResp.social_media_links?.linkedin || '',
          social_x: brandingResp.social_media_links?.x || '',
        })
      }
      setMfaEnabled(Boolean(mfaResp?.enabled))
      setSessions(sessionsResp?.sessions || [])
      setAuditRows(auditResp?.items || [])
      setRetention({
        enabled: Boolean(retentionResp?.enabled),
        retention_days: Number(retentionResp?.retention_days || 365),
      })
      setSystemHealth(systemHealthResp)
      setGlobalSettings(globalSettingsResp)
      setPolicies(policiesResp?.items || [])
      setMasterSummary(masterSummaryResp)
      setUserDirectory(usersResp?.items || [])
      setInsights(insightsResp)
      setDailyBrief(dailyBriefResp)
      setOverviewLoadError(results.some((item) => item.status === 'rejected'))
    } catch {
      setOverviewLoadError(true)
    }
  }

  useEffect(() => {
    void loadOverviewData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      void getCeoSystemHealth()
        .then(setSystemHealth)
        .catch(() => undefined)
    }, 30000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void getCeoUsers(userSearch)
        .then((response) => setUserDirectory(response.items || []))
        .catch(() => undefined)
    }, 250)
    return () => window.clearTimeout(timer)
  }, [userSearch])

  const onSubmitBranding = brandingForm.handleSubmit(async (values) => {
    setSavingBranding(true)
    try {
      const formData = new FormData()
      Object.entries(values).forEach(([key, value]) => {
        formData.append(key, value ?? '')
      })
      if (assetFiles.primary_logo) formData.append('primary_logo', assetFiles.primary_logo)
      if (assetFiles.favicon) formData.append('favicon', assetFiles.favicon)
      if (assetFiles.app_icon) formData.append('app_icon', assetFiles.app_icon)
      if (assetFiles.background_banner) formData.append('background_banner', assetFiles.background_banner)

      const response = await updateCeoBranding(formData)
      setBranding(response)
      setAssetFiles({
        primary_logo: null,
        favicon: null,
        app_icon: null,
        background_banner: null,
      })
      toast.success('Company branding updated')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to update branding')
    } finally {
      setSavingBranding(false)
    }
  })

  const onSubmitPassword = passwordForm.handleSubmit(async (values) => {
    if (values.new_password !== values.confirm_password) {
      toast.error('New password and confirm password do not match')
      return
    }
    setChangingPassword(true)
    try {
      await changeCeoPassword({
        current_password: values.current_password,
        new_password: values.new_password,
      })
      toast.success('Password updated')
      passwordForm.reset()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to update password')
    } finally {
      setChangingPassword(false)
    }
  })

  const handleMfaToggle = async () => {
    setTogglingMfa(true)
    try {
      const response = await toggleCeoMfa(!mfaEnabled)
      setMfaEnabled(Boolean(response.enabled))
      toast.success(response.enabled ? 'MFA enabled' : 'MFA disabled')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to update MFA status')
    } finally {
      setTogglingMfa(false)
    }
  }

  const handleLogoutSession = async (sessionId: string) => {
    try {
      await logoutCeoSession(sessionId)
      setSessions((prev) => prev.filter((row) => row.session_id !== sessionId))
      toast.success('Session logged out')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to log out session')
    }
  }

  const handleSaveRetention = async () => {
    setSavingRetention(true)
    try {
      const response = await updateCeoRetentionPolicy(retention)
      setRetention({
        enabled: Boolean(response.enabled),
        retention_days: Number(response.retention_days || 365),
      })
      toast.success('Data retention policy updated')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to update retention policy')
    } finally {
      setSavingRetention(false)
    }
  }

  const handleSaveGlobalSettings = async () => {
    if (!globalSettings) return
    setSavingGlobalSettings(true)
    try {
      const response = await updateCeoGlobalSettings(globalSettings)
      setGlobalSettings(response)
      toast.success('Global settings updated')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to update global settings')
    } finally {
      setSavingGlobalSettings(false)
    }
  }

  const handleEditPolicy = (policy: CeoPolicyItem) => {
    setEditingPolicyId(policy.id)
    policyForm.reset({
      policy_type: (policy.policy_type as PolicyFormValues['policy_type']) || 'leave_attendance',
      title: policy.title || '',
      content: policy.content || '',
      effective_from: policy.effective_from || '',
    })
  }

  const handleCancelPolicyEdit = () => {
    setEditingPolicyId(null)
    policyForm.reset({
      policy_type: 'leave_attendance',
      title: '',
      content: '',
      effective_from: '',
    })
  }

  const handleSavePolicy = policyForm.handleSubmit(async (values) => {
    setSavingPolicy(true)
    try {
      if (editingPolicyId) {
        const response = await updateCeoPolicy(editingPolicyId, values)
        setPolicies((prev) => prev.map((item) => (item.id === editingPolicyId ? response.item : item)))
        toast.success('Policy updated')
      } else {
        const response = await createCeoPolicy(values)
        setPolicies((prev) => [response.item, ...prev])
        toast.success('Policy created')
      }
      handleCancelPolicyEdit()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save policy')
    } finally {
      setSavingPolicy(false)
    }
  })

  const handleDeletePolicy = async (policyId: number) => {
    setDeletingPolicyId(policyId)
    try {
      await deleteCeoPolicy(policyId)
      setPolicies((prev) => prev.filter((item) => item.id !== policyId))
      if (editingPolicyId === policyId) handleCancelPolicyEdit()
      toast.success('Policy deleted')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to delete policy')
    } finally {
      setDeletingPolicyId(null)
    }
  }

  const handlePublishPolicy = async (policyId: number) => {
    setPublishingPolicyId(policyId)
    try {
      const response = await publishCeoPolicy(policyId)
      setPolicies((prev) =>
        prev.map((item) =>
          item.id === policyId
            ? { ...item, published: true, published_at: new Date().toISOString() }
            : item
        )
      )
      toast.success(`Policy published. ${response.notified_employees} employees notified for digital signature.`)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to publish policy')
    } finally {
      setPublishingPolicyId(null)
    }
  }

  const openMasterDataTab = () => {
    navigate('/ceo?tab=master-data')
  }

  const openAuditSection = () => {
    const node = document.getElementById('ceo-audit-logs')
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    navigate('/ceo/overview#audit')
  }

  const runWhatIfSimulation = async () => {
    const target_city = simForm.target_city.trim()
    const initial_investment = Number(simForm.initial_investment)
    const projected_staff_count = Number(simForm.projected_staff_count)
    if (!target_city || !initial_investment || !projected_staff_count) {
      toast.error('Please fill all simulator fields')
      return
    }

    setSimulating(true)
    try {
      const response = await simulateCeo({ target_city, initial_investment, projected_staff_count })
      setSimulationResult(response)
      toast.success('What-if simulation complete')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  useEffect(() => {
    if (!isBriefPlaying) return
    const timer = window.setInterval(() => {
      setBriefProgress((prev) => {
        if (prev >= 100) {
          window.clearInterval(timer)
          setIsBriefPlaying(false)
          return 100
        }
        return prev + 5
      })
    }, 300)
    return () => window.clearInterval(timer)
  }, [isBriefPlaying])

  const handlePlayDailyBrief = () => {
    if (!dailyBrief?.brief) {
      toast.error('Daily brief is not available yet.')
      return
    }
    setBriefProgress(0)
    setIsBriefPlaying(true)
  }

  const handleSendChiefMessage = async () => {
    const prompt = chiefInput.trim()
    if (!prompt) return
    const nextId = Date.now()
    setChiefMessages((prev) => [...prev, { id: nextId, sender: 'user', text: prompt }])
    setChiefInput('')
    setChiefThinking(true)
    try {
      const response: CeoAskNlpResponse = await askCeoAssistant(prompt)
      setChiefMessages((prev) => [
        ...prev,
        {
          id: nextId + 1,
          sender: 'ai',
          text: response.answer || 'I do not have a recommendation yet. Please try again.',
        },
      ])
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to get Chief of Staff response')
    } finally {
      setChiefThinking(false)
    }
  }

  return (
    <div className="relative">
      {overviewLoadError && (
        <section className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">Branding settings unavailable</p>
          <p className="mt-1 text-xs text-amber-700">Some overview widgets are temporarily unavailable. The page is showing fallback data.</p>
        </section>
      )}
      <div className="grid grid-cols-12 gap-6">
      <section className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
        <h2 className="text-xl font-bold text-slate-900">Company Identity &amp; Branding</h2>
        <p className="mt-1 text-sm text-slate-600">Manage public profile, legal identity and contact metadata for CEO overview.</p>
        <form className="mt-5 grid grid-cols-12 gap-4" onSubmit={onSubmitBranding}>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Company Name</label>
            <input className={INPUT_CLASS} {...brandingForm.register('company_name')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Legal Name</label>
            <input className={INPUT_CLASS} {...brandingForm.register('legal_name')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Registration Number</label>
            <input className={INPUT_CLASS} {...brandingForm.register('registration_number')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Tagline</label>
            <input className={INPUT_CLASS} {...brandingForm.register('tagline')} />
          </div>
          <div className="col-span-12">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Description</label>
            <textarea className={INPUT_CLASS} rows={3} {...brandingForm.register('description')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Address</label>
            <input className={INPUT_CLASS} {...brandingForm.register('contact_address')} />
          </div>
          <div className="col-span-12 md:col-span-3">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Phone</label>
            <input className={INPUT_CLASS} {...brandingForm.register('contact_phone')} />
          </div>
          <div className="col-span-12 md:col-span-3">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Email</label>
            <input className={INPUT_CLASS} {...brandingForm.register('contact_email')} />
          </div>
          <div className="col-span-12">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Website</label>
            <input className={INPUT_CLASS} {...brandingForm.register('contact_website')} />
          </div>
          <div className="col-span-12 md:col-span-3">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Facebook</label>
            <input className={INPUT_CLASS} {...brandingForm.register('social_facebook')} />
          </div>
          <div className="col-span-12 md:col-span-3">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Instagram</label>
            <input className={INPUT_CLASS} {...brandingForm.register('social_instagram')} />
          </div>
          <div className="col-span-12 md:col-span-3">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">LinkedIn</label>
            <input className={INPUT_CLASS} {...brandingForm.register('social_linkedin')} />
          </div>
          <div className="col-span-12 md:col-span-3">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">X</label>
            <input className={INPUT_CLASS} {...brandingForm.register('social_x')} />
          </div>
          <div className="col-span-12">
            <button
              type="submit"
              disabled={savingBranding}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingBranding ? 'Saving...' : 'Save Company Profile'}
            </button>
          </div>
        </form>
      </section>

      <section className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
        <h3 className="text-lg font-bold text-slate-900">Branding Asset Manager</h3>
        <p className="mt-1 text-sm text-slate-600">Upload and refresh primary visual assets.</p>
        <div className="mt-4 space-y-4">
          {[
            { id: 'primary_logo', label: 'Primary Logo', preview: assetPreview.primary_logo },
            { id: 'favicon', label: 'Favicon', preview: assetPreview.favicon },
            { id: 'app_icon', label: 'App Icon', preview: assetPreview.app_icon },
            { id: 'background_banner', label: 'Background Banner', preview: assetPreview.background_banner },
          ].map((asset) => (
            <div key={asset.id} className="rounded-lg border border-slate-200 p-3">
              <label className="mb-2 block text-xs font-semibold uppercase text-slate-600">{asset.label}</label>
              {asset.preview ? (
                <img
                  src={asset.preview}
                  key={`${asset.id}-${asset.preview}`}
                  alt={asset.label}
                  className="mb-2 h-20 w-full rounded-md border border-slate-200 object-contain"
                />
              ) : (
                <div className="mb-2 flex h-20 items-center justify-center rounded-md border border-dashed border-slate-300 text-xs text-slate-500">
                  No uploaded asset
                </div>
              )}
              <input
                type="file"
                accept="image/*"
                className="w-full text-xs text-slate-600"
                onChange={(event) =>
                  setAssetFiles((prev) => ({ ...prev, [asset.id]: event.target.files?.[0] || null }))
                }
              />
            </div>
          ))}
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12`}>
        <h3 className="text-lg font-bold text-slate-900">System &amp; Operational Health</h3>
        <p className="mt-1 text-sm text-slate-600">Live pulse for branch uptime, integration status, infra health and global events.</p>
        <div className="mt-4 grid grid-cols-12 gap-4">
          <div className="col-span-12 rounded-xl border border-emerald-200 bg-emerald-50 p-4 md:col-span-6 xl:col-span-3">
            <p className="text-xs font-semibold uppercase text-emerald-700">Branches Online / Offline</p>
            <p className="mt-2 text-2xl font-black text-emerald-900">
              {systemHealth?.branches_status.online ?? 5} Online, {systemHealth?.branches_status.offline ?? 1} Offline
            </p>
          </div>
          <div className="col-span-12 rounded-xl border border-blue-200 bg-blue-50 p-4 md:col-span-6 xl:col-span-3">
            <p className="text-xs font-semibold uppercase text-blue-700">Critical Integrations</p>
            <ul className="mt-2 space-y-1 text-sm text-blue-900">
              {(systemHealth?.critical_integrations || []).map((item) => (
                <li key={item.name} className="flex items-center justify-between">
                  <span>{item.name}</span>
                  <span className="font-semibold capitalize">{item.status}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="col-span-12 rounded-xl border border-amber-200 bg-amber-50 p-4 md:col-span-6 xl:col-span-3">
            <p className="text-xs font-semibold uppercase text-amber-700">Server &amp; DB Health</p>
            <div className="mt-2 space-y-1 text-sm text-amber-900">
              <p>CPU: {systemHealth?.server_db_health.cpu_percent ?? 0}%</p>
              <p>Memory: {systemHealth?.server_db_health.memory_percent ?? 0}%</p>
              <p>Storage: {systemHealth?.server_db_health.storage_percent ?? 0}%</p>
              <p>Last Backup: {formatDateTime(systemHealth?.server_db_health.last_backup_at || null)}</p>
            </div>
          </div>
          <div className="col-span-12 rounded-xl border border-slate-200 bg-slate-50 p-4 md:col-span-6 xl:col-span-3">
            <p className="text-xs font-semibold uppercase text-slate-700">Global Activity Feed</p>
            <div className="mt-2 max-h-36 space-y-2 overflow-y-auto pr-1 text-xs text-slate-700">
              {(systemHealth?.global_activity_feed || []).map((item) => (
                <div key={item.id} className="rounded-md bg-white p-2 shadow-sm">
                  <p className="font-medium">{item.event}</p>
                  <p className="text-[10px] text-slate-500">{formatDateTime(item.timestamp)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12`}>
        <h3 className="text-lg font-bold text-slate-900">User &amp; Access Management</h3>
        <p className="mt-1 text-sm text-slate-600">Master data summary, global directory, and compliance navigation.</p>
        <div className="mt-4 grid grid-cols-12 gap-4">
          {[
            { label: 'Total Branches', value: masterSummary?.total_branches ?? 0 },
            { label: 'Total Users', value: masterSummary?.total_users ?? 0 },
            { label: 'Total Patients', value: masterSummary?.total_patients ?? 0 },
          ].map((item) => (
            <button
              type="button"
              key={item.label}
              onClick={openMasterDataTab}
              className="col-span-12 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left hover:bg-slate-100 md:col-span-4"
            >
              <p className="text-xs font-semibold uppercase text-slate-600">{item.label}</p>
              <p className="mt-2 text-3xl font-black text-slate-900">{item.value}</p>
              <p className="mt-1 text-xs text-indigo-600">Open Master Data</p>
            </button>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <h4 className="text-base font-semibold text-slate-900">Global User Directory</h4>
          <div className="flex items-center gap-2">
            <input
              value={userSearch}
              onChange={(event) => setUserSearch(event.target.value)}
              placeholder="Search role, branch, name, status..."
              className={`${INPUT_CLASS} min-w-[260px]`}
            />
            <button
              type="button"
              onClick={openAuditSection}
              className="rounded-lg border border-indigo-200 px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
            >
              Open Audit & Compliance Logs
            </button>
          </div>
        </div>
        <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600">
              {userTable.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="px-3 py-2">
                      {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {userTable.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-t border-slate-100">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-2">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
              {userTable.getRowModel().rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-5 text-center text-slate-500">
                    No users found for the current filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12`}>
        <h3 className="text-lg font-bold text-slate-900">AI-Powered Proactive Insights &amp; Alerts</h3>
        <p className="mt-1 text-sm text-slate-600">Financial and operational risk highlights with opportunity guidance.</p>
        <div className="mt-4 grid grid-cols-12 gap-4">
          <div className="col-span-12 rounded-xl border border-rose-200 bg-rose-50 p-4 md:col-span-4">
            <p className="text-xs font-semibold uppercase text-rose-700">Financial Risks</p>
            <p className="mt-2 text-sm text-rose-900">{insights?.financial_risk || 'No financial risk insight available.'}</p>
          </div>
          <div className="col-span-12 rounded-xl border border-amber-200 bg-amber-50 p-4 md:col-span-4">
            <p className="text-xs font-semibold uppercase text-amber-700">Operational Risks</p>
            <p className="mt-2 text-sm text-amber-900">{insights?.operational_risk || 'No operational risk insight available.'}</p>
          </div>
          <div className="col-span-12 rounded-xl border border-emerald-200 bg-emerald-50 p-4 md:col-span-4">
            <p className="text-xs font-semibold uppercase text-emerald-700">Opportunities</p>
            <p className="mt-2 text-sm text-emerald-900">{insights?.opportunity || 'No opportunity insight available.'}</p>
          </div>
        </div>
        <div className="mt-6 rounded-xl border border-slate-200 p-4">
          <h4 className="text-base font-semibold text-slate-900">What-If Scenario Simulator</h4>
          <div className="mt-3 grid grid-cols-12 gap-3">
            <input
              value={simForm.target_city}
              onChange={(event) => setSimForm((prev) => ({ ...prev, target_city: event.target.value }))}
              placeholder="Target City"
              className={`${INPUT_CLASS} col-span-12 md:col-span-4`}
            />
            <input
              value={simForm.initial_investment}
              onChange={(event) => setSimForm((prev) => ({ ...prev, initial_investment: event.target.value }))}
              placeholder="Initial Investment (₹)"
              className={`${INPUT_CLASS} col-span-12 md:col-span-4`}
            />
            <input
              value={simForm.projected_staff_count}
              onChange={(event) => setSimForm((prev) => ({ ...prev, projected_staff_count: event.target.value }))}
              placeholder="Projected Staff Count"
              className={`${INPUT_CLASS} col-span-12 md:col-span-4`}
            />
          </div>
          <button
            type="button"
            onClick={() => void runWhatIfSimulation()}
            disabled={simulating}
            className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {simulating ? 'Simulating...' : 'Run Scenario'}
          </button>
          {simulationResult && (
            <div className="mt-4 grid grid-cols-12 gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
              <div className="col-span-12 md:col-span-4">
                <p className="text-xs text-slate-500">Breakeven Months</p>
                <p className="text-xl font-black text-slate-900">{simulationResult.breakeven_months}</p>
              </div>
              <div className="col-span-12 md:col-span-4">
                <p className="text-xs text-slate-500">Projected Annual Revenue</p>
                <p className="text-xl font-black text-slate-900">{new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(simulationResult.projected_annual_revenue || 0)}</p>
              </div>
              <div className="col-span-12 md:col-span-4">
                <p className="text-xs text-slate-500">Risk Factor</p>
                <p className="text-xl font-black text-slate-900">{simulationResult.risk_factor}</p>
              </div>
            </div>
          )}
        </div>
        <div className="mt-4 grid grid-cols-12 gap-4">
          <div className="col-span-12 rounded-xl border border-violet-200 bg-violet-50 p-4 md:col-span-6">
            <p className="text-xs font-semibold uppercase text-violet-700">Proactive Board Agenda Draft</p>
            <p className="mt-2 text-sm text-violet-900">
              {insights?.board_agenda_item || 'Agenda recommendation will appear after enough 7-day activity data is available.'}
            </p>
          </div>
          <div className="col-span-12 rounded-xl border border-sky-200 bg-sky-50 p-4 md:col-span-6">
            <p className="text-xs font-semibold uppercase text-sky-700">Daily Brief Video/Audio</p>
            <p className="mt-2 text-sm text-sky-900">{dailyBrief?.brief || 'No daily brief has been generated yet.'}</p>
            <button
              type="button"
              onClick={handlePlayDailyBrief}
              className="mt-3 rounded-lg bg-sky-700 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-800"
            >
              {isBriefPlaying ? 'Playing...' : 'Play Brief'}
            </button>
            <div className="mt-2 h-2 w-full rounded bg-sky-100">
              <div className="h-2 rounded bg-sky-600 transition-all" style={{ width: `${briefProgress}%` }} />
            </div>
          </div>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
        <h3 className="text-lg font-bold text-slate-900">Global Configuration</h3>
        <p className="mt-1 text-sm text-slate-600">Currency, timezone, language, tax and notification preferences.</p>
        <div className="mt-4 grid grid-cols-12 gap-3">
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Currency</label>
            <input
              className={INPUT_CLASS}
              value={globalSettings?.currency || ''}
              onChange={(event) => setGlobalSettings((prev) => (prev ? { ...prev, currency: event.target.value } : prev))}
            />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Timezone</label>
            <input
              className={INPUT_CLASS}
              value={globalSettings?.timezone || ''}
              onChange={(event) => setGlobalSettings((prev) => (prev ? { ...prev, timezone: event.target.value } : prev))}
            />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Language</label>
            <input
              className={INPUT_CLASS}
              value={globalSettings?.language || ''}
              onChange={(event) => setGlobalSettings((prev) => (prev ? { ...prev, language: event.target.value } : prev))}
            />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Financial Year</label>
            <input
              className={INPUT_CLASS}
              value={globalSettings?.financial_year || ''}
              onChange={(event) => setGlobalSettings((prev) => (prev ? { ...prev, financial_year: event.target.value } : prev))}
            />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">GST Percent</label>
            <input
              type="number"
              className={INPUT_CLASS}
              value={globalSettings?.tax_gst_settings?.gst_percent ?? 18}
              onChange={(event) =>
                setGlobalSettings((prev) =>
                  prev
                    ? {
                        ...prev,
                        tax_gst_settings: {
                          ...(prev.tax_gst_settings || {}),
                          gst_percent: Number(event.target.value || 0),
                        },
                      }
                    : prev
                )
              }
            />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Notification Preferences</label>
            <div className="mt-2 flex flex-wrap gap-3 text-sm">
              {[
                { key: 'email', label: 'Email' },
                { key: 'sms', label: 'SMS' },
                { key: 'in_app', label: 'In-App' },
              ].map((pref) => (
                <label key={pref.key} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={Boolean((globalSettings?.notification_preferences || {})[pref.key])}
                    onChange={(event) =>
                      setGlobalSettings((prev) =>
                        prev
                          ? {
                              ...prev,
                              notification_preferences: {
                                ...(prev.notification_preferences || {}),
                                [pref.key]: event.target.checked,
                              },
                            }
                          : prev
                      )
                    }
                  />
                  {pref.label}
                </label>
              ))}
            </div>
          </div>
          <div className="col-span-12">
            <button
              type="button"
              disabled={savingGlobalSettings}
              onClick={() => void handleSaveGlobalSettings()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingGlobalSettings ? 'Saving...' : 'Save Global Settings'}
            </button>
          </div>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
        <h3 className="text-lg font-bold text-slate-900">Policy Manager</h3>
        <p className="mt-1 text-sm text-slate-600">Create and publish Leave/Attendance, Expense, and Data Privacy policies.</p>
        <form className="mt-4 grid grid-cols-12 gap-3" onSubmit={handleSavePolicy}>
          <div className="col-span-12 md:col-span-5">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Policy Type</label>
            <select className={INPUT_CLASS} {...policyForm.register('policy_type')}>
              <option value="leave_attendance">Leave &amp; Attendance</option>
              <option value="expense">Expense</option>
              <option value="data_privacy">Data Privacy</option>
            </select>
          </div>
          <div className="col-span-12 md:col-span-7">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Title</label>
            <input className={INPUT_CLASS} {...policyForm.register('title')} />
          </div>
          <div className="col-span-12">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Policy Content</label>
            <textarea className={INPUT_CLASS} rows={4} {...policyForm.register('content')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Effective From</label>
            <input className={INPUT_CLASS} placeholder="YYYY-MM-DD" {...policyForm.register('effective_from')} />
          </div>
          <div className="col-span-12 flex items-center gap-2">
            <button
              type="submit"
              disabled={savingPolicy}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingPolicy ? 'Saving...' : editingPolicyId ? 'Update Policy' : 'Create Policy'}
            </button>
            {editingPolicyId && (
              <button
                type="button"
                onClick={handleCancelPolicyEdit}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel Edit
              </button>
            )}
          </div>
        </form>
      </section>

      <section className={`${CARD_CLASS} col-span-12`}>
        <h3 className="text-lg font-bold text-slate-900">Published & Draft Policies</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Effective From</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((policy) => (
                <tr key={policy.id} className="border-b border-slate-100">
                  <td className="px-3 py-2">{policy.policy_type.replace('_', ' ')}</td>
                  <td className="px-3 py-2">{policy.title}</td>
                  <td className="px-3 py-2">{policy.effective_from || '—'}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${policy.published ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                      {policy.published ? 'Published' : 'Draft'}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => handleEditPolicy(policy)} className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100">
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDeletePolicy(policy.id)}
                        disabled={deletingPolicyId === policy.id}
                        className="rounded border border-red-200 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                      >
                        {deletingPolicyId === policy.id ? 'Deleting...' : 'Delete'}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handlePublishPolicy(policy.id)}
                        disabled={publishingPolicyId === policy.id}
                        className="rounded border border-indigo-200 px-2 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
                      >
                        {publishingPolicyId === policy.id ? 'Publishing...' : 'Publish'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {policies.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-5 text-center text-slate-500">
                    No policies configured yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
        <h3 className="text-lg font-bold text-slate-900">Credentials &amp; MFA</h3>
        <form className="mt-4 grid grid-cols-12 gap-3" onSubmit={onSubmitPassword}>
          <div className="col-span-12">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Current Password</label>
            <input type="password" className={INPUT_CLASS} {...passwordForm.register('current_password')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">New Password</label>
            <input type="password" className={INPUT_CLASS} {...passwordForm.register('new_password')} />
          </div>
          <div className="col-span-12 md:col-span-6">
            <label className="mb-1 block text-xs font-semibold uppercase text-slate-600">Confirm Password</label>
            <input type="password" className={INPUT_CLASS} {...passwordForm.register('confirm_password')} />
          </div>
          <div className="col-span-12 flex items-center gap-3">
            <button
              type="submit"
              disabled={changingPassword}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {changingPassword ? 'Updating...' : 'Change Password'}
            </button>
          </div>
        </form>
        <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">
            MFA Status: <span className={mfaEnabled ? 'text-green-600' : 'text-amber-600'}>{mfaEnabled ? 'Active' : 'Inactive'}</span>
          </p>
          <button
            type="button"
            onClick={handleMfaToggle}
            disabled={togglingMfa}
            className="mt-3 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {togglingMfa ? 'Updating...' : mfaEnabled ? 'Disable MFA' : 'Enable MFA'}
          </button>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
        <h3 className="text-lg font-bold text-slate-900">Audit &amp; Privacy Control</h3>
        <div className="mt-4 rounded-lg border border-slate-200 p-4">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={retention.enabled}
              onChange={(event) => setRetention((prev) => ({ ...prev, enabled: event.target.checked }))}
            />
            Enable Data Retention Policy
          </label>
          <div className="mt-3 flex items-center gap-3">
            <input
              type="number"
              min={7}
              max={3650}
              className={`${INPUT_CLASS} max-w-[160px]`}
              value={retention.retention_days}
              onChange={(event) => setRetention((prev) => ({ ...prev, retention_days: Number(event.target.value || 365) }))}
            />
            <span className="text-sm text-slate-600">days</span>
          </div>
          <button
            type="button"
            onClick={handleSaveRetention}
            disabled={savingRetention}
            className="mt-3 rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {savingRetention ? 'Saving...' : 'Save Retention'}
          </button>
        </div>
      </section>

      <section className={`${CARD_CLASS} col-span-12`}>
        <h3 className="text-lg font-bold text-slate-900">Active Sessions</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Device ID</th>
                <th className="px-3 py-2">IP</th>
                <th className="px-3 py-2">Last Active</th>
                <th className="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((row) => (
                <tr key={row.session_id} className="border-b border-slate-100">
                  <td className="px-3 py-2">{row.device_id}</td>
                  <td className="px-3 py-2">{row.ip_address}</td>
                  <td className="px-3 py-2">{formatDateTime(row.last_active)}</td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => void handleLogoutSession(row.session_id)}
                      className="rounded-md border border-red-200 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-50"
                    >
                      Log Out Session
                    </button>
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-5 text-center text-slate-500">
                    No active sessions available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section id="ceo-audit-logs" className={`${CARD_CLASS} col-span-12`}>
        <h3 className="text-lg font-bold text-slate-900">Latest Audit Actions</h3>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Time</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Endpoint</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {auditRows.map((row) => (
                <tr key={row.id} className="border-b border-slate-100">
                  <td className="px-3 py-2">{formatDateTime(row.created_at)}</td>
                  <td className="px-3 py-2">{row.action}</td>
                  <td className="px-3 py-2">{row.http_method} {row.endpoint}</td>
                  <td className="px-3 py-2">{row.response_status}</td>
                </tr>
              ))}
              {auditRows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-5 text-center text-slate-500">
                    No audit activity found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      </div>
      <div className="fixed bottom-6 right-6 z-50">
      {isChiefOpen ? (
        <div className="h-[480px] w-[340px] rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between rounded-t-2xl bg-slate-900 px-4 py-3 text-white">
            <div>
              <p className="text-sm font-semibold">Virtual AI Chief of Staff</p>
              <p className="text-xs text-slate-300">Strategic assistant for CEO decisions</p>
            </div>
            <button type="button" onClick={() => setIsChiefOpen(false)} className="text-xs font-semibold text-slate-200 hover:text-white">
              Close
            </button>
          </div>
          <div className="h-[350px] space-y-2 overflow-y-auto p-3">
            {chiefMessages.map((message) => (
              <div
                key={message.id}
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  message.sender === 'user' ? 'ml-auto bg-indigo-600 text-white' : 'bg-slate-100 text-slate-800'
                }`}
              >
                {message.text}
              </div>
            ))}
            {chiefThinking && <p className="text-xs text-slate-500">AI Chief of Staff is thinking...</p>}
          </div>
          <div className="flex gap-2 border-t border-slate-200 p-3">
            <input
              value={chiefInput}
              onChange={(event) => setChiefInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  void handleSendChiefMessage()
                }
              }}
              placeholder="Ask for risks, action plans, or follow-ups..."
              className={`${INPUT_CLASS} flex-1`}
            />
            <button
              type="button"
              onClick={() => void handleSendChiefMessage()}
              disabled={chiefThinking}
              className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              Send
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setIsChiefOpen(true)}
          className="rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-xl hover:bg-slate-800"
        >
          Virtual AI Chief of Staff
        </button>
      )}
      </div>
    </div>
  )
}
