import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { attendanceApi, localDate } from '../../../services/attendanceApi';
import useAttendanceEvents from '../../../hooks/useAttendanceEvents';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatDate } from '../../Staff/shared/staffShared';
import '../../../styles/attendance.css';
import '../../../styles/staff.css';

export default function AttendanceReviewPage() {
  const [state, setState] = useState({ loading: true, records: [], corrections: [], leaves: [], error: '' });
  const [busy, setBusy] = useState('');
  const [note, setNote] = useState('');
  const [selected, setSelected] = useState('');
  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    try {
      const today = localDate();
      const [records, corrections, leaves] = await Promise.all([
        attendanceApi.managerRecords({ start: localDate(new Date(Date.now() - 30 * 86400000)), end: today }),
        attendanceApi.managerCorrections('pending'),
        attendanceApi.managerLeaves('pending'),
      ]);
      setState({ loading: false, records: records.data.records, corrections: corrections.data.corrections, leaves: leaves.data.leaves, error: '' });
    } catch (error) {
      setState({ loading: false, records: [], corrections: [], leaves: [], error: apiErrorMessage(error, 'Review queue could not be loaded.') });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useAttendanceEvents(load);

  const review = async (type, id, decision) => {
    if (!note.trim() || busy) return;
    setBusy(`${type}-${id}`);
    try {
      if (type === 'correction') await attendanceApi.reviewCorrection(id, decision, note.trim());
      else await attendanceApi.reviewLeave(id, decision, note.trim());
      toast.success(`${type === 'correction' ? 'Correction' : 'Leave'} ${decision}.`);
      setSelected('');
      setNote('');
      await load();
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Review could not be saved.'));
    } finally {
      setBusy('');
    }
  };

  const flagged = state.records.filter((record) => record.flags?.length);
  return <div className="staff-page">
    <PageHeader eyebrow="Manager · Team" title="Attendance exceptions" description="Flagged entries and pending correction and leave decisions for your outlet." action={<button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button>} />
    <nav className="attendance-links" aria-label="Attendance sections"><Link to="/manager/team/attendance">Live board</Link><Link to="/manager/team/attendance/suspicious">Review exceptions</Link></nav>
    {state.loading ? <LoadingBlock label="Loading review queue" /> : null}
    {!state.loading && state.error ? <div role="alert" className="manager-inline-state"><strong>Review unavailable.</strong><span>{state.error}</span></div> : null}
    {!state.loading && !state.error ? <>
      <section className="manager-panel"><div className="manager-section-heading"><div><h2>Flagged entries · {flagged.length}</h2><p>Flags are informational; corrections require a staff request before approval.</p></div></div>
        {flagged.length ? <ol className="staff-record-list">{flagged.map((record) => <li key={record.id}><div><strong>Staff #{record.staff_id} · {formatDate(record.work_date)}</strong><span>{record.flags.join(', ')}</span></div><span className="staff-pill">{record.status}</span></li>)}</ol> : <SectionEmpty title="No flagged entries" description="No flagged attendance records were returned for the last 30 days." />}
      </section>
      {[{ type: 'correction', title: 'Pending corrections', items: state.corrections }, { type: 'leave', title: 'Pending leave', items: state.leaves }].map(({ type, title, items }) => <section className="manager-panel" key={type}>
        <div className="manager-section-heading"><div><h2>{title} · {items.length}</h2>{type === 'correction' ? <p>Approval is disabled because the review feed does not include the requested replacement times. Reject with a note or review after the API exposes them.</p> : null}</div></div>
        {!items.length ? <SectionEmpty title={`No ${type} requests`} description="There are no pending requests to review." /> : <ol className="staff-record-list">{items.map((item) => {
          const key = `${type}-${item.id}`;
          return <li key={key} className="attendance-review-item">
            <div><strong>Staff #{item.staff_id} · {type === 'correction' ? `Record #${item.record_id}` : `${formatDate(item.start_date)} → ${formatDate(item.end_date)}`}</strong><span>{item.reason}</span></div>
            {selected === key ? <div className="attendance-review-actions">
              <label className="manager-form-field"><span>Decision note</span><textarea required minLength={3} maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} /></label>
              <button type="button" className="exec-button exec-button-primary" disabled={type === 'correction' || note.trim().length < 3 || !!busy} onClick={() => void review(type, item.id, 'approved')}>Approve</button>
              <button type="button" className="manager-inline-action" disabled={note.trim().length < 3 || !!busy} onClick={() => void review(type, item.id, 'rejected')}>Reject</button>
              <button type="button" className="manager-inline-action" disabled={!!busy} onClick={() => { setSelected(''); setNote(''); }}>Cancel</button>
            </div> : <button type="button" className="manager-inline-action" onClick={() => { setSelected(key); setNote(''); }}>Review</button>}
          </li>;
        })}</ol>}
      </section>)}
    </> : null}
  </div>;
}
