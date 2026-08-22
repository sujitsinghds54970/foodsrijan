import { useEffect } from 'react'
import { useForm } from 'react-hook-form'

import { StaffItem } from './types'

export type StaffFormValues = {
  full_name: string
  mobile: string
  email?: string
  address?: string
  city?: string
  specialization?: string
  degree?: string
  hospital_clinic_affiliation?: string
  years_of_experience?: number
  bank_account_number?: string
  ifsc_code?: string
  upi_id?: string
  commission_percentage: number
  latitude?: number
  longitude?: number
  portal_username?: string
  portal_password?: string
}

type Props = {
  open: boolean
  initialStaff: StaffItem | null
  onClose: () => void
  onSubmit: (values: StaffFormValues) => Promise<void>
}

const defaultValues: StaffFormValues = {
  full_name: '',
  mobile: '',
  email: '',
  address: '',
  city: '',
  specialization: '',
  degree: '',
  hospital_clinic_affiliation: '',
  years_of_experience: undefined,
  bank_account_number: '',
  ifsc_code: '',
  upi_id: '',
  commission_percentage: 0,
  latitude: undefined,
  longitude: undefined,
  portal_username: '',
  portal_password: '',
}

export default function StaffFormModal({ open, initialStaff, onClose, onSubmit }: Props) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<StaffFormValues>({ defaultValues })

  useEffect(() => {
    if (!open) return
    if (!initialStaff) {
      reset(defaultValues)
      return
    }

    reset({
      full_name: initialStaff.full_name || '',
      mobile: initialStaff.mobile || '',
      email: initialStaff.email || '',
      address: initialStaff.address || '',
      city: initialStaff.city || '',
      specialization: initialStaff.specialization || '',
      degree: initialStaff.degree || '',
      hospital_clinic_affiliation: initialStaff.hospital_clinic_affiliation || '',
      years_of_experience: initialStaff.years_of_experience,
      bank_account_number: initialStaff.bank_account_number || '',
      ifsc_code: initialStaff.ifsc_code || '',
      upi_id: initialStaff.upi_id || '',
      commission_percentage: initialStaff.commission_percentage || 0,
      latitude: initialStaff.latitude,
      longitude: initialStaff.longitude,
      portal_username: initialStaff.portal_username || '',
      portal_password: '',
    })
  }, [open, initialStaff, reset])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[110] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b sticky top-0 bg-white">
          <h3 className="text-2xl font-black text-slate-900">{initialStaff ? 'Edit Staff' : 'Add Referring Staff'}</h3>
        </div>

        <form
          onSubmit={handleSubmit(async values => {
            await onSubmit(values)
            onClose()
          })}
          className="p-6 space-y-8"
        >
          <section>
            <h4 className="text-lg font-black text-slate-800 mb-3">Personal</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input className="px-3 py-2 rounded-lg border" placeholder="Full Name" {...register('full_name', { required: true })} />
              <input className="px-3 py-2 rounded-lg border" placeholder="Mobile" {...register('mobile', { required: true })} />
              <input className="px-3 py-2 rounded-lg border" placeholder="Email" {...register('email')} />
              <input className="px-3 py-2 rounded-lg border" placeholder="City" {...register('city')} />
              <textarea className="px-3 py-2 rounded-lg border md:col-span-2" placeholder="Address" {...register('address')} />
            </div>
          </section>

          <section>
            <h4 className="text-lg font-black text-slate-800 mb-3">Professional</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input className="px-3 py-2 rounded-lg border" placeholder="Specialization" {...register('specialization')} />
              <input className="px-3 py-2 rounded-lg border" placeholder="Degree" {...register('degree')} />
              <input className="px-3 py-2 rounded-lg border" placeholder="Hospital/Clinic Affiliation" {...register('hospital_clinic_affiliation')} />
              <input className="px-3 py-2 rounded-lg border" type="number" placeholder="Years of Experience" {...register('years_of_experience', { valueAsNumber: true })} />
            </div>
          </section>

          <section>
            <h4 className="text-lg font-black text-slate-800 mb-3">Financial</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input className="px-3 py-2 rounded-lg border" placeholder="Bank Account Number" {...register('bank_account_number')} />
              <input className="px-3 py-2 rounded-lg border" placeholder="IFSC Code" {...register('ifsc_code')} />
              <input className="px-3 py-2 rounded-lg border" placeholder="UPI ID" {...register('upi_id')} />
              <input className="px-3 py-2 rounded-lg border" type="number" step="0.01" placeholder="Commission %" {...register('commission_percentage', { valueAsNumber: true })} />
            </div>
          </section>

          <section>
            <h4 className="text-lg font-black text-slate-800 mb-3">Geo Mapping</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input className="px-3 py-2 rounded-lg border" type="number" step="0.000001" placeholder="Latitude" {...register('latitude', { valueAsNumber: true })} />
              <input className="px-3 py-2 rounded-lg border" type="number" step="0.000001" placeholder="Longitude" {...register('longitude', { valueAsNumber: true })} />
            </div>
          </section>

          <section>
            <h4 className="text-lg font-black text-slate-800 mb-3">Staff Self-Service (Optional)</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input className="px-3 py-2 rounded-lg border" placeholder="Portal Username" {...register('portal_username')} />
              <input className="px-3 py-2 rounded-lg border" type="password" placeholder="Portal Password" {...register('portal_password')} />
            </div>
          </section>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700">Cancel</button>
            <button disabled={isSubmitting} className="px-4 py-2 rounded-lg bg-blue-600 text-white font-bold">
              {isSubmitting ? 'Saving...' : initialStaff ? 'Save Changes' : 'Create Staff'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
