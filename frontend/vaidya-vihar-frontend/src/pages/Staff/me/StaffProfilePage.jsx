import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { Link, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import RoutedTabs from '../../../components/SuperCEO/common/RoutedTabs';
import OrbitalMotif from '../../../components/SuperCEO/common/OrbitalMotif';
import {
  AuditTrailIcon,
  BriefingIcon,
  LedgerIcon,
  PortfolioIcon,
  PulseIcon,
  ShieldIcon,
  SparkIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi, staffRoleLabel } from '../../../services/staffApi';
import { resolveAssetUrl } from '../../../services/superCeoProfileApi';
import {
  FieldGrid,
  RolePill,
  SectionEmpty,
  formatCount,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
  makeInitials,
  readCollection,
  readNumber,
  readRecord,
  readValue,
} from '../shared/staffShared';

const BASE_PATH = '/staff/profile';
const DEFAULT_TAB = 'about';
const tabs = [
  { id: 'about', label: 'About', icon: <PortfolioIcon size={16} /> },
  { id: 'qualifications', label: 'Qualifications', icon: <BriefingIcon size={16} /> },
  { id: 'bank', label: 'Bank & Salary', icon: <LedgerIcon size={16} /> },
  { id: 'work', label: 'Work', icon: <PulseIcon size={16} /> },
  { id: 'security', label: 'Security', icon: <ShieldIcon size={16} /> },
  { id: 'preferences', label: 'Preferences', icon: <SparkIcon size={16} /> },
  { id: 'activity', label: 'Activity', icon: <AuditTrailIcon size={16} /> },
];
const validTabs = new Set(tabs.map((tab) => tab.id));

const buildDraft = (profile, workspace) => ({
  first_name: profile.first_name || workspace.me.first_name || '',
  last_name: profile.last_name || workspace.me.last_name || '',
  phone: profile.phone || profile.mobile || workspace.me.phone || '',
  email: profile.email || workspace.me.email || '',
  current_address: profile.current_address || profile.address || '',
  permanent_address: profile.permanent_address || '',
  emergency_contact_name: profile.emergency_contact_name || '',
  emergency_contact_phone: profile.emergency_contact_phone || '',
  emergency_contact_relation: profile.emergency_contact_relation || '',
});

const syncWorkspaceMe = (workspace, fields) => {
  if (typeof workspace.onWorkspaceChange !== 'function') return;
  workspace.onWorkspaceChange((current) => ({
    ...current,
    me: {
      ...current.me,
      ...fields,
      full_name: [fields.first_name ?? current.me.first_name, fields.last_name ?? current.me.last_name]
        .filter(Boolean)
        .join(' ')
        || current.me.full_name,
    },
  }));
};

export default function StaffProfilePage() {
  const workspace = useOutletContext();
  const { profileTab } = useParams();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const activeTabId = profileTab && validTabs.has(profileTab) ? profileTab : DEFAULT_TAB;

  const [profile, setProfile] = useState(() => workspace.me);
  const [draft, setDraft] = useState(() => buildDraft(workspace.me, workspace));
  const [saving, setSaving] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [summary, setSummary] = useState({ loading: true, dashboard: null, activity: [] });
  const [activityState, setActivityState] = useState({ loading: false, items: [], error: '' });

  useEffect(() => {
    if (!profileTab || !validTabs.has(profileTab)) {
      navigate(`${BASE_PATH}/${DEFAULT_TAB}`, { replace: true });
    }
  }, [navigate, profileTab]);

  const loadProfile = useCallback(async () => {
    const response = await staffApi.getMe();
    const record = readRecord(response.data, ['profile', 'staff', 'me', 'user']);
    const merged = {
      ...workspace.me,
      ...record,
      full_name: record.full_name || workspace.me.full_name,
      photo_url: record.photo_url || record.profile_photo_url || workspace.me.photo_url,
    };
    setProfile(merged);
    setDraft(buildDraft(merged, workspace));
    syncWorkspaceMe(workspace, merged);
  }, [workspace]);

  const loadSummary = useCallback(async () => {
    setSummary({ loading: true, dashboard: null, activity: [] });
    const [dashboard, activity] = await Promise.allSettled([
      staffApi.getMyDashboard(),
      staffApi.getMyActivity(),
    ]);
    setSummary({
      loading: false,
      dashboard: dashboard.status === 'fulfilled' ? dashboard.value.data : null,
      activity: activity.status === 'fulfilled' ? readCollection(activity.value.data, ['activity', 'events', 'items']).slice(0, 8) : [],
    });
  }, []);

  const loadActivity = useCallback(async () => {
    setActivityState({ loading: true, items: [], error: '' });
    try {
      const response = await staffApi.getMyActivity();
      setActivityState({ loading: false, items: readCollection(response.data, ['activity', 'events', 'items']), error: '' });
    } catch (error) {
      setActivityState({ loading: false, items: [], error: apiErrorMessage(error, 'Activity feed could not be loaded.') });
    }
  }, []);

  useEffect(() => {
    void loadProfile();
    void loadSummary();
  }, [loadProfile, loadSummary]);

  useEffect(() => {
    if (activeTabId === 'activity') void loadActivity();
  }, [activeTabId, loadActivity]);

  const displayName = useMemo(() => {
    const composed = [draft.first_name, draft.last_name].filter(Boolean).join(' ').trim();
    return composed || profile.full_name || workspace.me.full_name || 'Staff';
  }, [draft.first_name, draft.last_name, profile.full_name, workspace.me.full_name]);

  const dirty = [
    'first_name',
    'last_name',
    'phone',
    'email',
    'current_address',
    'permanent_address',
    'emergency_contact_name',
    'emergency_contact_phone',
    'emergency_contact_relation',
  ].some((key) => (draft[key] || '') !== ((buildDraft(profile, workspace)[key]) || ''));

  const metrics = useMemo(() => ([
    {
      label: 'Days worked',
      value: summary.loading ? '—' : formatCount(readNumber(summary.dashboard, ['days_worked', 'working_days', 'attendance_days'], null)),
    },
    {
      label: 'Tasks done',
      value: summary.loading ? '—' : formatCount(readNumber(summary.dashboard, ['tasks_done', 'completed_tasks', 'tasks_completed'], null)),
    },
    {
      label: 'Attendance %',
      value: summary.loading ? '—' : formatPercent(readNumber(summary.dashboard, ['attendance_percentage', 'attendance_rate'], null)),
    },
    {
      label: 'Rating',
      value: summary.loading
        ? '—'
        : (readValue(summary.dashboard, ['rating', 'average_rating', 'performance_rating'], null) == null
          ? '—'
          : `${Number(readValue(summary.dashboard, ['rating', 'average_rating', 'performance_rating'], 0)).toFixed(1)} / 5`),
    },
  ]), [summary.dashboard, summary.loading]);

  const saveAbout = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      const response = await staffApi.updateMe({
        first_name: draft.first_name.trim(),
        last_name: draft.last_name.trim(),
        phone: draft.phone.trim(),
        email: draft.email.trim() || undefined,
        current_address: draft.current_address.trim() || undefined,
        permanent_address: draft.permanent_address.trim() || undefined,
        emergency_contact_name: draft.emergency_contact_name.trim() || undefined,
        emergency_contact_phone: draft.emergency_contact_phone.trim() || undefined,
        emergency_contact_relation: draft.emergency_contact_relation.trim() || undefined,
      });
      const updated = readRecord(response.data, ['profile', 'staff', 'me', 'user']);
      const merged = {
        ...profile,
        ...updated,
        photo_url: updated.photo_url || updated.profile_photo_url || profile.photo_url,
        full_name: updated.full_name || [updated.first_name || draft.first_name, updated.last_name || draft.last_name].filter(Boolean).join(' '),
      };
      setProfile(merged);
      setDraft(buildDraft(merged, workspace));
      syncWorkspaceMe(workspace, merged);
      toast.success('Staff profile updated.');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to save your profile.'));
    } finally {
      setSaving(false);
    }
  };

  const uploadProfilePhoto = async (file) => {
    setUploadingPhoto(true);
    try {
      const response = await staffApi.uploadMyPhoto(file);
      const updated = readRecord(response.data, ['profile', 'staff', 'me', 'user']);
      const merged = {
        ...profile,
        ...updated,
        photo_url: updated.photo_url || updated.profile_photo_url || profile.photo_url,
      };
      setProfile(merged);
      syncWorkspaceMe(workspace, merged);
      toast.success('Profile photo updated.');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to upload your profile photo.'));
    } finally {
      setUploadingPhoto(false);
    }
  };

  const qualificationItems = Array.isArray(profile.qualifications) ? profile.qualifications : [];
  const certificationItems = Array.isArray(profile.certifications) ? profile.certifications : [];
  const skillItems = Array.isArray(profile.skills)
    ? profile.skills
    : typeof profile.skills === 'string'
      ? profile.skills.split(',').map((item) => item.trim()).filter(Boolean)
      : [];

  const panelContent = activeTabId === 'about' ? (
    <form className="exec-profile-panel" onSubmit={saveAbout}>
      <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel-content">
        <div className="manager-profile-grid">
          <section className="manager-panel">
            <div className="manager-section-heading">
              <div>
                <h2>Personal record</h2>
                <p>Update the contact information you can self-manage in the staff workspace.</p>
              </div>
            </div>
            <div className="manager-form-grid">
              <label className="manager-form-field" htmlFor="staff-first-name">
                <span>First name</span>
                <input id="staff-first-name" value={draft.first_name} onChange={(event) => setDraft((current) => ({ ...current, first_name: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="staff-last-name">
                <span>Last name</span>
                <input id="staff-last-name" value={draft.last_name} onChange={(event) => setDraft((current) => ({ ...current, last_name: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="staff-phone">
                <span>Phone</span>
                <input id="staff-phone" type="tel" value={draft.phone} onChange={(event) => setDraft((current) => ({ ...current, phone: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="staff-email">
                <span>Email</span>
                <input id="staff-email" type="email" value={draft.email} onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))} />
              </label>
              <label className="manager-form-field is-wide" htmlFor="staff-address">
                <span>Current address</span>
                <textarea id="staff-address" rows={4} value={draft.current_address} onChange={(event) => setDraft((current) => ({ ...current, current_address: event.target.value }))} />
              </label>
              <label className="manager-form-field is-wide" htmlFor="staff-permanent-address">
                <span>Permanent address</span>
                <textarea id="staff-permanent-address" rows={4} value={draft.permanent_address} onChange={(event) => setDraft((current) => ({ ...current, permanent_address: event.target.value }))} />
              </label>
            </div>
          </section>

          <section className="manager-panel">
            <div className="manager-section-heading">
              <div>
                <h2>Emergency contact</h2>
                <p>Store a reachable backup contact for urgent operational cases.</p>
              </div>
            </div>
            <div className="manager-form-grid">
              <label className="manager-form-field" htmlFor="staff-emergency-name">
                <span>Name</span>
                <input id="staff-emergency-name" value={draft.emergency_contact_name} onChange={(event) => setDraft((current) => ({ ...current, emergency_contact_name: event.target.value }))} />
              </label>
              <label className="manager-form-field" htmlFor="staff-emergency-phone">
                <span>Phone</span>
                <input id="staff-emergency-phone" type="tel" value={draft.emergency_contact_phone} onChange={(event) => setDraft((current) => ({ ...current, emergency_contact_phone: event.target.value }))} />
              </label>
              <label className="manager-form-field is-wide" htmlFor="staff-emergency-relation">
                <span>Relation</span>
                <input id="staff-emergency-relation" value={draft.emergency_contact_relation} onChange={(event) => setDraft((current) => ({ ...current, emergency_contact_relation: event.target.value }))} />
              </label>
            </div>
          </section>
        </div>
      </section>
      <footer className="exec-profile-panel-footer">
        <span>{dirty ? 'Save your changes to keep your staff profile in sync.' : 'Your profile details are up to date.'}</span>
        <button type="submit" className="exec-button exec-button-primary" disabled={saving || !dirty}>{saving ? 'Saving…' : 'Save changes'}</button>
      </footer>
    </form>
  ) : activeTabId === 'qualifications' ? (
    <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Qualifications</h2>
              <p>Published educational records returned by the self-service profile endpoint.</p>
            </div>
          </div>
          {!qualificationItems.length ? <SectionEmpty title="No qualifications on file" description="Qualifications will appear here once the staff profile includes them." /> : (
            <ol className="staff-audit-list">
              {qualificationItems.map((item, index) => (
                <li key={`qualification-${index}`}>
                  <strong>{item.degree || item.title || `Qualification ${index + 1}`}</strong>
                  <span>{[item.institution, item.year, item.grade].filter(Boolean).join(' · ') || 'No further details provided.'}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Certifications & skills</h2>
              <p>Additional capabilities and certifications shared with the outlet leadership team.</p>
            </div>
          </div>
          {certificationItems.length ? (
            <ol className="staff-audit-list">
              {certificationItems.map((item, index) => (
                <li key={`certification-${index}`}>
                  <strong>{item.name || item.title || `Certification ${index + 1}`}</strong>
                  <span>{[item.issuer, item.year, item.reference].filter(Boolean).join(' · ') || 'No further details provided.'}</span>
                </li>
              ))}
            </ol>
          ) : <SectionEmpty title="No certifications recorded" description="Certifications can be published here once the backend includes them." />}
          {skillItems.length ? (
            <div className="staff-chip-row">{skillItems.map((skill) => <span key={skill} className="staff-skill-chip">{skill}</span>)}</div>
          ) : <p className="staff-profile-activity-note">No skills tags are available yet.</p>}
        </section>
      </div>
    </section>
  ) : activeTabId === 'bank' ? (
    <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Bank details</h2>
              <p>Bank and payout details are view-only in this phase.</p>
            </div>
          </div>
          <FieldGrid items={[
            { label: 'Bank name', value: profile.bank_name || '—' },
            { label: 'Account number', value: profile.bank_account_number_masked || profile.bank_account_number || '—' },
            { label: 'IFSC', value: profile.ifsc_code || '—' },
            { label: 'UPI ID', value: profile.upi_id_masked || profile.upi_id || '—' },
          ]} />
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Salary snapshot</h2>
              <p>Salary figures are shown only if published by the self-service dashboard feed.</p>
            </div>
          </div>
          <FieldGrid items={[
            { label: 'Salary type', value: profile.salary_type || '—' },
            { label: 'Salary amount', value: profile.salary_amount != null ? formatCurrency(profile.salary_amount) : '—' },
            { label: 'Employment type', value: profile.employment_type || '—' },
            { label: 'Last payslip amount', value: formatCurrency(readValue(summary.dashboard, ['last_payslip_amount', 'latest_payslip_amount'], null)) },
          ]} />
        </section>
      </div>
    </section>
  ) : activeTabId === 'work' ? (
    <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Work profile</h2>
              <p>Your current outlet assignment and operational role context.</p>
            </div>
          </div>
          <FieldGrid items={[
            { label: 'Role', value: staffRoleLabel(profile.role || profile.staff_role || 'staff') },
            { label: 'Outlet', value: profile.outlet_name || workspace.outlet?.name || '—' },
            { label: 'Employee code', value: profile.employee_code || profile.staff_id || '—' },
            { label: 'Joining date', value: formatDate(profile.joined_at || profile.joining_date || profile.date_of_joining) },
            { label: 'Shift preference', value: profile.shift_preference || profile.shift || '—' },
            { label: 'Weekly off', value: profile.weekly_off_day || '—' },
          ]} />
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Work signals</h2>
              <p>Dashboard-backed highlights from attendance, tasks, and rating summaries.</p>
            </div>
          </div>
          <FieldGrid items={[
            { label: 'Tasks completed', value: formatCount(readNumber(summary.dashboard, ['tasks_done', 'completed_tasks', 'tasks_completed'], null)) },
            { label: 'Attendance', value: formatPercent(readNumber(summary.dashboard, ['attendance_percentage', 'attendance_rate'], null)) },
            { label: 'Pending requests', value: formatCount(readNumber(summary.dashboard, ['pending_requests', 'requests_pending'], null)) },
            { label: 'Rating', value: readValue(summary.dashboard, ['rating', 'average_rating', 'performance_rating'], null) == null ? '—' : `${Number(readValue(summary.dashboard, ['rating', 'average_rating', 'performance_rating'], 0)).toFixed(1)} / 5` },
          ]} />
        </section>
      </div>
    </section>
  ) : activeTabId === 'security' ? (
    <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Account security</h2>
              <p>Password changes and active-session visibility live in the dedicated security workspace tab.</p>
            </div>
          </div>
          <FieldGrid items={[
            { label: 'Username', value: profile.username || workspace.me.username || '—' },
            { label: 'Force password change', value: profile.force_password_change ? 'Enabled' : 'Not indicated' },
            { label: 'Current role', value: staffRoleLabel(profile.role || profile.staff_role || 'staff') },
            { label: 'Status', value: profile.is_active === false || String(profile.status || '').toLowerCase() === 'inactive' ? 'Inactive' : 'Active' },
          ]} />
          <p className="manager-note">Use the dedicated security page to update your password and review active sessions if the endpoint is available.</p>
          <Link className="exec-button exec-button-secondary" to="/staff/security">Open security settings</Link>
        </section>
      </div>
    </section>
  ) : activeTabId === 'preferences' ? (
    <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-profile-grid">
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Workspace defaults</h2>
              <p>Current self-service behaviors already active in the staff workspace.</p>
            </div>
          </div>
          <FieldGrid items={[
            { label: 'Landing page', value: 'Dashboard' },
            { label: 'Workspace search', value: 'Cmd/Ctrl + K' },
            { label: 'Theme sync', value: 'Live workspace theme updates' },
            { label: 'Motion', value: 'Respects reduced-motion preference' },
          ]} />
        </section>
        <section className="manager-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Personal preferences</h2>
              <p>No dedicated staff preference store is available yet.</p>
            </div>
          </div>
          <SectionEmpty title="No saved personal preferences" description="When backend-backed staff preferences are introduced, this section will replace the current informational placeholder." />
        </section>
      </div>
    </section>
  ) : (
    <section id="staff-profile-tabpanel" role="tabpanel" aria-labelledby={`staff-profile-tab-${activeTabId}`} tabIndex={0} className="exec-profile-panel exec-profile-panel-content">
      <div className="manager-section-heading">
        <div>
          <h2>Personal activity</h2>
          <p>Your most recent personal audit events from the staff self-service activity feed.</p>
        </div>
        <button type="button" className="manager-inline-action" onClick={() => void loadActivity()}>Refresh</button>
      </div>
      {activityState.loading ? <div className="manager-inline-state" role="status"><strong>Loading activity…</strong><span>Fetching the latest profile and request events.</span></div> : null}
      {!activityState.loading && activityState.error ? <div className="manager-inline-state" role="alert"><strong>Activity unavailable.</strong><span>{activityState.error}</span></div> : null}
      {!activityState.loading && !activityState.error && !activityState.items.length ? <SectionEmpty title="No activity yet" description="Your staff activity history will populate here once events are published by the backend." /> : null}
      {!activityState.loading && !activityState.error && activityState.items.length ? (
        <ol className="manager-activity-list">
          {activityState.items.map((item, index) => (
            <li key={item.id || `profile-activity-${index}`}>
              <i aria-hidden="true" />
              <div>
                <strong>{item.title || item.action || item.event || `Activity ${index + 1}`}</strong>
                <span>{item.description || item.detail || item.resource || 'No additional detail provided.'}</span>
              </div>
              <time>{formatDateTime(item.timestamp || item.created_at)}</time>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );

  return (
    <div className="exec-profile-page staff-profile-page">
      <section className="exec-profile-hero staff-profile-hero">
        <div className="exec-profile-hero-cover">
          <div className="exec-profile-hero-wash" />
          <OrbitalMotif compact={false} dots={4} />
          <span className="exec-profile-status"><span /> Staff self-service active</span>
        </div>
        <div className="exec-profile-hero-body">
          <div className="exec-profile-avatar">
            {profile.photo_url ? <img src={resolveAssetUrl(profile.photo_url)} alt={`${displayName} profile`} /> : makeInitials(displayName)}
            <button type="button" className="staff-hero-upload" onClick={() => inputRef.current?.click()} disabled={uploadingPhoto} aria-label="Upload profile photo">
              {uploadingPhoto ? '…' : '+'}
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
          <div className="exec-profile-heading">
            <p className="exec-eyebrow">The staff self-service record</p>
            <h1>{displayName}</h1>
            <div className="staff-hero-meta">
              <RolePill role={profile.role || profile.staff_role || 'staff'} />
              <p>{`${staffRoleLabel(profile.role || profile.staff_role || 'staff').toUpperCase()} · ${profile.outlet_name || workspace.outlet?.name || 'Assigned outlet'}`}</p>
            </div>
            <p>{[profile.employee_code || profile.staff_id, formatDate(profile.joined_at || profile.joining_date || profile.date_of_joining)].filter((value) => value && value !== '—').join(' · ') || 'Joining details not available yet.'}</p>
            <p className="manager-profile-subline">{[draft.email, draft.phone].filter(Boolean).join(' · ') || 'Contact details not available yet.'}</p>
          </div>
          <span className="exec-draft-pill">{profile.is_active === false || String(profile.status || '').toLowerCase() === 'inactive' ? 'Inactive account' : 'Account active'}</span>
        </div>
      </section>

      <section className="exec-profile-metrics" aria-label="Staff profile summary">
        {metrics.map((metric) => <div key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
      </section>

      <RoutedTabs basePath={BASE_PATH} activeTabId={activeTabId} tabs={tabs} idPrefix="staff-profile" ariaLabel="Staff profile sections" />

      {panelContent}
    </div>
  );
}
