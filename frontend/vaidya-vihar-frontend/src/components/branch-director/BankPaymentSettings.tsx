import { useEffect, useState } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

interface BranchBankDetailsForm {
  bank_name: string
  account_holder_name: string
  account_number: string
  ifsc_code: string
  upi_id: string
  soundbox_config_text: string
}

interface BankPaymentSettingsProps {
  branchId: number
  apiBase: string
  requestConfig: { headers: Record<string, string> }
}

const initialForm: BranchBankDetailsForm = {
  bank_name: '',
  account_holder_name: '',
  account_number: '',
  ifsc_code: '',
  upi_id: '',
  soundbox_config_text: '{\n  "provider": "",\n  "device_id": "",\n  "webhook": ""\n}',
}

export default function BankPaymentSettings({ branchId, apiBase, requestConfig }: BankPaymentSettingsProps) {
  const [form, setForm] = useState<BranchBankDetailsForm>(initialForm)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [isConfigured, setIsConfigured] = useState(false)

  useEffect(() => {
    const loadBankDetails = async () => {
      if (!branchId) return
      setLoading(true)
      try {
        const res = await axios.get(`${apiBase}/api/branches/${branchId}/bank-details`, requestConfig)
        const payload = res.data || {}
        const hasData = !!payload?.id

        if (!hasData) {
          setIsConfigured(false)
          setForm(initialForm)
          return
        }

        setIsConfigured(true)
        setForm({
          bank_name: payload.bank_name || '',
          account_holder_name: payload.account_holder_name || '',
          account_number: payload.account_number || '',
          ifsc_code: payload.ifsc_code || '',
          upi_id: payload.upi_id || '',
          soundbox_config_text: JSON.stringify(payload.soundbox_config || {}, null, 2),
        })
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || 'Failed to load bank details')
      } finally {
        setLoading(false)
      }
    }

    loadBankDetails()
  }, [branchId, apiBase, requestConfig])

  const updateField = (field: keyof BranchBankDetailsForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const validateForm = () => {
    if (!form.bank_name.trim()) return 'Bank name is required'
    if (!form.account_holder_name.trim()) return 'Account holder name is required'
    if (!form.account_number.trim()) return 'Account number is required'
    if (!form.ifsc_code.trim()) return 'IFSC code is required'
    if (!form.upi_id.trim()) return 'UPI ID is required'
    if (form.ifsc_code.trim().length !== 11) return 'IFSC code must be exactly 11 characters'
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validateForm()
    if (validationError) {
      toast.error(validationError)
      return
    }

    let parsedSoundbox: Record<string, any> | null = null
    if (form.soundbox_config_text.trim()) {
      try {
        parsedSoundbox = JSON.parse(form.soundbox_config_text)
      } catch {
        toast.error('Soundbox Config must be valid JSON')
        return
      }
    }

    const payload = {
      bank_name: form.bank_name.trim(),
      account_holder_name: form.account_holder_name.trim(),
      account_number: form.account_number.trim(),
      ifsc_code: form.ifsc_code.trim().toUpperCase(),
      upi_id: form.upi_id.trim(),
      soundbox_config: parsedSoundbox,
      is_active: true,
    }

    setSaving(true)
    try {
      await axios.post(`${apiBase}/api/branches/${branchId}/bank-details`, payload, requestConfig)
      setIsConfigured(true)
      toast.success('Bank & payment settings saved successfully')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save bank details')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="premium-card p-8 text-slate-600">Loading bank and payment settings...</div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="premium-card p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h4 className="text-2xl font-black gradient-text">Bank & Payment Settings</h4>
            <p className="text-sm text-slate-500 mt-1">Configure branch bank account, UPI ID, and soundbox integration JSON.</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-bold ${isConfigured ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
            {isConfigured ? 'Configured' : 'Not Configured'}
          </span>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Bank Name</label>
            <input
              value={form.bank_name}
              onChange={(e) => updateField('bank_name', e.target.value)}
              placeholder="e.g. HDFC Bank"
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-emerald-500 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Account Holder Name</label>
            <input
              value={form.account_holder_name}
              onChange={(e) => updateField('account_holder_name', e.target.value)}
              placeholder="Name as per bank account"
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-emerald-500 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Account Number</label>
            <input
              value={form.account_number}
              onChange={(e) => updateField('account_number', e.target.value)}
              placeholder="Bank account number"
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-emerald-500 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">IFSC Code</label>
            <input
              value={form.ifsc_code}
              onChange={(e) => updateField('ifsc_code', e.target.value.toUpperCase())}
              placeholder="e.g. HDFC0001234"
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-emerald-500 outline-none"
              required
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">UPI ID</label>
            <input
              value={form.upi_id}
              onChange={(e) => updateField('upi_id', e.target.value)}
              placeholder="e.g. branchname@okhdfcbank"
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-emerald-500 outline-none"
              required
            />
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Soundbox Config (JSON)</label>
            <textarea
              value={form.soundbox_config_text}
              onChange={(e) => updateField('soundbox_config_text', e.target.value)}
              rows={7}
              className="w-full px-4 py-3 rounded-xl border-2 border-slate-200 focus:border-emerald-500 outline-none font-mono text-sm"
              placeholder='{"provider":"HDFC","device_id":"...","webhook":"https://..."}'
            />
          </div>

          <div className="md:col-span-2 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-3 rounded-2xl bg-gradient-to-r from-emerald-600 to-green-600 text-white font-bold hover:shadow-xl transition disabled:opacity-60"
            >
              {saving ? 'Saving...' : 'Save Bank & Payment Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
