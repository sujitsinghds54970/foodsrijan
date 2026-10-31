import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import LoginCredentialsPanel from '../../../components/auth/LoginCredentialsPanel';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import {
  BriefingIcon,
  EmpireIcon,
  IconBadge,
  LedgerIcon,
  OrbitIcon,
  PortfolioIcon,
  PulseIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage, companyManagementApi } from '../../../services/companyManagementApi';
import '../../../styles/company-management.css';

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'details', label: 'Details' },
  { key: 'ceo', label: 'CEO & Team' },
  { key: 'financials', label: 'Financials' },
  { key: 'digital', label: 'Digital Reach' },
  { key: 'audit', label: 'Audit Log' },
];

const DETAIL_GROUPS = [
  {
    title: 'Basic Identity',
    fields: [
      ['Name', 'name'],
      ['Slug', 'slug'],
      ['Tagline', 'tagline'],
      ['Description', 'description'],
      ['Founded', 'founded_date'],
      ['Onboarding', 'onboarding_status'],
      ['Lifecycle status', 'status'],
      ['Logo URL', 'logo_url'],
    ],
  },
  {
    title: 'Legal & Financial',
    fields: [
      ['Legal name', 'legal_name'],
      ['Registration number', 'registration_number'],
      ['GSTIN', 'gstin'],
      ['PAN', 'pan_number'],
      ['FSSAI license', 'fssai_license'],
      ['CIN', 'cin_number'],
      ['Annual revenue range', 'annual_revenue_range'],
      ['Funding stage', 'funding_stage'],
    ],
  },
  {
    title: 'Location & Regions',
    fields: [
      ['Registered address', 'registered_address'],
      ['Corporate address', 'corporate_address'],
      ['Headquarters city', 'headquarters_city'],
      ['State / region', 'headquarters_state'],
      ['Country', 'headquarters_country'],
      ['Postal code', 'headquarters_pincode'],
      ['Operating regions', 'operating_regions'],
    ],
  },
  {
    title: 'Business Classification',
    fields: [
      ['Business domain', 'business_domain'],
      ['Business sub-domains', 'sub_domains'],
      ['Target market', 'target_market'],
      ['Estimated employees', 'employee_count_estimate'],
      ['Declared branches', 'number_of_branches'],
      ['Business description', 'business_description'],
    ],
  },
  {
    title: 'Bank Details',
    fields: [
      ['Account name', 'bank_account_name'],
      ['Account number', 'bank_account_number'],
      ['IFSC code', 'ifsc_code'],
      ['Bank name', 'bank_name'],
    ],
  },
];

const DIGITAL_LINKS = [
  ['Website', 'website_url', OrbitIcon],
  ['LinkedIn', 'linkedin_url', BriefingIcon],
  ['Instagram', 'instagram_url', PulseIcon],
  ['Facebook', 'facebook_url', EmpireIcon],
  ['X / Twitter', 'twitter_url', PortfolioIcon],
  ['YouTube', 'youtube_url', PulseIcon],
  ['Mobile app', 'mobile_app_url', OrbitIcon],
];

const AUDIT_ACTIONS = [
  'company.created',
  'company.updated',
  'company.deleted',
  'company.restored',
  'ceo.assigned',
  'ceo.updated',
  'ceo.password_reset',
  'ceo.removed',
];

const emptyCeoForm = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  username: '',
  password: '',
  password_confirm: '',
};

const emptyCEOProfile = { first_name: '', last_name: '', email: '', phone: '' };
const emptyLoginTest = { username: '', password: '' };

const formatDateTime = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString();
};

const displayValue = (value) => {
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'Not provided';
  if (value === null || value === undefined || value === '') return 'Not provided';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
};

const isHttpUrl = (value) => {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol);
  } catch {
    return false;
  }
};

function SectionHeader({ eyebrow, title, action }) {
  return (
    <div className="panel-header">
      <div><p className="eyebrow">{eyebrow}</p><h3>{title}</h3></div>
      {action}
    </div>
  );
}

function FactGrid({ company, fields }) {
  return (
    <dl className="company-facts">
      {fields.map(([label, key]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>{displayValue(company[key])}</dd>
        </div>
      ))}
    </dl>
  );
}

function CredentialsPanel({ credentials, onClose }) {
  const copyPassword = async () => {
    try {
      await navigator.clipboard.writeText(credentials.password);
      toast.success('Temporary password copied');
    } catch {
      toast.error('Clipboard access is unavailable. Select and copy the password manually.');
    }
  };

  return (
    <div className="company-credentials" role="status">
      <div>
        <strong>Temporary credentials — save them now</strong>
        <p>The password is shown only in this response and will not be available again.</p>
      </div>
      <dl>
        <div><dt>Username</dt><dd>{credentials.username}</dd></div>
        <div><dt>Login</dt><dd>{credentials.login_url}</dd></div>
        <div><dt>Password</dt><dd><code>{credentials.password}</code></dd></div>
      </dl>
      <div className="company-edit-actions">
        <button type="button" className="ghost-button" onClick={copyPassword}>Copy password</button>
        <button type="button" className="primary-button" onClick={onClose}>I’ve saved these credentials</button>
      </div>
    </div>
  );
}

function AuditList({ events, showChanges = false }) {
  if (!events.length) {
    return <EmptyState title="No audit events" description="Company changes and executive actions will be recorded here." />;
  }
  return (
    <ol className="company-audit-list">
      {events.map((event) => (
        <li key={event.id}>
          <span className="company-audit-marker" aria-hidden="true" />
          <div>
            <strong>{event.action.replace(/\./g, ' ')}</strong>
            <small>Actor #{event.actor_id ?? '—'} · {formatDateTime(event.created_at)}</small>
            {showChanges && Object.keys(event.changes || {}).length > 0 && (
              <pre className="company-audit-changes">{JSON.stringify(event.changes, null, 2)}</pre>
            )}
          </div>
          <span className="company-audit-resource">Record #{event.resource_id ?? '—'}</span>
        </li>
      ))}
    </ol>
  );
}

export default function CompanyDetailPage() {
  const { companyId, companyTab } = useParams();
  const navigate = useNavigate();
  const id = Number(companyId);
  const requestedTab = companyTab || 'overview';
  const activeTab = TABS.some(({ key }) => key === requestedTab) ? requestedTab : 'overview';
  const [company, setCompany] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [audit, setAudit] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditAction, setAuditAction] = useState('');
  const [loading, setLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(true);
  const [error, setError] = useState('');
  const [auxiliaryError, setAuxiliaryError] = useState('');
  const [addingCEO, setAddingCEO] = useState(false);
  const [editingCEO, setEditingCEO] = useState(false);
  const [testingLogin, setTestingLogin] = useState(false);
  const [loginTest, setLoginTest] = useState(emptyLoginTest);
  const [ceoProfile, setCeoProfile] = useState(emptyCEOProfile);
  const [ceoForm, setCeoForm] = useState(emptyCeoForm);
  const [ceoSaving, setCeoSaving] = useState(false);
  const [credentials, setCredentials] = useState(null);
  const ceo = company?.ceo;
  const auditPageCount = Math.max(1, Math.ceil(auditTotal / 20));

  useEffect(() => {
    if (!Number.isInteger(id) || id < 1) return;
    if (!companyTab || companyTab !== activeTab) {
      navigate(`/super-ceo/business/companies/${id}/${activeTab}`, { replace: true });
    }
  }, [activeTab, companyTab, id, navigate]);

  const loadCompany = useCallback(async () => {
    if (!Number.isInteger(id) || id < 1) {
      setError('The company identifier is invalid.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [companyResult, metricsResult] = await Promise.allSettled([
        companyManagementApi.get(id),
        companyManagementApi.metrics(id),
      ]);
      if (companyResult.status === 'rejected') throw companyResult.reason;
      setCompany(companyResult.value.data.company);
      setMetrics(metricsResult.status === 'fulfilled' ? metricsResult.value.data.metrics : null);
      setAuxiliaryError(metricsResult.status === 'rejected' ? 'Company metrics are unavailable.' : '');
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Unable to load this company.'));
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadAudit = useCallback(async () => {
    if (!Number.isInteger(id) || id < 1) return;
    setAuditLoading(true);
    try {
      const response = await companyManagementApi.audit(id, {
        page: auditPage,
        page_size: 20,
        action: auditAction || undefined,
      });
      setAudit(response.data.events);
      setAuditTotal(response.data.total);
    } catch (requestError) {
      setAuxiliaryError(apiErrorMessage(requestError, 'The audit history is unavailable.'));
      setAudit([]);
      setAuditTotal(0);
    } finally {
      setAuditLoading(false);
    }
  }, [auditAction, auditPage, id]);

  useEffect(() => { void loadCompany(); }, [loadCompany]);
  useEffect(() => { void loadAudit(); }, [loadAudit]);

  const handleCeoSubmit = async (event) => {
    event.preventDefault();
    setCeoSaving(true);
    try {
      const response = await companyManagementApi.createCEO(id, ceoForm);
      if (response.data.credentials) setCredentials(response.data.credentials);
      setCeoForm(emptyCeoForm);
      setAddingCEO(false);
      toast.success('Company CEO assigned');
      await Promise.all([loadCompany(), loadAudit()]);
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to assign this CEO.'));
    } finally {
      setCeoSaving(false);
    }
  };

  const handleResetPassword = async () => {
    if (!window.confirm('Reset this CEO’s password? The temporary password will be shown once.')) return;
    try {
      const response = await companyManagementApi.resetCEOPassword(id);
      if (response.data.credentials) setCredentials(response.data.credentials);
      toast.success('CEO password reset');
      await Promise.all([loadCompany(), loadAudit()]);
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to reset the CEO password.'));
    }
  };

  const handleRemoveCEO = async () => {
    if (!window.confirm('Remove this CEO assignment? The account will lose this company assignment.')) return;
    try {
      await companyManagementApi.removeCEO(id);
      toast.success('CEO assignment removed');
      await Promise.all([loadCompany(), loadAudit()]);
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to remove the CEO assignment.'));
    }
  };

  const handleEditCEO = () => {
    setCeoProfile({
      first_name: ceo?.first_name || '',
      last_name: ceo?.last_name || '',
      email: ceo?.email || '',
      phone: ceo?.phone || '',
    });
    setEditingCEO(true);
  };

  const handleCEOProfileSubmit = async (event) => {
    event.preventDefault();
    try {
      await companyManagementApi.updateCEO(id, ceoProfile);
      setEditingCEO(false);
      toast.success('CEO profile updated');
      await Promise.all([loadCompany(), loadAudit()]);
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to update the CEO profile.'));
    }
  };

  const handleLoginTest = async (event) => {
    event.preventDefault();
    try {
      const response = await companyManagementApi.testCEOLogin(id, loginTest);
      response.data.valid ? toast.success('CEO credentials are valid') : toast.error('CEO credentials are not valid');
    } catch (requestError) {
      toast.error(apiErrorMessage(requestError, 'Unable to test the CEO login.'));
    }
  };

  const socialLinks = useMemo(
    () => DIGITAL_LINKS.filter(([, key]) => company?.[key]),
    [company],
  );

  if (loading) return <section className="company-admin"><LoadingSkeleton /></section>;
  if (error || !company) {
    return (
      <section className="company-admin">
        <div className="company-inline-error" role="alert">
          <strong>Company details unavailable</strong><p>{error || 'Company not found.'}</p>
          <Link className="ghost-button compact" to="/super-ceo/business/companies">Back to companies</Link>
        </div>
      </section>
    );
  }

  const headquarters = [
    company.headquarters_city,
    company.headquarters_state,
    company.headquarters_country,
  ].filter(Boolean).join(', ') || 'Headquarters not provided';

  return (
    <section className="company-admin company-detail-page">
      <div className="company-detail-breadcrumb">
        <Link to="/super-ceo/business/companies">← Back to Companies</Link>
      </div>

      <header className="exec-hero company-admin-hero company-detail-hero">
        <div className="company-detail-title">
          {company.logo_url && isHttpUrl(company.logo_url)
            ? <img className="company-logo" src={company.logo_url} alt="" />
            : <span className="company-avatar company-avatar-large" aria-hidden="true">{company.name.slice(0, 1).toUpperCase()}</span>}
          <div>
            <p className="eyebrow">{company.business_domain || 'Company'} · {company.status} · {headquarters}</p>
            <h2>{company.name}</h2>
            <p className="page-subtitle">{company.tagline || company.legal_name || 'Company profile and executive controls.'}</p>
          </div>
        </div>
        <div className="company-detail-actions">
          <span className={`company-status status-${company.status}`}>{company.status}</span>
          <Link className="ghost-button" to={`/super-ceo/business/companies/${id}/edit`}>Edit</Link>
          <button type="button" className="ghost-button compact" aria-label="Refresh company data" onClick={() => { void loadCompany(); void loadAudit(); }}>↻</button>
        </div>
      </header>

      <nav className="company-tab-strip" aria-label="Company sections">
        {TABS.map((tab) => (
          <Link
            className={activeTab === tab.key ? 'active' : ''}
            aria-current={activeTab === tab.key ? 'page' : undefined}
            to={`/super-ceo/business/companies/${id}/${tab.key}`}
            key={tab.key}
          >
            {tab.label}
          </Link>
        ))}
      </nav>

      {auxiliaryError && <p className="company-inline-note" role="status">{auxiliaryError}</p>}

      {activeTab === 'overview' && (
        <div className="company-tab-content">
          <section className="company-stat-grid" aria-label="Company metrics">
            {[
              ['Active branches', metrics?.branches, OrbitIcon],
              ['Employees', metrics?.employees, PulseIcon],
              ['Customers', metrics?.customers, EmpireIcon],
              ['Recorded revenue', metrics?.revenue == null ? null : new Intl.NumberFormat(undefined, { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(metrics.revenue), LedgerIcon],
            ].map(([label, value, Icon]) => (
              <article className="company-stat-card" key={label}>
                <IconBadge tone="gold"><Icon size={18} /></IconBadge>
                <span>{label}</span>
                <strong>{value == null ? '—' : typeof value === 'number' ? value.toLocaleString() : value}</strong>
              </article>
            ))}
          </section>
          <div className="company-detail-grid">
            <section className="panel">
              <SectionHeader eyebrow="Company narrative" title="About the business" />
              <p className="company-bio">{company.description || company.business_description || 'No company biography has been provided yet.'}</p>
              <div className="company-digital-compact">
                {socialLinks.length ? socialLinks.map(([label, key, Icon]) => (
                  <a href={company[key]} target="_blank" rel="noreferrer" key={key}><Icon size={17} />{label}</a>
                )) : <span>No digital channels recorded</span>}
              </div>
            </section>
            <section className="panel company-audit-panel">
              <SectionHeader eyebrow="Governance" title="Recent activity" action={<Link className="ghost-button compact" to={`/super-ceo/business/companies/${id}/audit`}>View all</Link>} />
              {auditLoading ? <LoadingSkeleton /> : <AuditList events={audit.slice(0, 5)} />}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'details' && (
        <div className="company-tab-content company-detail-sections">
          {DETAIL_GROUPS.map((group) => (
            <section className="panel" key={group.title}>
              <SectionHeader
                eyebrow="Company record"
                title={group.title}
                action={group.title === 'Basic Identity' ? <Link className="ghost-button compact" to={`/super-ceo/business/companies/${id}/edit`}>Edit in wizard</Link> : null}
              />
              <FactGrid company={company} fields={group.fields} />
            </section>
          ))}
        </div>
      )}

      {activeTab === 'ceo' && (
        <div className="company-tab-content company-detail-grid">
          <section className="panel company-ceo-panel">
            <SectionHeader eyebrow="Leadership & access" title="Company CEO" />
            {ceo ? (
              <>
                <div className="company-ceo-card">
                  <span className="company-avatar" aria-hidden="true">{(ceo.first_name || ceo.username).slice(0, 1).toUpperCase()}</span>
                  <div>
                    <strong>{`${ceo.first_name || ''} ${ceo.last_name || ''}`.trim() || ceo.username}</strong>
                    <small>{ceo.email}</small>
                    <small>{ceo.phone || 'Phone not provided'} · @{ceo.username}</small>
                  </div>
                  <span className={`company-status ${ceo.is_active ? 'status-active' : 'status-inactive'}`}>{ceo.is_active ? 'Active' : 'Inactive'}</span>
                </div>
                <p className="company-ceo-meta">
                  Assigned {formatDateTime(ceo.ceo_assigned_at)} · {ceo.force_password_change ? 'Force password change enabled' : 'Password current'}
                </p>
                <div className="company-ceo-actions">
                  <button type="button" className="ghost-button compact" onClick={handleEditCEO}>Edit Profile</button>
                  <button type="button" className="ghost-button compact" onClick={handleResetPassword}>Reset Password</button>
                  <button type="button" className="ghost-button compact company-danger-action" onClick={handleRemoveCEO}>Remove Assignment</button>
                  <button type="button" className="ghost-button compact" onClick={() => { setLoginTest({ username: ceo.username, password: '' }); setTestingLogin(true); }}>Test Login</button>
                </div>
                <LoginCredentialsPanel endpoint={`/api/super-ceo/companies/${id}/ceo/credentials`} onUpdated={(login) => setCompany((current) => ({ ...current, ceo: { ...current.ceo, ...login } }))} />
              </>
            ) : (
              <>
                <EmptyState title="No company CEO assigned" description="Create an executive account to give this company an assigned leader." />
                {!addingCEO && <button type="button" className="primary-button company-action-button" onClick={() => setAddingCEO(true)}>Assign CEO</button>}
              </>
            )}

            {editingCEO && ceo && (
              <form className="company-ceo-form" onSubmit={handleCEOProfileSubmit}>
                <SectionHeader eyebrow="Secure profile update" title="Edit CEO profile" action={<button type="button" className="ghost-button compact" onClick={() => setEditingCEO(false)}>Cancel</button>} />
                <div className="company-form-grid">
                  {[
                    ['first_name', 'First name', 'text'],
                    ['last_name', 'Last name', 'text'],
                    ['email', 'Email', 'email'],
                    ['phone', 'Phone', 'tel'],
                  ].map(([name, label, type]) => (
                    <label className="company-form-field" key={name}><span>{label}</span><input name={name} type={type} value={ceoProfile[name]} onChange={(event) => setCeoProfile((current) => ({ ...current, [name]: event.target.value }))} required /></label>
                  ))}
                </div>
                <button type="submit" className="primary-button">Save CEO profile</button>
              </form>
            )}

            {addingCEO && (
              <form className="company-ceo-form" onSubmit={handleCeoSubmit}>
                <SectionHeader eyebrow="Leadership access" title="New CEO credentials" action={<button type="button" className="ghost-button compact" onClick={() => setAddingCEO(false)}>Cancel</button>} />
                <div className="company-form-grid">
                  {[
                    ['first_name', 'First name', 'text'],
                    ['last_name', 'Last name', 'text'],
                    ['email', 'Email', 'email'],
                    ['phone', 'Phone', 'tel'],
                    ['username', 'Username', 'text'],
                    ['password', 'Temporary password', 'password'],
                    ['password_confirm', 'Confirm password', 'password'],
                  ].map(([name, label, type]) => (
                    <label className="company-form-field" key={name}><span>{label}</span><input name={name} type={type} value={ceoForm[name]} onChange={(event) => setCeoForm((current) => ({ ...current, [name]: event.target.value }))} required minLength={name.startsWith('password') ? 12 : undefined} autoComplete={name.startsWith('password') ? 'new-password' : undefined} /></label>
                  ))}
                </div>
                <p className="company-form-footnote">The temporary password is returned once. Store it securely and ask the CEO to change it after sign-in.</p>
                <button type="submit" className="primary-button" disabled={ceoSaving}>{ceoSaving ? 'Assigning…' : 'Create CEO account'}</button>
              </form>
            )}

            {testingLogin && ceo && (
              <form className="company-ceo-form" onSubmit={handleLoginTest}>
                <SectionHeader eyebrow="Credential verification" title="Test CEO login" action={<button type="button" className="ghost-button compact" onClick={() => setTestingLogin(false)}>Cancel</button>} />
                <div className="company-form-grid">
                  <label className="company-form-field"><span>Username</span><input value={loginTest.username} onChange={(event) => setLoginTest((current) => ({ ...current, username: event.target.value }))} required /></label>
                  <label className="company-form-field"><span>Password</span><input type="password" value={loginTest.password} onChange={(event) => setLoginTest((current) => ({ ...current, password: event.target.value }))} required /></label>
                </div>
                <button type="submit" className="primary-button">Verify credentials</button>
              </form>
            )}
          </section>

          <section className="panel company-team-placeholder">
            <SectionHeader eyebrow="Leadership pipeline" title="Executive team" />
            <IconBadge tone="violet"><EmpireIcon size={22} /></IconBadge>
            <h4>Department Heads will appear here</h4>
            <p>This leadership layer is planned for Phase 4.</p>
          </section>
          {credentials && <section className="panel company-credential-panel company-detail-span"><CredentialsPanel credentials={credentials} onClose={() => setCredentials(null)} /></section>}
        </div>
      )}

      {activeTab === 'financials' && (
        <div className="company-tab-content company-detail-grid">
          <section className="panel">
            <SectionHeader eyebrow="Financial identity" title="Compliance & capital" />
            <FactGrid company={company} fields={[
              ['GSTIN', 'gstin'],
              ['PAN', 'pan_number'],
              ['FSSAI license', 'fssai_license'],
              ['Annual revenue range', 'annual_revenue_range'],
              ['Funding stage', 'funding_stage'],
            ]} />
          </section>
          <section className="panel">
            <SectionHeader eyebrow="Banking" title="Settlement account" />
            <FactGrid company={company} fields={[
              ['Account name', 'bank_account_name'],
              ['Account number', 'bank_account_number'],
              ['IFSC code', 'ifsc_code'],
              ['Bank name', 'bank_name'],
            ]} />
          </section>
          <section className="panel company-phase-placeholder company-detail-span">
            <IconBadge tone="gold"><LedgerIcon size={22} /></IconBadge>
            <div><h4>Revenue charts coming in Phase 2</h4><p>Trend and reconciliation views will appear after the approved finance integration.</p></div>
          </section>
        </div>
      )}

      {activeTab === 'digital' && (
        <div className="company-tab-content">
          <section className="company-digital-grid" aria-label="Company digital channels">
            {DIGITAL_LINKS.map(([label, key, Icon]) => (
              company[key] && isHttpUrl(company[key]) ? (
                <a className="company-digital-card" href={company[key]} target="_blank" rel="noreferrer" key={key}>
                  <IconBadge tone="teal"><Icon size={20} /></IconBadge><span>{label}</span><small>{company[key]}</small>
                </a>
              ) : (
                <article className="company-digital-card unavailable" key={key}>
                  <IconBadge tone="neutral"><Icon size={20} /></IconBadge><span>{label}</span><small>Not connected</small>
                </article>
              )
            ))}
          </section>
          <section className="panel company-contact-panel">
            <SectionHeader eyebrow="Direct channels" title="Support contacts" />
            <div className="company-contact-links">
              <a href={company.support_email ? `mailto:${company.support_email}` : undefined} aria-disabled={!company.support_email}>{company.support_email || 'Support email not provided'}</a>
              <a href={company.support_phone ? `tel:${company.support_phone}` : undefined} aria-disabled={!company.support_phone}>{company.support_phone || 'Support phone not provided'}</a>
            </div>
          </section>
          <section className="panel company-phase-placeholder">
            <IconBadge tone="violet"><PulseIcon size={22} /></IconBadge>
            <div><h4>Social media analytics coming in Phase 2</h4><p>Audience growth, engagement, and channel health will appear here.</p></div>
          </section>
        </div>
      )}

      {activeTab === 'audit' && (
        <section className="panel company-tab-content company-audit-panel">
          <SectionHeader eyebrow="Governance" title="Full audit history" action={<span className="company-register-total">{auditTotal} events</span>} />
          <div className="company-audit-toolbar">
            <label className="company-filter-field">
              <span>Action type</span>
              <select value={auditAction} onChange={(event) => { setAuditAction(event.target.value); setAuditPage(1); }}>
                <option value="">All actions</option>
                {AUDIT_ACTIONS.map((action) => <option value={action} key={action}>{action.replace(/\./g, ' ')}</option>)}
              </select>
            </label>
          </div>
          {auditLoading ? <LoadingSkeleton /> : <AuditList events={audit} showChanges />}
          <div className="company-pagination">
            <span>Showing page {auditPage} of {auditPageCount}</span>
            <div>
              <button type="button" className="ghost-button compact" disabled={auditPage <= 1 || auditLoading} onClick={() => setAuditPage((page) => page - 1)}>Previous</button>
              <span>{auditTotal.toLocaleString()} total</span>
              <button type="button" className="ghost-button compact" disabled={auditPage >= auditPageCount || auditLoading} onClick={() => setAuditPage((page) => page + 1)}>Next</button>
            </div>
          </div>
        </section>
      )}
    </section>
  );
}
