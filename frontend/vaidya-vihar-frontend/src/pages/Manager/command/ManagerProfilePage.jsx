import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { useNavigate, useOutletContext, useParams } from 'react-router-dom';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import RoutedTabs from '../../../components/SuperCEO/common/RoutedTabs';
import {
  AuditTrailIcon,
  BriefingIcon,
  PortfolioIcon,
  PulseIcon,
  ShieldIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import managerApi from '../../../services/managerApi';
import { resolveAssetUrl, superCeoProfileApi } from '../../../services/superCeoProfileApi';

const BASE_PATH = '/manager/profile';
const DEFAULT_TAB = 'about';

const tabs = [
  { id: 'about', label: 'About', icon: <PortfolioIcon size={16} /> },
  { id: 'qualifications', label: 'Qualifications', icon: <BriefingIcon size={16} /> },
  { id: 'security', label: 'Security', icon: <ShieldIcon size={16} /> },
  { id: 'preferences', label: 'Preferences', icon: <PulseIcon size={16} /> },
  { id: 'activity', label: 'Activity', icon: <AuditTrailIcon size={16} /> },
];

const validTabs = new Set(tabs.map((tab) => tab.id));

const toDateLabel = (value) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString();
};

const daysWithCompany = (value) => {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '—';
  return Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 86400000));
};

const locationLabel = (outlet) => [outlet?.address_line_1, outlet?.city, outlet?.state, outlet?.pincode].filter(Boolean).join(', ') || '—';

const readActivityItems = (payload) => {
  if (!payload || typeof payload !== 'object') return [];
  return payload.activity || payload.events || payload.items || [];
};

const readMetricValue = (payload, keys) => {
  if (!payload || typeof payload !== 'object') return null;
  const candidates = [payload, payload.kpis, payload.metrics, payload.summary, payload.health].filter(Boolean);
  for (const candidate of candidates) {
    for (const key of keys) {
      if (candidate[key] == null) continue;
      const value = candidate[key];
      if (typeof value === 'number' || typeof value === 'string') return value;
      if (value && typeof value === 'object') {
        if (value.source_status && ['degraded', 'empty', 'pending', 'unavailable'].includes(String(value.source_status).toLowerCase())) return null;
        const metricValue = value.value ?? value.count ?? value.total ?? value.rating ?? value.score ?? value.average_rating;
        if (metricValue != null) return metricValue;
      }
    }
  }
  return null;
};

const formatRating = (value) => {
  if (value == null) return '—';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(1)} / 5` : '—';
};

const formatCount = (value) => {
  if (value == null) return '—';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(numeric) : '—';
};

const buildDraftFromWorkspace = (workspace) => ({
  first_name: workspace.manager.first_name || '',
  last_name: workspace.manager.last_name || '',
  phone: workspace.manager.phone || '',
  email: workspace.manager.email || '',
  username: workspace.manager.username || '',
  photo_url: workspace.manager.photo_url || '',
});

const syncWorkspaceManager = (workspace, fields) => {
  if (typeof workspace.onWorkspaceChange !== 'function') return;
  workspace.onWorkspaceChange((current) => ({
    ...current,
    manager: {
      ...current.manager,
      ...fields,
      full_name: [fields.first_name ?? current.manager.first_name, fields.last_name ?? current.manager.last_name]
        .filter(Boolean)
        .join(' ')
        || current.manager.display_name
        || current.manager.username,
    },
  }));
};

export default function ManagerProfilePage() {
  const workspace = useOutletContext();
  const { profileTab } = useParams();
  const navigate = useNavigate();
  const activeTabId = profileTab && validTabs.has(profileTab) ? profileTab : DEFAULT_TAB;
  const [draft, setDraft] = useState(() => buildDraftFromWorkspace(workspace));
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [summarySignals, setSummarySignals] = useState({
    loading: true,
    ordersManaged: workspace.metrics.orders_today ?? null,
    staffOverseen: workspace.metrics.team_size ?? null,
    rating: null,
  });
  const [activityState, setActivityState] = useState({ loading: false, error: '', items: [] });
  const inputRef = useRef(null);

  useEffect(() => {
    if (!profileTab || !validTabs.has(profileTab)) navigate(`${BASE_PATH}/${DEFAULT_TAB}`, { replace: true });
  }, [navigate, profileTab]);

  useEffect(() => {
    setDraft(buildDraftFromWorkspace(workspace));
  }, [workspace]);

  const loadSummarySignals = useCallback(async () => {
    setSummarySignals((current) => ({ ...current, loading: true }));
    const [statsResult, kpiResult, healthResult] = await Promise.allSettled([
      managerApi.stats(),
      managerApi.kpis(),
      managerApi.health(),
    ]);

    setSummarySignals({
      loading: false,
      ordersManaged: statsResult.status === 'fulfilled'
        ? (statsResult.value.data.stats.orders_today ?? workspace.metrics.orders_today ?? null)
        : workspace.metrics.orders_today ?? null,
      staffOverseen: kpiResult.status === 'fulfilled'
        ? (readMetricValue(kpiResult.value.data, ['active_staff', 'staff_on_shift', 'staff_count', 'active_staff_count']) ?? workspace.metrics.team_size ?? null)
        : workspace.metrics.team_size ?? null,
      rating: healthResult.status === 'fulfilled'
        ? (readMetricValue(healthResult.value.data, ['feedback_summary', 'customer_feedback', 'avg_rating', 'average_rating', 'rating']) ?? readMetricValue(kpiResult.status === 'fulfilled' ? kpiResult.value.data : null, ['avg_rating', 'average_rating', 'rating', 'average_customer_rating_30d']))
        : readMetricValue(kpiResult.status === 'fulfilled' ? kpiResult.value.data : null, ['avg_rating', 'average_rating', 'rating', 'average_customer_rating_30d']),
    });
  }, [workspace.metrics.orders_today, workspace.metrics.team_size]);

  useEffect(() => { void loadSummarySignals(); }, [loadSummarySignals]);

  const loadActivity = useCallback(async () => {
    setActivityState({ loading: true, error: '', items: [] });
    try {
      const response = await managerApi.activity();
      setActivityState({
        loading: false,
        error: '',
        items: readActivityItems(response.data).slice(0, 10),
      });
    } catch (error) {
      setActivityState({
        loading: false,
        error: apiErrorMessage(error, 'Manager activity could not be loaded.'),
        items: [],
      });
    }
  }, []);

  useEffect(() => {
    if (activeTabId === 'activity') void loadActivity();
  }, [activeTabId, loadActivity]);

  const dirty = (
    draft.first_name !== (workspace.manager.first_name || '')
    || draft.last_name !== (workspace.manager.last_name || '')
    || draft.phone !== (workspace.manager.phone || '')
  );

  const displayName = useMemo(() => {
    const composed = [draft.first_name, draft.last_name].filter(Boolean).join(' ').trim();
    return composed || workspace.manager.display_name || workspace.manager.full_name || workspace.manager.username;
  }, [draft.first_name, draft.last_name, workspace.manager.display_name, workspace.manager.full_name, workspace.manager.username]);

  const initials = displayName
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  const saveAbout = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const response = await managerApi.updateMe({
        first_name: draft.first_name.trim(),
        last_name: draft.last_name.trim(),
        phone: draft.phone.trim(),
      });
      const updated = response.data.manager;
      setDraft({
        first_name: updated.first_name || '',
        last_name: updated.last_name || '',
        phone: updated.phone || '',
        email: updated.email || workspace.manager.email || '',
        username: updated.username || workspace.manager.username || '',
        photo_url: updated.profile_photo_url || updated.manager_photo_url || draft.photo_url,
      });
      syncWorkspaceManager(workspace, {
        first_name: updated.first_name || '',
        last_name: updated.last_name || '',
        phone: updated.phone || '',
        email: updated.email || workspace.manager.email || '',
        username: updated.username || workspace.manager.username || '',
        photo_url: updated.profile_photo_url || updated.manager_photo_url || draft.photo_url,
        display_name: updated.display_name || null,
      });
      toast.success('Manager profile updated.');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to save your manager profile.'));
    } finally {
      setSaving(false);
    }
  };

  const uploadProfilePhoto = async (file) => {
    setUploadingPhoto(true);
    try {
      const asset = await superCeoProfileApi.upload('profile-photo', file);
      const response = await managerApi.updateMe({ manager_photo_url: asset.url });
      const updated = response.data.manager;
      setDraft((current) => ({
        ...current,
        photo_url: updated.profile_photo_url || updated.manager_photo_url || asset.url,
      }));
      syncWorkspaceManager(workspace, {
        photo_url: updated.profile_photo_url || updated.manager_photo_url || asset.url,
        display_name: updated.display_name || workspace.manager.display_name || null,
      });
      toast.success('Profile photo updated.');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to upload your profile photo.'));
    } finally {
      setUploadingPhoto(false);
    }
  };

  const metrics = [
    { label: 'Days with company', value: summarySignals.loading ? '—' : formatCount(daysWithCompany(workspace.manager.assigned_at)) },
    { label: 'Orders managed', value: summarySignals.loading ? '—' : formatCount(summarySignals.ordersManaged) },
    { label: 'Staff overseen', value: summarySignals.loading ? '—' : formatCount(summarySignals.staffOverseen) },
    { label: 'Rating', value: summarySignals.loading ? '—' : formatRating(summarySignals.rating) },
  ];

  const panelContent = activeTabId === 'about' ? (
    <form className="exec-profile-panel" onSubmit={saveAbout}>
      <section id="manager-profile-tabpanel" role="tabpanel" aria-labelledby={`manager-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel-content">
        <div className="manager-profile-grid">
          <section className="manager-panel">
            <div className="manager-section-heading">
              <div>
                <h2>Personal record</h2>
                <p>Update the contact details you directly control in the manager workspace.</p>
              </div>
            </div>
            <div className="manager-form-grid">
              <label className="manager-form-field" htmlFor="manager-first-name">
                <span>First name</span>
                <input id="manager-first-name" value={draft.first_name} onChange={(event) => setDraft((current) => ({ ...current, first_name: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="manager-last-name">
                <span>Last name</span>
                <input id="manager-last-name" value={draft.last_name} onChange={(event) => setDraft((current) => ({ ...current, last_name: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="manager-phone">
                <span>Phone</span>
                <input id="manager-phone" type="tel" value={draft.phone} onChange={(event) => setDraft((current) => ({ ...current, phone: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="manager-email">
                <span>Email</span>
                <input id="manager-email" type="email" value={draft.email} disabled readOnly />
              </label>
              <label className="manager-form-field is-wide" htmlFor="manager-username">
                <span>Username</span>
                <input id="manager-username" value={draft.username} disabled readOnly />
              </label>
            </div>
          </section>

          <section className="manager-panel">
            <div className="manager-section-heading">
              <div>
                <h2>Profile photo</h2>
                <p>Upload a new profile portrait for your manager account.</p>
              </div>
            </div>
            <div className="manager-profile-photo-panel">
              <div className="manager-profile-avatar large">
                {draft.photo_url ? <img src={resolveAssetUrl(draft.photo_url)} alt={`${displayName} profile`} /> : initials}
              </div>
              <div className="manager-profile-photo-copy">
                <strong>{displayName}</strong>
                <span>{workspace.manager.role_label}</span>
                <small>PNG, JPG, WebP or SVG, up to 5 MB.</small>
                <button type="button" className="exec-button exec-button-secondary" onClick={() => inputRef.current?.click()} disabled={uploadingPhoto}>
                  {uploadingPhoto ? 'Uploading…' : draft.photo_url ? 'Replace profile photo' : 'Upload profile photo'}
                </button>
                <input
                  ref={inputRef}
                  className="exec-visually-hidden"
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) void uploadProfilePhoto(file);
                    event.target.value = '';
                  }}
                />
              </div>
            </div>
          </section>

          <section className="manager-panel">
            <div className="manager-section-heading">
              <div>
                <h2>Outlet assignment</h2>
                <p>Your current store context and operating scope.</p>
              </div>
            </div>
            <dl className="manager-stat-list">
              <div><dt>Outlet</dt><dd>{workspace.outlet?.name || '—'}</dd></div>
              <div><dt>Company</dt><dd>{workspace.outlet?.company_name || '—'}</dd></div>
              <div><dt>Assigned on</dt><dd>{toDateLabel(workspace.manager.assigned_at)}</dd></div>
              <div><dt>Location</dt><dd>{locationLabel(workspace.outlet)}</dd></div>
            </dl>
          </section>

          <section className="manager-panel">
            <div className="manager-section-heading">
              <div>
                <h2>Outlet contact details</h2>
                <p>Operational coordinates already stored against your outlet.</p>
              </div>
            </div>
            <dl className="manager-stat-list">
              <div><dt>Outlet email</dt><dd>{workspace.outlet?.outlet_email || '—'}</dd></div>
              <div><dt>Outlet phone</dt><dd>{workspace.outlet?.outlet_phone || '—'}</dd></div>
              <div><dt>Opening hours</dt><dd>{[workspace.outlet?.opening_time, workspace.outlet?.closing_time].filter(Boolean).join(' - ') || '—'}</dd></div>
              <div><dt>Maps link</dt><dd>{workspace.outlet?.google_maps_url ? <a href={workspace.outlet.google_maps_url} target="_blank" rel="noreferrer">Open map</a> : '—'}</dd></div>
            </dl>
          </section>
        </div>
      </section>
      <footer className="exec-profile-panel-footer">
        <span>{dirty ? 'Save your changes to keep the manager record in sync.' : 'Manager contact details are up to date.'}</span>
        <button type="submit" className="exec-button exec-button-primary" disabled={saving || !dirty}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </footer>
    </form>
  ) : activeTabId === 'qualifications' ? (
    <section id="manager-profile-tabpanel" role="tabpanel" aria-labelledby={`manager-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Operational credentials</h2>
              <p>Licences and site credentials already attached to your outlet record.</p>
            </div>
          </div>
          <dl className="manager-stat-list">
            <div><dt>Role</dt><dd>{workspace.manager.role_label}</dd></div>
            <div><dt>Outlet code</dt><dd>{workspace.outlet?.code || '—'}</dd></div>
            <div><dt>FSSAI licence</dt><dd>{workspace.outlet?.fssai_license || '—'}</dd></div>
            <div><dt>Trade licence</dt><dd>{workspace.outlet?.trade_license || '—'}</dd></div>
            <div><dt>Health permit</dt><dd>{workspace.outlet?.health_permit || '—'}</dd></div>
            <div><dt>Licence expiry</dt><dd>{toDateLabel(workspace.outlet?.license_expiry_date)}</dd></div>
          </dl>
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Manager qualifications</h2>
              <p>Personal training and certification records have not been onboarded for manager accounts yet.</p>
            </div>
          </div>
          <EmptyState
            title="No personal qualifications stored"
            description="When manager certification records are added to the platform, they will appear in this section."
          />
        </section>
      </div>
    </section>
  ) : activeTabId === 'security' ? (
    <section id="manager-profile-tabpanel" role="tabpanel" aria-labelledby={`manager-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Account identity</h2>
              <p>Current sign-in and authority details for this manager account.</p>
            </div>
          </div>
          <dl className="manager-stat-list">
            <div><dt>Username</dt><dd>{workspace.manager.username || '—'}</dd></div>
            <div><dt>Role</dt><dd>{workspace.manager.role_label}</dd></div>
            <div><dt>Email</dt><dd>{workspace.manager.email || '—'}</dd></div>
            <div><dt>Phone</dt><dd>{workspace.manager.phone || '—'}</dd></div>
          </dl>
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Security controls</h2>
              <p>Only controls with confirmed backend support are shown here.</p>
            </div>
          </div>
          <dl className="manager-stat-list">
            <div><dt>Profile photo upload</dt><dd>Enabled</dd></div>
            <div><dt>Self-service password reset</dt><dd>Not available in this workspace</dd></div>
            <div><dt>Recovery email</dt><dd>—</dd></div>
            <div><dt>Recovery phone</dt><dd>—</dd></div>
          </dl>
          <p className="manager-note">If you need a password reset or role change, contact your Company CEO.</p>
        </section>
      </div>
    </section>
  ) : activeTabId === 'preferences' ? (
    <section id="manager-profile-tabpanel" role="tabpanel" aria-labelledby={`manager-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Workspace defaults</h2>
              <p>Current frontend behaviours already active in the manager workspace.</p>
            </div>
          </div>
          <dl className="manager-stat-list">
            <div><dt>Landing page</dt><dd>Dashboard</dd></div>
            <div><dt>Workspace search</dt><dd>Cmd/Ctrl + K</dd></div>
            <div><dt>Theme</dt><dd>Executive dark</dd></div>
            <div><dt>Motion</dt><dd>Follows reduced-motion system preference</dd></div>
          </dl>
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Personal preferences</h2>
              <p>No backend-backed manager preference store is available yet.</p>
            </div>
          </div>
          <EmptyState
            title="No saved personal preferences"
            description="When outlet-manager specific preferences are introduced, they will appear here instead of placeholder dashes."
          />
        </section>
      </div>
    </section>
  ) : (
    <section id="manager-profile-tabpanel" role="tabpanel" aria-labelledby={`manager-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-section-heading">
        <div>
          <h2>Recent activity</h2>
          <p>The last 10 manager-facing events published by the dashboard activity feed.</p>
        </div>
        <button type="button" className="manager-inline-action" onClick={() => void loadActivity()}>
          Refresh
        </button>
      </div>
      {activityState.loading ? <div className="manager-inline-state" role="status"><strong>Loading activity…</strong><span>Pulling the latest manager events.</span></div> : null}
      {!activityState.loading && activityState.error ? (
        <div className="manager-inline-state" role="alert">
          <strong>Activity unavailable.</strong>
          <span>{activityState.error}</span>
        </div>
      ) : null}
      {!activityState.loading && !activityState.error && !activityState.items.length ? (
        <EmptyState
          title="No recent activity yet"
          description="This activity tab will populate as soon as the manager dashboard backend starts emitting events."
        />
      ) : null}
      {!activityState.loading && !activityState.error && activityState.items.length ? (
        <ol className="manager-activity-list">
          {activityState.items.map((item, index) => (
            <li key={item.id || item.event_id || `profile-activity-${index}`}>
              <i aria-hidden="true" />
              <div>
                <strong>{item.title || item.action || item.event || `Activity ${index + 1}`}</strong>
                <span>{item.description || item.detail || item.resource || 'No additional detail provided.'}</span>
              </div>
              <time>{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Just now'}</time>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );

  return (
    <div className="exec-profile-page manager-profile-page">
      <section className="exec-profile-hero">
        <div className="exec-profile-hero-cover" style={workspace.outlet?.cover_photo_url ? { backgroundImage: `url("${resolveAssetUrl(workspace.outlet.cover_photo_url)}")` } : undefined}>
          <div className="exec-profile-hero-wash" />
          <span className="exec-profile-status"><span /> Manager account active</span>
        </div>
        <div className="exec-profile-hero-body">
          <div className="exec-profile-avatar">
            {draft.photo_url
              ? <img src={resolveAssetUrl(draft.photo_url)} alt={`${displayName} profile`} />
              : initials}
          </div>
          <div className="exec-profile-heading">
            <p className="exec-eyebrow">The operator record</p>
            <h1>{displayName}</h1>
            <p>{`MANAGER · ${workspace.outlet?.name || 'Unassigned Outlet'} · ${workspace.outlet?.company_name || 'FoodSrijan'}`}</p>
            <p className="manager-profile-subline">{[workspace.manager.email, workspace.manager.phone].filter(Boolean).join(' · ') || 'Contact details not available yet.'}</p>
          </div>
          <span className="exec-draft-pill">{workspace.outlet?.is_active ? 'Outlet active' : 'Outlet status pending'}</span>
        </div>
      </section>

      <section className="exec-profile-metrics" aria-label="Manager profile summary">
        {metrics.map((metric) => <div key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
      </section>

      <RoutedTabs basePath={BASE_PATH} activeTabId={activeTabId} tabs={tabs} idPrefix="manager-profile" ariaLabel="Manager profile sections" />

      {panelContent}
    </div>
  );
}
