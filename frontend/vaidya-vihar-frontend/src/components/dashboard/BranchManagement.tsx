import React, { useEffect, useMemo, useRef, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import BankPaymentSettings from '../branch-director/BankPaymentSettings'
import BranchDirectorOverviewDashboard from '../overview/BranchDirectorOverviewDashboard'

interface Branch {
  id: number
  name: string
  location: string
  city: string
  state: string
  pincode: string
  phone: string
  email?: string
  address: string
  license_number?: string
  opening_hours?: string
  facilities?: string
  branch_code: string
  is_active: boolean
  created_at: string
  updated_at?: string
  total_staff?: number
  total_customers?: number
  monthly_revenue?: number
  modalities?: string[]
}

interface BranchStats {
  branch_id: number
  branch_name: string
  total_staff: number
  total_customers: number
  monthly_revenue: number
  total_appointments: number
  pending_payments: number
  inventory_value: number
  active_services: number
}

interface BranchAdminCredentials {
  username: string
  email: string
  password: string
  role: string
}

interface BranchCreateResponse extends Branch {
  branch_admin_credentials?: BranchAdminCredentials
}

interface Asset {
  id: number
  branch_id: number
  asset_name: string
  model?: string
  serial_no?: string
  purchase_date?: string
  last_maintenance_date?: string
  status: string
  notes?: string
  created_at: string
}

interface BranchActivityLog {
  id: number
  user_id: number
  username?: string
  branch_id?: number
  action: string
  entity_type: string
  entity_id?: number
  description: string
  ip_address?: string
  user_agent?: string
  timestamp: string
}

const emptyForm = {
  name: '',
  location: '',
  city: '',
  state: '',
  pincode: '',
  phone: '',
  email: '',
  address: '',
  license_number: '',
  opening_hours: '',
  facilities: '',
  modalities: [] as string[],
}

export default function BranchManagement() {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingBranchId, setEditingBranchId] = useState<number | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [selectedStats, setSelectedStats] = useState<BranchStats | null>(null)
  const [statsBranchId, setStatsBranchId] = useState<number | null>(null)
  const [newBranchCredentials, setNewBranchCredentials] = useState<BranchAdminCredentials | null>(null)
  const [form, setForm] = useState(emptyForm)
  const [selectedBranch, setSelectedBranch] = useState<Branch | null>(null)
  const [branchDetailTab, setBranchDetailTab] = useState<'overview' | 'assets' | 'analytics' | 'settings' | 'activity' | 'bank-payment'>('overview')
  // Assets UI state
  const [assets, setAssets] = useState<Asset[]>([])
  const [assetsLoading, setAssetsLoading] = useState(false)
  const [assetsBranchId, setAssetsBranchId] = useState<number | null>(null)
  const [assetForm, setAssetForm] = useState({ asset_name: '', model: '', serial_no: '', status: 'active', notes: '' })
  const [assetEditingId, setAssetEditingId] = useState<number | null>(null)
  const [branchActivity, setBranchActivity] = useState<BranchActivityLog[]>([])
  const [branchActivityLoading, setBranchActivityLoading] = useState(false)
  const [deleteConfirmBranch, setDeleteConfirmBranch] = useState<Branch | null>(null)
  const [deleting, setDeleting] = useState(false)
  const lastErrorTimeRef = useRef(0)
  const API_BASE =
    process.env.REACT_APP_API_BASE_URL ||
    ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
      ? 'http://127.0.0.1:8000'
      : window.location.origin)

  const isSuperAdmin = user?.role === 'super_admin'

  const requestConfig = useMemo(() => {
    const headers: Record<string, string> = {}
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    return { headers }
  }, [token])

  const notifyError = (message: string) => {
    setError(message)
    const now = Date.now()
    if (now - lastErrorTimeRef.current >= 5000) {
      lastErrorTimeRef.current = now
      toast.error(message)
    }
  }

  const fetchBranches = async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      params.append('include_stats', 'true')
      params.append('active_only', showInactive ? 'false' : 'true')
      if (!isSuperAdmin && user?.branch_id) {
        params.append('branch_id', String(user.branch_id))
      }
      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim())
      }

      const res = await axios.get(`${API_BASE}/api/branches/?${params.toString()}`, requestConfig)
      setBranches(res.data || [])
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : Array.isArray(err.response.data.detail)
              ? err.response.data.detail.map((e: any) => typeof e === 'string' ? e : e.msg || JSON.stringify(e)).join(', ')
              : JSON.stringify(err.response.data.detail))
        : 'Failed to fetch branches';
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBranches()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const resetForm = () => {
    setForm(emptyForm)
    setEditingBranchId(null)
    setNewBranchCredentials(null)
  }

  const onEdit = (branch: Branch) => {
    setEditingBranchId(branch.id)
    setSelectedBranch(branch)
    setBranchDetailTab('settings')
    setForm({
      name: branch.name || '',
      location: branch.location || '',
      city: branch.city || '',
      state: branch.state || '',
      pincode: branch.pincode || '',
      phone: branch.phone || '',
      email: branch.email || '',
      address: branch.address || '',
      license_number: branch.license_number || '',
      opening_hours: branch.opening_hours || '',
      facilities: branch.facilities || '',
      modalities: (branch as any).modalities || [],
    })
    setSuccess('')
    setError('')
    setNewBranchCredentials(null)
  }

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isSuperAdmin) {
      const msg = 'Only super admin can create branches'
      setError(msg)
      notifyError(msg)
      return
    }

    const requiredFields: Array<keyof typeof form> = ['name', 'location', 'city', 'state', 'pincode', 'phone', 'address']
    const missing = requiredFields.find((field) => !String(form[field] || '').trim())
    if (missing) {
      const msg = `${missing.replace('_', ' ')} is required`
      setError(msg)
      notifyError(msg)
      return
    }

    const pincode = form.pincode.trim()
    if (!/^\d{6}$/.test(pincode)) {
      const msg = 'Pincode must be exactly 6 digits'
      setError(msg)
      notifyError(msg)
      return
    }

    const phone = form.phone.trim()
    if (!/^\d{10,15}$/.test(phone)) {
      const msg = 'Phone must be 10 to 15 digits'
      setError(msg)
      notifyError(msg)
      return
    }

    if (form.email?.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      const msg = 'Please enter a valid email address'
      setError(msg)
      notifyError(msg)
      return
    }

    setSaving(true)
    setError('')
    setSuccess('')
    setNewBranchCredentials(null)

    try {
      const payload = {
        name: form.name.trim(),
        location: form.location.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
        pincode,
        phone,
        email: form.email?.trim() || null,
        address: form.address.trim(),
        license_number: form.license_number?.trim() || null,
        opening_hours: form.opening_hours?.trim() || null,
        facilities: form.facilities?.trim() || null,
        modalities: form.modalities || [],
      }

      if (editingBranchId) {
        await axios.put(`${API_BASE}/api/branches/${editingBranchId}`, payload, requestConfig)
        setSuccess('Branch updated successfully.')
        toast.success('Branch updated successfully.')
      } else {
        const response = await axios.post<BranchCreateResponse>(`${API_BASE}/api/branches`, payload, requestConfig)
        console.log('CREATE_BRANCH_RESPONSE:', response?.data)

        let credentials =
          (response.data as any)?.branch_admin_credentials ||
          (response.data as any)?.data?.branch_admin_credentials ||
          (response.data as any)?.credentials ||
          null

        if (!credentials && (response.data as any)?.id) {
          try {
            const fallbackRes = await axios.get(
              `${API_BASE}/api/branches/${(response.data as any).id}/admin-credentials`,
              requestConfig
            )
            console.log('ADMIN_CREDENTIALS_FALLBACK_RESPONSE:', fallbackRes?.data)
            credentials =
              (fallbackRes.data as any)?.branch_admin_credentials ||
              (fallbackRes.data as any)?.data?.branch_admin_credentials ||
              (fallbackRes.data as any)?.credentials ||
              null
          } catch (fallbackErr: any) {
            console.error('Failed to fetch fallback admin credentials:', fallbackErr)
          }
        }

        console.log('EXTRACTED_CREDENTIALS:', credentials)

        if (credentials) {
          setSuccess('Branch created successfully! Branch admin credentials generated.')
          toast.success('Branch created successfully.')
          setNewBranchCredentials(credentials)
        } else {
          setSuccess('Branch created successfully.')
          toast.success('Branch created successfully.')
          notifyError('Branch created, but credentials were not returned by API.')
        }
      }

      await fetchBranches()
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail
        ? (typeof err.response.data.detail === 'string'
            ? err.response.data.detail
            : Array.isArray(err.response.data.detail)
              ? err.response.data.detail.map((e: any) => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg || JSON.stringify(e)}`).join(', ')
              : JSON.stringify(err.response.data.detail))
        : err?.message || 'Unable to save branch'
      setError(errorMsg)
      notifyError(errorMsg)
    } finally {
      setSaving(false)
    }
  }

  const onDeactivate = async (branchId: number) => {
    if (!isSuperAdmin) return
    setError('')
    setSuccess('')
    try {
      await axios.delete(`${API_BASE}/api/branches/${branchId}`, requestConfig)
      setSuccess('Branch deleted successfully.')
      toast.success('Branch deleted successfully.')
      // Immediately refresh with current filters (active_only=true by default)
      await fetchBranches()
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : 'Unable to delete branch';
      setError(errorMsg)
      notifyError(errorMsg)
    }
  }

  const onDeletePermanent = async () => {
    if (!deleteConfirmBranch || !isSuperAdmin) return
    setDeleting(true)
    setError('')
    setSuccess('')
    try {
      const response = await axios.delete(
        `${API_BASE}/api/branches/${deleteConfirmBranch.id}`,
        requestConfig
      )
      const message = response.data?.message || 'Branch deleted successfully.'
      setSuccess(message)
      toast.success(message)
      setDeleteConfirmBranch(null)
      // Immediately refresh with current filters
      await fetchBranches()
      if (selectedBranch?.id === deleteConfirmBranch.id) {
        setSelectedBranch(null)
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : 'Unable to delete branch';
      setError(errorMsg)
      notifyError(errorMsg)
    } finally {
      setDeleting(false)
    }
  }

  const onActivate = async (branchId: number) => {
    if (!isSuperAdmin) return
    setError('')
    setSuccess('')
    try {
      await axios.post(`${API_BASE}/api/branches/${branchId}/activate`, {}, requestConfig)
      setSuccess('Branch activated successfully.')
      await fetchBranches()
      if (selectedBranch?.id === branchId) {
        await onViewBranch(selectedBranch, branchDetailTab)
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : 'Unable to activate branch';
      setError(errorMsg)
    }
  }

  const onLoadStats = async (branchId: number) => {
    setStatsBranchId(branchId)
    setSelectedStats(null)
    setError('')
    try {
      const res = await axios.get(`${API_BASE}/api/branches/${branchId}/statistics`, requestConfig)
      setSelectedStats(res.data)
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : 'Unable to fetch branch statistics';
      setError(errorMsg)
    } finally {
      setStatsBranchId(null)
    }
  }

  const fetchAssets = async (branchId: number) => {
    setAssetsBranchId(branchId)
    setAssetsLoading(true)
    setError('')
    try {
      const res = await axios.get(`${API_BASE}/api/assets/?branch_id=${branchId}`, requestConfig)
      setAssets(res.data || [])
    } catch (err: any) {
      setError('Failed to load assets')
    } finally {
      setAssetsLoading(false)
    }
  }

  const fetchBranchActivity = async (branchId: number) => {
    setError('')
    setBranchActivityLoading(true)
    try {
      const res = await axios.get(`${API_BASE}/api/activity-logs/?branch_id=${branchId}`, requestConfig)
      setBranchActivity(res.data || [])
    } catch (err: any) {
      setError('Unable to load branch activity logs')
    } finally {
      setBranchActivityLoading(false)
    }
  }

  const onCreateOrUpdateAsset = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const payload = { ...assetForm, branch_id: assetsBranchId }
      if (assetEditingId) {
        await axios.put(`${API_BASE}/api/assets/${assetEditingId}`, payload, requestConfig)
      } else {
        await axios.post(`${API_BASE}/api/assets/`, payload, requestConfig)
      }
      setAssetForm({ asset_name: '', model: '', serial_no: '', status: 'active', notes: '' })
      setAssetEditingId(null)
      await fetchAssets(assetsBranchId as number)
    } catch (err: any) {
      setError('Unable to save asset')
    }
  }

  const onViewBranch = async (branch: Branch, tab: 'overview' | 'assets' | 'analytics' | 'settings' | 'activity' | 'bank-payment' = 'overview') => {
    setBranchDetailTab(tab)
    setError('')
    setNewBranchCredentials(null)
    const branchId = branch.id
    setAssetsBranchId(branchId)

    try {
      const res = await axios.get(`${API_BASE}/api/branches/${branchId}`, requestConfig)
      setSelectedBranch(res.data)
    } catch (err: any) {
      setError('Unable to load branch details')
      return
    }

    await fetchAssets(branchId)
    await onLoadStats(branchId)
    await fetchBranchActivity(branchId)
  }

  const onCloseBranchDetails = () => {
    setSelectedBranch(null)
    setBranchDetailTab('overview')
    setAssetsBranchId(null)
    setAssets([])
    setAssetEditingId(null)
    setSelectedStats(null)
  }
  const onEditAsset = (a: Asset) => {
    setAssetEditingId(a.id)
    setAssetForm({ asset_name: a.asset_name || '', model: a.model || '', serial_no: a.serial_no || '', status: a.status || 'active', notes: a.notes || '' })
  }

  const onDeleteAsset = async (id: number) => {
    if (!window.confirm('Delete this asset?')) return
    try {
      await axios.delete(`${API_BASE}/api/assets/${id}`, requestConfig)
      await fetchAssets(assetsBranchId as number)
    } catch (err: any) {
      setError('Unable to delete asset')
    }
  }

  if (!isSuperAdmin) {
    return (
      <div className="premium-card p-8">
        <h2 className="text-2xl font-black gradient-text">Branch Management</h2>
        <p className="text-slate-600 mt-3 font-medium">Only super admin can access branch management.</p>
      </div>
    )
  }

  return (
    <>
      {/* Delete Confirmation Modal */}
      {deleteConfirmBranch && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-8 relative">
            <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-red-500 via-rose-500 to-pink-500 rounded-t-3xl" />
            
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-4xl">⚠️</span>
              </div>
              <h3 className="text-2xl font-black text-slate-900 mb-2">Delete Branch?</h3>
              <p className="text-sm text-slate-600 font-medium">
                Are you sure you want to permanently delete <strong className="text-red-600">{deleteConfirmBranch.name}</strong>?
              </p>
            </div>

            <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-4 mb-6">
              <p className="text-sm text-red-800 font-semibold mb-2">⚠️ Warning:</p>
              <ul className="text-xs text-red-700 space-y-1 font-medium">
                <li>• All associated branch data will be archived/removed</li>
                <li>• Staff, customers, and inventory will be deactivated</li>
                <li>• This action cannot be undone</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setDeleteConfirmBranch(null)}
                disabled={deleting}
                className="flex-1 px-4 py-3 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={onDeletePermanent}
                disabled={deleting}
                className="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold hover:shadow-xl transition-all disabled:opacity-50 hover:-translate-y-0.5"
              >
                {deleting ? '⏳ Deleting...' : '🗑️ Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-8">
      {/* Header Section */}
      <div className="premium-card p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-red-200/30 to-orange-200/30 rounded-full blur-3xl -mr-32 -mt-32" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-purple-200/30 to-pink-200/30 rounded-full blur-3xl -ml-24 -mb-24" />
        
        <div className="relative">
          <div className="flex items-center mb-3">
            <h2 className="text-4xl font-black gradient-text">Branch Management</h2>
            <div className="ml-4 px-4 py-1.5 rounded-full bg-gradient-to-r from-red-500 to-orange-500 text-white text-xs font-bold uppercase tracking-wider shadow-lg">
              Super Admin
            </div>
          </div>
          <p className="text-lg text-slate-600 font-medium">Create, update, monitor, and control all city branches from one premium control center.</p>
        </div>

        {error && (
          <div className="mt-6 rounded-2xl bg-gradient-to-r from-red-50 to-rose-50 border-2 border-red-200 text-red-700 px-6 py-4 text-sm font-semibold shadow-lg">
            <div className="flex items-center">
              <span className="text-2xl mr-3">⚠️</span>
              {error}
            </div>
          </div>
        )}
        
        {success && (
          <div className="mt-6 rounded-2xl bg-gradient-to-r from-emerald-50 to-teal-50 border-2 border-emerald-200 text-emerald-700 px-6 py-4 text-sm font-semibold shadow-lg">
            <div className="flex items-center">
              <span className="text-2xl mr-3">✅</span>
              {success}
            </div>
          </div>
        )}
      </div>

      {/* New Branch Credentials Display */}
      {newBranchCredentials && (
        <div className="premium-card p-8 border-4 border-purple-200 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-purple-500 via-pink-500 to-red-500" />
          <div className="flex items-center mb-6">
            <span className="text-4xl mr-4">🎉</span>
            <div>
              <h3 className="text-2xl font-black gradient-text">Branch Admin Credentials Created!</h3>
              <p className="text-sm text-slate-600 font-semibold mt-1">Save these credentials securely - they won't be shown again!</p>
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 shadow-2xl">
              <p className="text-xs uppercase tracking-widest text-cyan-400 mb-3 font-bold">Login Credentials</p>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Username</p>
                  <p className="font-mono text-lg text-white font-bold">{newBranchCredentials.username}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Email</p>
                  <p className="font-mono text-sm text-white">{newBranchCredentials.email}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Password</p>
                  <p className="font-mono text-lg text-emerald-400 font-bold">{newBranchCredentials.password}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-400 mb-1">Role</p>
                  <p className="font-mono text-sm text-purple-400 uppercase font-bold">{newBranchCredentials.role}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl p-6 border-2 border-amber-200">
              <p className="text-xs uppercase tracking-widest text-amber-700 mb-3 font-bold">⚠️ Important Instructions</p>
              <ul className="space-y-2 text-sm text-slate-700 font-medium">
                <li className="flex items-start">
                  <span className="text-emerald-600 mr-2 font-bold">✓</span>
                  <span>Copy and save these credentials immediately</span>
                </li>
                <li className="flex items-start">
                  <span className="text-emerald-600 mr-2 font-bold">✓</span>
                  <span>Share securely with the branch administrator</span>
                </li>
                <li className="flex items-start">
                  <span className="text-emerald-600 mr-2 font-bold">✓</span>
                  <span>Branch admin should change password on first login</span>
                </li>
                <li className="flex items-start">
                  <span className="text-red-600 mr-2 font-bold">✗</span>
                  <span>These credentials will not be displayed again</span>
                </li>
              </ul>
              <button
                onClick={() => {
                  const text = `Branch Admin Credentials\n\nUsername: ${newBranchCredentials.username}\nEmail: ${newBranchCredentials.email}\nPassword: ${newBranchCredentials.password}\nRole: ${newBranchCredentials.role}`;
                  navigator.clipboard.writeText(text);
                  alert('Credentials copied to clipboard!');
                }}
                className="mt-4 w-full px-4 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold hover:shadow-xl transition-all hover:-translate-y-0.5"
              >
                📋 Copy Credentials
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Form */}
      <form onSubmit={onSubmit} className="premium-card p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <h3 className="text-2xl font-black gradient-text">
              {editingBranchId ? '✏️ Edit Branch' : '➕ Create New Branch'}
            </h3>
          </div>
          {editingBranchId && (
            <button 
              type="button" 
              onClick={resetForm} 
              className="px-5 py-2.5 rounded-xl bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 transition-all hover:shadow-lg"
            >
              ✕ Cancel Edit
            </button>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {Object.entries(form)
            .filter(([key]) => key !== 'modalities')
            .map(([key, value]) => (
              <div key={key} className={key === 'facilities' || key === 'address' ? 'md:col-span-2' : ''}>
                <label className="block text-sm font-black uppercase tracking-wider text-slate-700 mb-2">
                  {key.replace('_', ' ')}
                  {['name', 'location', 'city', 'state', 'pincode', 'phone', 'address'].includes(key) && (
                    <span className="text-red-500 ml-1">*</span>
                  )}
                </label>
                {key === 'facilities' || key === 'address' ? (
                  <textarea
                    value={value}
                    required={['address'].includes(key)}
                    onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                    className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm transition-all"
                    placeholder={`Enter ${key.replace('_', ' ')}`}
                    rows={3}
                  />
                ) : (
                  <input
                    value={value}
                    required={['name', 'location', 'city', 'state', 'pincode', 'phone', 'address'].includes(key)}
                    onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                    className="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm transition-all"
                    placeholder={`Enter ${key.replace('_', ' ')}`}
                  />
                )}
              </div>
            ))}
          {/* Modalities selector */}
          <div className="md:col-span-2">
            <label className="block text-sm font-black uppercase tracking-wider text-slate-700 mb-2">Modalities</label>
            <div className="flex gap-3 flex-wrap">
              {['Pathology', 'XRay', 'Sonography', 'CT', 'MRI'].map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, modalities: prev.modalities.includes(m) ? prev.modalities.filter((x: string) => x !== m) : [...prev.modalities, m] }))}
                  className={`px-4 py-2 rounded-xl text-sm font-bold ${form.modalities.includes(m) ? 'bg-purple-600 text-white' : 'bg-slate-100 text-slate-700'}`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8">
          <button
            type="submit"
            disabled={saving}
            className="px-8 py-4 rounded-xl text-white text-base font-black bg-gradient-to-r from-red-600 via-pink-600 to-purple-600 hover:shadow-2xl disabled:opacity-50 transition-all hover:-translate-y-1 uppercase tracking-wider"
          >
            {saving ? '⏳ Saving...' : editingBranchId ? '💾 Update Branch' : '🚀 Create Branch'}
          </button>
        </div>
      </form>

      {/* Branches List */}
      <div className="premium-card p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h3 className="text-2xl font-black gradient-text">🏢 All Branches</h3>
            <p className="text-sm text-slate-500 mt-1">Search, filter, and manage branch locations with instant analytics.</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative">
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && fetchBranches()}
                placeholder="Search by name, location, code..."
                className="w-full sm:w-80 rounded-2xl border-2 border-slate-200 bg-white px-4 py-3 pr-12 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 shadow-sm"
              />
              <button
                type="button"
                onClick={fetchBranches}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-purple-600 px-3 py-2 text-white shadow-lg hover:bg-purple-700 transition"
              >
                🔎
              </button>
            </div>
            <label className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={() => setShowInactive((prev) => !prev)}
                className="h-4 w-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
              />
              Show inactive branches
            </label>
            <button
              onClick={fetchBranches}
              className="rounded-2xl bg-gradient-to-r from-purple-500 to-pink-500 px-5 py-3 text-white font-bold shadow-xl hover:shadow-2xl transition-all hover:-translate-y-0.5"
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-12 h-12 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin" />
            <p className="text-slate-500 font-semibold mt-4">Loading branches...</p>
          </div>
        ) : branches.length === 0 ? (
          <div className="text-center py-12 bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl">
            <span className="text-6xl mb-4 block">🏢</span>
            <p className="text-slate-500 font-semibold">No branches found. Create your first branch!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b-2 border-purple-200">
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">Branch</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">City/State</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">Code</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">Status</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">Staff</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">Customers</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider">Revenue</th>
                  <th className="py-4 px-4 font-black text-slate-700 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr key={b.id} className="border-b border-slate-100 hover:bg-gradient-to-r hover:from-purple-50 hover:to-pink-50 transition-all">
                    <td className="py-4 px-4">
                      <div className="font-black text-slate-900 text-base">{b.name}</div>
                      <div className="text-xs text-slate-500 font-semibold mt-1">{b.location}</div>
                    </td>
                    <td className="py-4 px-4 font-semibold text-slate-700">{b.city}, {b.state}</td>
                    <td className="py-4 px-4">
                      <span className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 font-bold text-xs">
                        {b.branch_code}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`text-xs px-3 py-1.5 rounded-full font-bold ${b.is_active ? 'bg-gradient-to-r from-emerald-100 to-teal-100 text-emerald-700' : 'bg-gradient-to-r from-red-100 to-rose-100 text-red-700'}`}>
                        {b.is_active ? '✓ Active' : '✗ Inactive'}
                      </span>
                    </td>
                    <td className="py-4 px-4 font-bold text-slate-900">{b.total_staff ?? 0}</td>
                    <td className="py-4 px-4 font-bold text-slate-900">{b.total_customers ?? 0}</td>
                    <td className="py-4 px-4 font-bold text-emerald-600">₹{Number(b.monthly_revenue || 0).toLocaleString()}</td>
                    <td className="py-4 px-4">
                      <div className="flex justify-end gap-2 flex-wrap">
                        <button
                          onClick={() => {
                            if (isSuperAdmin) {
                              navigate(`/branch-details/${b.id}`)
                              return
                            }
                            onViewBranch(b, 'overview')
                          }}
                          className="px-4 py-2 rounded-lg bg-slate-500 text-white font-bold hover:bg-slate-600 transition-all hover:shadow-lg text-xs"
                        >
                          {isSuperAdmin ? '🔍 View Branch Details' : '🔍 Details'}
                        </button>
                        <button
                          onClick={() => onEdit(b)}
                          className="px-4 py-2 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 transition-all hover:shadow-lg text-xs"
                        >
                          ✏️ Edit
                        </button>
                        <button
                          onClick={() => onViewBranch(b, 'assets')}
                          className="px-4 py-2 rounded-lg bg-amber-500 text-white font-bold hover:bg-amber-600 transition-all hover:shadow-lg text-xs"
                        >
                          🛠️ Assets
                        </button>
                        <button 
                          onClick={() => onLoadStats(b.id)} 
                          className="px-4 py-2 rounded-lg bg-purple-500 text-white font-bold hover:bg-purple-600 transition-all hover:shadow-lg text-xs"
                        >
                          {statsBranchId === b.id ? '⏳' : '📊'} Stats
                        </button>
                        {b.is_active ? (
                          <button 
                            onClick={() => onDeactivate(b.id)} 
                            className="px-4 py-2 rounded-lg bg-orange-500 text-white font-bold hover:bg-orange-600 transition-all hover:shadow-lg text-xs"
                          >
                            🚫 Deactivate
                          </button>
                        ) : (
                          <button 
                            onClick={() => onActivate(b.id)} 
                            className="px-4 py-2 rounded-lg bg-emerald-500 text-white font-bold hover:bg-emerald-600 transition-all hover:shadow-lg text-xs"
                          >
                            ✅ Activate
                          </button>
                        )}
                        <button 
                          onClick={() => setDeleteConfirmBranch(b)}
                          title="Permanently remove this branch"
                          className="px-4 py-2 rounded-lg bg-red-600 text-white font-bold hover:bg-red-700 transition-all hover:shadow-lg text-xs"
                        >
                          🗑️ Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Branch Statistics */}
      {selectedStats && !selectedBranch && (
        <div className="premium-card p-8">
          <h3 className="text-2xl font-black gradient-text mb-6">📊 Branch Statistics • {selectedStats.branch_name}</h3>
          <div className="grid md:grid-cols-4 gap-6">
            {[
              { label: 'Total Staff', value: selectedStats.total_staff, icon: '👨‍⚕️', gradient: 'from-blue-500 to-cyan-500' },
              { label: 'Total Customers', value: selectedStats.total_customers, icon: '👥', gradient: 'from-emerald-500 to-teal-500' },
              { label: 'Monthly Revenue', value: `₹${Number(selectedStats.monthly_revenue || 0).toLocaleString()}`, icon: '💰', gradient: 'from-amber-500 to-orange-500' },
              { label: 'Appointments', value: selectedStats.total_appointments, icon: '📅', gradient: 'from-purple-500 to-pink-500' },
              { label: 'Pending Payments', value: `₹${Number(selectedStats.pending_payments || 0).toLocaleString()}`, icon: '⏳', gradient: 'from-red-500 to-rose-500' },
              { label: 'Inventory Value', value: `₹${Number(selectedStats.inventory_value || 0).toLocaleString()}`, icon: '📦', gradient: 'from-indigo-500 to-purple-500' },
              { label: 'Active Services', value: selectedStats.active_services, icon: '🔧', gradient: 'from-pink-500 to-rose-500' },
            ].map((stat, index) => (
              <div key={index} className="stats-card">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg mb-4`}>
                  <span className="text-2xl">{stat.icon}</span>
                </div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">{stat.label}</p>
                <p className="text-2xl font-black text-slate-900">{stat.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {selectedBranch && (
        <div className="space-y-8">
          <div className="premium-card p-8">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
              <div>
                <h3 className="text-3xl font-black gradient-text">{selectedBranch.name}</h3>
                <p className="text-sm text-slate-500">{selectedBranch.location} • {selectedBranch.city}, {selectedBranch.state}</p>
                <p className="mt-2 text-xs uppercase tracking-widest text-slate-400 font-bold">Branch ID: {selectedBranch.id}</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => onEdit(selectedBranch)}
                  className="rounded-2xl bg-blue-600 px-5 py-3 text-white font-bold shadow-xl hover:bg-blue-700 transition"
                >
                  ✏️ Edit Branch
                </button>
                <button
                  onClick={onCloseBranchDetails}
                  className="rounded-2xl bg-slate-100 px-5 py-3 font-bold text-slate-800 hover:bg-slate-200 transition"
                >
                  ← Back to Branches
                </button>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-3xl bg-slate-50 p-6 shadow-sm border border-slate-100">
                <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Branch Code</p>
                <p className="font-black text-xl text-slate-900">{selectedBranch.branch_code}</p>
                <p className="text-sm text-slate-500 mt-2">Created: {new Date(selectedBranch.created_at).toLocaleDateString()}</p>
              </div>
              <div className="rounded-3xl bg-slate-50 p-6 shadow-sm border border-slate-100">
                <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Status</p>
                <span className={`inline-flex items-center px-3 py-2 rounded-full text-xs font-bold ${selectedBranch.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>{selectedBranch.is_active ? 'Active' : 'Inactive'}</span>
                <p className="text-sm text-slate-500 mt-2">Last updated: {selectedBranch.updated_at ? new Date(selectedBranch.updated_at).toLocaleDateString() : '—'}</p>
              </div>
              <div className="rounded-3xl bg-slate-50 p-6 shadow-sm border border-slate-100">
                <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Modalities</p>
                <div className="flex flex-wrap gap-2">
                  {(selectedBranch.modalities || []).length > 0 ? (
                    (selectedBranch.modalities || []).map((modality) => (
                      <span key={modality} className="px-3 py-2 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold">{modality}</span>
                    ))
                  ) : (
                    <span className="text-sm text-slate-500">No modalities set</span>
                  )}
                </div>
              </div>
            </div>
          </div>
          <div className="premium-card p-6">
            <div className="flex flex-wrap gap-3">
              {[
                'overview',
                'assets',
                'analytics',
                'settings',
                'activity',
                ...(isSuperAdmin ? ['bank-payment'] : []),
              ].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setBranchDetailTab(tab as any)}
                  className={`px-4 py-3 rounded-2xl font-bold text-sm ${branchDetailTab === tab ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
                >
                  {tab === 'bank-payment' ? 'Bank & Payment Settings' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>
          </div>
          {isSuperAdmin && branchDetailTab === 'bank-payment' && (
            <BankPaymentSettings
              branchId={selectedBranch.id}
              apiBase={API_BASE}
              requestConfig={requestConfig}
            />
          )}
          {branchDetailTab === 'overview' && (
            <BranchDirectorOverviewDashboard
              branchId={selectedBranch.id}
              showBackButton={false}
            />
          )}
          {branchDetailTab === 'assets' && (
            <div className="space-y-6">
              <div className="premium-card p-8">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h4 className="text-2xl font-black gradient-text">Asset Management</h4>
                    <p className="text-sm text-slate-500">Track equipment, maintenance status, and branch hardware inventory.</p>
                  </div>
                </div>
                <form onSubmit={onCreateOrUpdateAsset} className="grid gap-4 md:grid-cols-4 mb-6">
                  <input value={assetForm.asset_name} onChange={(e) => setAssetForm((p) => ({ ...p, asset_name: e.target.value }))} placeholder="Asset name" className="px-4 py-3 rounded-xl border-2 border-slate-200" required />
                  <input value={assetForm.model} onChange={(e) => setAssetForm((p) => ({ ...p, model: e.target.value }))} placeholder="Model" className="px-4 py-3 rounded-xl border-2 border-slate-200" />
                  <input value={assetForm.serial_no} onChange={(e) => setAssetForm((p) => ({ ...p, serial_no: e.target.value }))} placeholder="Serial No" className="px-4 py-3 rounded-xl border-2 border-slate-200" />
                  <select value={assetForm.status} onChange={(e) => setAssetForm((p) => ({ ...p, status: e.target.value }))} className="px-4 py-3 rounded-xl border-2 border-slate-200">
                    <option value="active">Active</option>
                    <option value="under_repair">Under Repair</option>
                    <option value="retired">Retired</option>
                  </select>
                  <textarea value={assetForm.notes} onChange={(e) => setAssetForm((p) => ({ ...p, notes: e.target.value }))} placeholder="Notes" className="md:col-span-4 rounded-xl border-2 border-slate-200 px-4 py-3" rows={2} />
                  <button type="submit" className="md:col-span-1 px-5 py-3 rounded-2xl bg-purple-600 text-white font-black hover:bg-purple-700 transition">{assetEditingId ? 'Update asset' : 'Add asset'}</button>
                </form>
                {assetsLoading ? (
                  <div className="text-center py-8">Loading assets…</div>
                ) : assets.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">No assets found yet for this branch.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left border-b-2 border-slate-200">
                          <th className="py-3 px-3 font-black">Asset</th>
                          <th className="py-3 px-3 font-black">Model</th>
                          <th className="py-3 px-3 font-black">Serial</th>
                          <th className="py-3 px-3 font-black">Status</th>
                          <th className="py-3 px-3 font-black">Added</th>
                          <th className="py-3 px-3 font-black text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {assets.map((a) => (
                          <tr key={a.id} className="border-b hover:bg-slate-50 transition">
                            <td className="py-3 px-3 font-semibold">{a.asset_name}</td>
                            <td className="py-3 px-3">{a.model || '—'}</td>
                            <td className="py-3 px-3">{a.serial_no || '—'}</td>
                            <td className="py-3 px-3">{a.status}</td>
                            <td className="py-3 px-3">{new Date(a.created_at).toLocaleDateString()}</td>
                            <td className="py-3 px-3 text-right">
                              <div className="inline-flex gap-2">
                                <button type="button" onClick={() => onEditAsset(a)} className="px-3 py-2 rounded-xl bg-blue-500 text-white text-xs">Edit</button>
                                <button type="button" onClick={() => onDeleteAsset(a.id)} className="px-3 py-2 rounded-xl bg-red-500 text-white text-xs">Delete</button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
          {branchDetailTab === 'analytics' && selectedStats && (
            <div className="space-y-6">
              <div className="premium-card p-8">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h4 className="text-2xl font-black gradient-text mb-2">Branch Analytics</h4>
                    <p className="text-sm text-slate-500">Deep dive into performance, cash flow and service activity.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onLoadStats(selectedBranch.id)}
                    className="rounded-2xl bg-slate-900 px-4 py-3 text-white font-bold hover:bg-slate-800 transition"
                  >
                    🔄 Refresh Analytics
                  </button>
                </div>
                <div className="grid gap-4 md:grid-cols-4 mt-6">
                  {[
                    { label: 'Revenue', value: `₹${Number(selectedStats.monthly_revenue || 0).toLocaleString()}`, accent: 'from-emerald-500 to-teal-500' },
                    { label: 'Appointments', value: selectedStats.total_appointments, accent: 'from-purple-500 to-fuchsia-500' },
                    { label: 'Pending Payments', value: `₹${Number(selectedStats.pending_payments || 0).toLocaleString()}`, accent: 'from-amber-500 to-orange-500' },
                    { label: 'Inventory Value', value: `₹${Number(selectedStats.inventory_value || 0).toLocaleString()}`, accent: 'from-slate-500 to-slate-700' },
                  ].map((item) => (
                    <div key={item.label} className="rounded-3xl p-6 shadow-sm bg-white border border-slate-200">
                      <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">{item.label}</p>
                      <div className="text-2xl font-black text-slate-900">{item.value}</div>
                      <div className={`mt-4 h-2 rounded-full bg-gradient-to-r ${item.accent}`} />
                    </div>
                  ))}
                </div>
                <div className="grid gap-4 md:grid-cols-3 mt-6">
                  {[
                    { label: 'Staff', value: selectedStats.total_staff, emoji: '👨‍⚕️' },
                    { label: 'Customers', value: selectedStats.total_customers, emoji: '👥' },
                    { label: 'Services', value: selectedStats.active_services, emoji: '🔧' },
                  ].map((item) => (
                    <div key={item.label} className="rounded-3xl bg-slate-50 p-6 shadow-sm">
                      <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">{item.emoji} {item.label}</p>
                      <p className="text-3xl font-black text-slate-900">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {branchDetailTab === 'analytics' && !selectedStats && (
            <div className="premium-card p-8 text-slate-500">Loading analytics…</div>
          )}
          {branchDetailTab === 'activity' && (
            <div className="premium-card p-8">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-4">
                <div>
                  <h4 className="text-2xl font-black gradient-text">Branch Activity Timeline</h4>
                  <p className="text-sm text-slate-500">Audit trail for branch operations and administrative changes.</p>
                </div>
                <button
                  type="button"
                  onClick={() => selectedBranch && fetchBranchActivity(selectedBranch.id)}
                  className="rounded-2xl bg-slate-900 px-4 py-3 text-white font-bold hover:bg-slate-800 transition"
                >
                  {branchActivityLoading ? 'Refreshing…' : 'Refresh Activity'}
                </button>
              </div>
              {branchActivityLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-12 h-12 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin" />
                  <p className="text-slate-500 font-semibold mt-4">Loading activity...</p>
                </div>
              ) : branchActivity.length === 0 ? (
                <div className="rounded-3xl bg-slate-50 p-8 text-slate-500">No recent activity found for this branch.</div>
              ) : (
                <div className="space-y-4">
                  {branchActivity.map((log) => (
                    <div key={log.id} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <div>
                          <p className="text-sm text-slate-500 uppercase tracking-wider font-bold">{log.action.replace(/_/g, ' ')}</p>
                          <p className="text-base font-black text-slate-900">{log.description}</p>
                        </div>
                        <p className="text-xs text-slate-400">{new Date(log.timestamp).toLocaleString()}</p>
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm text-slate-600">
                        <div><span className="font-semibold">Entity</span>: {log.entity_type} #{log.entity_id ?? '—'}</div>
                        <div><span className="font-semibold">User</span>: {log.username || log.user_id}</div>
                        <div><span className="font-semibold">Source</span>: {log.ip_address || 'unknown'}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {branchDetailTab === 'settings' && (
            <div className="space-y-6">
              <div className="premium-card p-8">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
                  <div>
                    <h4 className="text-2xl font-black gradient-text mb-2">Branch Settings</h4>
                    <p className="text-sm text-slate-500">Quickly manage branch meta information and workflow settings.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setEditingBranchId(selectedBranch.id)}
                    className="rounded-2xl bg-blue-600 px-5 py-3 text-white font-bold hover:bg-blue-700 transition"
                  >
                    ✏️ Edit branch details
                  </button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-3xl bg-slate-50 p-6 shadow-sm">
                    <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Branch License</p>
                    <p className="text-sm text-slate-700">{selectedBranch.license_number || 'Not configured'}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-50 p-6 shadow-sm">
                    <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Pincode</p>
                    <p className="text-sm text-slate-700">{selectedBranch.pincode}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-50 p-6 shadow-sm">
                    <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Location</p>
                    <p className="text-sm text-slate-700">{selectedBranch.location}</p>
                  </div>
                  <div className="rounded-3xl bg-slate-50 p-6 shadow-sm">
                    <p className="text-xs uppercase tracking-widest text-slate-400 font-bold mb-3">Branch Code</p>
                    <p className="text-sm text-slate-700">{selectedBranch.branch_code}</p>
                  </div>
                </div>
              </div>
              <div className="premium-card p-8 rounded-3xl bg-gradient-to-br from-slate-950 to-slate-900 text-white shadow-2xl">
                <h5 className="text-xl font-black mb-4">Branch health score</h5>
                <div className="space-y-4">
                  {[
                    { label: 'Monthly Revenue', value: selectedBranch.monthly_revenue || 0, max: 500000, accent: 'bg-emerald-500' },
                    { label: 'Active Staff', value: selectedBranch.total_staff || 0, max: 50, accent: 'bg-sky-500' },
                    { label: 'Active Customers', value: selectedBranch.total_customers || 0, max: 2000, accent: 'bg-fuchsia-500' },
                  ].map((item) => {
                    const ratio = Math.min(100, Math.round((item.value / item.max) * 100))
                    return (
                      <div key={item.label}>
                        <div className="flex justify-between text-sm font-semibold text-slate-200 mb-2">
                          <span>{item.label}</span>
                          <span>{item.value.toLocaleString()}</span>
                        </div>
                        <div className="h-3 rounded-full bg-slate-800 overflow-hidden">
                          <div className={`${item.accent} h-full rounded-full`} style={{ width: `${ratio}%` }} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      </div>
    </>
  )
}
