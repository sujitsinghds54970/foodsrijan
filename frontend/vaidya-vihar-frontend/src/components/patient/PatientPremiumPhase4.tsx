import { useCallback, useEffect, useMemo, useState } from 'react'
import { MapContainer, Polyline, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import toast from 'react-hot-toast'

import { useAuth } from '../../contexts/AuthContext'
import {
  connectPatientWearable,
  getPatientEmergencyAlerts,
  getPatientFamilyProfile,
  getPatientHomeCollectionMap,
  getPatientSecondOpinionRequests,
  getPatientVaultDocuments,
  getPatientWearables,
  requestPatientSecondOpinion,
  uploadPatientVaultDocument,
} from './b2cApi'

import 'leaflet/dist/leaflet.css'

interface PatientPremiumPhase4Props {
  active: boolean
}

type WearableProvider = 'Apple Health' | 'Google Fit' | 'Fitbit'

const DEFAULT_CENTER: [number, number] = [28.6139, 77.209]

export default function PatientPremiumPhase4({ active }: PatientPremiumPhase4Props) {
  const { token } = useAuth()
  const patientToken = typeof window !== 'undefined' ? localStorage.getItem('patient_portal_token') : null
  const apiToken = patientToken || token
  const [loading, setLoading] = useState(false)
  const [familyProfile, setFamilyProfile] = useState<any>(null)
  const [mapData, setMapData] = useState<any>(null)
  const [vaultDocs, setVaultDocs] = useState<any[]>([])
  const [wearables, setWearables] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [secondOpinions, setSecondOpinions] = useState<any[]>([])
  const [vaultFile, setVaultFile] = useState<File | null>(null)
  const [vaultLabel, setVaultLabel] = useState('Upload prescription / report')
  const [wearableProvider, setWearableProvider] = useState<WearableProvider>('Apple Health')
  const [wearableToken, setWearableToken] = useState('')
  const [secondOpinionReportId, setSecondOpinionReportId] = useState('')
  const [secondOpinionPanel, setSecondOpinionPanel] = useState('Senior Specialist Panel')

  const routePoints = useMemo(() => {
    if (!mapData?.route_points?.length) return [DEFAULT_CENTER, DEFAULT_CENTER]
    return mapData.route_points.map((point: any) => [Number(point.lat), Number(point.lng)] as [number, number])
  }, [mapData])

  const loadAll = useCallback(async () => {
    if (!apiToken) return
    setLoading(true)
    try {
      const [familyRes, mapRes, docsRes, wearablesRes, alertsRes, secondOpinionRes] = await Promise.all([
        getPatientFamilyProfile(apiToken),
        getPatientHomeCollectionMap(apiToken),
        getPatientVaultDocuments(apiToken),
        getPatientWearables(apiToken),
        getPatientEmergencyAlerts(apiToken),
        getPatientSecondOpinionRequests(apiToken),
      ])
      setFamilyProfile(familyRes)
      setMapData(mapRes)
      setVaultDocs(docsRes.items || [])
      setWearables(wearablesRes.items || [])
      setAlerts(alertsRes.items || [])
      setSecondOpinions(secondOpinionRes.items || [])
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to load premium patient features')
    } finally {
      setLoading(false)
    }
  }, [apiToken])

  useEffect(() => {
    if (!active || !apiToken) return
    void loadAll()
  }, [active, apiToken, loadAll])

  useEffect(() => {
    if (!active || !apiToken) return

    const refreshOnAlert = () => {
      void loadAll()
    }

    window.addEventListener('patient-critical-alert', refreshOnAlert)
    return () => window.removeEventListener('patient-critical-alert', refreshOnAlert)
  }, [active, apiToken, loadAll])

  const uploadVaultDocument = async () => {
    if (!apiToken || !vaultFile) {
      toast.error('Choose a file first')
      return
    }
    try {
      const result = await uploadPatientVaultDocument(apiToken, vaultFile, vaultLabel)
      setVaultDocs((prev) => [result.document, ...prev])
      setVaultFile(null)
      setVaultLabel('Upload prescription / report')
      toast.success(result.message)
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to upload document')
    }
  }

  const connectWearable = async () => {
    if (!apiToken) return
    try {
      const result = await connectPatientWearable(apiToken, { provider: wearableProvider, token: wearableToken || undefined })
      toast.success(result.message)
      setWearableToken('')
      await loadAll()
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to connect wearable')
    }
  }

  const requestSecondOpinion = async () => {
    if (!apiToken) return
    const reportId = Number(secondOpinionReportId)
    if (!reportId) {
      toast.error('Enter a valid report ID')
      return
    }
    try {
      const result = await requestPatientSecondOpinion(apiToken, {
        report_id: reportId,
        specialist_panel: secondOpinionPanel,
      })
      setSecondOpinions((prev) => [result, ...prev])
      toast.success(result.message)
      if (result.payment_url) {
        window.open(result.payment_url, '_blank')
      }
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Unable to request second opinion')
    }
  }

  if (!active) return null

  const criticalAlertCount = alerts.length

  return (
    <section className="space-y-6 rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-2xl">
      {criticalAlertCount > 0 && (
        <div className="rounded-2xl border border-rose-300 bg-rose-50 p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-rose-700">Emergency & Critical Alert</p>
          <h3 className="mt-1 text-lg font-black text-rose-900">Critical values detected in {criticalAlertCount} report{criticalAlertCount > 1 ? 's' : ''}</h3>
          <p className="mt-1 text-sm text-rose-800">Please review the flagged report summary immediately. SMS, in-app, and email notifications have been recorded for these alerts.</p>
        </div>
      )}

      <div className="rounded-3xl bg-gradient-to-r from-slate-950 via-cyan-900 to-emerald-800 p-5 text-white">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-100">Phase 4 Premium</p>
        <h2 className="mt-1 text-2xl font-black">Unified Family Health Profile</h2>
        <p className="mt-2 max-w-3xl text-sm text-cyan-50">
          One patient account for the entire family with secure vault uploads, mock live home collection tracking, wearable syncing, and premium specialist review.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 lg:col-span-2">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Family Profile</p>
              <h3 className="text-lg font-bold text-slate-900">{familyProfile?.headline || 'Unified Family Health Profile'}</h3>
            </div>
            <button type="button" onClick={() => void loadAll()} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-white">
              Refresh
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-600">{familyProfile?.summary || 'Single account shared by the family for reports, vault uploads, and bookings.'}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-white p-3 shadow-sm">
              <p className="text-xs uppercase text-slate-500">Primary Member</p>
              <p className="mt-1 font-semibold text-slate-900">{familyProfile?.primary_member?.full_name || '-'}</p>
              <p className="text-xs text-slate-500">{familyProfile?.primary_member?.mobile || '-'}</p>
            </div>
            <div className="rounded-xl bg-white p-3 shadow-sm">
              <p className="text-xs uppercase text-slate-500">Family Group</p>
              <p className="mt-1 font-semibold text-slate-900">{familyProfile?.family_group || 'Shared Family Wallet/Profile'}</p>
              <p className="text-xs text-slate-500">Members: {familyProfile?.members?.length || 0}</p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {(familyProfile?.members || []).map((member: any) => (
              <span key={member.id} className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white">
                {member.name} · {member.relation}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Wearable Sync</p>
          <h3 className="mt-1 text-lg font-bold text-slate-900">Connect to Fitbit/Apple Health</h3>
          <p className="mt-1 text-sm text-slate-600">Connect to Fitbit/Apple Health</p>
          <div className="mt-3 space-y-2">
            <select value={wearableProvider} onChange={(event) => setWearableProvider(event.target.value as WearableProvider)} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm">
              <option>Apple Health</option>
              <option>Google Fit</option>
              <option>Fitbit</option>
            </select>
            <input
              value={wearableToken}
              onChange={(event) => setWearableToken(event.target.value)}
              placeholder="Optional access token"
              className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm"
            />
            <button type="button" onClick={() => void connectWearable()} className="w-full rounded-xl bg-cyan-600 px-3 py-2 text-sm font-semibold text-white">
              {wearableProvider === 'Apple Health' ? 'Connect to Apple Health' : 'Connect to Fitbit/Apple Health'}
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {wearables.slice(0, 3).map((item) => (
              <div key={item.id} className="rounded-lg bg-slate-50 p-3 text-sm">
                <p className="font-semibold text-slate-900">{item.provider}</p>
                <p className="text-xs text-slate-500">Status: {item.status}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Home Collection Map</p>
              <h3 className="text-lg font-bold text-slate-900">Phlebotomist Live Route</h3>
            </div>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">{mapData?.status || 'mock_live'}</span>
          </div>
          <div className="mt-3 h-[380px] overflow-hidden rounded-2xl border border-slate-200">
            <MapContainer center={mapData?.patient_location ? [mapData.patient_location.lat, mapData.patient_location.lng] : DEFAULT_CENTER} zoom={13} className="h-full w-full">
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Polyline positions={routePoints} pathOptions={{ color: '#0f766e', weight: 4 }} />
              {mapData?.patient_location && (
                <CircleMarker center={[mapData.patient_location.lat, mapData.patient_location.lng]} radius={11} pathOptions={{ color: '#2563eb', fillColor: '#2563eb', fillOpacity: 0.85 }}>
                  <Popup>Patient Home</Popup>
                </CircleMarker>
              )}
              {mapData?.phlebotomist_location && (
                <CircleMarker center={[mapData.phlebotomist_location.lat, mapData.phlebotomist_location.lng]} radius={11} pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.85 }}>
                  <Popup>Phlebotomist</Popup>
                </CircleMarker>
              )}
            </MapContainer>
          </div>
          <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
            <p className="font-semibold text-slate-900">ETA: {mapData?.eta_minutes ?? 18} minutes</p>
            <p>{mapData?.message || 'Static mock coordinates enabled for demo tracking.'}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Centralized Health Vault</p>
            <h3 className="mt-1 text-lg font-bold text-slate-900">Upload Scanned Reports</h3>
            <div className="mt-3 space-y-2">
              <input value={vaultLabel} onChange={(event) => setVaultLabel(event.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Vault label" />
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={(event) => setVaultFile(event.target.files?.[0] || null)} className="w-full rounded-xl border border-dashed border-slate-300 px-3 py-2 text-sm" />
              <button type="button" onClick={() => void uploadVaultDocument()} className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white">
                Upload to Secure Vault
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Emergency & Critical Alerts</p>
            <h3 className="mt-1 text-lg font-bold text-slate-900">SMS + In-App + Email</h3>
            <div className="mt-3 space-y-2">
              {alerts.length === 0 ? (
                <p className="text-sm text-slate-500">No emergency alerts triggered yet.</p>
              ) : (
                alerts.map((item) => (
                  <div key={item.id} className="rounded-xl bg-rose-50 p-3 text-sm text-rose-900">
                    <p className="font-semibold">{item.alert_type}</p>
                    <p className="text-xs">{new Date(item.triggered_at).toLocaleString()}</p>
                    <p className="text-xs">Channels: {(item.delivery_channels || []).join(', ')}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Second Opinion Service</p>
          <h3 className="mt-1 text-lg font-bold text-slate-900">Premium Specialist Panel</h3>
          <div className="mt-3 space-y-2">
            <input value={secondOpinionReportId} onChange={(event) => setSecondOpinionReportId(event.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Report ID" />
            <input value={secondOpinionPanel} onChange={(event) => setSecondOpinionPanel(event.target.value)} className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Specialist panel" />
            <button type="button" onClick={() => void requestSecondOpinion()} className="w-full rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white">
              Request Second Opinion
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">Placeholder payment gateway flow opens automatically for premium review requests.</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Vault Items</p>
          <h3 className="mt-1 text-lg font-bold text-slate-900">OCR Text Extracted</h3>
          <div className="mt-3 space-y-3">
            {vaultDocs.length === 0 ? (
              <p className="text-sm text-slate-500">No vault documents yet.</p>
            ) : (
              vaultDocs.map((doc) => (
                <div key={doc.id} className="rounded-xl bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-semibold text-slate-900">{doc.document_label || doc.original_filename}</p>
                    <a href={doc.file_url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-cyan-700 underline">Open</a>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{doc.mime_type || 'file'} · {Math.max(1, Math.round((doc.file_size || 0) / 1024))} KB</p>
                  <p className="mt-2 text-sm text-slate-700 line-clamp-3">{doc.extracted_text}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Second Opinion Queue</p>
          <div className="mt-3 space-y-2">
            {secondOpinions.length === 0 ? (
              <p className="text-sm text-slate-500">No second opinion requests yet.</p>
            ) : (
              secondOpinions.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 p-3 text-sm">
                  <p className="font-semibold text-slate-900">Report #{item.report_id}</p>
                  <p className="text-xs text-slate-500">{item.specialist_panel}</p>
                  <p className="text-xs text-slate-500">Status: {item.status}</p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Wearables</p>
          <div className="mt-3 space-y-2">
            {wearables.length === 0 ? (
              <p className="text-sm text-slate-500">No wearable sync configured yet.</p>
            ) : (
              wearables.map((item) => (
                <div key={item.id} className="rounded-xl bg-slate-50 p-3 text-sm">
                  <p className="font-semibold text-slate-900">{item.provider}</p>
                  <p className="text-xs text-slate-500">{item.status}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading premium patient features...</p>}
    </section>
  )
}
