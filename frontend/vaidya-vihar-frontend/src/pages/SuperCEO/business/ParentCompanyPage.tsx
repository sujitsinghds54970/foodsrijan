import { CSSProperties, ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import RoutedTabs, { RoutedTab } from '../../../components/SuperCEO/common/RoutedTabs';
import useExecutiveEventStream from '../../../hooks/useExecutiveEventStream';
import {
  AuditTrailIcon,
  BriefingIcon,
  GavelIcon,
  LedgerIcon,
  PortfolioIcon,
  SparkIcon,
} from '../../../components/SuperCEO/icons';
import {
  ParentCompany,
  ParentCompanyAudit,
  ParentCompanyUpdate,
  parentCompanyApi,
  resolveAssetUrl,
  requestErrorMessage,
  superCeoProfileApi,
} from '../../../services/superCeoProfileApi';

const BASE_PATH = '/super-ceo/system/parent-company';
const DEFAULT_TAB = 'identity';
const AUDIT_PAGE_SIZE = 10;
const LIVE_EVENTS = ['parent_company.published'];

const tabs: RoutedTab[] = [
  { id: 'identity', label: 'Identity', icon: <PortfolioIcon size={16} /> },
  { id: 'brand', label: 'Brand', icon: <SparkIcon size={16} /> },
  { id: 'digital', label: 'Digital', icon: <BriefingIcon size={16} /> },
  { id: 'legal', label: 'Legal', icon: <GavelIcon size={16} /> },
  { id: 'financial', label: 'Financial', icon: <LedgerIcon size={16} /> },
  { id: 'audit', label: 'Audit', icon: <AuditTrailIcon size={16} /> },
];
const validTabs = new Set(tabs.map((tab) => tab.id));

type ParentCompanyField =
  | 'name' | 'tagline' | 'description' | 'logo_url' | 'banner_url'
  | 'primary_color' | 'secondary_color' | 'accent_color' | 'display_font' | 'body_font'
  | 'founded_date' | 'legal_name' | 'registration_number' | 'gstin' | 'pan_number' | 'fssai_license' | 'cin_number'
  | 'bank_account_name' | 'bank_account_number' | 'ifsc_code' | 'bank_name' | 'annual_revenue_range' | 'funding_stage' | 'last_funding_round_date' | 'total_funding_raised'
  | 'registered_address' | 'corporate_address' | 'headquarters_city' | 'headquarters_state' | 'headquarters_country' | 'headquarters_pincode'
  | 'website_url' | 'linkedin_url' | 'instagram_url' | 'facebook_url' | 'twitter_url' | 'youtube_url' | 'ios_app_url' | 'android_app_url'
  | 'support_email' | 'support_phone' | 'whatsapp_business_number' | 'business_domain' | 'sub_domains' | 'target_market' | 'employee_count_estimate';

interface CompanyFieldSpec {
  key: ParentCompanyField;
  label: string;
  type?: 'text' | 'email' | 'tel' | 'url' | 'date' | 'number' | 'textarea' | 'color' | 'select';
  wide?: boolean;
  hint?: string;
  options?: string[];
}

const fieldGroups: Record<string, CompanyFieldSpec[]> = {
  identity: [
    { key: 'name', label: 'Group name' },
    { key: 'tagline', label: 'Tagline' },
    { key: 'founded_date', label: 'Founded date', type: 'date' },
    { key: 'business_domain', label: 'Business domain' },
    { key: 'target_market', label: 'Target market', type: 'select', options: ['India', 'International', 'Both'] },
    { key: 'employee_count_estimate', label: 'Estimated employee count' },
    { key: 'description', label: 'Group description', type: 'textarea', wide: true },
  ],
  brand: [
    { key: 'primary_color', label: 'Primary color', type: 'color' },
    { key: 'secondary_color', label: 'Secondary color', type: 'color' },
    { key: 'accent_color', label: 'Accent color', type: 'color' },
    { key: 'display_font', label: 'Display font' },
    { key: 'body_font', label: 'Body font' },
  ],
  digital: [
    { key: 'website_url', label: 'Website', type: 'url' },
    { key: 'support_email', label: 'Support email', type: 'email' },
    { key: 'support_phone', label: 'Support phone', type: 'tel' },
    { key: 'whatsapp_business_number', label: 'WhatsApp business number', type: 'tel' },
    { key: 'linkedin_url', label: 'LinkedIn', type: 'url' },
    { key: 'instagram_url', label: 'Instagram', type: 'url' },
    { key: 'facebook_url', label: 'Facebook', type: 'url' },
    { key: 'twitter_url', label: 'X / Twitter', type: 'url' },
    { key: 'youtube_url', label: 'YouTube', type: 'url' },
    { key: 'ios_app_url', label: 'iOS app', type: 'url' },
    { key: 'android_app_url', label: 'Android app', type: 'url' },
    { key: 'sub_domains', label: 'Operating sub-domains', type: 'textarea', wide: true, hint: 'Separate multiple sub-domains with commas.' },
  ],
  legal: [
    { key: 'legal_name', label: 'Registered legal name', wide: true },
    { key: 'registration_number', label: 'Registration number' },
    { key: 'gstin', label: 'GSTIN' },
    { key: 'pan_number', label: 'PAN' },
    { key: 'fssai_license', label: 'FSSAI license' },
    { key: 'cin_number', label: 'CIN' },
    { key: 'headquarters_city', label: 'Headquarters city' },
    { key: 'headquarters_state', label: 'State / region' },
    { key: 'headquarters_country', label: 'Country' },
    { key: 'headquarters_pincode', label: 'Postal code' },
    { key: 'registered_address', label: 'Registered address', type: 'textarea', wide: true },
    { key: 'corporate_address', label: 'Corporate address', type: 'textarea', wide: true },
  ],
  financial: [
    { key: 'annual_revenue_range', label: 'Annual revenue range', hint: 'Example: 1-10Cr' },
    { key: 'funding_stage', label: 'Funding stage', hint: 'Example: Seed, Series A, Bootstrapped' },
    { key: 'last_funding_round_date', label: 'Last funding round date', type: 'date' },
    { key: 'total_funding_raised', label: 'Total funding raised', type: 'number' },
    { key: 'bank_account_name', label: 'Bank account name' },
    { key: 'bank_account_number', label: 'Bank account number' },
    { key: 'ifsc_code', label: 'IFSC code' },
    { key: 'bank_name', label: 'Bank name' },
  ],
  audit: [],
};

const allFields: ParentCompanyField[] = [
  ...Object.values(fieldGroups).flat().map((field) => field.key),
  'logo_url',
  'banner_url',
];

type ParentCompanyForm = Partial<Record<ParentCompanyField, string>>;

const formFromCompany = (published: ParentCompany, draft?: Partial<ParentCompany> | null): ParentCompanyForm => {
  const source = { ...published, ...(draft || {}) };
  const form: ParentCompanyForm = {};
  allFields.forEach((field) => {
    const value = source[field];
    form[field] = Array.isArray(value) ? value.join(', ') : value == null ? '' : String(value);
  });
  return form;
};

const payloadFromForm = (form: ParentCompanyForm): ParentCompanyUpdate => {
  const payload: ParentCompanyUpdate = { name: (form.name || '').trim() };
  allFields.forEach((field) => {
    const value = form[field]?.trim() || null;
    if (field === 'name') {
      payload.name = value || '';
    } else if (field === 'sub_domains') {
      payload.sub_domains = value ? value.split(',').map((domain) => domain.trim()).filter(Boolean) : [];
    } else {
      payload[field] = value;
    }
  });
  return payload;
};

const dateLabel = (value?: string | null) => {
  if (!value) return 'Not published yet';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

function CompanyField({ field, value, onChange }: { field: CompanyFieldSpec; value: string; onChange: (value: string) => void }) {
  const inputId = `parent-company-${field.key}`;
  const shared = {
    id: inputId,
    value,
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => onChange(event.target.value),
  };
  return (
    <label className={`exec-profile-field${field.wide ? ' is-wide' : ''}`} htmlFor={inputId}>
      <span>{field.label}</span>
      {field.type === 'textarea' ? (
        <textarea {...shared} rows={4} />
      ) : field.type === 'select' ? (
        <select {...shared}>
          <option value="">Choose a market</option>
          {(field.options || []).map((option) => <option value={option} key={option}>{option}</option>)}
        </select>
      ) : field.type === 'color' ? (
        <span className="exec-color-field">
          <input {...shared} type="text" placeholder="#D6A84F" pattern="^#[0-9A-Fa-f]{6}$" />
          <input
            type="color"
            value={/^#[0-9A-Fa-f]{6}$/.test(value) ? value : '#d6a84f'}
            aria-label={`Choose ${field.label.toLowerCase()}`}
            onChange={(event) => onChange(event.target.value)}
          />
        </span>
      ) : (
        <input {...shared} type={field.type || 'text'} autoComplete="off" />
      )}
      {field.hint && <small className="exec-field-hint">{field.hint}</small>}
    </label>
  );
}

function ImageUpload({
  title, value, busy, onFile, isBanner = false,
}: {
  title: string;
  value: string;
  busy: boolean;
  onFile: (file: File) => void;
  isBanner?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className={`exec-profile-upload exec-company-image${isBanner ? ' is-cover' : ''}`}>
      <div className="exec-profile-upload-preview">
        {value ? <img src={resolveAssetUrl(value)} alt={`${title} preview`} /> : <PortfolioIcon size={isBanner ? 28 : 24} />}
      </div>
      <div className="exec-profile-upload-copy">
        <strong>{title}</strong>
        <span>PNG, JPG, WebP or SVG · maximum 5 MB</span>
        <button type="button" className="exec-button exec-button-secondary" disabled={busy} onClick={() => inputRef.current?.click()}>
          {busy ? 'Uploading…' : value ? 'Replace image' : 'Upload image'}
        </button>
      </div>
      <input
        ref={inputRef}
        className="exec-visually-hidden"
        type="file"
        accept="image/png,image/jpeg,image/webp,image/svg+xml"
        aria-label={`Upload ${title.toLowerCase()}`}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onFile(file);
          event.target.value = '';
        }}
      />
    </div>
  );
}

export default function ParentCompanyPage() {
  const { companyTab } = useParams();
  const navigate = useNavigate();
  const activeTabId = companyTab && validTabs.has(companyTab) ? companyTab : DEFAULT_TAB;
  const [published, setPublished] = useState<ParentCompany | null>(null);
  const [form, setForm] = useState<ParentCompanyForm>({});
  const [audit, setAudit] = useState<ParentCompanyAudit[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditField, setAuditField] = useState('');
  const [auditError, setAuditError] = useState('');
  const [hasDraft, setHasDraft] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState('');
  const [busy, setBusy] = useState('');
  const [draftSavedAt, setDraftSavedAt] = useState<Date | null>(null);
  const [uploading, setUploading] = useState<'company-logo' | 'company-banner' | null>(null);
  const [confirmAction, setConfirmAction] = useState<'publish' | 'discard' | null>(null);

  useEffect(() => {
    if (!companyTab || !validTabs.has(companyTab)) {
      navigate(`${BASE_PATH}/${DEFAULT_TAB}`, { replace: true });
    }
  }, [companyTab, navigate]);

  const loadAudit = useCallback(async (page: number) => {
    setAuditLoading(true);
    try {
      const response = await parentCompanyApi.audit({ page, page_size: AUDIT_PAGE_SIZE, field: auditField || undefined });
      setAudit(response.audit);
      setAuditTotal(response.total);
      setAuditError('');
    } catch (error) {
      setAudit([]);
      setAuditTotal(0);
      setAuditError(requestErrorMessage(error, 'Recent Parent Company activity could not be loaded.'));
    } finally {
      setAuditLoading(false);
    }
  }, [auditField]);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setPageError('');
    try {
      const result = await parentCompanyApi.get();
      setPublished(result.published);
      setForm(formFromCompany(result.published, result.draft));
      setHasDraft(result.has_draft);
      setDirty(false);
    } catch (error) {
      setPageError(requestErrorMessage(error, 'The Parent Company profile could not be loaded.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadPage(); }, [loadPage]);

  useEffect(() => {
    if (activeTabId === 'audit') void loadAudit(auditPage);
  }, [activeTabId, auditPage, loadAudit]);

  const dirtyRef = useRef(false);
  useEffect(() => { dirtyRef.current = dirty; }, [dirty]);
  const selfPublishedAtRef = useRef(0);
  const auditPageRef = useRef(auditPage);
  useEffect(() => { auditPageRef.current = auditPage; }, [auditPage]);
  const activeTabRef = useRef(activeTabId);
  useEffect(() => { activeTabRef.current = activeTabId; }, [activeTabId]);

  const handlePublishedBroadcast = useCallback(async () => {
    if (Date.now() - selfPublishedAtRef.current < 5000) return;
    try {
      const result = await parentCompanyApi.get();
      setPublished(result.published);
      setHasDraft(result.has_draft);
      if (!dirtyRef.current) setForm(formFromCompany(result.published, result.draft));
      if (activeTabRef.current === 'audit') await loadAudit(auditPageRef.current);
      toast.success(dirtyRef.current
        ? 'Parent Company was published elsewhere. Your unsaved edits were kept.'
        : 'Parent Company profile updated.');
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The updated Parent Company profile could not be loaded.'));
    }
  }, [loadAudit]);

  useExecutiveEventStream(LIVE_EVENTS, handlePublishedBroadcast);

  const updateField = (field: ParentCompanyField, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setDirty(true);
  };

  const uploadImage = async (kind: 'company-logo' | 'company-banner', file: File) => {
    setUploading(kind);
    try {
      const asset = await superCeoProfileApi.upload(kind, file);
      updateField(kind === 'company-logo' ? 'logo_url' : 'banner_url', asset.url);
      toast.success('Image uploaded. Save the draft to apply it.');
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The image could not be uploaded.'));
    } finally {
      setUploading(null);
    }
  };

  const saveDraft = useCallback(async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    setBusy('saving');
    try {
      const result = await parentCompanyApi.saveDraft(payloadFromForm(form));
      setHasDraft(result.has_draft);
      setDirty(false);
      setDraftSavedAt(new Date());
      toast.success('Parent Company draft saved.');
      return true;
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The Parent Company draft could not be saved.'));
      return false;
    } finally {
      setBusy('');
    }
  }, [form]);

  useEffect(() => {
    if (!dirty || activeTabId === 'audit') return undefined;
    const timer = window.setTimeout(() => {
      void saveDraft();
    }, 30000);
    return () => window.clearTimeout(timer);
  }, [activeTabId, dirty, saveDraft]);

  const discardDraft = async () => {
    setBusy('discarding');
    try {
      await parentCompanyApi.discardDraft();
      if (published) setForm(formFromCompany(published));
      setHasDraft(false);
      setDirty(false);
      setConfirmAction(null);
      toast.success('Draft discarded. Published details are unchanged.');
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The draft could not be discarded.'));
    } finally {
      setBusy('');
    }
  };

  const publishDraft = async () => {
    setBusy('publishing');
    try {
      const saved = await parentCompanyApi.saveDraft(payloadFromForm(form));
      setHasDraft(saved.has_draft);
      const result = await parentCompanyApi.publish();
      selfPublishedAtRef.current = Date.now();
      setPublished(result.published);
      setForm(formFromCompany(result.published));
      setHasDraft(false);
      setDirty(false);
      setConfirmAction(null);
      toast.success('Parent Company profile published.');
      await loadAudit(auditPageRef.current);
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The Parent Company profile could not be published.'));
    } finally {
      setBusy('');
    }
  };

  if (loading) return <div className="exec-profile-state" role="status">Loading Parent Company profile…</div>;

  if (pageError || !published) {
    return (
      <section className="exec-profile-state exec-profile-state-error" role="alert">
        <h1>Parent Company unavailable</h1>
        <p>{pageError || 'The Parent Company profile could not be loaded.'}</p>
        <button type="button" className="exec-button exec-button-primary" onClick={() => void loadPage()}>Try again</button>
      </section>
    );
  }

  const activeGroupFields = fieldGroups[activeTabId] || fieldGroups.identity;
  const isWorking = Boolean(busy);
  const isAuditTab = activeTabId === 'audit';
  const totalAuditPages = Math.max(1, Math.ceil(auditTotal / AUDIT_PAGE_SIZE));

  const panelBody = (
    <>
      <div className="exec-section-heading">
        <div><p className="exec-eyebrow">Parent Company record</p><h2>{tabs.find((tab) => tab.id === activeTabId)?.label}</h2></div>
        <span>{isAuditTab ? `${auditTotal} recorded changes` : dirty ? 'Unsaved changes' : hasDraft ? 'Draft saved' : 'Published values'}</span>
      </div>

      {activeTabId === 'brand' && (
        <div className="exec-profile-upload-grid exec-company-uploads">
          <ImageUpload title="Group logo" value={form.logo_url || ''} busy={uploading === 'company-logo'} onFile={(file) => void uploadImage('company-logo', file)} />
          <ImageUpload title="Group banner" value={form.banner_url || ''} busy={uploading === 'company-banner'} onFile={(file) => void uploadImage('company-banner', file)} isBanner />
        </div>
      )}

      {isAuditTab ? (
        <>
          <div className="exec-activity-toolbar">
            <label className="exec-profile-field" htmlFor="parent-company-audit-field">
              <span>Filter by changed field</span>
              <input id="parent-company-audit-field" value={auditField} onChange={(event) => { setAuditField(event.target.value); setAuditPage(1); }} placeholder="Example: primary_color" />
            </label>
            <button type="button" className="exec-button exec-button-secondary" disabled={auditLoading} onClick={() => void loadAudit(auditPage)}>
              {auditLoading ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
          <div className="exec-profile-activity exec-company-audit">
            {auditError
              ? <p className="exec-inline-error" role="status">{auditError}</p>
              : audit.length
                ? (
                  <ol>
                    {audit.map((event) => (
                      <li key={event.id}>
                        <span className="exec-activity-dot" />
                        <div><strong>{event.action.replace(/[._]/g, ' ')}</strong><small>Executive user {event.actor_id ?? '—'}</small></div>
                        <time>{event.timestamp ? new Date(event.timestamp).toLocaleString() : '—'}</time>
                      </li>
                    ))}
                  </ol>
                )
                : <p className="exec-profile-help">No Parent Company changes have been recorded yet.</p>}
          </div>
          <nav className="exec-pagination" aria-label="Audit pagination">
            <button type="button" className="exec-button exec-button-secondary" disabled={auditPage <= 1 || auditLoading} onClick={() => setAuditPage((page) => Math.max(1, page - 1))}>Previous</button>
            <span>Page {auditPage} of {totalAuditPages}</span>
            <button type="button" className="exec-button exec-button-secondary" disabled={auditPage >= totalAuditPages || auditLoading} onClick={() => setAuditPage((page) => Math.min(totalAuditPages, page + 1))}>Next</button>
          </nav>
        </>
      ) : (
        <>
          <div className="exec-profile-field-grid">
            {activeGroupFields.map((field) => (
              <CompanyField key={field.key} field={field} value={form[field.key] || ''} onChange={(value) => updateField(field.key, value)} />
            ))}
          </div>
          {activeTabId === 'brand' && <p className="exec-profile-help">Brand colors, fonts and imagery are saved to the draft and become authoritative when published.</p>}
          {activeTabId === 'brand' && (
            <article
              className="exec-brand-preview"
              style={{
                '--brand-primary': form.primary_color || '#D6A84F',
                '--brand-secondary': form.secondary_color || '#8C78F5',
                '--brand-accent': form.accent_color || '#14B8A6',
                fontFamily: form.body_font || 'var(--font-body)',
              } as CSSProperties}
            >
              <span>Live brand preview</span>
              <h3 style={{ fontFamily: form.display_font || 'var(--font-display)' }}>{form.name || 'FoodSrijan Group'}</h3>
              <p>{form.tagline || 'One group identity, published across every executive workspace.'}</p>
              <button type="button">Executive action</button>
            </article>
          )}
          {activeTabId === 'legal' && <p className="exec-profile-help">Registration identifiers and addresses are validated by the service when a draft is saved.</p>}
        </>
      )}
    </>
  );

  return (
    <div className="exec-profile-page exec-parent-company-page">
      <section className="exec-profile-hero exec-company-hero">
        <div className="exec-profile-hero-cover" style={form.banner_url ? { backgroundImage: `url("${resolveAssetUrl(form.banner_url)}")` } : undefined}>
          <div className="exec-profile-hero-wash" />
          <span className="exec-profile-status"><span /> Parent entity · ID {published.id}</span>
        </div>
        <div className="exec-profile-hero-body">
          <div className="exec-company-avatar">
            {form.logo_url ? <img src={resolveAssetUrl(form.logo_url)} alt={`${form.name || 'Parent Company'} logo`} /> : <PortfolioIcon size={42} />}
          </div>
          <div className="exec-profile-heading">
            <p className="exec-eyebrow">Group authority & identity</p>
            <h1>{form.name || 'Parent Company'}</h1>
            <p>{form.tagline || 'Authoritative group profile and public brand details.'}</p>
          </div>
          <div className="exec-company-publication">
            <span className={hasDraft || dirty ? 'has-draft' : ''}>{hasDraft || dirty ? 'Draft in progress' : 'Published profile'}</span>
            <small>{published.published_at ? `Last published ${dateLabel(published.published_at)}` : 'Not published yet'}</small>
          </div>
        </div>
      </section>

      <RoutedTabs basePath={BASE_PATH} activeTabId={activeTabId} tabs={tabs} idPrefix="parent-company" ariaLabel="Parent Company profile sections" />

      {isAuditTab ? (
        <section
          id="parent-company-tabpanel"
          role="tabpanel"
          aria-labelledby={`parent-company-tab-${activeTabId}`}
          tabIndex={0}
          className="exec-profile-panel exec-profile-panel-content"
        >
          {panelBody}
        </section>
      ) : (
        <form className="exec-profile-panel" onSubmit={(event) => void saveDraft(event)}>
          <section
            id="parent-company-tabpanel"
            role="tabpanel"
            aria-labelledby={`parent-company-tab-${activeTabId}`}
            tabIndex={0}
            className="exec-profile-panel-content"
          >
            {panelBody}
          </section>
          <footer className="exec-profile-panel-footer exec-company-panel-footer">
            <span>{dirty
              ? 'Changes are not saved to the draft yet.'
              : hasDraft
                ? `Draft · saved ${draftSavedAt ? draftSavedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'recently'}`
                : `Last published ${dateLabel(published.published_at)}.`}</span>
            <div className="exec-company-actions">
              {hasDraft && <button type="button" className="exec-button exec-button-secondary" disabled={isWorking} onClick={() => setConfirmAction('discard')}>Discard draft</button>}
              <button type="submit" className="exec-button exec-button-secondary" disabled={isWorking || !dirty}>
                {busy === 'saving' ? 'Saving…' : 'Save draft'}
              </button>
              <button type="button" className="exec-button exec-button-primary" disabled={isWorking || (!hasDraft && !dirty) || !form.name?.trim()} onClick={() => setConfirmAction('publish')}>
                {busy === 'publishing' ? 'Publishing…' : 'Publish profile'}
              </button>
            </div>
          </footer>
        </form>
      )}

      {confirmAction && (
        <div className="profile-dialog-backdrop">
          <section
            className="profile-confirm-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="parent-action-title"
            aria-describedby="parent-action-description"
            onKeyDown={(event) => { if (event.key === 'Escape' && !isWorking) setConfirmAction(null); }}
          >
            <div className="profile-dialog-icon"><PortfolioIcon size={22} /></div>
            <h2 id="parent-action-title">{confirmAction === 'publish' ? 'Publish Parent Company profile?' : 'Discard this draft?'}</h2>
            <p id="parent-action-description">
              {confirmAction === 'publish'
                ? 'This will make the current Parent Company details the published group record.'
                : 'The saved draft will be removed. Your currently published details will remain unchanged.'}
            </p>
            <div className="profile-dialog-actions">
              <button type="button" className="exec-button exec-button-secondary" autoFocus disabled={isWorking} onClick={() => setConfirmAction(null)}>Cancel</button>
              <button
                type="button"
                className={`exec-button ${confirmAction === 'publish' ? 'exec-button-primary' : 'exec-button-danger'}`}
                disabled={isWorking}
                onClick={() => void (confirmAction === 'publish' ? publishDraft() : discardDraft())}
              >
                {busy === 'publishing' ? 'Publishing…' : busy === 'discarding' ? 'Discarding…' : confirmAction === 'publish' ? 'Publish now' : 'Discard draft'}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
