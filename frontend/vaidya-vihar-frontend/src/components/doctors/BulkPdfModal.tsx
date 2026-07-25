import { useState } from 'react'

import { DoctorItem, ShareResultItem } from './types'

type Props = {
  open: boolean
  selectedDoctors: DoctorItem[]
  onClose: () => void
  onSend: (files: File[]) => Promise<ShareResultItem[]>
}

export default function BulkPdfModal({ open, selectedDoctors, onClose, onSend }: Props) {
  const [files, setFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [results, setResults] = useState<ShareResultItem[]>([])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[110] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-3xl rounded-2xl shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h3 className="text-2xl font-black text-slate-900">Send Bulk PDF</h3>
          <p className="text-slate-500 mt-1">Selected doctors: {selectedDoctors.length}</p>
        </div>

        <div className="p-6 space-y-4">
          <div className="rounded-xl border border-dashed p-4">
            <label className="text-sm font-semibold text-slate-700">Upload ZIP or Multiple PDFs</label>
            <input
              type="file"
              multiple
              accept=".pdf,.zip"
              className="mt-2 block w-full"
              onChange={e => {
                const selected = e.target.files ? Array.from(e.target.files) : []
                setFiles(selected)
              }}
            />
            <p className="text-xs text-slate-500 mt-2">Files selected: {files.length}</p>
          </div>

          <div className="rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
            <p className="font-semibold">Message Template</p>
            <p className="mt-1">Dear Dr. [Name], Please find attached patient reports and referral updates from VaidyaVihar Diagnostic.</p>
          </div>

          <div className="flex justify-end gap-3">
            <button className="px-4 py-2 rounded-lg border" onClick={onClose}>Close</button>
            <button
              disabled={submitting || files.length === 0 || selectedDoctors.length === 0}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white font-bold disabled:opacity-50"
              onClick={async () => {
                setSubmitting(true)
                try {
                  const response = await onSend(files)
                  setResults(response)
                } finally {
                  setSubmitting(false)
                }
              }}
            >
              {submitting ? 'Generating...' : 'Generate WhatsApp/Email Links'}
            </button>
          </div>

          {results.length > 0 && (
            <div className="space-y-3">
              <h4 className="font-black text-slate-800">Generated Links</h4>
              {results.map(item => (
                <div key={item.doctor_id} className="border rounded-xl p-3">
                  <p className="font-semibold text-slate-800">{item.doctor_name}</p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {item.email_link && (
                      <a href={item.email_link} target="_blank" rel="noreferrer" className="px-3 py-1 rounded bg-indigo-600 text-white text-xs">
                        Open Email
                      </a>
                    )}
                    {item.whatsapp_link && (
                      <a href={item.whatsapp_link} target="_blank" rel="noreferrer" className="px-3 py-1 rounded bg-emerald-600 text-white text-xs">
                        Open WhatsApp
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
