import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import { EmpireIcon, OrbitIcon, PortfolioIcon, PulseIcon } from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { outletApi } from '../../../services/outletApi';
import '../../../styles/outlets.css';

const base = '/company-ceo/operations/outlets';
const pageSize = 12;
const statuses = ['planning', 'setup', 'active', 'temporarily_closed', 'permanently_closed'];
const regions = ['north_india', 'south_india', 'east_india', 'west_india', 'international'];
const title = (value) => value?.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) || 'Not set';

export default function OutletsPage() {
  const [outlets, setOutlets] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [type, setType] = useState('');
  const [city, setCity] = useState('');
  const [region, setRegion] = useState('');
  const [includeDeleted, setIncludeDeleted] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await outletApi.list({ page, page_size: pageSize, search: search || undefined, status: status || undefined, outlet_type: type || undefined, city: city.trim() || undefined, region: region || undefined, include_deleted: includeDeleted });
      setOutlets(response.data.outlets);
      setTotal(response.data.total);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to load outlets.'));
    } finally {
      setLoading(false);
    }
  }, [page, search, status, type, city, region, includeDeleted]);

  const loadStats = useCallback(async () => {
    setStatsError('');
    try { setStats((await outletApi.stats()).data.stats); }
    catch (requestError) { setStatsError(apiErrorMessage(requestError, 'Outlet statistics are unavailable.')); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadStats(); }, [loadStats]);

  const mutate = async (outlet, action) => {
    if (action === 'archive' && !window.confirm(`Archive ${outlet.name}? This may be blocked by active operations or an assigned manager.`)) return;
    setBusy(outlet.id);
    try {
      if (action === 'archive') await outletApi.remove(outlet.id);
      else await outletApi.restore(outlet.id);
      toast.success(`${outlet.name} ${action === 'archive' ? 'archived' : 'restored'}`);
      await Promise.all([load(), loadStats()]);
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, `Unable to ${action} this outlet.`));
    } finally { setBusy(null); }
  };

  return (
    <section className="company-admin outlet-admin">
      <header className="exec-hero company-admin-hero">
        <div><p className="eyebrow">Operations · Outlet network</p><h2>Outlets</h2><p className="page-subtitle">Build and govern the operating locations in your company.</p></div>
        <Link className="primary-button company-action-button" to={`${base}/new`}>Add outlet <span aria-hidden="true">+</span></Link>
      </header>
      <div className="metric-grid four-up outlet-kpis" aria-label="Outlet portfolio statistics">
        <KpiCard label="Total outlets" value={stats?.total_outlets} tone="violet" icon={EmpireIcon} source="Company outlet register" />
        <KpiCard label="Active" value={stats?.active_outlets} tone="teal" icon={OrbitIcon} source="Operating locations" />
        <KpiCard label="In setup" value={stats?.by_status?.setup} tone="gold" icon={PulseIcon} source="Preparing to open" />
        <KpiCard label="Without manager" value={stats?.outlets_without_manager} tone="sunset" icon={PortfolioIcon} source="Assignment needed" />
      </div>
      {statsError && <p role="status">{statsError}</p>}
      <div className="panel outlet-filters" aria-label="Outlet filters">
        <form onSubmit={(event) => { event.preventDefault(); setPage(1); setSearch(query.trim()); }}>
          <label>Search outlets<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, code, city" /></label>
          <button className="ghost-button compact" type="submit">Search</button>
        </form>
        <label>Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">All statuses</option>{statuses.map((item) => <option value={item} key={item}>{title(item)}</option>)}</select></label>
        <label>Type<select value={type} onChange={(event) => { setType(event.target.value); setPage(1); }}><option value="">All types</option>{['dine_in', 'takeaway', 'cloud_kitchen', 'kiosk', 'food_truck', 'cafe', 'bakery', 'bar', 'fine_dine', 'qsr', 'buffet', 'drive_through', 'other'].map((item) => <option value={item} key={item}>{title(item)}</option>)}</select></label>
        <label>City<input type="search" value={city} onChange={(event) => { setCity(event.target.value); setPage(1); }} placeholder="Filter by city" /></label>
        <label>Region<select value={region} onChange={(event) => { setRegion(event.target.value); setPage(1); }}><option value="">All regions</option>{regions.map((item) => <option value={item} key={item}>{title(item)}</option>)}</select></label>
        <label className="outlet-check"><input type="checkbox" checked={includeDeleted} onChange={(event) => { setIncludeDeleted(event.target.checked); setPage(1); }} /> Include archived</label>
        <button type="button" className="ghost-button compact" disabled={loading} onClick={() => { void load(); void loadStats(); }}>Refresh</button>
      </div>
      <section className="panel outlet-register" aria-labelledby="outlet-register-title">
        <div className="panel-header"><div><p className="eyebrow">Outlet register</p><h3 id="outlet-register-title">Operating network</h3></div><span>{total.toLocaleString()} records</span></div>
        {loading ? <LoadingSkeleton /> : error ? <div role="alert"><p>{error}</p><button className="ghost-button compact" onClick={() => void load()}>Retry</button></div>
          : outlets.length === 0 ? <EmptyState title="No outlets found" description="Adjust the filters or create your first outlet." />
            : <div className="outlet-cards">{outlets.map((outlet) => (
              <article className="outlet-card" key={outlet.id}>
                <div className="outlet-card-top"><span className="outlet-monogram" aria-hidden="true">{outlet.name.slice(0, 2).toUpperCase()}</span><span className="outlet-status">{outlet.is_deleted ? 'Archived' : title(outlet.status)}</span></div>
                <h4><Link to={`${base}/${outlet.id}/overview`}>{outlet.name}</Link></h4>
                <p>{outlet.code} · {title(outlet.outlet_type)}</p><p>{[outlet.city, outlet.state].filter(Boolean).join(', ')}</p>
                <p>Manager: {outlet.manager ? `${outlet.manager.first_name} ${outlet.manager.last_name}` : 'Not assigned'}</p>
                <p>Staff: {outlet.staff_count ?? '—'} · Revenue: — · Orders: —</p>
                <div className="outlet-card-actions"><Link className="ghost-button compact" to={`${base}/${outlet.id}/overview`}>View details</Link><Link className="ghost-button compact" to={`${base}/${outlet.id}/edit`}>Edit</Link>
                  <button type="button" className="ghost-button compact" disabled={busy === outlet.id} onClick={() => void mutate(outlet, outlet.is_deleted ? 'restore' : 'archive')}>{outlet.is_deleted ? 'Restore' : 'Archive'}</button></div>
              </article>
            ))}</div>}
        <div className="outlet-pagination"><button className="ghost-button compact" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page} of {Math.max(1, Math.ceil(total / pageSize))}</span><button className="ghost-button compact" disabled={page * pageSize >= total || loading} onClick={() => setPage(page + 1)}>Next</button></div>
      </section>
    </section>
  );
}
