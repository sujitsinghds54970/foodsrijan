import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import { EmpireIcon, OrbitIcon, PortfolioIcon, PulseIcon } from '../../../components/SuperCEO/icons';
import { apiErrorMessage, companyManagementApi } from '../../../services/companyManagementApi';
import '../../../styles/company-management.css';

const PAGE_SIZE = 10;

const formatDate = (date) => {
  if (!date) return '—';
  const parsed = new Date(date);
  return Number.isNaN(parsed.getTime())
    ? '—'
    : parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

export default function CompaniesPage() {
  const [companies, setCompanies] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyCompanyId, setBusyCompanyId] = useState(null);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState('');

  const loadCompanies = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await companyManagementApi.list({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        status: status || undefined,
        include_deleted: includeDeleted || status === 'archived',
      });
      setCompanies(response.data.companies);
      setTotal(response.data.total);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to load the company portfolio.'));
    } finally {
      setLoading(false);
    }
  }, [includeDeleted, page, search, status]);

  useEffect(() => {
    void loadCompanies();
  }, [loadCompanies]);

  const loadStats = useCallback(async () => {
    setStatsError('');
    try {
      const response = await companyManagementApi.stats();
      setStats(response.data.stats);
    } catch (requestError) {
      setStatsError(apiErrorMessage(requestError, 'Portfolio statistics are unavailable.'));
    }
  }, []);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const handleSearch = (event) => {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const handleStatusChange = (event) => {
    setPage(1);
    setStatus(event.target.value);
  };

  const handleDeletedChange = (event) => {
    setPage(1);
    setIncludeDeleted(event.target.checked);
  };

  const handleDelete = async (company) => {
    const confirmed = window.confirm(`Archive ${company.name}? Active staff, customers, branches, orders, and assigned CEOs can prevent archiving.`);
    if (!confirmed) return;
    setBusyCompanyId(company.id);
    try {
      await companyManagementApi.remove(company.id);
      toast.success(`${company.name} archived`);
      await loadCompanies();
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to archive this company.'));
    } finally {
      setBusyCompanyId(null);
    }
  };

  const handleRestore = async (company) => {
    setBusyCompanyId(company.id);
    try {
      await companyManagementApi.restore(company.id);
      toast.success(`${company.name} restored`);
      await loadCompanies();
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to restore this company.'));
    } finally {
      setBusyCompanyId(null);
    }
  };

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const activeCount = companies.filter((company) => company.is_active && !company.is_deleted).length;

  return (
    <section className="company-admin">
      <header className="exec-hero company-admin-hero">
        <div>
          <p className="eyebrow">Business · Portfolio control</p>
          <h2>Companies</h2>
          <p className="page-subtitle">Create, govern, and inspect every operating company in the group.</p>
        </div>
        <div className="company-admin-hero-actions">
          <span className="company-count-pill"><strong>{total}</strong> records · {activeCount} active on this page</span>
          <Link className="primary-button company-action-button" to="/super-ceo/business/companies/new">Add company <span aria-hidden="true">+</span></Link>
        </div>
      </header>

      <section className="company-portfolio-kpis metric-grid four-up" aria-label="Company portfolio statistics">
        <KpiCard label="Active Companies" value={stats?.active_companies} tone="violet" icon={EmpireIcon} source="Source · companies registry" />
        <KpiCard label="Active Branches" value={stats?.active_branches} tone="teal" icon={OrbitIcon} source="Source · declared branch totals" />
        <KpiCard label="Active Users" value={stats?.active_users} tone="gold" icon={PulseIcon} source="Source · active company users" />
        <KpiCard label="Pending Onboarding" value={stats?.pending_onboarding} tone="sunset" icon={PortfolioIcon} source="Source · onboarding workflow" />
      </section>
      {statsError && <p className="company-inline-note" role="status">{statsError}</p>}

      <section className="company-admin-toolbar panel" aria-label="Company filters">
        <form className="company-search-form" onSubmit={handleSearch}>
          <label className="company-search-label" htmlFor="company-search">Find a company</label>
          <div className="company-search-control">
            <input
              id="company-search"
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search name, legal name, or slug"
            />
            <button className="ghost-button compact" type="submit">Search</button>
          </div>
        </form>
        <label className="company-filter-field">
          <span>Status</span>
          <select value={status} onChange={handleStatusChange}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="suspended">Suspended</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <label className="company-deleted-toggle">
          <input type="checkbox" checked={includeDeleted} onChange={handleDeletedChange} />
          <span>Include archived records</span>
        </label>
        <button type="button" className="ghost-button compact company-refresh" onClick={() => { void loadCompanies(); void loadStats(); }} disabled={loading}>Refresh</button>
      </section>

      <section className="panel company-list-panel" aria-labelledby="company-list-title">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Company register</p>
            <h3 id="company-list-title">Operating portfolio</h3>
          </div>
          <span className="company-register-total">{total.toLocaleString()} total</span>
        </div>
        {loading ? <LoadingSkeleton /> : error ? (
          <div className="company-inline-error" role="alert">
            <strong>Company register unavailable</strong>
            <p>{error}</p>
            <button type="button" className="ghost-button compact" onClick={loadCompanies}>Retry</button>
          </div>
        ) : companies.length === 0 ? (
          <EmptyState
            title={search || status ? 'No companies match these filters' : 'No companies in the register yet'}
            description={search || status ? 'Adjust the search or status filter to see more records.' : 'Create the first company to begin managing the group portfolio.'}
          />
        ) : (
          <>
            <div className="company-table-scroll">
              <table className="company-table">
                <thead>
                  <tr>
                    <th scope="col">Company</th>
                    <th scope="col">Business</th>
                    <th scope="col">Headquarters</th>
                    <th scope="col">Status</th>
                    <th scope="col">Created</th>
                    <th scope="col"><span className="sr-only">Actions</span></th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company) => (
                    <tr key={company.id} className={company.is_deleted ? 'is-archived' : ''}>
                      <td>
                        {company.is_deleted ? (
                          <span className="company-name-link company-name-static">
                            <span className="company-avatar" aria-hidden="true">{company.name.slice(0, 1).toUpperCase()}</span>
                            <span><strong>{company.name}</strong><small>{company.legal_name || company.slug}</small></span>
                          </span>
                        ) : <Link className="company-name-link" to={`/super-ceo/business/companies/${company.id}/overview`}>
                          <span className="company-avatar" aria-hidden="true">{company.name.slice(0, 1).toUpperCase()}</span>
                          <span>
                            <strong>{company.name}</strong>
                            <small>{company.legal_name || company.slug}</small>
                          </span>
                        </Link>}
                      </td>
                      <td>{company.business_domain || 'Unclassified'}</td>
                      <td>{[company.headquarters_city, company.headquarters_state].filter(Boolean).join(', ') || 'Not set'}</td>
                      <td><span className={`company-status status-${company.is_deleted ? 'archived' : company.status}`}>{company.is_deleted ? 'Archived' : company.status}</span></td>
                      <td className="company-date">{formatDate(company.created_at)}</td>
                      <td>
                        <div className="company-row-actions">
                          {company.is_deleted ? (
                            <button type="button" className="ghost-button compact" onClick={() => handleRestore(company)} disabled={busyCompanyId === company.id}>Restore</button>
                          ) : (
                            <>
                              <Link className="ghost-button compact" to={`/super-ceo/business/companies/${company.id}`}>Open</Link>
                              <button type="button" className="ghost-button compact company-danger-action" onClick={() => handleDelete(company)} disabled={busyCompanyId === company.id}>Archive</button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="company-pagination">
              <span>Showing {Math.min((page - 1) * PAGE_SIZE + 1, total)}–{Math.min(page * PAGE_SIZE, total)} of {total}</span>
              <div>
                <button type="button" className="ghost-button compact" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1 || loading}>Previous</button>
                <span aria-live="polite">Page {page} of {pageCount}</span>
                <button type="button" className="ghost-button compact" onClick={() => setPage((current) => Math.min(pageCount, current + 1))} disabled={page >= pageCount || loading}>Next</button>
              </div>
            </div>
          </>
        )}
      </section>
    </section>
  );
}
