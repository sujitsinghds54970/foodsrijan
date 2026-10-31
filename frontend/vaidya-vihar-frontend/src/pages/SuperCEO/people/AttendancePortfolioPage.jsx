import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { companyManagementApi, apiErrorMessage } from '../../../services/companyManagementApi';
import { attendanceApi, localDate, monthBounds } from '../../../services/attendanceApi';
import { LoadingBlock, PageHeader, SectionEmpty } from '../../Staff/shared/staffShared';
import '../../../styles/attendance.css';
import '../../../styles/manager.css';
import '../../../styles/staff.css';

export default function AttendancePortfolioPage() {
  const [page, setPage] = useState(1);
  const [month, setMonth] = useState(localDate().slice(0, 7));
  const [state, setState] = useState({ loading: true, companies: [], total: 0, attendance: {}, failures: {}, error: '' });
  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    try {
      const response = await companyManagementApi.list({ page, page_size: 10 });
      const companies = response.data.companies;
      const results = await Promise.allSettled(companies.map((company) => attendanceApi.portfolioRecords({ company_id: company.id, ...monthBounds(month) })));
      const attendance = {};
      const failures = {};
      results.forEach((result, index) => {
        if (result.status === 'fulfilled') attendance[companies[index].id] = result.value.data.records;
        else failures[companies[index].id] = apiErrorMessage(result.reason, 'Attendance unavailable.');
      });
      setState({ loading: false, companies, total: response.data.total, attendance, failures, error: '' });
    } catch (error) {
      setState({ loading: false, companies: [], total: 0, attendance: {}, failures: {}, error: apiErrorMessage(error, 'Company portfolio could not be loaded.') });
    }
  }, [page, month]);
  useEffect(() => { void load(); }, [load]);

  return <div className="staff-page">
    <PageHeader eyebrow="Super CEO · People" title="Attendance across companies" description="Scoped attendance entries, open shifts and flagged records across the company portfolio." action={<input type="month" value={month} aria-label="Attendance month" onChange={(event) => { setPage(1); setMonth(event.target.value); }} />} />
    {state.loading ? <LoadingBlock label="Loading companies" /> : null}
    {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Portfolio unavailable.</strong><span>{state.error}</span><button type="button" className="manager-inline-action" onClick={() => void load()}>Retry</button></div> : null}
    {!state.loading && !state.error ? <section className="manager-panel">
      <div className="manager-section-heading"><div><h2>Companies · {state.total}</h2><p>Entry counts are not attendance rates; they do not include staff who did not clock in.</p></div></div>
      {state.companies.length ? <ol className="staff-record-list">{state.companies.map((company) => {
        const rows = state.attendance[company.id] || [];
        return <li key={company.id}><div><strong>{company.name}</strong><span>{state.failures[company.id] || `${rows.length} entries · ${rows.filter((record) => record.flags?.length).length} flagged · ${rows.filter((record) => !record.clock_out).length} open shifts`}</span></div><Link className="manager-inline-action" to={`/super-ceo/business/companies/${company.id}`}>View company</Link></li>;
      })}</ol> : <SectionEmpty title="No companies found" description="Companies added to the portfolio will appear here." />}
      {state.total > 10 ? <div className="attendance-pager"><button type="button" className="manager-inline-action" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} of {Math.ceil(state.total / 10)}</span><button type="button" className="manager-inline-action" disabled={page * 10 >= state.total} onClick={() => setPage(page + 1)}>Next</button></div> : null}
    </section> : null}
  </div>;
}
