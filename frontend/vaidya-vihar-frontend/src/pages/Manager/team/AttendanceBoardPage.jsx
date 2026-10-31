import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Link, useOutletContext } from 'react-router-dom';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import { attendanceApi, localDate } from '../../../services/attendanceApi';
import useAttendanceEvents from '../../../hooks/useAttendanceEvents';
import { LoadingBlock, PageHeader, SectionEmpty, formatDateTime, readCollection } from '../../Staff/shared/staffShared';
import '../../../styles/attendance.css';
import '../../../styles/staff.css';

export default function AttendanceBoardPage() {
  const { outlet } = useOutletContext();
  const [state, setState] = useState({ loading: true, team: [], records: [], shifts: [], error: '', teamError: '' });
  const [shiftForm, setShiftForm] = useState({ name: '', start_time: '09:00', end_time: '17:00', grace_minutes: 10 });
  const [assignment, setAssignment] = useState({ staff_id: '', shift_id: '', work_date: localDate() });
  const [fence, setFence] = useState({ latitude: '', longitude: '', radius_meters: '100', enabled: true });
  const [fenceError, setFenceError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '', teamError: '' }));
    const [staff, records, shifts] = await Promise.allSettled([
      staffApi.list({ page: 1, page_size: 100 }),
      attendanceApi.managerRecords({ start: localDate(), end: localDate() }), attendanceApi.shifts(),
    ]);
    setState({
      loading: false,
      team: staff.status === 'fulfilled' ? readCollection(staff.value.data, ['items', 'staff']) : [],
      records: records.status === 'fulfilled' ? records.value.data.records : [],
      shifts: shifts.status === 'fulfilled' ? shifts.value.data.shifts : [],
      error: [records, shifts].filter((result) => result.status === 'rejected').map((result) => apiErrorMessage(result.reason, 'Attendance data could not be loaded.')).join(' '),
      teamError: staff.status === 'rejected' ? apiErrorMessage(staff.reason, 'Team roster could not be loaded.') : '',
    });
  }, []);

  useEffect(() => {
    let active = true;
    attendanceApi.geofence().then((response) => {
      if (active && response.data.geofence) {
        const current = response.data.geofence;
        setFence({ latitude: String(current.latitude), longitude: String(current.longitude), radius_meters: String(current.radius_meters), enabled: current.enabled });
      }
    }).catch((error) => {
      if (active) setFenceError(apiErrorMessage(error, 'Geofence could not be loaded.'));
    });
    return () => { active = false; };
  }, []);

  const saveFence = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFenceError('');
    try {
      await attendanceApi.saveGeofence({ latitude: Number(fence.latitude), longitude: Number(fence.longitude), radius_meters: Number(fence.radius_meters), enabled: fence.enabled });
      toast.success('Outlet geofence saved.');
    } catch (error) {
      setFenceError(apiErrorMessage(error, 'Geofence could not be saved.'));
    } finally { setSaving(false); }
  };

  const saveShift = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await attendanceApi.createShift(shiftForm);
      toast.success('Shift created.');
      setShiftForm({ name: '', start_time: '09:00', end_time: '17:00', grace_minutes: 10 });
      await load();
    } catch (error) {
      setState((current) => ({ ...current, teamError: apiErrorMessage(error, 'Shift could not be created.') }));
    } finally { setSaving(false); }
  };
  const saveAssignment = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await attendanceApi.assignShift({ staff_id: Number(assignment.staff_id), shift_id: Number(assignment.shift_id), work_date: assignment.work_date });
      toast.success('Shift assigned.');
      setAssignment({ staff_id: '', shift_id: '', work_date: localDate() });
      await load();
    } catch (error) {
      setState((current) => ({ ...current, teamError: apiErrorMessage(error, 'Shift could not be assigned.') }));
    } finally { setSaving(false); }
  };

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(timer);
  }, [load]);
  useAttendanceEvents(load);
  const onShift = state.records.filter((record) => !record.clock_out);

  return (
    <div className="staff-page">
      <PageHeader eyebrow="Manager · Team" title="Attendance & shifts" description={`Managed clocked-in staff at ${outlet?.name || 'your outlet'}. Updates on attendance events and every minute.`} action={<button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh now</button>} />
      <nav className="attendance-links" aria-label="Attendance sections"><Link to="/manager/team/attendance">Live board</Link><Link to="/manager/team/attendance/suspicious">Review exceptions</Link></nav>
      {state.loading ? <LoadingBlock label="Loading outlet attendance" /> : null}
      {!state.loading && state.error ? <div role="alert" className="manager-inline-state"><strong>Live attendance unavailable.</strong><span>{state.error}</span><button type="button" className="manager-inline-action" onClick={() => void load()}>Retry</button></div> : null}
      {!state.loading && !state.error ? (
        <>
        <section className="manager-panel">
          <div className="manager-section-heading"><div><h2>On shift now · {onShift.length}</h2><p>Open clock-in records for today. This is not a scheduled roster or absence report.</p></div></div>
          <div className="staff-summary-strip"><div><span>Clocked in today</span><strong>{state.records.length}</strong></div><div><span>Flagged entries</span><strong>{state.records.filter((record) => record.flags?.length).length}</strong></div><div><span>Currently on shift</span><strong>{onShift.length}</strong></div></div>
          {onShift.length ? <ol className="staff-record-list">{onShift.map((record) => (
            <li key={record.id}><div><strong>{state.team.find((person) => person.id === record.staff_id)?.full_name || `Staff #${record.staff_id}`}</strong><span>{state.shifts.find((shift) => shift.id === record.shift_id)?.name || 'Unassigned shift'} · {record.flags?.join(', ') || 'No flags'}</span></div><div className="manager-list-meta"><b>{record.status}</b><small>In {formatDateTime(record.clock_in)}</small></div></li>
          ))}</ol> : <SectionEmpty title="Nobody clocked in" description="There are no open clock-in records for this outlet today." />}
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading"><div><h2>Shift planning</h2><p>Create an outlet shift, then assign a staff member to a work date.</p></div></div>
          <ol className="staff-record-list">{state.shifts.map((shift) => <li key={shift.id}><strong>{shift.name}</strong><span>{shift.start_time}–{shift.end_time} · {shift.grace_minutes} min grace</span></li>)}</ol>
          <form className="manager-form-grid" onSubmit={saveShift}>
            <label className="manager-form-field"><span>Shift name</span><input required value={shiftForm.name} onChange={(event) => setShiftForm({ ...shiftForm, name: event.target.value })} /></label>
            <label className="manager-form-field"><span>Start</span><input type="time" required value={shiftForm.start_time} onChange={(event) => setShiftForm({ ...shiftForm, start_time: event.target.value })} /></label>
            <label className="manager-form-field"><span>End</span><input type="time" required value={shiftForm.end_time} onChange={(event) => setShiftForm({ ...shiftForm, end_time: event.target.value })} /></label>
            <label className="manager-form-field"><span>Grace (minutes)</span><input type="number" min="0" max="120" value={shiftForm.grace_minutes} onChange={(event) => setShiftForm({ ...shiftForm, grace_minutes: Number(event.target.value) })} /></label>
            <button type="submit" className="exec-button exec-button-primary" disabled={saving}>Create shift</button>
          </form>
          <form className="manager-form-grid" onSubmit={saveAssignment}>
            <label className="manager-form-field"><span>Staff member</span><select required value={assignment.staff_id} onChange={(event) => setAssignment({ ...assignment, staff_id: event.target.value })}><option value="">Select staff</option>{state.team.map((person) => <option key={person.id} value={person.id}>{person.full_name || person.display_name || person.username}</option>)}</select></label>
            <label className="manager-form-field"><span>Shift</span><select required value={assignment.shift_id} onChange={(event) => setAssignment({ ...assignment, shift_id: event.target.value })}><option value="">Select shift</option>{state.shifts.filter((shift) => shift.active).map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}</select></label>
            <label className="manager-form-field"><span>Work date</span><input type="date" required value={assignment.work_date} onChange={(event) => setAssignment({ ...assignment, work_date: event.target.value })} /></label>
            <button type="submit" className="exec-button exec-button-primary" disabled={saving || !state.shifts.length}>Assign shift</button>
          </form>
        </section>
        </>
      ) : null}
      <section className="manager-panel">
        <div className="manager-section-heading"><div><h2>Outlet clock-in geofence</h2><p>Set the permitted location before staff can clock in. Use your outlet's verified coordinates.</p></div></div>
        {fenceError ? <div className="manager-inline-state" role="alert">{fenceError}</div> : null}
        <form className="manager-form-grid" onSubmit={saveFence}>
          <label className="manager-form-field"><span>Latitude</span><input type="number" step="any" min="-90" max="90" required value={fence.latitude} onChange={(event) => setFence({ ...fence, latitude: event.target.value })} /></label>
          <label className="manager-form-field"><span>Longitude</span><input type="number" step="any" min="-180" max="180" required value={fence.longitude} onChange={(event) => setFence({ ...fence, longitude: event.target.value })} /></label>
          <label className="manager-form-field"><span>Radius (meters)</span><input type="number" min="1" max="5000" required value={fence.radius_meters} onChange={(event) => setFence({ ...fence, radius_meters: event.target.value })} /></label>
          <label className="manager-form-field"><span>Enabled</span><input type="checkbox" checked={fence.enabled} onChange={(event) => setFence({ ...fence, enabled: event.target.checked })} /></label>
          <button type="submit" className="exec-button exec-button-primary" disabled={saving}>Save geofence</button>
        </form>
      </section>
      <section className="manager-panel">
        <div className="manager-section-heading"><div><h2>Team shift preferences</h2><p>Preferences from the outlet staff directory; not published schedules.</p></div></div>
        {!state.loading && state.teamError ? <div className="manager-inline-state" role="alert">{state.teamError}</div> : null}
        {!state.loading && !state.teamError && !state.team.length ? <SectionEmpty title="No staff assigned" description="Add team members to your outlet to see their shift preferences." /> : null}
        {!state.loading && !state.teamError && state.team.length ? <ol className="staff-record-list">{state.team.map((person) => (
          <li key={person.id || person.staff_profile_id}><div><strong>{person.full_name || person.display_name || [person.first_name, person.last_name].filter(Boolean).join(' ') || person.username}</strong><span>{person.staff_role || person.role || 'Staff'}</span></div><div className="manager-list-meta"><b>{person.shift_preference || 'Not assigned'}</b><small>{person.weekly_off_day ? `Weekly off: ${person.weekly_off_day}` : ''}</small></div></li>
        ))}</ol> : null}
      </section>
    </div>
  );
}
