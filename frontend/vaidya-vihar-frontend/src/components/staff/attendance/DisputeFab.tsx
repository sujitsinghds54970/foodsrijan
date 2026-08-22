import { useState } from 'react'

interface DisputeFabProps {
  onSubmit: (payload: { attendance_date: string; reason: string }) => Promise<void>
}

export default function DisputeFab({ onSubmit }: DisputeFabProps) {
  const [open, setOpen] = useState(false)
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [presetReason, setPresetReason] = useState('Wrong late mark')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)

  const submit = async () => {
    if (!description.trim()) return
    setSaving(true)
    try {
      await onSubmit({ attendance_date: date, reason: `${presetReason}: ${description.trim()}` })
      setDescription('')
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-rose-600 px-5 py-3 text-sm font-bold text-white shadow-xl hover:bg-rose-700"
      >
        Fix My Attendance
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-5 dark:bg-slate-900">
            <h4 className="text-lg font-bold text-slate-900 dark:text-slate-100">Order an Attendance Issue</h4>
            <div className="mt-3 space-y-3">
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800" />
              <select value={presetReason} onChange={(e) => setPresetReason(e.target.value)} className="w-full rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800">
                <option>Wrong late mark</option>
                <option>Missed day</option>
                <option>Other</option>
              </select>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full rounded-lg border px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
                placeholder="Describe what happened"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setOpen(false)} className="rounded-md border px-3 py-2 text-sm dark:border-slate-700">Close</button>
              <button onClick={submit} disabled={saving} className="rounded-md bg-rose-600 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-60">
                {saving ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
