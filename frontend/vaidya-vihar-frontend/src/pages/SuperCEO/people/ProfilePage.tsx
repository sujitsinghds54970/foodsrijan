import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import RoutedTabs, { RoutedTab } from '../../../components/SuperCEO/common/RoutedTabs';
import {
  AuditTrailIcon,
  BriefingIcon,
  CrownIcon,
  PulseIcon,
  ShieldIcon,
} from '../../../components/SuperCEO/icons';
import {
  ProfileActivity,
  ProfileEntry,
  SuperCEOProfile,
  resolveAssetUrl,
  requestErrorMessage,
  superCeoProfileApi,
} from '../../../services/superCeoProfileApi';

const BASE_PATH = '/super-ceo/people/profile';
const DEFAULT_TAB = 'about';

const tabs: RoutedTab[] = [
  { id: 'about', label: 'About', icon: <CrownIcon size={16} /> },
  { id: 'qualifications', label: 'Qualifications', icon: <BriefingIcon size={16} /> },
  { id: 'security', label: 'Security', icon: <ShieldIcon size={16} /> },
  { id: 'preferences', label: 'Preferences', icon: <PulseIcon size={16} /> },
  { id: 'activity', label: 'Activity', icon: <AuditTrailIcon size={16} /> },
];
const validTabs = new Set(tabs.map((tab) => tab.id));

type ProfileTextKey =
  | 'first_name' | 'last_name' | 'display_name' | 'email' | 'phone' | 'date_of_birth' | 'gender' | 'bio'
  | 'location_city' | 'location_state' | 'location_country' | 'timezone'
  | 'emergency_contact_name' | 'emergency_contact_phone'
  | 'assistant_name' | 'assistant_email' | 'assistant_phone'
  | 'recovery_email' | 'recovery_phone';

interface ProfileFieldSpec {
  key: ProfileTextKey;
  label: string;
  type?: string;
  wide?: boolean;
}

const personalFields: ProfileFieldSpec[] = [
  { key: 'first_name', label: 'First name' },
  { key: 'last_name', label: 'Last name' },
  { key: 'display_name', label: 'Display name' },
  { key: 'date_of_birth', label: 'Date of birth', type: 'date' },
  { key: 'gender', label: 'Gender' },
  { key: 'timezone', label: 'Time zone' },
];

const contactFields: ProfileFieldSpec[] = [
  { key: 'email', label: 'Executive email', type: 'email' },
  { key: 'phone', label: 'Phone', type: 'tel' },
  { key: 'location_city', label: 'City' },
  { key: 'location_state', label: 'State / region' },
  { key: 'location_country', label: 'Country' },
  { key: 'emergency_contact_name', label: 'Emergency contact' },
  { key: 'emergency_contact_phone', label: 'Emergency phone', type: 'tel' },
  { key: 'assistant_name', label: 'Executive assistant' },
  { key: 'assistant_email', label: 'Assistant email', type: 'email' },
  { key: 'assistant_phone', label: 'Assistant phone', type: 'tel' },
];

const recoveryFields: ProfileFieldSpec[] = [
  { key: 'recovery_email', label: 'Recovery email', type: 'email' },
  { key: 'recovery_phone', label: 'Recovery phone', type: 'tel' },
];

type EntryKey = 'qualifications' | 'certifications' | 'achievements';

interface EntryFieldSpec {
  key: string;
  label: string;
  type?: string;
  wide?: boolean;
}

interface EntryListSpec {
  key: EntryKey;
  title: string;
  eyebrow: string;
  emptyLabel: string;
  addLabel: string;
  titleField: string;
  subtitleField: string;
  metaField: string;
  fields: EntryFieldSpec[];
}

const entryLists: EntryListSpec[] = [
  {
    key: 'qualifications',
    title: 'Education',
    eyebrow: 'Academic record',
    emptyLabel: 'No education entries have been added yet.',
    addLabel: 'Add education',
    titleField: 'degree',
    subtitleField: 'institution',
    metaField: 'year',
    fields: [
      { key: 'degree', label: 'Degree or programme' },
      { key: 'institution', label: 'Institution' },
      { key: 'field_of_study', label: 'Field of study' },
      { key: 'year', label: 'Year completed' },
      { key: 'notes', label: 'Notes', type: 'textarea', wide: true },
    ],
  },
  {
    key: 'certifications',
    title: 'Certifications',
    eyebrow: 'Professional credentials',
    emptyLabel: 'No certifications have been added yet.',
    addLabel: 'Add certification',
    titleField: 'name',
    subtitleField: 'issuer',
    metaField: 'year',
    fields: [
      { key: 'name', label: 'Certification name' },
      { key: 'issuer', label: 'Issuing authority' },
      { key: 'credential_id', label: 'Credential ID' },
      { key: 'year', label: 'Year issued' },
      { key: 'notes', label: 'Notes', type: 'textarea', wide: true },
    ],
  },
  {
    key: 'achievements',
    title: 'Achievements',
    eyebrow: 'Executive milestones',
    emptyLabel: 'No achievements have been added yet.',
    addLabel: 'Add achievement',
    titleField: 'title',
    subtitleField: 'awarded_by',
    metaField: 'year',
    fields: [
      { key: 'title', label: 'Achievement' },
      { key: 'awarded_by', label: 'Awarded by' },
      { key: 'year', label: 'Year' },
      { key: 'description', label: 'Description', type: 'textarea', wide: true },
    ],
  },
];

interface ToggleSpec { key: string; label: string; hint: string }
interface ChoiceSpec { key: string; label: string; options: Array<{ value: string; label: string }> }

const preferenceToggles: ToggleSpec[] = [
  { key: 'email_notifications', label: 'Email notifications', hint: 'Group briefings and escalations by email.' },
  { key: 'sms_alerts', label: 'SMS alerts', hint: 'Critical alerts sent to your executive phone.' },
  { key: 'weekly_digest', label: 'Weekly digest', hint: 'A Monday summary of group performance.' },
  { key: 'desktop_notifications', label: 'Desktop notifications', hint: 'In-browser alerts while the workspace is open.' },
  { key: 'compact_tables', label: 'Compact tables', hint: 'Denser rows across reporting tables.' },
];

const preferenceChoices: ChoiceSpec[] = [
  {
    key: 'theme',
    label: 'Workspace theme',
    options: [
      { value: 'dark', label: 'Executive dark' },
      { value: 'system', label: 'Match system' },
    ],
  },
  {
    key: 'landing_page',
    label: 'Default landing page',
    options: [
      { value: 'overview', label: 'Overview' },
      { value: 'performance', label: 'Performance' },
      { value: 'companies', label: 'Companies' },
      { value: 'profile', label: 'Super CEO Profile' },
    ],
  },
  {
    key: 'language',
    label: 'Language',
    options: [
      { value: 'en', label: 'English' },
      { value: 'hi', label: 'Hindi' },
    ],
  },
  {
    key: 'date_format',
    label: 'Date format',
    options: [
      { value: 'dd-mm-yyyy', label: 'DD-MM-YYYY' },
      { value: 'mm-dd-yyyy', label: 'MM-DD-YYYY' },
      { value: 'yyyy-mm-dd', label: 'YYYY-MM-DD' },
    ],
  },
  {
    key: 'digest_time',
    label: 'Briefing delivery time',
    options: [
      { value: 'morning', label: 'Morning (08:00)' },
      { value: 'midday', label: 'Midday (13:00)' },
      { value: 'evening', label: 'Evening (19:00)' },
    ],
  },
];

const ACTIVITY_PAGE_SIZE = 10;

const entryText = (entry: ProfileEntry, key: string): string => {
  const value = entry[key];
  return value == null ? '' : String(value);
};

const dateTimeLabel = (value?: string | null) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

function TextField({
  id, label, value, type = 'text', wide = false, required = false, disabled = false, onChange,
}: {
  id: string;
  label: string;
  value: string;
  type?: string;
  wide?: boolean;
  required?: boolean;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  const shared = {
    id,
    value,
    disabled,
    onChange: (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(event.target.value),
    autoComplete: 'off',
  };
  return (
    <label className={`exec-profile-field${wide ? ' is-wide' : ''}`} htmlFor={id}>
      <span>{label}</span>
      {type === 'textarea' ? <textarea {...shared} rows={4} /> : <input {...shared} type={type} required={required} />}
    </label>
  );
}

function UploadField({
  title, imageUrl, busy, onFile, cover = false,
}: {
  title: string;
  imageUrl: string;
  busy: boolean;
  onFile: (file: File) => void;
  cover?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div className={`exec-profile-upload${cover ? ' is-cover' : ''}`}>
      <div className="exec-profile-upload-preview">
        {imageUrl ? <img src={resolveAssetUrl(imageUrl)} alt={`${title} preview`} /> : <CrownIcon size={cover ? 28 : 24} />}
      </div>
      <div className="exec-profile-upload-copy">
        <strong>{title}</strong>
        <span>PNG, JPG, WebP or SVG · maximum 5 MB</span>
        <button type="button" className="exec-button exec-button-secondary" onClick={() => inputRef.current?.click()} disabled={busy}>
          {busy ? 'Uploading…' : imageUrl ? 'Replace image' : 'Upload image'}
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

function EntryCardList({
  spec, entries, busy, onAdd, onEdit, onDelete,
}: {
  spec: EntryListSpec;
  entries: ProfileEntry[];
  busy: boolean;
  onAdd: () => void;
  onEdit: (index: number) => void;
  onDelete: (index: number) => void;
}) {
  return (
    <section className="exec-entry-list" aria-label={spec.title}>
      <div className="exec-section-heading">
        <div><p className="exec-eyebrow">{spec.eyebrow}</p><h2>{spec.title}</h2></div>
        <button type="button" className="exec-button exec-button-secondary" disabled={busy} onClick={onAdd}>
          {spec.addLabel}
        </button>
      </div>
      {entries.length ? (
        <ul className="exec-entry-cards">
          {entries.map((entry, index) => (
            <li className="exec-entry-card" key={`${spec.key}-${index}`}>
              <div className="exec-entry-card-body">
                <strong>{entryText(entry, spec.titleField) || 'Untitled entry'}</strong>
                <span>{entryText(entry, spec.subtitleField) || '—'}</span>
                {entryText(entry, spec.metaField) && <small>{entryText(entry, spec.metaField)}</small>}
              </div>
              <div className="exec-entry-card-actions">
                <button type="button" className="exec-button exec-button-secondary" disabled={busy} onClick={() => onEdit(index)}>Edit</button>
                <button type="button" className="exec-button exec-button-danger" disabled={busy} onClick={() => onDelete(index)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="exec-profile-help">{spec.emptyLabel}</p>
      )}
    </section>
  );
}

interface EntryDialogState {
  listKey: EntryKey;
  index: number | null;
  values: Record<string, string>;
}

interface ProfilePageProps {
  basePath?: string;
  authorityLabel?: string;
  organizationName?: string;
  metrics?: Array<{ label: string; value: string | number }>;
  idPrefix?: string;
}

export default function ProfilePage({
  basePath = BASE_PATH,
  authorityLabel = 'Super CEO',
  organizationName = 'FoodSrijan Group',
  metrics,
  idPrefix = 'super-ceo-profile',
}: ProfilePageProps) {
  const { profileTab } = useParams();
  const navigate = useNavigate();
  const activeTabId = profileTab && validTabs.has(profileTab) ? profileTab : DEFAULT_TAB;
  const [profile, setProfile] = useState<SuperCEOProfile | null>(null);
  const [preferences, setPreferences] = useState<Record<string, unknown>>({});
  const [activity, setActivity] = useState<ProfileActivity[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityPage, setActivityPage] = useState(1);
  const [activityFilter, setActivityFilter] = useState('');
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<'profile-photo' | 'cover-photo' | null>(null);
  const [dirty, setDirty] = useState(false);
  const [pageError, setPageError] = useState('');
  const [entryDialog, setEntryDialog] = useState<EntryDialogState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ listKey: EntryKey; index: number } | null>(null);

  useEffect(() => {
    if (!profileTab || !validTabs.has(profileTab)) {
      navigate(`${basePath}/${DEFAULT_TAB}`, { replace: true });
    }
  }, [basePath, navigate, profileTab]);

  const applyProfile = useCallback((result: SuperCEOProfile) => {
    setProfile(result);
    setPreferences((result.preferences && typeof result.preferences === 'object' ? result.preferences : {}) as Record<string, unknown>);
  }, []);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setPageError('');
    try {
      applyProfile(await superCeoProfileApi.get());
      setDirty(false);
    } catch (error) {
      setPageError(requestErrorMessage(error, 'The executive profile could not be loaded.'));
    } finally {
      setLoading(false);
    }
  }, [applyProfile]);

  useEffect(() => { void loadPage(); }, [loadPage]);

  const loadActivity = useCallback(async (page: number) => {
    setActivityLoading(true);
    try {
      const response = await superCeoProfileApi.activity({ page, page_size: ACTIVITY_PAGE_SIZE });
      setActivity(response.activity);
      setActivityTotal(response.total);
      setActivityError('');
    } catch (error) {
      setActivity([]);
      setActivityTotal(0);
      setActivityError(requestErrorMessage(error, 'Recent activity could not be loaded.'));
    } finally {
      setActivityLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTabId === 'activity') void loadActivity(activityPage);
  }, [activeTabId, activityPage, loadActivity]);

  const updateText = (key: ProfileTextKey, value: string) => {
    setProfile((current) => (current ? { ...current, [key]: value } : current));
    setDirty(true);
  };

  const updatePreference = (key: string, value: unknown) => {
    setPreferences((current) => ({ ...current, [key]: value }));
    setDirty(true);
  };

  const uploadImage = async (kind: 'profile-photo' | 'cover-photo', file: File) => {
    setUploading(kind);
    try {
      const asset = await superCeoProfileApi.upload(kind, file);
      const field = kind === 'profile-photo' ? 'profile_photo_url' : 'cover_photo_url';
      setProfile((current) => (current ? { ...current, [field]: asset.url } : current));
      setDirty(true);
      toast.success('Image uploaded. Save your profile to apply it.');
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The image could not be uploaded.'));
    } finally {
      setUploading(null);
    }
  };

  const persistEntries = async (listKey: EntryKey, entries: ProfileEntry[]) => {
    setSaving(true);
    try {
      const result = await superCeoProfileApi.update({ [listKey]: entries });
      applyProfile(result.profile);
      toast.success('Entry saved.');
      return true;
    } catch (error) {
      toast.error(requestErrorMessage(error, 'The entry could not be saved.'));
      return false;
    } finally {
      setSaving(false);
    }
  };

  const submitEntryDialog = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!entryDialog || !profile) return;
    const spec = entryLists.find((item) => item.key === entryDialog.listKey);
    if (!spec) return;
    const cleaned: ProfileEntry = {};
    spec.fields.forEach((field) => {
      const value = entryDialog.values[field.key]?.trim();
      if (value) cleaned[field.key] = value;
    });
    if (!Object.keys(cleaned).length) {
      toast.error('Add at least one detail before saving.');
      return;
    }
    const existing = (profile[entryDialog.listKey] || []) as ProfileEntry[];
    const next = entryDialog.index == null
      ? [...existing, cleaned]
      : existing.map((item, index) => (index === entryDialog.index ? cleaned : item));
    if (await persistEntries(entryDialog.listKey, next)) setEntryDialog(null);
  };

  const confirmDeleteEntry = async () => {
    if (!deleteTarget || !profile) return;
    const existing = (profile[deleteTarget.listKey] || []) as ProfileEntry[];
    const next = existing.filter((_, index) => index !== deleteTarget.index);
    if (await persistEntries(deleteTarget.listKey, next)) setDeleteTarget(null);
  };

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    try {
      const payload: Partial<SuperCEOProfile> = activeTabId === 'about'
        ? {
          first_name: profile.first_name || '',
          last_name: profile.last_name || '',
          display_name: profile.display_name || null,
          email: profile.email || null,
          phone: profile.phone || null,
          date_of_birth: profile.date_of_birth || null,
          gender: profile.gender || null,
          bio: profile.bio || null,
          profile_photo_url: profile.profile_photo_url || null,
          cover_photo_url: profile.cover_photo_url || null,
          location_city: profile.location_city || null,
          location_state: profile.location_state || null,
          location_country: profile.location_country || null,
          timezone: profile.timezone || null,
          emergency_contact_name: profile.emergency_contact_name || null,
          emergency_contact_phone: profile.emergency_contact_phone || null,
          assistant_name: profile.assistant_name || null,
          assistant_email: profile.assistant_email || null,
          assistant_phone: profile.assistant_phone || null,
          preferred_contact_method: profile.preferred_contact_method || null,
        }
        : activeTabId === 'security'
          ? { recovery_email: profile.recovery_email || null, recovery_phone: profile.recovery_phone || null }
          : { preferences };
      const result = await superCeoProfileApi.update(payload);
      applyProfile(result.profile);
      setDirty(false);
      toast.success('Profile changes saved.');
    } catch (error) {
      toast.error(requestErrorMessage(error, 'Profile changes could not be saved.'));
    } finally {
      setSaving(false);
    }
  };

  const filteredActivity = useMemo(() => {
    const needle = activityFilter.trim().toLowerCase();
    if (!needle) return activity;
    return activity.filter((item) => (
      item.action.toLowerCase().includes(needle) || (item.resource || '').toLowerCase().includes(needle)
    ));
  }, [activity, activityFilter]);

  const renderFields = (fields: ProfileFieldSpec[]) => fields.map((field) => (
    <TextField
      key={field.key}
      id={`profile-${field.key}`}
      label={field.label}
      value={profile?.[field.key] || ''}
      type={field.type}
      wide={field.wide}
      required={field.key === 'first_name' || field.key === 'last_name'}
      onChange={(value) => updateText(field.key, value)}
    />
  ));

  if (loading) return <div className="exec-profile-state" role="status">Loading executive profile…</div>;

  if (pageError || !profile) {
    return (
      <section className="exec-profile-state exec-profile-state-error" role="alert">
        <h1>Profile unavailable</h1>
        <p>{pageError || 'The executive profile could not be loaded.'}</p>
        <button type="button" className="exec-button exec-button-primary" onClick={() => void loadPage()}>Try again</button>
      </section>
    );
  }

  const displayName = profile.display_name || [profile.first_name, profile.last_name].filter(Boolean).join(' ') || profile.username;
  const isFormTab = activeTabId === 'about' || activeTabId === 'security' || activeTabId === 'preferences';
  const totalActivityPages = Math.max(1, Math.ceil(activityTotal / ACTIVITY_PAGE_SIZE));
  const dialogSpec = entryDialog ? entryLists.find((item) => item.key === entryDialog.listKey) : null;

  const panelContent = (
    <>
      {activeTabId === 'about' && (
        <>
          <div className="exec-section-heading"><div><p className="exec-eyebrow">Personal details</p><h2>About</h2></div><span>Private executive record</span></div>
          <div className="exec-profile-field-grid">{renderFields(personalFields)}</div>
          <div className="exec-section-heading"><div><p className="exec-eyebrow">Reachability</p><h2>Contact & location</h2></div></div>
          <div className="exec-profile-field-grid">
            {renderFields(contactFields)}
            <label className="exec-profile-field" htmlFor="profile-preferred-contact">
              <span>Preferred contact method</span>
              <select
                id="profile-preferred-contact"
                value={profile.preferred_contact_method || ''}
                onChange={(event) => {
                  const value = event.target.value;
                  if (value === '' || value === 'email' || value === 'phone' || value === 'whatsapp') {
                    setProfile((current) => (current ? { ...current, preferred_contact_method: value || null } : current));
                  }
                  setDirty(true);
                }}
              >
                <option value="">Not specified</option>
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="whatsapp">WhatsApp</option>
              </select>
            </label>
          </div>
          <div className="exec-section-heading"><div><p className="exec-eyebrow">Executive narrative</p><h2>Biography</h2></div></div>
          <TextField id="profile-bio" label="Executive biography" type="textarea" wide value={profile.bio || ''} onChange={(value) => updateText('bio', value)} />
          <div className="exec-profile-upload-grid">
            <UploadField title="Profile portrait" imageUrl={profile.profile_photo_url || ''} busy={uploading === 'profile-photo'} onFile={(file) => void uploadImage('profile-photo', file)} />
            <UploadField title="Cover image" imageUrl={profile.cover_photo_url || ''} busy={uploading === 'cover-photo'} onFile={(file) => void uploadImage('cover-photo', file)} cover />
          </div>
        </>
      )}

      {activeTabId === 'security' && (
        <>
          <div className="exec-section-heading"><div><p className="exec-eyebrow">Account protection</p><h2>Security</h2></div><span>Recovery details are saved</span></div>
          <div className="exec-security-grid">
            <article className="exec-security-card">
              <header><strong>Two-factor authentication</strong><span className="exec-soon-pill">Coming soon</span></header>
              <p>Require a second factor for every executive sign-in.</p>
              <label className="exec-toggle is-disabled">
                <input type="checkbox" role="switch" checked={false} disabled aria-label="Two-factor authentication" readOnly />
                <span className="exec-toggle-track" aria-hidden="true"><span /></span>
                <span className="exec-toggle-label">Disabled</span>
              </label>
            </article>
            <article className="exec-security-card">
              <header><strong>Active sessions</strong><span className="exec-soon-pill">Coming soon</span></header>
              <p>Review and revoke devices signed in to the executive workspace.</p>
              <button type="button" className="exec-button exec-button-secondary" disabled>Manage sessions</button>
            </article>
            <article className="exec-security-card">
              <header><strong>Login history</strong><span className="exec-soon-pill">Coming soon</span></header>
              <p>A signed audit of recent sign-ins, locations and devices.</p>
              <button type="button" className="exec-button exec-button-secondary" disabled>View history</button>
            </article>
            <article className="exec-security-card">
              <header><strong>Password</strong><span className="exec-soon-pill">Coming soon</span></header>
              <p>Rotate your executive password from this workspace.</p>
              <button type="button" className="exec-button exec-button-secondary" disabled>Change password</button>
            </article>
          </div>
          <div className="exec-section-heading"><div><p className="exec-eyebrow">Account recovery</p><h2>Recovery channels</h2></div></div>
          <div className="exec-profile-field-grid">{renderFields(recoveryFields)}</div>
        </>
      )}

      {activeTabId === 'preferences' && (
        <>
          <div className="exec-section-heading"><div><p className="exec-eyebrow">Workspace settings</p><h2>Preferences</h2></div><span>Applies to your account only</span></div>
          <div className="exec-toggle-grid">
            {preferenceToggles.map((toggle) => (
              <label className="exec-toggle-row" key={toggle.key}>
                <span className="exec-toggle-copy"><strong>{toggle.label}</strong><small>{toggle.hint}</small></span>
                <span className="exec-toggle">
                  <input
                    type="checkbox"
                    role="switch"
                    checked={Boolean(preferences[toggle.key])}
                    onChange={(event) => updatePreference(toggle.key, event.target.checked)}
                  />
                  <span className="exec-toggle-track" aria-hidden="true"><span /></span>
                </span>
              </label>
            ))}
          </div>
          <div className="exec-profile-field-grid">
            {preferenceChoices.map((choice) => (
              <label className="exec-profile-field" htmlFor={`preference-${choice.key}`} key={choice.key}>
                <span>{choice.label}</span>
                <select
                  id={`preference-${choice.key}`}
                  value={typeof preferences[choice.key] === 'string' ? String(preferences[choice.key]) : ''}
                  onChange={(event) => updatePreference(choice.key, event.target.value || null)}
                >
                  <option value="">Not set</option>
                  {choice.options.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
                </select>
              </label>
            ))}
          </div>
        </>
      )}
    </>
  );

  return (
    <div className="exec-profile-page">
      <section className="exec-profile-hero">
        <div className="exec-profile-hero-cover" style={profile.cover_photo_url ? { backgroundImage: `url("${resolveAssetUrl(profile.cover_photo_url)}")` } : undefined}>
          <div className="exec-profile-hero-wash" />
          <span className="exec-profile-status"><span /> Executive account {profile.is_verified ? 'verified' : 'active'}</span>
        </div>
        <div className="exec-profile-hero-body">
          <div className="exec-profile-avatar">
            {profile.profile_photo_url
              ? <img src={resolveAssetUrl(profile.profile_photo_url)} alt={`${displayName} profile`} />
              : <CrownIcon size={48} />}
          </div>
          <div className="exec-profile-heading">
            <p className="exec-eyebrow">The executive record</p>
            <h1>{displayName}</h1>
            <p>{authorityLabel} · {organizationName}</p>
          </div>
          {dirty && <span className="exec-draft-pill">Unsaved changes</span>}
        </div>
      </section>

      <section className="exec-profile-metrics" aria-label="Executive profile summary">
        {(metrics || [
          { label: 'Companies overseen', value: profile.stats?.companies_overseen ?? '—' },
          { label: 'Decisions recorded', value: profile.stats?.decisions_made ?? '—' },
          { label: 'Group team members', value: profile.stats?.team_size ?? '—' },
          { label: 'Tenure', value: profile.stats ? `${Math.floor(profile.stats.tenure_days / 365)}y ${Math.floor((profile.stats.tenure_days % 365) / 30)}m` : '—' },
        ]).map((metric) => <div key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong></div>)}
      </section>

      <RoutedTabs basePath={basePath} activeTabId={activeTabId} tabs={tabs} idPrefix={idPrefix} ariaLabel={`${authorityLabel} profile sections`} />

      {isFormTab ? (
        <form className="exec-profile-panel" onSubmit={saveProfile}>
          <section
            id={`${idPrefix}-tabpanel`}
            role="tabpanel"
            aria-labelledby={`${idPrefix}-tab-${activeTabId}`}
            tabIndex={0}
            className="exec-profile-panel-content"
          >
            {panelContent}
          </section>
          <footer className="exec-profile-panel-footer">
            <span>{dirty ? 'Remember to save the changes in this section.' : 'Changes are saved to your executive record.'}</span>
            <button type="submit" className="exec-button exec-button-primary" disabled={saving || !dirty}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </footer>
        </form>
      ) : (
        <section
          id={`${idPrefix}-tabpanel`}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-tab-${activeTabId}`}
          tabIndex={0}
          className="exec-profile-panel exec-profile-panel-content"
        >
          {activeTabId === 'qualifications' && entryLists.map((spec) => (
            <EntryCardList
              key={spec.key}
              spec={spec}
              entries={(profile[spec.key] || []) as ProfileEntry[]}
              busy={saving}
              onAdd={() => setEntryDialog({ listKey: spec.key, index: null, values: {} })}
              onEdit={(index) => {
                const entry = ((profile[spec.key] || []) as ProfileEntry[])[index] || {};
                const values: Record<string, string> = {};
                spec.fields.forEach((field) => { values[field.key] = entryText(entry, field.key); });
                setEntryDialog({ listKey: spec.key, index, values });
              }}
              onDelete={(index) => setDeleteTarget({ listKey: spec.key, index })}
            />
          ))}

          {activeTabId === 'activity' && (
            <>
              <div className="exec-section-heading">
                <div><p className="exec-eyebrow">Executive trail</p><h2>Activity</h2></div>
                <span>{activityTotal} recorded events</span>
              </div>
              <div className="exec-activity-toolbar">
                <label className="exec-profile-field" htmlFor="activity-filter">
                  <span>Filter events</span>
                  <input
                    id="activity-filter"
                    type="search"
                    value={activityFilter}
                    placeholder="Search by action or resource"
                    onChange={(event) => setActivityFilter(event.target.value)}
                  />
                </label>
                <button type="button" className="exec-button exec-button-secondary" disabled={activityLoading} onClick={() => void loadActivity(activityPage)}>
                  {activityLoading ? 'Refreshing…' : 'Refresh'}
                </button>
              </div>
              <div className="exec-profile-activity">
                {activityError
                  ? <p className="exec-inline-error" role="status">{activityError}</p>
                  : filteredActivity.length
                    ? (
                      <ol>
                        {filteredActivity.map((item) => (
                          <li key={item.id}>
                            <span className="exec-activity-dot" />
                            <div><strong>{item.action.replace(/[._]/g, ' ')}</strong><small>{item.resource || 'Executive profile'}</small></div>
                            <time>{dateTimeLabel(item.timestamp)}</time>
                          </li>
                        ))}
                      </ol>
                    )
                    : <p className="exec-profile-help">{activityFilter ? 'No events match this filter on the current page.' : 'No profile activity has been recorded yet.'}</p>}
              </div>
              <nav className="exec-pagination" aria-label="Activity pagination">
                <button type="button" className="exec-button exec-button-secondary" disabled={activityPage <= 1 || activityLoading} onClick={() => setActivityPage((page) => Math.max(1, page - 1))}>Previous</button>
                <span>Page {activityPage} of {totalActivityPages}</span>
                <button type="button" className="exec-button exec-button-secondary" disabled={activityPage >= totalActivityPages || activityLoading} onClick={() => setActivityPage((page) => Math.min(totalActivityPages, page + 1))}>Next</button>
              </nav>
            </>
          )}
        </section>
      )}

      {entryDialog && dialogSpec && (
        <div className="profile-dialog-backdrop">
          <form
            className="profile-confirm-dialog exec-entry-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="entry-dialog-title"
            onSubmit={(event) => void submitEntryDialog(event)}
            onKeyDown={(event) => { if (event.key === 'Escape' && !saving) setEntryDialog(null); }}
          >
            <div className="profile-dialog-icon"><BriefingIcon size={22} /></div>
            <h2 id="entry-dialog-title">{entryDialog.index == null ? `Add ${dialogSpec.title.toLowerCase()} entry` : `Edit ${dialogSpec.title.toLowerCase()} entry`}</h2>
            <div className="exec-profile-field-grid">
              {dialogSpec.fields.map((field, fieldIndex) => (
                <label className={`exec-profile-field${field.wide ? ' is-wide' : ''}`} htmlFor={`entry-${field.key}`} key={field.key}>
                  <span>{field.label}</span>
                  {field.type === 'textarea'
                    ? (
                      <textarea
                        id={`entry-${field.key}`}
                        rows={3}
                        value={entryDialog.values[field.key] || ''}
                        onChange={(event) => setEntryDialog((current) => (current ? { ...current, values: { ...current.values, [field.key]: event.target.value } } : current))}
                      />
                    )
                    : (
                      <input
                        id={`entry-${field.key}`}
                        type="text"
                        autoComplete="off"
                        autoFocus={fieldIndex === 0}
                        value={entryDialog.values[field.key] || ''}
                        onChange={(event) => setEntryDialog((current) => (current ? { ...current, values: { ...current.values, [field.key]: event.target.value } } : current))}
                      />
                    )}
                </label>
              ))}
            </div>
            <div className="profile-dialog-actions">
              <button type="button" className="exec-button exec-button-secondary" disabled={saving} onClick={() => setEntryDialog(null)}>Cancel</button>
              <button type="submit" className="exec-button exec-button-primary" disabled={saving}>{saving ? 'Saving…' : 'Save entry'}</button>
            </div>
          </form>
        </div>
      )}

      {deleteTarget && (
        <div className="profile-dialog-backdrop">
          <section
            className="profile-confirm-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="entry-delete-title"
            aria-describedby="entry-delete-description"
            onKeyDown={(event) => { if (event.key === 'Escape' && !saving) setDeleteTarget(null); }}
          >
            <div className="profile-dialog-icon"><ShieldIcon size={22} /></div>
            <h2 id="entry-delete-title">Delete this entry?</h2>
            <p id="entry-delete-description">The entry will be removed from your executive profile immediately.</p>
            <div className="profile-dialog-actions">
              <button type="button" className="exec-button exec-button-secondary" autoFocus disabled={saving} onClick={() => setDeleteTarget(null)}>Cancel</button>
              <button type="button" className="exec-button exec-button-danger" disabled={saving} onClick={() => void confirmDeleteEntry()}>
                {saving ? 'Deleting…' : 'Delete entry'}
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
