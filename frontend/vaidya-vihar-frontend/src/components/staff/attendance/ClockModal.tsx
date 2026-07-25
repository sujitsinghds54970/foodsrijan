import { useRef, useState } from 'react'
import Webcam from 'react-webcam'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'

interface ClockModalProps {
  open: boolean
  action: 'in' | 'out'
  location: { lat?: number; lng?: number }
  onClose: () => void
  onConfirm: (payload: { selfie?: File; workMode: 'onsite' | 'work_from_home'; wfhReason?: string }) => Promise<void>
}

export default function ClockModal({ open, action, location, onClose, onConfirm }: ClockModalProps) {
  const webcamRef = useRef<Webcam>(null)
  const [preview, setPreview] = useState<string>('')
  const [file, setFile] = useState<File | undefined>(undefined)
  const [workMode, setWorkMode] = useState<'onsite' | 'work_from_home'>('onsite')
  const [wfhReason, setWfhReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [capturing, setCapturing] = useState(false)

  const supportedTypes = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp'])

  const captureSelfieFromWebcam = async (): Promise<File | null> => {
    const image = webcamRef.current?.getScreenshot()
    if (!image) return null
    setPreview(image)
    setCapturing(true)
    try {
      const blob = await fetch(image).then((res) => res.blob())
      const captured = new File([blob], `selfie-${Date.now()}.jpg`, { type: 'image/jpeg' })
      setFile(captured)
      return captured
    } catch {
      toast.error('Unable to capture selfie. Please retry.')
      setFile(undefined)
      return null
    } finally {
      setCapturing(false)
    }
  }

  const dropzone = useDropzone({
    multiple: false,
    accept: { 'image/jpeg': [], 'image/png': [], 'image/webp': [] },
    onDrop: (accepted) => {
      const picked = accepted[0]
      if (!picked) return
      if (!supportedTypes.has((picked.type || '').toLowerCase())) {
        toast.error('Please upload JPG, PNG, or WEBP image only')
        return
      }
      setFile(picked)
      setPreview(URL.createObjectURL(picked))
    },
  })

  const submit = async () => {
    if (capturing) {
      toast.error('Please wait for selfie capture to complete')
      return
    }

    let selfieFile = file
    if (!selfieFile) {
      selfieFile = await captureSelfieFromWebcam() || undefined
    }

    setSaving(true)
    try {
      await onConfirm({ selfie: selfieFile, workMode, wfhReason: wfhReason || undefined })
      onClose()
      setPreview('')
      setFile(undefined)
      setWfhReason('')
      setWorkMode('onsite')
    } catch {
      // The parent already shows a detailed API error toast; keep modal open for correction.
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white p-5 dark:bg-slate-900">
        <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Confirm Clock {action === 'in' ? 'In' : 'Out'}</h3>
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
          Location: {location.lat?.toFixed(5) || '-'}, {location.lng?.toFixed(5) || '-'}
        </p>

        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border p-2 dark:border-slate-700">
            <Webcam ref={webcamRef} screenshotFormat="image/jpeg" className="h-40 w-full rounded-lg object-cover" />
            <button onClick={() => void captureSelfieFromWebcam()} disabled={capturing} className="mt-2 w-full rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900">
              {capturing ? 'Capturing...' : 'Capture from Webcam'}
            </button>
          </div>
          <div>
            <div {...dropzone.getRootProps()} className="h-40 cursor-pointer rounded-xl border border-dashed border-slate-300 p-2 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-300">
              <input {...dropzone.getInputProps()} />
              {preview ? <img src={preview} alt="Selfie preview" className="h-full w-full rounded-lg object-cover" /> : 'Drop or click to upload selfie'}
            </div>
          </div>
        </div>

        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-3 text-sm">
            <label className="font-semibold text-slate-700 dark:text-slate-200">Work Mode:</label>
            <select value={workMode} onChange={(e) => setWorkMode(e.target.value as 'onsite' | 'work_from_home')} className="rounded border px-2 py-1 dark:border-slate-700 dark:bg-slate-800">
              <option value="onsite">Onsite</option>
              <option value="work_from_home">Work from Home</option>
            </select>
          </div>
          {workMode === 'work_from_home' && (
            <input
              value={wfhReason}
              onChange={(e) => setWfhReason(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              placeholder="WFH reason"
            />
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border px-3 py-2 text-sm dark:border-slate-700">Cancel</button>
          <button onClick={() => void submit()} disabled={saving || capturing} className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
            {saving ? 'Submitting...' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  )
}
