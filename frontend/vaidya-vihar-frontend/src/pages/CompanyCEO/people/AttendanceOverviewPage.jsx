import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { attendanceApi, localDate, monthBounds } from '../../../services/attendanceApi';
import useAttendanceEvents from '../../../hooks/useAttendanceEvents';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatDate, formatDateTime } from '../../Staff/shared/staffShared';
import '../../../styles/attendance.css';
import '../../../styles/manager.css';
import '../../../styles/staff.css';

export default function AttendanceOverviewPage() {
  const workspace = useOutletContext();
  const branches = workspace?.branches || [];
  const [month, setMonth] = useState(localDate().slice(0, 7));
  const [outletId, setOutletId] = useState('');
  const [state, setState] = useState({ loading: true, records: [], error: '' });
  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    try {
      const response = await attendanceApi.companyRecords({ ...monthBounds(month), outlet_id: outletId ? Number(outletId) : undefined });
      setState({ loading: false, records: response.data.records, error: '' });
    } catch (error) {
      setState({ loading: false, records: [], error: apiErrorMessage(error, 'Company attendance could not be loaded.') });
    }
  }, [month, outletId]);
  useEffect(() => { void load(); }, [load]);
  useAttendanceEvents(load);

  return <div className="staff-page">
    <PageHeader eyebrow="Company CEO · People" title="Attendance overview" description={`Attendance across ${workspace?.company?.name || 'your company'}.`} action={<input type="month" value={month} onChange={(event) => setMonth(event.target.value)} aria-label="Attendance month" />} />
    <label className="manager-form-field"><span>Outlet</span><select value={outletId} onChange={(event) => setOutletId(event.target.value)}><option value="">All outlets</option>{branches.map((branch) => <option value={branch.id} key={branch.id}>{branch.name}</option>)}</select></label>
    {state.loading ? <LoadingBlock label="Loading company attendance" /> : null}
    {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Attendance unavailable.</strong><span>{state.error}</span><button type="button" className="manager-inline-action" onClick={() => void load()}>Retry</button></div> : null}
    {!state.loading && !state.error ? <section className="manager-panel">
      <div className="staff-summary-strip"><div><span>Clocked entries</span><strong>{state.records.length}</strong></div><div><span>Flagged entries</span><strong>{state.records.filter((record) => record.flags?.length).length}</strong></div><div><span>Open shifts</span><strong>{state.records.filter((record) => !record.clock_out).length}</strong></div></div>
      {state.records.length ? <ol className="staff-record-list">{state.records.map((record) => <li key={record.id}><div><strong>Staff #{record.staff_id} · {formatDate(record.work_date)}</strong><span>Outlet #{record.outlet_id} · {formatDateTime(record.clock_in)} → {formatDateTime(record.clock_out)}</span></div><div className="manager-list-meta"><b>{record.status}</b><small>{record.flags?.join(', ')}</small></div></li>)}</ol> : <SectionEmpty title="No entries" description="No clock entries were returned for this period and outlet." />}
    </section> : null}
    <section className="manager-panel">
      <div className="manager-section-heading"><div><h2>Company outlets · {branches.length}</h2><p>Locations in the company workspace, not attendance totals.</p></div></div>
      {branches.length ? <ol className="staff-record-list">{branches.map((branch) => <li key={branch.id}><div><strong>{branch.name}</strong><span>{[branch.city, branch.state].filter(Boolean).join(', ') || branch.branch_code}</span></div><span className="staff-pill">{branch.is_active ? 'Active outlet' : 'Inactive outlet'}</span></li>)}</ol> : <SectionEmpty title="No outlets found" description="Add an outlet before tracking attendance across the company." />}
    </section>
  </div>;
}
