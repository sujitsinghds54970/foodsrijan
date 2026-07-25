import { LinkedDeviceItem } from '../types'

interface LinkedDevicesCardProps {
  devices: LinkedDeviceItem[]
  onResetToken: () => void
}

const formatDateTime = (value?: string | null) => {
  if (!value) return '-'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? '-' : d.toLocaleString()
}

export default function LinkedDevicesCard({ devices, onResetToken }: LinkedDevicesCardProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Linked Devices & Credentials</h3>
        <button
          onClick={onResetToken}
          className="rounded-md bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-900 dark:bg-slate-100 dark:text-slate-900"
        >
          Reset Device Token
        </button>
      </div>

      {devices.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-300">No linked devices found.</p>
      ) : (
        <div className="space-y-2">
          {devices.map((device) => (
            <div key={device.id} className="rounded-lg border border-slate-100 p-3 dark:border-slate-800">
              <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{device.device_type}: {device.device_id}</p>
              <p className="text-xs text-slate-600 dark:text-slate-300">Last sync: {formatDateTime(device.last_sync)}</p>
              <p className="text-xs">
                <span className={`rounded-full px-2 py-0.5 ${device.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200' : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-100'}`}>
                  {device.is_active ? 'Active' : 'Inactive'}
                </span>
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
