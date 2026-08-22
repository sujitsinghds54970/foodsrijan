import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  CeoSettingsAiAutomationResponse,
  CeoSettingsBranchLocalizationResponse,
  CeoSettingsBrandingResponse,
  CeoSettingsDataComplianceResponse,
  CeoSettingsFeatureFlagsResponse,
  CeoSettingsIntegrationsApiResponse,
  CeoSettingsImportExportMigrationResponse,
  CeoSettingsMaintenanceHealthResponse,
  CeoSettingsSecurityResponse,
  CeoSettingsUiExperienceResponse,
  CeoSettingsWowFeaturesResponse,
  getCeoAuditLog,
  getCeoSettingsAiAutomationConfiguration,
  getCeoSettingsBranchLocalizationManagement,
  getCeoSettingsBranding,
  getCeoSettingsDataComplianceManagement,
  getCeoSettingsFeatureFlags,
  getCeoSettingsImportExportMigration,
  getCeoSettingsIntegrationsApiManagement,
  getCeoSettingsMaintenanceSystemHealth,
  getCeoSettingsSecurity,
  getCeoSettingsUiExperience,
  getCeoSettingsWowFeatures,
  updateCeoSettingsAiAutomationConfiguration,
  updateCeoSettingsBranchLocalizationManagement,
  updateCeoSettingsBranding,
  updateCeoSettingsDataComplianceManagement,
  updateCeoSettingsFeatureFlags,
  updateCeoSettingsImportExportMigration,
  updateCeoSettingsIntegrationsApiManagement,
  updateCeoSettingsMaintenanceSystemHealth,
  updateCeoSettingsSecurity,
  updateCeoSettingsUiExperience,
  updateCeoSettingsWowFeatures,
} from './api'

const CARD_CLASS = 'rounded-xl border border-slate-200 bg-white p-5 shadow-sm'

const stripMeta = <T extends Record<string, any>>(obj: T): T => {
  const copy = { ...obj }
  delete copy.is_mock
  delete copy.table_reference
  delete copy.future_data_mapping
  return copy
}

const CeoSystemSettings = () => {
  const [loading, setLoading] = useState(true)
  const [branding, setBranding] = useState<CeoSettingsBrandingResponse | null>(null)
  const [security, setSecurity] = useState<CeoSettingsSecurityResponse | null>(null)
  const [flags, setFlags] = useState<CeoSettingsFeatureFlagsResponse | null>(null)
  const [integrations, setIntegrations] = useState<CeoSettingsIntegrationsApiResponse | null>(null)
  const [branchLocalization, setBranchLocalization] = useState<CeoSettingsBranchLocalizationResponse | null>(null)
  const [dataCompliance, setDataCompliance] = useState<CeoSettingsDataComplianceResponse | null>(null)
  const [aiAutomation, setAiAutomation] = useState<CeoSettingsAiAutomationResponse | null>(null)
  const [uiExperience, setUiExperience] = useState<CeoSettingsUiExperienceResponse | null>(null)
  const [maintenanceHealth, setMaintenanceHealth] = useState<CeoSettingsMaintenanceHealthResponse | null>(null)
  const [importExportMigration, setImportExportMigration] = useState<CeoSettingsImportExportMigrationResponse | null>(null)
  const [wowFeatures, setWowFeatures] = useState<CeoSettingsWowFeaturesResponse | null>(null)
  const [savingBranding, setSavingBranding] = useState(false)
  const [savingSecurity, setSavingSecurity] = useState(false)
  const [savingFlags, setSavingFlags] = useState(false)
  const [savingIntegrations, setSavingIntegrations] = useState(false)
  const [savingBranchLocalization, setSavingBranchLocalization] = useState(false)
  const [savingDataCompliance, setSavingDataCompliance] = useState(false)
  const [savingAiAutomation, setSavingAiAutomation] = useState(false)
  const [savingUiExperience, setSavingUiExperience] = useState(false)
  const [savingMaintenanceHealth, setSavingMaintenanceHealth] = useState(false)
  const [savingImportExportMigration, setSavingImportExportMigration] = useState(false)
  const [savingWowFeatures, setSavingWowFeatures] = useState(false)
  const [settingsLoadError, setSettingsLoadError] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setSettingsLoadError(false)
      try {
        const results = await Promise.allSettled([
          getCeoSettingsBranding(),
          getCeoSettingsSecurity(),
          getCeoSettingsFeatureFlags(),
          getCeoSettingsIntegrationsApiManagement(),
          getCeoSettingsBranchLocalizationManagement(),
          getCeoSettingsDataComplianceManagement(),
          getCeoSettingsAiAutomationConfiguration(),
          getCeoSettingsUiExperience(),
          getCeoSettingsMaintenanceSystemHealth(),
          getCeoSettingsImportExportMigration(),
          getCeoSettingsWowFeatures(),
          getCeoAuditLog(10),
        ])
        const brandingResp = results[0].status === 'fulfilled' ? results[0].value : null
        const securityResp = results[1].status === 'fulfilled' ? results[1].value : null
        const flagsResp = results[2].status === 'fulfilled' ? results[2].value : null
        const integrationsResp = results[3].status === 'fulfilled' ? results[3].value : null
        const branchLocalizationResp = results[4].status === 'fulfilled' ? results[4].value : null
        const dataComplianceResp = results[5].status === 'fulfilled' ? results[5].value : null
        const aiAutomationResp = results[6].status === 'fulfilled' ? results[6].value : null
        const uiExperienceResp = results[7].status === 'fulfilled' ? results[7].value : null
        const maintenanceHealthResp = results[8].status === 'fulfilled' ? results[8].value : null
        const importExportMigrationResp = results[9].status === 'fulfilled' ? results[9].value : null
        const wowFeaturesResp = results[10].status === 'fulfilled' ? results[10].value : null
        const auditResp = results[11].status === 'fulfilled' ? results[11].value : null

        if (brandingResp) setBranding(brandingResp)
        if (securityResp) {
          setSecurity({ ...securityResp, audit_log_immutable: auditResp?.items || securityResp.audit_log_immutable || [] })
        }
        if (flagsResp) setFlags(flagsResp)
        if (integrationsResp) setIntegrations(integrationsResp)
        if (branchLocalizationResp) setBranchLocalization(branchLocalizationResp)
        if (dataComplianceResp) setDataCompliance(dataComplianceResp)
        if (aiAutomationResp) setAiAutomation(aiAutomationResp)
        if (uiExperienceResp) setUiExperience(uiExperienceResp)
        if (maintenanceHealthResp) setMaintenanceHealth(maintenanceHealthResp)
        if (importExportMigrationResp) setImportExportMigration(importExportMigrationResp)
        if (wowFeaturesResp) setWowFeatures(wowFeaturesResp)
        setSettingsLoadError(results.some((item) => item.status === 'rejected'))
      } catch {
        setSettingsLoadError(true)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  const saveBranding = async () => {
    if (!branding) return
    setSavingBranding(true)
    try {
      await updateCeoSettingsBranding(stripMeta(branding))
      toast.success('Branding settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save branding')
    } finally {
      setSavingBranding(false)
    }
  }

  const saveSecurity = async () => {
    if (!security) return
    setSavingSecurity(true)
    try {
      const payload = stripMeta(security)
      delete (payload as any).audit_log_immutable
      await updateCeoSettingsSecurity(payload)
      toast.success('Security settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save security settings')
    } finally {
      setSavingSecurity(false)
    }
  }

  const saveFlags = async () => {
    if (!flags) return
    setSavingFlags(true)
    try {
      await updateCeoSettingsFeatureFlags(stripMeta(flags))
      toast.success('Feature flags saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save feature flags')
    } finally {
      setSavingFlags(false)
    }
  }

  const saveIntegrations = async () => {
    if (!integrations) return
    setSavingIntegrations(true)
    try {
      await updateCeoSettingsIntegrationsApiManagement(stripMeta(integrations))
      toast.success('Integrations settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save integrations settings')
    } finally {
      setSavingIntegrations(false)
    }
  }

  const saveBranchLocalization = async () => {
    if (!branchLocalization) return
    setSavingBranchLocalization(true)
    try {
      await updateCeoSettingsBranchLocalizationManagement(stripMeta(branchLocalization))
      toast.success('Branch localization settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save branch localization settings')
    } finally {
      setSavingBranchLocalization(false)
    }
  }

  const saveDataCompliance = async () => {
    if (!dataCompliance) return
    setSavingDataCompliance(true)
    try {
      await updateCeoSettingsDataComplianceManagement(stripMeta(dataCompliance))
      toast.success('Data & compliance settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save data & compliance settings')
    } finally {
      setSavingDataCompliance(false)
    }
  }

  const saveAiAutomation = async () => {
    if (!aiAutomation) return
    setSavingAiAutomation(true)
    try {
      await updateCeoSettingsAiAutomationConfiguration(stripMeta(aiAutomation))
      toast.success('AI & automation settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save AI & automation settings')
    } finally {
      setSavingAiAutomation(false)
    }
  }

  const saveUiExperience = async () => {
    if (!uiExperience) return
    setSavingUiExperience(true)
    try {
      await updateCeoSettingsUiExperience(stripMeta(uiExperience))
      toast.success('UI & experience settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save UI & experience settings')
    } finally {
      setSavingUiExperience(false)
    }
  }

  const saveMaintenanceHealth = async () => {
    if (!maintenanceHealth) return
    setSavingMaintenanceHealth(true)
    try {
      await updateCeoSettingsMaintenanceSystemHealth(stripMeta(maintenanceHealth))
      toast.success('Maintenance & system health settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save maintenance & system health settings')
    } finally {
      setSavingMaintenanceHealth(false)
    }
  }

  const saveImportExportMigration = async () => {
    if (!importExportMigration) return
    setSavingImportExportMigration(true)
    try {
      await updateCeoSettingsImportExportMigration(stripMeta(importExportMigration))
      toast.success('Import/export & migration settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save import/export & migration settings')
    } finally {
      setSavingImportExportMigration(false)
    }
  }

  const saveWowFeatures = async () => {
    if (!wowFeatures) return
    setSavingWowFeatures(true)
    try {
      await updateCeoSettingsWowFeatures(stripMeta(wowFeatures))
      toast.success('System wow features settings saved')
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to save system wow features settings')
    } finally {
      setSavingWowFeatures(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700">
          Loading System Settings...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {settingsLoadError && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-semibold text-amber-800">Branding settings unavailable</p>
          <p className="mt-1 text-xs text-amber-700">Some System Settings APIs are temporarily unavailable. Loaded sections are shown with fallback behavior.</p>
        </section>
      )}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-black text-slate-900">System Settings</h1>
        <p className="mt-1 text-sm text-slate-600">Enterprise configuration controls for branding, security policies, and feature management.</p>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Company &amp; Branding (The Face)</h2>
          <button onClick={saveBranding} disabled={savingBranding || !branding} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingBranding ? 'Saving...' : 'Save Branding'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Company Profile</p>
            <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
              <input value={branding?.company_profile.company_name || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, company_name: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Company Name" />
              <input value={branding?.company_profile.legal_name || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, legal_name: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Legal Name" />
              <input value={branding?.company_profile.registration_number || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, registration_number: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Registration Number" />
              <input value={branding?.company_profile.tagline || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, tagline: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Tagline" />
              <textarea value={branding?.company_profile.description || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, description: e.target.value } } : s)} className="md:col-span-2 h-20 rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Description" />
              <input value={branding?.company_profile.contact_information.address || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, contact_information: { ...s.company_profile.contact_information, address: e.target.value } } } : s)} className="md:col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Address" />
              <input value={branding?.company_profile.contact_information.phone || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, contact_information: { ...s.company_profile.contact_information, phone: e.target.value } } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Phone" />
              <input value={branding?.company_profile.contact_information.email || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, contact_information: { ...s.company_profile.contact_information, email: e.target.value } } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Email" />
              <input value={branding?.company_profile.contact_information.website || ''} onChange={(e) => setBranding((s) => s ? { ...s, company_profile: { ...s.company_profile, contact_information: { ...s.company_profile.contact_information, website: e.target.value } } } : s)} className="md:col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Website" />
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Brand Color Palette</p>
            <div className="mt-3 space-y-3">
              {(['primary_color', 'secondary_color', 'accent_color'] as const).map((key) => (
                <label key={key} className="flex items-center gap-2 text-sm text-slate-700">
                  <span className="w-28 capitalize">{key.replace('_', ' ')}</span>
                  <input type="color" value={branding?.brand_color_palette[key] || '#000000'} onChange={(e) => setBranding((s) => s ? { ...s, brand_color_palette: { ...s.brand_color_palette, [key]: e.target.value } } : s)} />
                  <input value={branding?.brand_color_palette[key] || ''} onChange={(e) => setBranding((s) => s ? { ...s, brand_color_palette: { ...s.brand_color_palette, [key]: e.target.value } } : s)} className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm" />
                </label>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Branding Asset Manager</p>
            {branding?.branding_asset_manager.primary_logo_web ? (
              <img
                src={branding.branding_asset_manager.primary_logo_web}
                key={branding.branding_asset_manager.primary_logo_web}
                alt="Company Logo"
                className="mt-3 h-20 w-full rounded-md border border-slate-200 object-contain"
              />
            ) : null}
            <div className="mt-3 space-y-2">
              {Object.entries(branding?.branding_asset_manager || {}).map(([k, v]) => (
                <input key={k} value={v} onChange={(e) => setBranding((s) => s ? { ...s, branding_asset_manager: { ...s.branding_asset_manager, [k]: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder={k.replaceAll('_', ' ')} />
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Default Language &amp; Locale</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <input value={branding?.default_language_locale.language || ''} onChange={(e) => setBranding((s) => s ? { ...s, default_language_locale: { ...s.default_language_locale, language: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Language" />
              <input value={branding?.default_language_locale.date_format || ''} onChange={(e) => setBranding((s) => s ? { ...s, default_language_locale: { ...s.default_language_locale, date_format: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Date format" />
              <input value={branding?.default_language_locale.timezone || ''} onChange={(e) => setBranding((s) => s ? { ...s, default_language_locale: { ...s.default_language_locale, timezone: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Timezone" />
              <input value={branding?.default_language_locale.currency || ''} onChange={(e) => setBranding((s) => s ? { ...s, default_language_locale: { ...s.default_language_locale, currency: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Currency" />
            </div>
            <div className="mt-4">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <input type="checkbox" checked={branding?.white_label_configuration.enabled || false} onChange={(e) => setBranding((s) => s ? { ...s, white_label_configuration: { ...s.white_label_configuration, enabled: e.target.checked } } : s)} />
                White-label Configuration Enabled
              </label>
              <div className="mt-2 space-y-2">
                {(branding?.white_label_configuration.branches || []).map((branch, idx) => (
                  <div key={branch.branch_name} className="grid grid-cols-1 gap-2 rounded-md border border-slate-200 p-2 md:grid-cols-4">
                    <input value={branch.branch_name} onChange={(e) => setBranding((s) => {
                      if (!s) return s
                      const branches = [...s.white_label_configuration.branches]
                      branches[idx] = { ...branches[idx], branch_name: e.target.value }
                      return { ...s, white_label_configuration: { ...s.white_label_configuration, branches } }
                    })} className="rounded-md border border-slate-300 px-2 py-1 text-xs" placeholder="Branch" />
                    <input value={branch.subdomain} onChange={(e) => setBranding((s) => {
                      if (!s) return s
                      const branches = [...s.white_label_configuration.branches]
                      branches[idx] = { ...branches[idx], subdomain: e.target.value }
                      return { ...s, white_label_configuration: { ...s.white_label_configuration, branches } }
                    })} className="rounded-md border border-slate-300 px-2 py-1 text-xs" placeholder="Subdomain" />
                    <input value={branch.logo} onChange={(e) => setBranding((s) => {
                      if (!s) return s
                      const branches = [...s.white_label_configuration.branches]
                      branches[idx] = { ...branches[idx], logo: e.target.value }
                      return { ...s, white_label_configuration: { ...s.white_label_configuration, branches } }
                    })} className="rounded-md border border-slate-300 px-2 py-1 text-xs" placeholder="Logo URL" />
                    <input value={branch.theme} onChange={(e) => setBranding((s) => {
                      if (!s) return s
                      const branches = [...s.white_label_configuration.branches]
                      branches[idx] = { ...branches[idx], theme: e.target.value }
                      return { ...s, white_label_configuration: { ...s.white_label_configuration, branches } }
                    })} className="rounded-md border border-slate-300 px-2 py-1 text-xs" placeholder="Theme" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">System &amp; Security (The Fort Knox)</h2>
          <button onClick={saveSecurity} disabled={savingSecurity || !security} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingSecurity ? 'Saving...' : 'Save Security'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">CEO Fortified Authentication</p>
            <div className="mt-2 space-y-2 text-sm">
              <label className="flex items-center gap-2"><input type="checkbox" checked={security?.ceo_fortified_authentication.biometric_login_enabled || false} onChange={(e) => setSecurity((s) => s ? { ...s, ceo_fortified_authentication: { ...s.ceo_fortified_authentication, biometric_login_enabled: e.target.checked } } : s)} /> Biometric login enabled</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={security?.ceo_fortified_authentication.webauthn_fido2_enabled || false} onChange={(e) => setSecurity((s) => s ? { ...s, ceo_fortified_authentication: { ...s.ceo_fortified_authentication, webauthn_fido2_enabled: e.target.checked } } : s)} /> WebAuthn / FIDO2 enabled</label>
              <p className="text-xs text-slate-600">{security?.ceo_fortified_authentication.enrollment_status}</p>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Global Password Policy</p>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
              <input type="number" value={security?.global_password_policy.minimum_length || 0} onChange={(e) => setSecurity((s) => s ? { ...s, global_password_policy: { ...s.global_password_policy, minimum_length: Number(e.target.value) } } : s)} className="rounded-md border border-slate-300 px-3 py-2" placeholder="Min length" />
              <input type="number" value={security?.global_password_policy.expiration_days || 0} onChange={(e) => setSecurity((s) => s ? { ...s, global_password_policy: { ...s.global_password_policy, expiration_days: Number(e.target.value) } } : s)} className="rounded-md border border-slate-300 px-3 py-2" placeholder="Expiry days" />
              {(['require_uppercase', 'require_lowercase', 'require_numbers', 'require_special_characters'] as const).map((k) => (
                <label key={k} className="flex items-center gap-2 rounded-md border border-slate-200 px-2 py-1 text-xs">
                  <input type="checkbox" checked={security?.global_password_policy[k] || false} onChange={(e) => setSecurity((s) => s ? { ...s, global_password_policy: { ...s.global_password_policy, [k]: e.target.checked } } : s)} />
                  {k.replaceAll('_', ' ')}
                </label>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">MFA Policy &amp; Session Management</p>
            <div className="mt-2 space-y-2">
              <input value={security?.mfa_policy.mode || ''} onChange={(e) => setSecurity((s) => s ? { ...s, mfa_policy: { ...s.mfa_policy, mode: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="MFA mode" />
              <input type="number" value={security?.session_inactivity_management.auto_sign_out_minutes || 0} onChange={(e) => setSecurity((s) => s ? { ...s, session_inactivity_management: { ...s.session_inactivity_management, auto_sign_out_minutes: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Auto sign-out (minutes)" />
              <input type="number" value={security?.session_inactivity_management.max_concurrent_sessions || 0} onChange={(e) => setSecurity((s) => s ? { ...s, session_inactivity_management: { ...s.session_inactivity_management, max_concurrent_sessions: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Max concurrent sessions" />
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">IP Allowlisting / Restriction</p>
            <label className="mt-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={security?.ip_allowlisting_restriction.enabled || false} onChange={(e) => setSecurity((s) => s ? { ...s, ip_allowlisting_restriction: { ...s.ip_allowlisting_restriction, enabled: e.target.checked } } : s)} />
              Enable IP allowlisting
            </label>
            <textarea value={(security?.ip_allowlisting_restriction.allowed_ips || []).join('\n')} onChange={(e) => setSecurity((s) => s ? { ...s, ip_allowlisting_restriction: { ...s.ip_allowlisting_restriction, allowed_ips: e.target.value.split('\n').map((ip) => ip.trim()).filter(Boolean) } } : s)} className="mt-2 h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="One IP per line" />
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Audit Log (Immutable)</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">ID</th><th className="pb-2 pr-4">Action</th><th className="pb-2 pr-4">Method</th><th className="pb-2 pr-4">Endpoint</th><th className="pb-2 pr-4">Status</th><th className="pb-2">At</th></tr></thead>
                <tbody>
                  {(security?.audit_log_immutable || []).map((row) => (
                    <tr key={row.id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.id}</td><td className="py-2 pr-4 text-slate-700">{row.action}</td><td className="py-2 pr-4 text-slate-700">{row.http_method}</td><td className="py-2 pr-4 text-slate-700">{row.endpoint}</td><td className="py-2 pr-4 text-slate-700">{row.response_status}</td><td className="py-2 text-slate-700">{row.created_at || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Feature Flags &amp; Module Management (The Future-Proof Engine)</h2>
          <button onClick={saveFlags} disabled={savingFlags || !flags} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingFlags ? 'Saving...' : 'Save Flags'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-8`}>
            <p className="text-sm font-semibold text-slate-700">Feature Flag Dashboard</p>
            <div className="mt-3 space-y-2">
              {(flags?.feature_flag_dashboard || []).map((flagItem, idx) => (
                <label key={flagItem.feature_key} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <span>
                    <span className="font-semibold text-slate-800">{flagItem.label}</span>
                    <span className="ml-2 text-xs text-slate-500">({flagItem.category})</span>
                  </span>
                  <input
                    type="checkbox"
                    checked={flagItem.enabled}
                    onChange={(e) => setFlags((s) => {
                      if (!s) return s
                      const updated = [...s.feature_flag_dashboard]
                      updated[idx] = { ...updated[idx], enabled: e.target.checked }
                      return { ...s, feature_flag_dashboard: updated }
                    })}
                  />
                </label>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Module Activation</p>
            <div className="mt-3 space-y-2">
              {(flags?.module_activation || []).map((moduleItem, idx) => (
                <label key={moduleItem.module} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm">
                  <span className="font-semibold text-slate-800">{moduleItem.module}</span>
                  <input
                    type="checkbox"
                    checked={moduleItem.enabled}
                    onChange={(e) => setFlags((s) => {
                      if (!s) return s
                      const updated = [...s.module_activation]
                      updated[idx] = { ...updated[idx], enabled: e.target.checked }
                      return { ...s, module_activation: updated }
                    })}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Flag Categories</p>
            <div className="mt-3 space-y-2">
              {(flags?.flag_categories || []).map((cat) => (
                <div key={cat.category} className="rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{cat.category}</p>
                  <p className="text-xs text-slate-600">{cat.description}</p>
                  <p className="mt-1 text-xs text-slate-700">Enabled {cat.enabled_count}/{cat.flags_count}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Flag Change Audit</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Timestamp</th><th className="pb-2 pr-4">User ID</th><th className="pb-2 pr-4">Flag</th><th className="pb-2 pr-4">Old</th><th className="pb-2">New</th></tr></thead>
                <tbody>
                  {(flags?.flag_change_audit || []).map((row, idx) => (
                    <tr key={`${row.feature_key}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.timestamp}</td><td className="py-2 pr-4 text-slate-700">{row.user_id}</td><td className="py-2 pr-4 font-semibold text-slate-800">{row.feature_key}</td><td className="py-2 pr-4 text-slate-700">{String(row.old_value)}</td><td className="py-2 text-slate-700">{String(row.new_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Integrations &amp; API Management (The Connective Tissue)</h2>
          <button onClick={saveIntegrations} disabled={savingIntegrations || !integrations} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingIntegrations ? 'Saving...' : 'Save Integrations'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">LIS Integration</p>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={integrations?.lis_integration.enabled || false}
                  onChange={(e) => setIntegrations((s) => (s ? { ...s, lis_integration: { ...s.lis_integration, enabled: e.target.checked } } : s))}
                />
                Enable LIS Integration
              </label>
              <input value={integrations?.lis_integration.api_key || ''} onChange={(e) => setIntegrations((s) => (s ? { ...s, lis_integration: { ...s.lis_integration, api_key: e.target.value } } : s))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="API key" />
              <input value={integrations?.lis_integration.endpoint || ''} onChange={(e) => setIntegrations((s) => (s ? { ...s, lis_integration: { ...s.lis_integration, endpoint: e.target.value } } : s))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Endpoint" />
              <textarea value={integrations?.lis_integration.data_mapping || ''} onChange={(e) => setIntegrations((s) => (s ? { ...s, lis_integration: { ...s.lis_integration, data_mapping: e.target.value } } : s))} className="h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Data mapping" />
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">SMS / Email / WhatsApp Gateway</p>
            <div className="mt-3 space-y-2 text-sm">
              <input value={integrations?.communication_gateways.sms.provider || ''} onChange={(e) => setIntegrations((s) => (s ? { ...s, communication_gateways: { ...s.communication_gateways, sms: { ...s.communication_gateways.sms, provider: e.target.value } } } : s))} className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="SMS provider" />
              <input value={integrations?.communication_gateways.email.provider || ''} onChange={(e) => setIntegrations((s) => (s ? { ...s, communication_gateways: { ...s.communication_gateways, email: { ...s.communication_gateways.email, provider: e.target.value } } } : s))} className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="Email provider" />
              <input value={integrations?.communication_gateways.whatsapp.provider || ''} onChange={(e) => setIntegrations((s) => (s ? { ...s, communication_gateways: { ...s.communication_gateways, whatsapp: { ...s.communication_gateways.whatsapp, provider: e.target.value } } } : s))} className="w-full rounded-md border border-slate-300 px-3 py-2" placeholder="WhatsApp provider" />
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Analyzer &amp; Device Integration</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Device</th><th className="pb-2 pr-4">Type</th><th className="pb-2 pr-4">Connection</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(integrations?.analyzer_device_integration || []).map((row, idx) => (
                    <tr key={`${row.device_name}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.device_name}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.device_type}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.connection_type}</td>
                      <td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Payment Gateway Configuration</p>
            <div className="mt-3 space-y-2">
              {(integrations?.payment_gateway_configuration || []).map((gateway, idx) => (
                <label key={`${gateway.gateway}-${idx}`} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <span>{gateway.gateway} · {gateway.provider}</span>
                  <input
                    type="checkbox"
                    checked={gateway.enabled}
                    onChange={(e) => setIntegrations((s) => {
                      if (!s) return s
                      const updated = [...s.payment_gateway_configuration]
                      updated[idx] = { ...updated[idx], enabled: e.target.checked }
                      return { ...s, payment_gateway_configuration: updated }
                    })}
                  />
                </label>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">API Key Management</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Key Name</th><th className="pb-2 pr-4">Masked Key</th><th className="pb-2 pr-4">Status</th><th className="pb-2 pr-4">Created</th><th className="pb-2">Last Used</th></tr></thead>
                <tbody>
                  {(integrations?.api_key_management || []).map((row) => (
                    <tr key={row.key_name} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.key_name}</td><td className="py-2 pr-4 text-slate-700">{row.masked_key}</td><td className="py-2 pr-4 text-slate-700">{row.status}</td><td className="py-2 pr-4 text-slate-700">{row.created_at}</td><td className="py-2 text-slate-700">{row.last_used_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Branch &amp; Localization Management (The Network Control)</h2>
          <button onClick={saveBranchLocalization} disabled={savingBranchLocalization || !branchLocalization} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingBranchLocalization ? 'Saving...' : 'Save Branch Settings'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Multi-Branch Configuration</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">Address</th><th className="pb-2 pr-4">Contact</th><th className="pb-2 pr-4">Hours</th><th className="pb-2 pr-4">Timezone</th><th className="pb-2">Status</th></tr></thead>
                <tbody>
                  {(branchLocalization?.multi_branch_configuration || []).map((row, idx) => (
                    <tr key={`${row.branch_id}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.branch_name}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.address}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.phone}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.operating_hours}</td>
                      <td className="py-2 pr-4 text-slate-700">{row.timezone}</td>
                      <td className="py-2 text-slate-700">{row.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Branch-Level Pricing &amp; Discounts</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Branch</th><th className="pb-2 pr-4">MenuItem</th><th className="pb-2 pr-4">Price</th><th className="pb-2 pr-4">Discount</th><th className="pb-2">Package</th></tr></thead>
                <tbody>
                  {(branchLocalization?.branch_level_pricing_discounts || []).map((row, idx) => (
                    <tr key={`${row.branch_name}-${row.test_code}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.branch_name}</td><td className="py-2 pr-4 text-slate-700">{row.test_code}</td><td className="py-2 pr-4 text-slate-700">₹{row.price}</td><td className="py-2 pr-4 text-slate-700">{row.discount_percent}%</td><td className="py-2 text-slate-700">{row.package_rule}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Branch-Level Staff &amp; Permissions</p>
            <div className="mt-3 space-y-2">
              {(branchLocalization?.branch_level_staff_permissions || []).map((row, idx) => (
                <div key={`${row.branch_name}-${row.role}-${idx}`} className="rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{row.branch_name} · {row.role}</p>
                  <p className="text-xs text-slate-600">{row.permissions.join(', ')}</p>
                </div>
              ))}
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Central MenuItem Catalog</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Code</th><th className="pb-2 pr-4">MenuItem Name</th><th className="pb-2 pr-4">Category</th><th className="pb-2">Active</th></tr></thead>
                <tbody>
                  {(branchLocalization?.central_test_catalog || []).map((row) => (
                    <tr key={row.test_code} className="border-b border-slate-100">
                      <td className="py-2 pr-4 text-slate-700">{row.test_code}</td><td className="py-2 pr-4 text-slate-700">{row.test_name}</td><td className="py-2 pr-4 text-slate-700">{row.category}</td><td className="py-2 text-slate-700">{String(row.active)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">2-Click Branch Switching</p>
            <div className="mt-3 space-y-2">
              <select
                value={branchLocalization?.branch_switching.current_view_branch || ''}
                onChange={(e) => setBranchLocalization((s) => (s ? { ...s, branch_switching: { ...s.branch_switching, current_view_branch: e.target.value } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                {(branchLocalization?.branch_switching.available_branches || []).map((branch) => (
                  <option key={branch} value={branch}>{branch}</option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={branchLocalization?.branch_switching.quick_switch_enabled || false}
                  onChange={(e) => setBranchLocalization((s) => (s ? { ...s, branch_switching: { ...s.branch_switching, quick_switch_enabled: e.target.checked } } : s))}
                />
                Enable quick branch switching
              </label>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Data &amp; Compliance Management (The Rulebook)</h2>
          <button onClick={saveDataCompliance} disabled={savingDataCompliance || !dataCompliance} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingDataCompliance ? 'Saving...' : 'Save Data & Compliance'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Data Retention Policy</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <input type="number" value={dataCompliance?.data_retention_policy.patient_data_retention_years || 0} onChange={(e) => setDataCompliance((s) => s ? { ...s, data_retention_policy: { ...s.data_retention_policy, patient_data_retention_years: Number(e.target.value) } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Customer data years" />
              <input type="number" value={dataCompliance?.data_retention_policy.test_results_retention_years || 0} onChange={(e) => setDataCompliance((s) => s ? { ...s, data_retention_policy: { ...s.data_retention_policy, test_results_retention_years: Number(e.target.value) } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="MenuItem results years" />
              <input type="number" value={dataCompliance?.data_retention_policy.audit_logs_retention_years || 0} onChange={(e) => setDataCompliance((s) => s ? { ...s, data_retention_policy: { ...s.data_retention_policy, audit_logs_retention_years: Number(e.target.value) } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Audit logs years" />
              <label className="flex items-center gap-2 rounded-md border border-slate-200 px-2 py-1 text-sm">
                <input type="checkbox" checked={dataCompliance?.data_retention_policy.auto_purge_enabled || false} onChange={(e) => setDataCompliance((s) => s ? { ...s, data_retention_policy: { ...s.data_retention_policy, auto_purge_enabled: e.target.checked } } : s)} />
                Auto purge enabled
              </label>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Data Anonymization Rules</p>
            <div className="mt-3 space-y-2 text-sm">
              {([
                ['enabled', 'Anonymization enabled'],
                ['mask_phone', 'Mask phone'],
                ['mask_email', 'Mask email'],
                ['hash_patient_identifier', 'Hash patient identifier'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2">
                  <input type="checkbox" checked={Boolean(dataCompliance?.data_anonymization_rules[key])} onChange={(e) => setDataCompliance((s) => s ? { ...s, data_anonymization_rules: { ...s.data_anonymization_rules, [key]: e.target.checked } } : s)} />
                  {label}
                </label>
              ))}
              <input type="number" value={dataCompliance?.data_anonymization_rules.reporting_dataset_salt_rotation_days || 0} onChange={(e) => setDataCompliance((s) => s ? { ...s, data_anonymization_rules: { ...s.data_anonymization_rules, reporting_dataset_salt_rotation_days: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Salt rotation days" />
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Consent Management</p>
            <div className="mt-3 space-y-2">
              <input value={dataCompliance?.consent_management.default_consent_form_version || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, consent_management: { ...s.consent_management, default_consent_form_version: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Default consent form version" />
              <input type="number" value={dataCompliance?.consent_management.consent_expiry_days || 0} onChange={(e) => setDataCompliance((s) => s ? { ...s, consent_management: { ...s.consent_management, consent_expiry_days: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Consent expiry days" />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={dataCompliance?.consent_management.require_digital_signature || false} onChange={(e) => setDataCompliance((s) => s ? { ...s, consent_management: { ...s.consent_management, require_digital_signature: e.target.checked } } : s)} /> Require digital signature</label>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={dataCompliance?.consent_management.tracking_enabled || false} onChange={(e) => setDataCompliance((s) => s ? { ...s, consent_management: { ...s.consent_management, tracking_enabled: e.target.checked } } : s)} /> Consent tracking enabled</label>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">GDPR / HIPAA / DPDP Compliance</p>
            <div className="mt-3 space-y-2">
              <input value={dataCompliance?.regulatory_compliance.dpdp_mode || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, regulatory_compliance: { ...s.regulatory_compliance, dpdp_mode: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="DPDP mode" />
              <input value={dataCompliance?.regulatory_compliance.gdpr_mode || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, regulatory_compliance: { ...s.regulatory_compliance, gdpr_mode: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="GDPR mode" />
              <input value={dataCompliance?.regulatory_compliance.hipaa_mode || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, regulatory_compliance: { ...s.regulatory_compliance, hipaa_mode: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="HIPAA mode" />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={dataCompliance?.regulatory_compliance.cross_border_transfer_restriction || false} onChange={(e) => setDataCompliance((s) => s ? { ...s, regulatory_compliance: { ...s.regulatory_compliance, cross_border_transfer_restriction: e.target.checked } } : s)} /> Restrict cross-border transfer</label>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Backup &amp; Disaster Recovery</p>
            <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-5">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={dataCompliance?.backup_disaster_recovery.automated_backup_enabled || false} onChange={(e) => setDataCompliance((s) => s ? { ...s, backup_disaster_recovery: { ...s.backup_disaster_recovery, automated_backup_enabled: e.target.checked } } : s)} /> Auto backup</label>
              <input value={dataCompliance?.backup_disaster_recovery.backup_frequency || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, backup_disaster_recovery: { ...s.backup_disaster_recovery, backup_frequency: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Backup frequency" />
              <input type="number" value={dataCompliance?.backup_disaster_recovery.backup_retention_days || 0} onChange={(e) => setDataCompliance((s) => s ? { ...s, backup_disaster_recovery: { ...s.backup_disaster_recovery, backup_retention_days: Number(e.target.value) } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Retention days" />
              <input value={dataCompliance?.backup_disaster_recovery.dr_drill_frequency || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, backup_disaster_recovery: { ...s.backup_disaster_recovery, dr_drill_frequency: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="DR drill frequency" />
              <input value={dataCompliance?.backup_disaster_recovery.last_successful_backup || ''} onChange={(e) => setDataCompliance((s) => s ? { ...s, backup_disaster_recovery: { ...s.backup_disaster_recovery, last_successful_backup: e.target.value } } : s)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Last successful backup" />
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">AI &amp; Automation Configuration (The Brain)</h2>
          <button onClick={saveAiAutomation} disabled={savingAiAutomation || !aiAutomation} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingAiAutomation ? 'Saving...' : 'Save AI & Automation'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">AI Auto-Validation Rules</p>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={aiAutomation?.ai_auto_validation_rules.enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_auto_validation_rules: { ...s.ai_auto_validation_rules, enabled: e.target.checked } } : s)} /> Enabled</label>
              <input type="number" value={aiAutomation?.ai_auto_validation_rules.max_reference_range_deviation_percent || 0} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_auto_validation_rules: { ...s.ai_auto_validation_rules, max_reference_range_deviation_percent: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Max deviation %" />
              <input type="number" step="0.01" min="0" max="1" value={aiAutomation?.ai_auto_validation_rules.minimum_confidence_threshold || 0} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_auto_validation_rules: { ...s.ai_auto_validation_rules, minimum_confidence_threshold: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Min confidence (0-1)" />
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={aiAutomation?.ai_auto_validation_rules.critical_result_requires_manual_review || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_auto_validation_rules: { ...s.ai_auto_validation_rules, critical_result_requires_manual_review: e.target.checked } } : s)} /> Critical results require manual review</label>
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">AI Delta-Check Alerts</p>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={aiAutomation?.ai_delta_check_alerts.enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_delta_check_alerts: { ...s.ai_delta_check_alerts, enabled: e.target.checked } } : s)} /> Enabled</label>
              <input type="number" value={aiAutomation?.ai_delta_check_alerts.delta_percent_threshold || 0} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_delta_check_alerts: { ...s.ai_delta_check_alerts, delta_percent_threshold: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Delta threshold %" />
              <input type="number" value={aiAutomation?.ai_delta_check_alerts.lookback_days || 0} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_delta_check_alerts: { ...s.ai_delta_check_alerts, lookback_days: Number(e.target.value) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Lookback days" />
              <input value={(aiAutomation?.ai_delta_check_alerts.alert_channels || []).join(', ')} onChange={(e) => setAiAutomation((s) => s ? { ...s, ai_delta_check_alerts: { ...s.ai_delta_check_alerts, alert_channels: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Alert channels (comma separated)" />
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Automated Order Delivery</p>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.automated_report_delivery.enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, automated_report_delivery: { ...s.automated_report_delivery, enabled: e.target.checked } } : s)} /> Enabled</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.automated_report_delivery.whatsapp_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, automated_report_delivery: { ...s.automated_report_delivery, whatsapp_enabled: e.target.checked } } : s)} /> WhatsApp</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.automated_report_delivery.sms_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, automated_report_delivery: { ...s.automated_report_delivery, sms_enabled: e.target.checked } } : s)} /> SMS</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.automated_report_delivery.email_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, automated_report_delivery: { ...s.automated_report_delivery, email_enabled: e.target.checked } } : s)} /> Email</label>
              <input value={aiAutomation?.automated_report_delivery.delivery_window || ''} onChange={(e) => setAiAutomation((s) => s ? { ...s, automated_report_delivery: { ...s.automated_report_delivery, delivery_window: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Delivery window" />
            </div>
          </div>
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Predictive Analytics Settings</p>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.predictive_analytics_settings.demand_forecasting_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, predictive_analytics_settings: { ...s.predictive_analytics_settings, demand_forecasting_enabled: e.target.checked } } : s)} /> Demand forecasting</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.predictive_analytics_settings.patient_churn_model_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, predictive_analytics_settings: { ...s.predictive_analytics_settings, patient_churn_model_enabled: e.target.checked } } : s)} /> Customer churn prediction</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.predictive_analytics_settings.inventory_optimization_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, predictive_analytics_settings: { ...s.predictive_analytics_settings, inventory_optimization_enabled: e.target.checked } } : s)} /> Inventory optimization</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={aiAutomation?.predictive_analytics_settings.drift_monitoring_enabled || false} onChange={(e) => setAiAutomation((s) => s ? { ...s, predictive_analytics_settings: { ...s.predictive_analytics_settings, drift_monitoring_enabled: e.target.checked } } : s)} /> Drift monitoring</label>
              <input value={aiAutomation?.predictive_analytics_settings.model_refresh_frequency || ''} onChange={(e) => setAiAutomation((s) => s ? { ...s, predictive_analytics_settings: { ...s.predictive_analytics_settings, model_refresh_frequency: e.target.value } } : s)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Model refresh frequency" />
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">User Interface &amp; Experience (The Look &amp; Feel)</h2>
          <button onClick={saveUiExperience} disabled={savingUiExperience || !uiExperience} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingUiExperience ? 'Saving...' : 'Save UI & Experience'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Default Theme</p>
            <div className="mt-3 space-y-2">
              <select
                value={uiExperience?.default_theme.theme || 'light'}
                onChange={(e) => setUiExperience((s) => (s ? { ...s, default_theme: { ...s.default_theme, theme: e.target.value } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
              <input
                value={uiExperience?.default_theme.default_density || ''}
                onChange={(e) => setUiExperience((s) => (s ? { ...s, default_theme: { ...s.default_theme, default_density: e.target.value } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Default density"
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={uiExperience?.default_theme.allow_user_override || false}
                  onChange={(e) => setUiExperience((s) => (s ? { ...s, default_theme: { ...s.default_theme, allow_user_override: e.target.checked } } : s))}
                />
                Allow user theme override
              </label>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">UI Element Visibility</p>
            <div className="mt-3 space-y-2 text-sm">
              {(['footer', 'billing_history', 'support_buttons', 'help_center_widget', 'quick_action_fab'] as const).map((key) => (
                <label key={key} className="flex items-center justify-between rounded-md border border-slate-200 px-3 py-2">
                  <span className="capitalize text-slate-700">{key.replaceAll('_', ' ')}</span>
                  <input
                    type="checkbox"
                    checked={Boolean(uiExperience?.ui_element_visibility[key])}
                    onChange={(e) => setUiExperience((s) => (s ? { ...s, ui_element_visibility: { ...s.ui_element_visibility, [key]: e.target.checked } } : s))}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Dashboard Customization</p>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={uiExperience?.dashboard_customization.personalized_layouts_enabled || false}
                  onChange={(e) => setUiExperience((s) => (s ? { ...s, dashboard_customization: { ...s.dashboard_customization, personalized_layouts_enabled: e.target.checked } } : s))}
                />
                Personalized dashboard layouts
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={uiExperience?.dashboard_customization.draggable_widgets_enabled || false}
                  onChange={(e) => setUiExperience((s) => (s ? { ...s, dashboard_customization: { ...s.dashboard_customization, draggable_widgets_enabled: e.target.checked } } : s))}
                />
                Draggable widgets enabled
              </label>
              <div className="rounded-md border border-slate-200 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Layout Presets</p>
                <div className="mt-2 space-y-2">
                  {(uiExperience?.dashboard_customization.layout_presets || []).map((preset, idx) => (
                    <div key={`${preset.name}-${idx}`} className="rounded-md bg-slate-50 p-2">
                      <input
                        value={preset.name}
                        onChange={(e) => setUiExperience((s) => {
                          if (!s) return s
                          const layout_presets = [...s.dashboard_customization.layout_presets]
                          layout_presets[idx] = { ...layout_presets[idx], name: e.target.value }
                          return { ...s, dashboard_customization: { ...s.dashboard_customization, layout_presets } }
                        })}
                        className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
                        placeholder="Preset name"
                      />
                      <input
                        value={preset.widgets.join(', ')}
                        onChange={(e) => setUiExperience((s) => {
                          if (!s) return s
                          const layout_presets = [...s.dashboard_customization.layout_presets]
                          layout_presets[idx] = { ...layout_presets[idx], widgets: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) }
                          return { ...s, dashboard_customization: { ...s.dashboard_customization, layout_presets } }
                        })}
                        className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
                        placeholder="Widgets (comma separated)"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12`}>
            <p className="text-sm font-semibold text-slate-700">Role-Specific Dashboards</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Role</th><th className="pb-2 pr-4">Default Dashboard</th><th className="pb-2">Key Modules</th></tr></thead>
                <tbody>
                  {(uiExperience?.role_specific_dashboards || []).map((row, idx) => (
                    <tr key={`${row.role}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{row.role}</td>
                      <td className="py-2 pr-4">
                        <input
                          value={row.default_dashboard}
                          onChange={(e) => setUiExperience((s) => {
                            if (!s) return s
                            const role_specific_dashboards = [...s.role_specific_dashboards]
                            role_specific_dashboards[idx] = { ...role_specific_dashboards[idx], default_dashboard: e.target.value }
                            return { ...s, role_specific_dashboards }
                          })}
                          className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                        />
                      </td>
                      <td className="py-2">
                        <input
                          value={row.key_modules.join(', ')}
                          onChange={(e) => setUiExperience((s) => {
                            if (!s) return s
                            const role_specific_dashboards = [...s.role_specific_dashboards]
                            role_specific_dashboards[idx] = { ...role_specific_dashboards[idx], key_modules: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) }
                            return { ...s, role_specific_dashboards }
                          })}
                          className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                          placeholder="Modules (comma separated)"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Maintenance &amp; System Health (The Check Engine Light)</h2>
          <button onClick={saveMaintenanceHealth} disabled={savingMaintenanceHealth || !maintenanceHealth} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingMaintenanceHealth ? 'Saving...' : 'Save Maintenance Settings'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">System Status Dashboard</p>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>Overall status: <span className="font-semibold uppercase">{maintenanceHealth?.system_status_dashboard.overall_status}</span></p>
              <p>Active branches: Online {maintenanceHealth?.system_status_dashboard.active_branches.online} · Degraded {maintenanceHealth?.system_status_dashboard.active_branches.degraded} · Offline {maintenanceHealth?.system_status_dashboard.active_branches.offline}</p>
              <p>Database: {maintenanceHealth?.system_status_dashboard.database_health.status} · Lag {maintenanceHealth?.system_status_dashboard.database_health.replication_lag_seconds}s · Connections {maintenanceHealth?.system_status_dashboard.database_health.connections_used_percent}%</p>
              <p>Backup: {maintenanceHealth?.system_status_dashboard.backup_status.status} · Last {maintenanceHealth?.system_status_dashboard.backup_status.last_successful_backup}</p>
              <p className="text-xs text-slate-500">Last refreshed: {maintenanceHealth?.system_status_dashboard.last_refreshed_at}</p>
            </div>
            <div className="mt-3 space-y-2">
              {(maintenanceHealth?.system_status_dashboard.critical_integrations || []).map((integration, idx) => (
                <div key={`${integration.name}-${idx}`} className="rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{integration.name}</p>
                  <p className="text-xs text-slate-600">Status: {integration.status} · Latency: {integration.latency_ms} ms</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Scheduled Jobs &amp; Automations</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">Job</th><th className="pb-2 pr-4">Type</th><th className="pb-2 pr-4">Status</th><th className="pb-2 pr-4">Last Run</th><th className="pb-2">Next Run</th></tr></thead>
                <tbody>
                  {(maintenanceHealth?.scheduled_jobs_automations || []).map((job, idx) => (
                    <tr key={`${job.job_name}-${idx}`} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{job.job_name}</td>
                      <td className="py-2 pr-4 text-slate-700">{job.job_type}</td>
                      <td className="py-2 pr-4 text-slate-700">{job.status}</td>
                      <td className="py-2 pr-4 text-slate-700">{job.last_run_time}</td>
                      <td className="py-2 text-slate-700">{job.next_run_time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-5`}>
            <p className="text-sm font-semibold text-slate-700">Maintenance Mode</p>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={maintenanceHealth?.maintenance_mode.enabled || false}
                  onChange={(e) => setMaintenanceHealth((s) => (s ? { ...s, maintenance_mode: { ...s.maintenance_mode, enabled: e.target.checked } } : s))}
                />
                Enable maintenance mode
              </label>
              <input
                value={maintenanceHealth?.maintenance_mode.planned_window || ''}
                onChange={(e) => setMaintenanceHealth((s) => (s ? { ...s, maintenance_mode: { ...s.maintenance_mode, planned_window: e.target.value } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Planned window"
              />
              <textarea
                value={maintenanceHealth?.maintenance_mode.user_facing_message || ''}
                onChange={(e) => setMaintenanceHealth((s) => (s ? { ...s, maintenance_mode: { ...s.maintenance_mode, user_facing_message: e.target.value } } : s))}
                className="h-24 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="User-facing maintenance message"
              />
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-7`}>
            <p className="text-sm font-semibold text-slate-700">Error &amp; Incident Log</p>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-4">ID</th><th className="pb-2 pr-4">Severity</th><th className="pb-2 pr-4">Component</th><th className="pb-2 pr-4">Status</th><th className="pb-2 pr-4">Occurred</th><th className="pb-2">Resolved</th></tr></thead>
                <tbody>
                  {(maintenanceHealth?.error_incident_log || []).map((incident) => (
                    <tr key={incident.id} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-semibold text-slate-800">{incident.id}</td>
                      <td className="py-2 pr-4 text-slate-700">{incident.severity}</td>
                      <td className="py-2 pr-4 text-slate-700">{incident.component}</td>
                      <td className="py-2 pr-4 text-slate-700">{incident.status}</td>
                      <td className="py-2 pr-4 text-slate-700">{incident.occurred_at}</td>
                      <td className="py-2 text-slate-700">{incident.resolved_at || 'Pending'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Import / Export &amp; Data Migration (The Data Gateway)</h2>
          <button onClick={saveImportExportMigration} disabled={savingImportExportMigration || !importExportMigration} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingImportExportMigration ? 'Saving...' : 'Save Data Gateway Settings'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Bulk Data Import</p>
            <div className="mt-3 space-y-2 text-sm">
              <input
                value={(importExportMigration?.bulk_data_import.supported_entities || []).join(', ')}
                onChange={(e) => setImportExportMigration((s) => (s ? { ...s, bulk_data_import: { ...s.bulk_data_import, supported_entities: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="Supported entities"
              />
              <input
                value={(importExportMigration?.bulk_data_import.supported_formats || []).join(', ')}
                onChange={(e) => setImportExportMigration((s) => (s ? { ...s, bulk_data_import: { ...s.bulk_data_import, supported_formats: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="Supported formats"
              />
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-3">Job</th><th className="pb-2 pr-3">Entity</th><th className="pb-2 pr-3">Status</th><th className="pb-2">Processed</th></tr></thead>
                <tbody>
                  {(importExportMigration?.bulk_data_import.last_import_jobs || []).map((job) => (
                    <tr key={job.job_id} className="border-b border-slate-100">
                      <td className="py-2 pr-3 text-slate-700">{job.job_id}</td>
                      <td className="py-2 pr-3 text-slate-700">{job.entity}</td>
                      <td className="py-2 pr-3 text-slate-700">{job.status}</td>
                      <td className="py-2 text-slate-700">{job.processed_records}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Bulk Data Export</p>
            <div className="mt-3 space-y-2 text-sm">
              <input
                value={(importExportMigration?.bulk_data_export.available_exports || []).join(', ')}
                onChange={(e) => setImportExportMigration((s) => (s ? { ...s, bulk_data_export: { ...s.bulk_data_export, available_exports: e.target.value.split(',').map((v) => v.trim()).filter(Boolean) } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="Available exports"
              />
              <input
                value={importExportMigration?.bulk_data_export.default_format || ''}
                onChange={(e) => setImportExportMigration((s) => (s ? { ...s, bulk_data_export: { ...s.bulk_data_export, default_format: e.target.value } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="Default format"
              />
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-3">Job</th><th className="pb-2 pr-3">Dataset</th><th className="pb-2 pr-3">Status</th><th className="pb-2">Rows</th></tr></thead>
                <tbody>
                  {(importExportMigration?.bulk_data_export.last_export_jobs || []).map((job) => (
                    <tr key={job.job_id} className="border-b border-slate-100">
                      <td className="py-2 pr-3 text-slate-700">{job.job_id}</td>
                      <td className="py-2 pr-3 text-slate-700">{job.dataset}</td>
                      <td className="py-2 pr-3 text-slate-700">{job.status}</td>
                      <td className="py-2 text-slate-700">{job.rows_exported}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-4`}>
            <p className="text-sm font-semibold text-slate-700">Data Migration Tools</p>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={importExportMigration?.data_migration_tools.validation_checks_enabled || false}
                  onChange={(e) => setImportExportMigration((s) => (s ? { ...s, data_migration_tools: { ...s.data_migration_tools, validation_checks_enabled: e.target.checked } } : s))}
                />
                Validation checks enabled
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={importExportMigration?.data_migration_tools.rollback_supported || false}
                  onChange={(e) => setImportExportMigration((s) => (s ? { ...s, data_migration_tools: { ...s.data_migration_tools, rollback_supported: e.target.checked } } : s))}
                />
                Rollback supported
              </label>
            </div>
            <div className="mt-3 space-y-2">
              {(importExportMigration?.data_migration_tools.legacy_connectors || []).map((connector, idx) => (
                <div key={`${connector.connector_name}-${idx}`} className="rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{connector.connector_name}</p>
                  <p className="text-xs text-slate-600">{connector.source_type} · {connector.status}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">System Wow Features</h2>
          <button onClick={saveWowFeatures} disabled={savingWowFeatures || !wowFeatures} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {savingWowFeatures ? 'Saving...' : 'Save Wow Features'}
          </button>
        </div>
        <div className="grid grid-cols-12 gap-4">
          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Digital Constitution Version Control</p>
            <div className="mt-3 space-y-2 text-sm">
              <p>Current version: <span className="font-semibold">{wowFeatures?.digital_constitution_version_control.current_version}</span></p>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={wowFeatures?.digital_constitution_version_control.rollback_allowed || false}
                  onChange={(e) => setWowFeatures((s) => (s ? { ...s, digital_constitution_version_control: { ...s.digital_constitution_version_control, rollback_allowed: e.target.checked } } : s))}
                />
                Rollback allowed
              </label>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead><tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500"><th className="pb-2 pr-3">Version</th><th className="pb-2 pr-3">By</th><th className="pb-2">Summary</th></tr></thead>
                <tbody>
                  {(wowFeatures?.digital_constitution_version_control.version_history || []).map((v) => (
                    <tr key={v.version} className="border-b border-slate-100">
                      <td className="py-2 pr-3 text-slate-700">{v.version}</td>
                      <td className="py-2 pr-3 text-slate-700">{v.changed_by}</td>
                      <td className="py-2 text-slate-700">{v.change_summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Configuration Push</p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <input
                type="number"
                value={wowFeatures?.configuration_push.target_branches || 0}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, configuration_push: { ...s.configuration_push, target_branches: Number(e.target.value) } } : s))}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Target branches"
              />
              <input
                type="number"
                value={wowFeatures?.configuration_push.pending_changes_count || 0}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, configuration_push: { ...s.configuration_push, pending_changes_count: Number(e.target.value) } } : s))}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Pending changes"
              />
              <input
                value={wowFeatures?.configuration_push.last_push_status || ''}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, configuration_push: { ...s.configuration_push, last_push_status: e.target.value } } : s))}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Last push status"
              />
              <input
                value={wowFeatures?.configuration_push.last_push_by || ''}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, configuration_push: { ...s.configuration_push, last_push_by: e.target.value } } : s))}
                className="rounded-md border border-slate-300 px-3 py-2"
                placeholder="Last push by"
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">Last push at: {wowFeatures?.configuration_push.last_push_at}</p>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Zero-Downtime Feature Rollout</p>
            <div className="mt-3 space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={wowFeatures?.zero_downtime_feature_rollout.enabled || false}
                  onChange={(e) => setWowFeatures((s) => (s ? { ...s, zero_downtime_feature_rollout: { ...s.zero_downtime_feature_rollout, enabled: e.target.checked } } : s))}
                />
                Enable progressive rollout
              </label>
              <input
                type="number"
                value={wowFeatures?.zero_downtime_feature_rollout.default_rollout_percent || 0}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, zero_downtime_feature_rollout: { ...s.zero_downtime_feature_rollout, default_rollout_percent: Number(e.target.value) } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="Default rollout %"
              />
            </div>
            <div className="mt-3 space-y-2">
              {(wowFeatures?.zero_downtime_feature_rollout.active_rollouts || []).map((rollout, idx) => (
                <div key={`${rollout.feature_key}-${idx}`} className="rounded-md border border-slate-200 px-3 py-2 text-sm">
                  <p className="font-semibold text-slate-800">{rollout.feature_key}</p>
                  <p className="text-xs text-slate-600">{rollout.current_percent}% · {rollout.status}</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${CARD_CLASS} col-span-12 lg:col-span-6`}>
            <p className="text-sm font-semibold text-slate-700">Automated System Health Order</p>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={wowFeatures?.automated_system_health_report.enabled || false}
                  onChange={(e) => setWowFeatures((s) => (s ? { ...s, automated_system_health_report: { ...s.automated_system_health_report, enabled: e.target.checked } } : s))}
                />
                Enable health report
              </label>
              <input
                value={wowFeatures?.automated_system_health_report.cadence || ''}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, automated_system_health_report: { ...s.automated_system_health_report, cadence: e.target.value } } : s))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="Cadence"
              />
              <textarea
                value={wowFeatures?.automated_system_health_report.summary || ''}
                onChange={(e) => setWowFeatures((s) => (s ? { ...s, automated_system_health_report: { ...s.automated_system_health_report, summary: e.target.value } } : s))}
                className="h-24 w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="AI summary"
              />
              <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-700">
                <p>Uptime: {wowFeatures?.automated_system_health_report.kpi_snapshot.uptime_percent}%</p>
                <p>Open incidents: {wowFeatures?.automated_system_health_report.kpi_snapshot.open_incidents}</p>
                <p>Backup success rate: {wowFeatures?.automated_system_health_report.kpi_snapshot.backup_success_rate_percent}%</p>
                <p>Avg API latency: {wowFeatures?.automated_system_health_report.kpi_snapshot.avg_api_latency_ms} ms</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default CeoSystemSettings
