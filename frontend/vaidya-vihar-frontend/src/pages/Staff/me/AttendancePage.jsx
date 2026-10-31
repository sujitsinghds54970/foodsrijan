import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import toast from 'react-hot-toast';
import { attendanceApi, attendanceTime, localDate, monthBounds } from '../../../services/attendanceApi';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatDate } from '../shared/staffShared';
import '../../../styles/attendance.css';

export default function AttendancePage() {
  const { me } = useOutletContext();
  const [month, setMonth] = useState(localDate().slice(0, 7));
  const [state, setState] = useState({ loading: true, records: [], shifts: [], leaves: [], corrections: [], error: '', extrasError: '' });
  const [clocking, setClocking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [leave, setLeave] = useState({ start_date: '', end_date: '', leave_type: 'annual', reason: '' });
  const [correction, setCorrection] = useState({ record_id: '', requested_clock_in: '', requested_clock_out: '', reason: '' });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '', extrasError: '' }));
    const bounds = monthBounds(month);
    const [records, shifts, leaves, corrections] = await Promise.allSettled([
      attendanceApi.mine(bounds), attendanceApi.myShifts(bounds), attendanceApi.myLeaves(), attendanceApi.myCorrections(),
    ]);
    setState({
      loading: false,
      records: records.status === 'fulfilled' ? records.value.data.records : [],
      shifts: shifts.status === 'fulfilled' ? shifts.value.data.assignments : [],
      leaves: leaves.status === 'fulfilled' ? leaves.value.data.leaves : [],
      corrections: corrections.status === 'fulfilled' ? corrections.value.data.corrections : [],
      error: records.status === 'rejected' ? apiErrorMessage(records.reason, 'Attendance could not be loaded.') : '',
      extrasError: [shifts, leaves, corrections].filter((result) => result.status === 'rejected').map((result) => apiErrorMessage(result.reason, 'Related attendance information could not be loaded.')).join(' '),
    });
  }, [month]);
  useEffect(() => { void load(); }, [load]);

  const today = localDate();
  const todayRecord = state.records.find((record) => record.work_date === today);
  const nextAction = !todayRecord ? 'in' : !todayRecord.clock_out ? 'out' : null;
  const clock = async () => {
    if (!nextAction || clocking) return;
    setClocking(true);
    try {
      await attendanceApi.clock(nextAction);
      toast.success(`Clock-${nextAction} recorded.`);
      await load();
    } catch (error) {
      toast.error(error instanceof Error && error.message.startsWith('Location')
        ? error.message
        : apiErrorMessage(error, 'Could not record attendance. Verify location access and outlet geofence.'));
    } finally {
      setClocking(false);
    }
  };

  const submitLeave = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await attendanceApi.requestLeave(leave);
      toast.success('Leave requested.');
      setLeave({ start_date: '', end_date: '', leave_type: 'annual', reason: '' });
      await load();
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Could not submit leave.'));
    } finally {
      setSaving(false);
    }
  };

  const submitCorrection = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await attendanceApi.requestCorrection({
        record_id: Number(correction.record_id),
        requested_clock_in: correction.requested_clock_in || undefined,
        requested_clock_out: correction.requested_clock_out || undefined,
        reason: correction.reason.trim(),
      });
      toast.success('Correction requested.');
      setCorrection({ record_id: '', requested_clock_in: '', requested_clock_out: '', reason: '' });
      await load();
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Could not request a correction.'));
    } finally {
      setSaving(false);
    }
  };

  return <div className="staff-page">
    <PageHeader eyebrow="Staff · Me" title="Attendance" description="Clock your shift using your current location, review records, and request leave or corrections." action={<input type="month" className="staff-month-input" value={month} onChange={(event) => setMonth(event.target.value)} aria-label="Attendance month" />} />
    <nav className="attendance-links" aria-label="Attendance sections"><a href="#clock">Clock</a><a href="#history">History</a><a href="#leave">Leave</a><a href="#corrections">Corrections</a></nav>
    <section id="clock" className="manager-panel">
      <div className="manager-section-heading"><div><h2>Today's shift</h2><p>{formatDate(today)} · {me?.outlet_name || 'Your outlet'}</p></div><button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button></div>
      {state.loading ? <LoadingBlock label="Checking clock status" /> : null}
      {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Clock status unavailable.</strong><span>{state.error}</span></div> : null}
      {!state.loading && !state.error && month !== today.slice(0, 7) ? <p>Select the current month to clock your shift.</p> : null}
      {!state.loading && !state.error && month === today.slice(0, 7) ? <div className="attendance-clock-row">
        <dl className="manager-stat-list"><div><dt>Clock in</dt><dd>{attendanceTime(todayRecord?.clock_in)}</dd></div><div><dt>Clock out</dt><dd>{attendanceTime(todayRecord?.clock_out)}</dd></div><div><dt>Shift preference</dt><dd>{me?.shift_preference || 'Not set'}</dd></div></dl>
        {nextAction ? <button type="button" className="exec-button exec-button-primary" disabled={clocking} onClick={() => void clock()}>{clocking ? 'Getting location…' : `Clock ${nextAction}`}</button> : <span role="status">Today's shift is complete.</span>}
        <small>Location access is required. Clocking is restricted to your outlet's geofence.</small>
      </div> : null}
    </section>
    <section id="history" className="manager-panel">
      <div className="manager-section-heading"><div><h2>Attendance history</h2><p>Managed attendance entries for {month}.</p></div></div>
      {!state.loading && !state.error && !state.records.length ? <SectionEmpty title="No attendance records" description="No clock entries were recorded for this month." /> : null}
      {!state.loading && !state.error && state.records.length ? <ol className="staff-record-list">{state.records.map((record) => <li key={record.id}><div><strong>{record.work_date}</strong><span>{attendanceTime(record.clock_in)} → {attendanceTime(record.clock_out)}</span><small>{record.flags?.length ? `Flags: ${record.flags.join(', ')}` : ''}</small></div><div className="manager-list-meta"><b>{record.status}</b><small>{record.minutes_worked == null ? 'In progress' : `${record.minutes_worked} minutes`}</small></div></li>)}</ol> : null}
    </section>
    {state.extrasError ? <div className="manager-inline-state" role="alert">{state.extrasError}</div> : null}
    <section className="manager-panel"><div className="manager-section-heading"><div><h2>Assigned shifts</h2></div></div>
      {!state.loading && !state.shifts.length ? <SectionEmpty title="No shifts assigned" description="Your manager has not assigned shifts for this month." /> : null}
      <ol className="staff-record-list">{state.shifts.map((shift) => <li key={shift.id}><strong>{formatDate(shift.work_date)}</strong><span>Shift #{shift.shift_id}</span></li>)}</ol>
    </section>
    <section id="leave" className="manager-panel">
      <div className="manager-section-heading"><div><h2>Leave</h2><p>Submit a dated leave request to your manager.</p></div></div>
      <form className="manager-form-grid" onSubmit={submitLeave}>
        <label className="manager-form-field"><span>Start date</span><input type="date" required value={leave.start_date} onChange={(event) => setLeave({ ...leave, start_date: event.target.value })} /></label>
        <label className="manager-form-field"><span>End date</span><input type="date" required min={leave.start_date} value={leave.end_date} onChange={(event) => setLeave({ ...leave, end_date: event.target.value })} /></label>
        <label className="manager-form-field"><span>Leave type</span><select value={leave.leave_type} onChange={(event) => setLeave({ ...leave, leave_type: event.target.value })}><option value="annual">Annual</option><option value="sick">Sick</option><option value="unpaid">Unpaid</option></select></label>
        <label className="manager-form-field is-wide"><span>Reason</span><textarea required minLength={3} maxLength={2000} value={leave.reason} onChange={(event) => setLeave({ ...leave, reason: event.target.value })} /></label>
        <button type="submit" className="exec-button exec-button-primary" disabled={saving}>Request leave</button>
      </form>
      <ol className="staff-record-list">{state.leaves.map((item) => <li key={item.id}><div><strong>{item.leave_type} · {item.status}</strong><span>{formatDate(item.start_date)} → {formatDate(item.end_date)}</span></div><span>{item.reason}</span></li>)}</ol>
    </section>
    <section id="corrections" className="manager-panel">
      <div className="manager-section-heading"><div><h2>Corrections</h2><p>Request a change to one of your recorded shifts. Times are entered in UTC.</p></div></div>
      <form className="manager-form-grid" onSubmit={submitCorrection}>
        <label className="manager-form-field"><span>Record</span><select required value={correction.record_id} onChange={(event) => setCorrection({ ...correction, record_id: event.target.value })}><option value="">Select a record</option>{state.records.map((record) => <option key={record.id} value={record.id}>{record.work_date} · #{record.id}</option>)}</select></label>
        <label className="manager-form-field"><span>Corrected clock in (UTC)</span><input type="datetime-local" value={correction.requested_clock_in} onChange={(event) => setCorrection({ ...correction, requested_clock_in: event.target.value })} /></label>
        <label className="manager-form-field"><span>Corrected clock out (UTC)</span><input type="datetime-local" value={correction.requested_clock_out} onChange={(event) => setCorrection({ ...correction, requested_clock_out: event.target.value })} /></label>
        <label className="manager-form-field is-wide"><span>Reason</span><textarea required minLength={3} maxLength={2000} value={correction.reason} onChange={(event) => setCorrection({ ...correction, reason: event.target.value })} /></label>
        <button type="submit" className="exec-button exec-button-primary" disabled={saving || (!correction.requested_clock_in && !correction.requested_clock_out)}>Request correction</button>
      </form>
      <ol className="staff-record-list">{state.corrections.map((item) => <li key={item.id}><strong>Record #{item.record_id} · {item.status}</strong><span>{item.reason}</span></li>)}</ol>
    </section>
  </div>;
}
