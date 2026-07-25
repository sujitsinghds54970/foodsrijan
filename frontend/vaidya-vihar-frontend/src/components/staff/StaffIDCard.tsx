import { useMemo, useRef } from 'react'
import QRCode from 'react-qr-code'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { resolveStaffMediaUrl } from './api'
import { StaffDetail } from './types'

interface StaffIDCardProps {
  staff: StaffDetail
  branchName?: string
  downloadButtonLabel?: string
}

const CR80_CARD_WIDTH_MM = 85.6
const CR80_CARD_HEIGHT_MM = 54
const CR80_SAFE_MARGIN_MM = 3

export default function StaffIDCard({ staff, branchName, downloadButtonLabel = 'Download PDF' }: StaffIDCardProps) {
  const frontRef = useRef<HTMLDivElement>(null)
  const backRef = useRef<HTMLDivElement>(null)
  const basePhotoUrl = useMemo(
    () => resolveStaffMediaUrl((staff as any).photo_url || (staff as any).photo_path || (staff as any).profile_photo_url || (staff as any).profile_photo_path),
    [staff],
  )
  const photoUrl = useMemo(() => {
    if (!basePhotoUrl) return ''
    const version = encodeURIComponent((staff as any).updated_at || (staff as any).created_at || Date.now())
    return `${basePhotoUrl}${basePhotoUrl.includes('?') ? '&' : '?'}v=${version}`
  }, [basePhotoUrl, staff])
  const cardBranchName = branchName || (staff as any)?.branch_name || 'VaidyaVihar Diagnostic'

  const waitForImages = async (container: HTMLElement) => {
    const images = Array.from(container.querySelectorAll('img'))
    await Promise.all(
      images.map((img) => {
        if (img.complete && img.naturalWidth > 0) return Promise.resolve()
        return new Promise<void>((resolve) => {
          const done = () => resolve()
          img.addEventListener('load', done, { once: true })
          img.addEventListener('error', done, { once: true })
        })
      }),
    )
  }

  const downloadPdf = async () => {
    if (!frontRef.current || !backRef.current) return

    const pdf = new jsPDF({
      orientation: 'landscape',
      unit: 'mm',
      format: [CR80_CARD_WIDTH_MM, CR80_CARD_HEIGHT_MM],
    })

    const cardRefs = [frontRef.current, backRef.current]
    for (let i = 0; i < cardRefs.length; i += 1) {
      await waitForImages(cardRefs[i])
      const canvas = await html2canvas(cardRefs[i], { scale: 3, useCORS: true, backgroundColor: '#ffffff' })
      const imgData = canvas.toDataURL('image/png')
      if (i > 0) pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, 0, CR80_CARD_WIDTH_MM, CR80_CARD_HEIGHT_MM)
    }

    pdf.save(`${staff.staff_id}_id_card.pdf`)
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-900">ID Card</h3>
        <button onClick={downloadPdf} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-black">
          {downloadButtonLabel}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div
          className="font-sans"
          style={{
            width: `${CR80_CARD_WIDTH_MM}mm`,
            height: `${CR80_CARD_HEIGHT_MM}mm`,
            padding: `${CR80_SAFE_MARGIN_MM}mm`,
            boxSizing: 'border-box',
            background: 'linear-gradient(145deg, #e7f1ff 0%, #ffffff 45%, #dbeafe 100%)',
            border: '1px solid #bfdbfe',
            borderTop: '5px solid #2563eb',
            borderRadius: '4mm',
            boxShadow: '0 3mm 7mm rgba(37, 99, 235, 0.18)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
          }}
        >
          <p
            style={{
              margin: 0,
              textAlign: 'center',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: '#1d4ed8',
              fontSize: '8.2pt',
              lineHeight: 1.1,
              paddingBottom: '1.2mm',
            }}
          >
            {cardBranchName}
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '2.2mm', flex: 1 }}>
            <div style={{ width: '34%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '1.6mm' }}>
              <div
                style={{
                  width: '20mm',
                  height: '20mm',
                  overflow: 'hidden',
                  borderRadius: '2.4mm',
                  border: '1px solid #93c5fd',
                  background: '#ffffff',
                  boxShadow: '0 1mm 2.2mm rgba(15, 23, 42, 0.18)',
                }}
              >
                {photoUrl ? (
                  <img
                    key={photoUrl}
                    src={photoUrl}
                    alt="Staff avatar"
                    crossOrigin="anonymous"
                    style={{ width: '20mm', height: '20mm', objectFit: 'cover', display: 'block' }}
                  />
                ) : (
                  <div
                    style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '16pt',
                      color: '#1d4ed8',
                    }}
                  >
                    👤
                  </div>
                )}
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1.3mm',
                  padding: '0.9mm 1.7mm',
                  borderRadius: '999px',
                  border: '1px solid #67e8f9',
                  background: 'linear-gradient(90deg, #0284c7 0%, #0891b2 52%, #0f766e 100%)',
                  boxShadow: '0 1mm 2mm rgba(14, 116, 144, 0.35)',
                }}
              >
                <span
                  style={{
                    width: '3.6mm',
                    height: '3.6mm',
                    borderRadius: '1.2mm',
                    background: 'linear-gradient(180deg, #ffffff 0%, #dbeafe 100%)',
                    color: '#0369a1',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '8pt',
                    fontWeight: 900,
                    lineHeight: 1,
                    boxShadow: 'inset 0 0 0 0.3mm #93c5fd',
                  }}
                >
                  +
                </span>
                <span style={{ color: '#ffffff', fontSize: '6.5pt', fontWeight: 800, letterSpacing: '0.04em' }}>MEDICAL STAFF</span>
              </div>
            </div>

            <div
              style={{
                width: '66%',
                minWidth: 0,
                borderRadius: '2mm',
                border: '1px solid #dbeafe',
                background: 'rgba(255, 255, 255, 0.92)',
                padding: '1.5mm 1.8mm',
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontWeight: 800,
                  color: '#0f172a',
                  fontSize: '9.5pt',
                  lineHeight: 1.12,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {staff.full_name || 'Staff Name'}
              </p>
              <p style={{ margin: '0.8mm 0 0', fontWeight: 700, color: '#2563eb', fontSize: '7.3pt', lineHeight: 1.15 }}>Role: {staff.designation || 'Staff'}</p>
              <p style={{ margin: '0.7mm 0 0', color: '#334155', fontSize: '7pt', lineHeight: 1.15 }}>Phone: {staff.mobile || '-'}</p>
              <p style={{ margin: '0.6mm 0 0', color: '#334155', fontSize: '6.9pt', lineHeight: 1.15 }}>Employee ID: {staff.staff_id}</p>
              <div style={{ marginTop: '0.8mm', display: 'flex', gap: '1.8mm', flexWrap: 'wrap', color: '#64748b', fontSize: '6.2pt', lineHeight: 1.1 }}>
                <span>Issue: {new Date().toLocaleDateString()}</span>
                <span>Valid: 2027</span>
              </div>
            </div>
          </div>
        </div>

        <div
          className="font-sans"
          style={{
            width: `${CR80_CARD_WIDTH_MM}mm`,
            height: `${CR80_CARD_HEIGHT_MM}mm`,
            padding: `${CR80_SAFE_MARGIN_MM}mm`,
            boxSizing: 'border-box',
            background: 'linear-gradient(145deg, #eaf3ff 0%, #ffffff 45%, #dbeafe 100%)',
            border: '1px solid #bfdbfe',
            borderTop: '5px solid #2563eb',
            borderRadius: '4mm',
            boxShadow: '0 3mm 7mm rgba(37, 99, 235, 0.18)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
          }}
        >
          <p
            style={{
              margin: 0,
              textAlign: 'center',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: '#1d4ed8',
              fontSize: '8.2pt',
              lineHeight: 1.1,
              paddingBottom: '1.2mm',
            }}
          >
            {cardBranchName}
          </p>

          <div style={{ display: 'flex', alignItems: 'stretch', gap: '2.2mm', flex: 1 }}>
            <div
              style={{
                width: '72%',
                minWidth: 0,
                borderRadius: '2mm',
                border: '1px solid #dbeafe',
                background: 'rgba(255, 255, 255, 0.92)',
                padding: '1.8mm 2mm',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <p style={{ margin: 0, fontWeight: 800, color: '#0f172a', fontSize: '8pt', lineHeight: 1.2 }}>Contact Details</p>
              <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2, wordBreak: 'break-word' }}><span style={{ fontWeight: 700 }}>Address:</span> {staff.address || '-'}</p>
              <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2 }}><span style={{ fontWeight: 700 }}>Phone:</span> {staff.mobile || '-'}</p>
              <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2, wordBreak: 'break-word' }}><span style={{ fontWeight: 700 }}>Email:</span> {staff.email || '-'}</p>
              <div style={{ marginTop: '1.1mm', display: 'flex', gap: '2mm', flexWrap: 'wrap', color: '#475569', fontSize: '6.6pt', lineHeight: 1.15, fontWeight: 600 }}>
                <span>Department: {staff.department || '-'}</span>
              </div>
            </div>

            <div style={{ width: '28%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <div
                style={{
                  width: '18mm',
                  height: '18mm',
                  lineHeight: 0,
                  borderRadius: '2mm',
                  border: '1px solid #93c5fd',
                  background: '#ffffff',
                  padding: '1.3mm',
                  boxShadow: '0 1mm 2.2mm rgba(15, 23, 42, 0.18)',
                }}
              >
                <QRCode
                  value={`STAFF_BACK|${staff.staff_id}|${staff.full_name}|${staff.mobile}|${staff.email}`}
                  size={160}
                  style={{ width: '100%', height: '100%', display: 'block' }}
                />
              </div>
            </div>
          </div>
        </div>

        <div
          aria-hidden="true"
          className="pointer-events-none fixed"
          style={{ position: 'fixed', left: '-10000px', top: '0', pointerEvents: 'none', zIndex: -1 }}
        >
          <div
            ref={frontRef}
            className="font-sans"
            style={{
              width: `${CR80_CARD_WIDTH_MM}mm`,
              height: `${CR80_CARD_HEIGHT_MM}mm`,
              padding: `${CR80_SAFE_MARGIN_MM}mm`,
              boxSizing: 'border-box',
              background: 'linear-gradient(145deg, #e7f1ff 0%, #ffffff 45%, #dbeafe 100%)',
              border: '1px solid #bfdbfe',
              borderTop: '5px solid #2563eb',
              borderRadius: '4mm',
              boxShadow: '0 3mm 7mm rgba(37, 99, 235, 0.18)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
            }}
          >
            <p
              style={{
                margin: 0,
                textAlign: 'center',
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                color: '#1d4ed8',
                fontSize: '8.2pt',
                lineHeight: 1.1,
                paddingBottom: '1.2mm',
              }}
            >
              {cardBranchName}
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: '2.2mm', flex: 1 }}>
              <div style={{ width: '34%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '1.6mm' }}>
                <div
                  style={{
                    width: '20mm',
                    height: '20mm',
                    overflow: 'hidden',
                    borderRadius: '2.4mm',
                    border: '1px solid #93c5fd',
                    background: '#ffffff',
                    boxShadow: '0 1mm 2.2mm rgba(15, 23, 42, 0.18)',
                  }}
                >
                  {photoUrl ? (
                    <img
                      key={photoUrl}
                      src={photoUrl}
                      alt="Staff avatar"
                      crossOrigin="anonymous"
                      style={{ width: '20mm', height: '20mm', objectFit: 'cover', display: 'block' }}
                    />
                  ) : (
                    <div
                      style={{
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '16pt',
                        color: '#1d4ed8',
                      }}
                    >
                      👤
                    </div>
                  )}
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1.3mm',
                    padding: '0.9mm 1.7mm',
                    borderRadius: '999px',
                    border: '1px solid #67e8f9',
                    background: 'linear-gradient(90deg, #0284c7 0%, #0891b2 52%, #0f766e 100%)',
                    boxShadow: '0 1mm 2mm rgba(14, 116, 144, 0.35)',
                  }}
                >
                  <span
                    style={{
                      width: '3.6mm',
                      height: '3.6mm',
                      borderRadius: '1.2mm',
                      background: 'linear-gradient(180deg, #ffffff 0%, #dbeafe 100%)',
                      color: '#0369a1',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '8pt',
                      fontWeight: 900,
                      lineHeight: 1,
                      boxShadow: 'inset 0 0 0 0.3mm #93c5fd',
                    }}
                  >
                    +
                  </span>
                  <span style={{ color: '#ffffff', fontSize: '6.5pt', fontWeight: 800, letterSpacing: '0.04em' }}>MEDICAL STAFF</span>
                </div>
              </div>

              <div
                style={{
                  width: '66%',
                  minWidth: 0,
                  borderRadius: '2mm',
                  border: '1px solid #dbeafe',
                  background: 'rgba(255, 255, 255, 0.92)',
                  padding: '1.5mm 1.8mm',
                }}
              >
                <p
                  style={{
                    margin: 0,
                    fontWeight: 800,
                    color: '#0f172a',
                    fontSize: '9.5pt',
                    lineHeight: 1.12,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {staff.full_name || 'Staff Name'}
                </p>
                <p style={{ margin: '0.8mm 0 0', fontWeight: 700, color: '#2563eb', fontSize: '7.3pt', lineHeight: 1.15 }}>Role: {staff.designation || 'Staff'}</p>
                <p style={{ margin: '0.7mm 0 0', color: '#334155', fontSize: '7pt', lineHeight: 1.15 }}>Phone: {staff.mobile || '-'}</p>
                <p style={{ margin: '0.6mm 0 0', color: '#334155', fontSize: '6.9pt', lineHeight: 1.15 }}>Employee ID: {staff.staff_id}</p>
                <div style={{ marginTop: '0.8mm', display: 'flex', gap: '1.8mm', flexWrap: 'wrap', color: '#64748b', fontSize: '6.2pt', lineHeight: 1.1 }}>
                  <span>Issue: {new Date().toLocaleDateString()}</span>
                  <span>Valid: 2027</span>
                </div>
              </div>
            </div>
          </div>

          <div
            ref={backRef}
            className="mt-3 font-sans"
            style={{
              width: `${CR80_CARD_WIDTH_MM}mm`,
              height: `${CR80_CARD_HEIGHT_MM}mm`,
              padding: `${CR80_SAFE_MARGIN_MM}mm`,
              boxSizing: 'border-box',
              background: 'linear-gradient(145deg, #eaf3ff 0%, #ffffff 45%, #dbeafe 100%)',
              border: '1px solid #bfdbfe',
              borderTop: '5px solid #2563eb',
              borderRadius: '4mm',
              boxShadow: '0 3mm 7mm rgba(37, 99, 235, 0.18)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              fontFamily: 'Poppins, Segoe UI, Arial, sans-serif',
            }}
          >
            <p
              style={{
                margin: 0,
                textAlign: 'center',
                fontWeight: 800,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                color: '#1d4ed8',
                fontSize: '8.2pt',
                lineHeight: 1.1,
                paddingBottom: '1.2mm',
              }}
            >
              {cardBranchName}
            </p>

            <div style={{ display: 'flex', alignItems: 'stretch', gap: '2.2mm', flex: 1 }}>
              <div
                style={{
                  width: '72%',
                  minWidth: 0,
                  borderRadius: '2mm',
                  border: '1px solid #dbeafe',
                  background: 'rgba(255, 255, 255, 0.92)',
                  padding: '1.8mm 2mm',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <p style={{ margin: 0, fontWeight: 800, color: '#0f172a', fontSize: '8pt', lineHeight: 1.2 }}>Contact Details</p>
                <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2, wordBreak: 'break-word' }}><span style={{ fontWeight: 700 }}>Address:</span> {staff.address || '-'}</p>
                <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2 }}><span style={{ fontWeight: 700 }}>Phone:</span> {staff.mobile || '-'}</p>
                <p style={{ margin: '0.9mm 0 0', color: '#1e293b', fontSize: '7.3pt', lineHeight: 1.2, wordBreak: 'break-word' }}><span style={{ fontWeight: 700 }}>Email:</span> {staff.email || '-'}</p>
                <div style={{ marginTop: '1.1mm', display: 'flex', gap: '2mm', flexWrap: 'wrap', color: '#475569', fontSize: '6.6pt', lineHeight: 1.15, fontWeight: 600 }}>
                  <span>Department: {staff.department || '-'}</span>
                </div>
              </div>

              <div style={{ width: '28%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <div
                  style={{
                    width: '18mm',
                    height: '18mm',
                    lineHeight: 0,
                    borderRadius: '2mm',
                    border: '1px solid #93c5fd',
                    background: '#ffffff',
                    padding: '1.3mm',
                    boxShadow: '0 1mm 2.2mm rgba(15, 23, 42, 0.18)',
                  }}
                >
                  <QRCode
                    value={`STAFF_BACK|${staff.staff_id}|${staff.full_name}|${staff.mobile}|${staff.email}`}
                    size={160}
                    style={{ width: '100%', height: '100%', display: 'block' }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
