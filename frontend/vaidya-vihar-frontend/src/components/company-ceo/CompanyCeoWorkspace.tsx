import { useEffect, useMemo, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import {
  AuditTrailIcon,
  BriefingIcon,
  CommandIcon,
  EmpireIcon,
  IconBadge,
  LedgerIcon,
  OrbitIcon,
  PortfolioIcon,
  PulseIcon,
  ShieldIcon,
} from '../SuperCEO/icons';
import KpiCard from '../SuperCEO/common/KpiCard';
import LoadingSkeleton from '../SuperCEO/common/LoadingSkeleton';
import { useAuth } from '../../contexts/AuthContext';
import { companyCeoApi, type CompanyCeoWorkspaceData } from '../../services/companyCeoApi';
import { apiErrorMessage } from '../../services/companyManagementApi';
import '@fontsource/fraunces/500.css';
import '@fontsource/fraunces/600.css';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/manrope/700.css';
import '../../styles/exec-tokens.css';
import '../../styles/company-ceo.css';

const NAV_ITEMS = [
  { id: 'overview', label: 'Command Overview', icon: BriefingIcon },
  { id: 'profile', label: 'Company Profile', icon: PortfolioIcon },
  { id: 'leadership', label: 'Leadership', icon: EmpireIcon },
  { id: 'operations', label: 'Operations', icon: OrbitIcon },
  { id: 'governance', label: 'Governance', icon: ShieldIcon },
];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value || 0);

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString();
};

const valueOrFallback = (value: unknown) => {
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'Not provided';
  return value === null || value === undefined || value === '' ? 'Not provided' : String(value);
};

function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="company-ceo-page-header">
      <p>{eyebrow}</p>
      <h1>{title}</h1>
      <span>{description}</span>
    </header>
  );
}

function FactPanel({ title, fields, company }: { title: string; fields: Array<[string, keyof CompanyCeoWorkspaceData['company']]>; company: CompanyCeoWorkspaceData['company'] }) {
  return (
    <section className="company-ceo-panel">
      <h2>{title}</h2>
      <dl className="company-ceo-facts">
        {fields.map(([label, key]) => <div key={key}><dt>{label}</dt><dd>{valueOrFallback(company[key])}</dd></div>)}
      </dl>
    </section>
  );
}

function Overview({ data }: { data: CompanyCeoWorkspaceData }) {
  const { company, executive, metrics, audit } = data;
  return (
    <>
      <section className="company-ceo-hero">
        <div>
          <p>Company command · Live scope</p>
          <h1>Good day, {executive.first_name}</h1>
          <span>{company.name} is your active executive context. Every signal below is isolated to this company.</span>
        </div>
        <div className="company-ceo-hero-status"><i /> Active company scope<strong>{company.name}</strong></div>
      </section>
      <section className="company-ceo-kpis metric-grid four-up">
        <KpiCard label="Active Branches" value={metrics.branches} tone="teal" icon={OrbitIcon} source="Source · branch registry" />
        <KpiCard label="Employees" value={metrics.employees} tone="violet" icon={EmpireIcon} source="Source · employee records" />
        <KpiCard label="Customers" value={metrics.customers} tone="gold" icon={PulseIcon} source="Source · customer records" />
        <KpiCard label="Recorded Revenue" value={formatCurrency(metrics.revenue)} tone="sunset" icon={LedgerIcon} source="Source · daily analytics" />
      </section>
      <div className="company-ceo-grid">
        <section className="company-ceo-panel">
          <div className="company-ceo-panel-heading"><div><p>Executive brief</p><h2>Company pulse</h2></div><IconBadge tone="gold"><BriefingIcon size={19} /></IconBadge></div>
          <p className="company-ceo-narrative">{company.description || company.business_description || 'Add a company description to establish the operating narrative for your leadership team.'}</p>
          <div className="company-ceo-signal-grid">
            <div><span>Active users</span><strong>{metrics.active_users}</strong></div>
            <div><span>Brands</span><strong>{data.brands.filter((brand) => brand.is_active).length}</strong></div>
            <div><span>Departments</span><strong>{data.departments.filter((department) => department.is_active).length}</strong></div>
            <div><span>Onboarding</span><strong>{company.onboarding_status || 'Not set'}</strong></div>
          </div>
        </section>
        <section className="company-ceo-panel">
          <div className="company-ceo-panel-heading"><div><p>Governance stream</p><h2>Recent activity</h2></div><IconBadge tone="rose"><AuditTrailIcon size={19} /></IconBadge></div>
          <ul className="company-ceo-activity">
            {audit.events.slice(0, 5).map((event) => <li key={event.id}><i /><div><strong>{event.action.replace(/\./g, ' ')}</strong><span>{formatDateTime(event.created_at)}</span></div></li>)}
            {!audit.events.length && <li className="empty">No company activity has been recorded yet.</li>}
          </ul>
        </section>
      </div>
    </>
  );
}

function Profile({ data }: { data: CompanyCeoWorkspaceData }) {
  return (
    <>
      <PageHeader eyebrow="Company identity" title={data.company.name} description="The authoritative operating, legal, and digital profile for your assigned company." />
      <div className="company-ceo-grid">
        <FactPanel title="Identity" company={data.company} fields={[['Legal name', 'legal_name'], ['Business domain', 'business_domain'], ['Tagline', 'tagline'], ['Founded', 'founded_date'], ['Funding stage', 'funding_stage'], ['Target market', 'target_market']]} />
        <FactPanel title="Location" company={data.company} fields={[['Headquarters city', 'headquarters_city'], ['State', 'headquarters_state'], ['Country', 'headquarters_country'], ['Postal code', 'headquarters_pincode'], ['Operating regions', 'operating_regions'], ['Registered address', 'registered_address']]} />
        <FactPanel title="Compliance" company={data.company} fields={[['Registration number', 'registration_number'], ['GSTIN', 'gstin'], ['PAN', 'pan_number'], ['FSSAI license', 'fssai_license'], ['CIN', 'cin_number'], ['Annual revenue range', 'annual_revenue_range']]} />
        <FactPanel title="Contact & digital" company={data.company} fields={[['Website', 'website_url'], ['Support email', 'support_email'], ['Support phone', 'support_phone'], ['LinkedIn', 'linkedin_url'], ['Instagram', 'instagram_url'], ['Mobile app', 'mobile_app_url']]} />
      </div>
    </>
  );
}

function Leadership({ data }: { data: CompanyCeoWorkspaceData }) {
  const executive = data.executive;
  return (
    <>
      <PageHeader eyebrow="People command" title="Leadership" description="Your executive identity and the company’s active organizational structure." />
      <section className="company-ceo-panel company-ceo-leader-card">
        <div className="company-ceo-avatar">{`${executive.first_name[0] || ''}${executive.last_name[0] || ''}`}</div>
        <div><p>Assigned Company CEO</p><h2>{executive.first_name} {executive.last_name}</h2><span>{executive.email} · {executive.phone}</span><small>@{executive.username} · Assigned {formatDateTime(executive.ceo_assigned_at)}</small></div>
        <span className="company-ceo-status"><i /> Active</span>
      </section>
      <div className="company-ceo-grid">
        <section className="company-ceo-panel">
          <div className="company-ceo-panel-heading"><div><p>Organization</p><h2>Departments</h2></div><strong>{data.departments.length}</strong></div>
          <div className="company-ceo-entity-list">{data.departments.map((department) => <article key={department.id}><IconBadge tone="violet"><CommandIcon size={18} /></IconBadge><div><strong>{department.name}</strong><span>{department.description || department.code || 'Department profile'}</span></div><small>{department.is_active ? 'Active' : 'Inactive'}</small></article>)}{!data.departments.length && <p className="company-ceo-empty">No departments have been configured.</p>}</div>
        </section>
        <section className="company-ceo-panel">
          <div className="company-ceo-panel-heading"><div><p>Portfolio architecture</p><h2>Brands</h2></div><strong>{data.brands.length}</strong></div>
          <div className="company-ceo-entity-list">{data.brands.map((brand) => <article key={brand.id}><IconBadge tone="gold"><PortfolioIcon size={18} /></IconBadge><div><strong>{brand.name}</strong><span>{brand.description || brand.slug}</span></div><small>{brand.is_active ? 'Active' : 'Inactive'}</small></article>)}{!data.brands.length && <p className="company-ceo-empty">No brands have been configured.</p>}</div>
        </section>
      </div>
    </>
  );
}

function Operations({ data }: { data: CompanyCeoWorkspaceData }) {
  return (
    <>
      <PageHeader eyebrow="Operating network" title="Operations" description="A company-scoped view of branches and declared operating coverage." />
      <section className="company-ceo-panel">
        <div className="company-ceo-panel-heading"><div><p>Branch network</p><h2>Operating locations</h2></div><strong>{data.branches.length}</strong></div>
        <div className="company-ceo-branch-grid">
          {data.branches.map((branch) => <article key={branch.id}><IconBadge tone="teal"><OrbitIcon size={20} /></IconBadge><div><h3>{branch.name}</h3><p>{branch.city}, {branch.state}</p><span>{branch.branch_code}</span></div><small className={branch.is_active ? 'active' : ''}>{branch.is_active ? 'Active' : 'Inactive'}</small></article>)}
          {!data.branches.length && <p className="company-ceo-empty">No branch records are connected to this company yet.</p>}
        </div>
      </section>
      <section className="company-ceo-panel company-ceo-roadmap"><IconBadge tone="sunset"><PulseIcon size={22} /></IconBadge><div><h2>Operational analytics foundation ready</h2><p>Inventory, supply chain, workforce, and revenue drilldowns can be connected here in the next approved phase.</p></div></section>
    </>
  );
}

function Governance({ data }: { data: CompanyCeoWorkspaceData }) {
  return (
    <>
      <PageHeader eyebrow="Control & accountability" title="Governance" description="Immutable company activity and key compliance identifiers within your assigned scope." />
      <div className="company-ceo-grid governance">
        <section className="company-ceo-panel">
          <div className="company-ceo-panel-heading"><div><p>Compliance posture</p><h2>Registered identifiers</h2></div><IconBadge tone="rose"><ShieldIcon size={19} /></IconBadge></div>
          <dl className="company-ceo-facts"><div><dt>GSTIN</dt><dd>{valueOrFallback(data.company.gstin)}</dd></div><div><dt>PAN</dt><dd>{valueOrFallback(data.company.pan_number)}</dd></div><div><dt>FSSAI</dt><dd>{valueOrFallback(data.company.fssai_license)}</dd></div><div><dt>CIN</dt><dd>{valueOrFallback(data.company.cin_number)}</dd></div></dl>
        </section>
        <section className="company-ceo-panel">
          <div className="company-ceo-panel-heading"><div><p>Audit assurance</p><h2>Company audit trail</h2></div><strong>{data.audit.total}</strong></div>
          <ul className="company-ceo-activity full">{data.audit.events.map((event) => <li key={event.id}><i /><div><strong>{event.action.replace(/\./g, ' ')}</strong><span>Actor #{event.actor_id ?? '—'} · {formatDateTime(event.created_at)}</span></div></li>)}{!data.audit.events.length && <li className="empty">No audit events recorded.</li>}</ul>
        </section>
      </div>
    </>
  );
}

export default function CompanyCeoWorkspace() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [data, setData] = useState<CompanyCeoWorkspaceData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Company CEO';
  const initials = fullName.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  const activeLabel = useMemo(() => NAV_ITEMS.find((item) => location.pathname.endsWith(`/${item.id}`))?.label || 'Command Overview', [location.pathname]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await companyCeoApi.workspace();
      setData(response.data);
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to load your company workspace.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  if (loading) return <main className="company-ceo-loading"><LoadingSkeleton /></main>;
  if (error || !data) return <main className="company-ceo-loading"><div className="company-ceo-error" role="alert"><strong>Company workspace unavailable</strong><p>{error}</p><button type="button" onClick={() => void load()}>Retry</button></div></main>;

  return (
    <div className="company-ceo-shell">
      <a className="company-ceo-skip" href="#company-ceo-content">Skip to content</a>
      {sidebarOpen && <button type="button" className="company-ceo-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`company-ceo-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <button type="button" className="company-ceo-close" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}>×</button>
        <div className="company-ceo-brand"><div>FS</div><span><strong>{data.company.name}</strong><small>Executive Command</small></span></div>
        <section className="company-ceo-identity"><div className="company-ceo-avatar">{initials}</div><div><strong>{fullName}</strong><span>Company CEO</span></div><i /></section>
        <nav aria-label="Company CEO navigation">{NAV_ITEMS.map(({ id, label, icon: Icon }) => <NavLink key={id} to={`/company-ceo/${id}`} onClick={() => setSidebarOpen(false)} className={({ isActive }) => isActive ? 'active' : ''}><IconBadge tone={id === 'operations' ? 'teal' : id === 'governance' ? 'rose' : id === 'leadership' ? 'violet' : 'gold'}><Icon size={18} /></IconBadge><span>{label}</span></NavLink>)}</nav>
        <div className="company-ceo-scope"><span>Active company scope</span><strong>{data.company.name}</strong><small>Company ID {data.company.id}</small></div>
        <button type="button" className="company-ceo-signout" onClick={logout}>Sign out</button>
      </aside>
      <div className="company-ceo-main">
        <header className="company-ceo-topbar"><button type="button" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}><CommandIcon size={19} /></button><div><span>Company CEO · Executive Command</span><strong>{activeLabel}</strong></div><div className="company-ceo-topbar-scope"><i />{data.company.name}</div></header>
        <main id="company-ceo-content" className="company-ceo-content">
          <Routes>
            <Route path="/company-ceo/overview" element={<Overview data={data} />} />
            <Route path="/company-ceo/profile" element={<Profile data={data} />} />
            <Route path="/company-ceo/leadership" element={<Leadership data={data} />} />
            <Route path="/company-ceo/operations" element={<Operations data={data} />} />
            <Route path="/company-ceo/governance" element={<Governance data={data} />} />
            <Route path="*" element={<Navigate to="/company-ceo/overview" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
