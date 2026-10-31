import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Link, useOutletContext } from 'react-router-dom';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import {
  AuditTrailIcon,
  BriefingIcon,
  PortfolioIcon,
  PulseIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi, staffRoleLabel } from '../../../services/staffApi';
import '../../../styles/staff.css';
import {
  Avatar,
  LoadingBlock,
  PageHeader,
  RolePill,
  StatusPill,
  formatCount,
  formatDate,
  readCollection,
  readNumber,
  readRecord,
} from '../../Staff/shared/staffShared';

const WIZARD_STEPS = [
  { id: 'identity', title: 'Identity', hint: 'Names, role, code, and photo' },
  { id: 'personal', title: 'Personal Details', hint: 'Demographics and contact details' },
  { id: 'documents', title: 'Identity Documents', hint: 'Optional government IDs' },
  { id: 'employment', title: 'Bank & Employment', hint: 'Joining, salary, and shift setup' },
  { id: 'qualifications', title: 'Qualifications & Experience', hint: 'Education, skills, and history' },
  { id: 'credentials', title: 'Login Credentials', hint: 'Username and password' },
  { id: 'review', title: 'Review & Confirm', hint: 'Final verification before save' },
];

const createEmptyDraft = (outletCode = 'OUTLET') => ({
  first_name: '',
  last_name: '',
  phone: '+91 ',
  email: '',
  employee_code: `${outletCode}-EMP-${String(Math.floor(Math.random() * 900) + 100)}`,
  staff_role: 'waiter',
  photo_file: null,
  photo_preview: '',
  date_of_birth: '',
  gender: '',
  blood_group: '',
  marital_status: '',
  current_address: '',
  permanent_address: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  emergency_contact_relation: '',
  aadhaar_number: '',
  pan_number: '',
  voter_id: '',
  driving_license: '',
  document_file: null,
  bank_account_name: '',
  bank_account_number: '',
  ifsc_code: '',
  bank_name: '',
  branch_name: '',
  upi_id: '',
  joining_date: '',
  employment_type: 'full_time',
  salary_type: 'monthly',
  salary_amount: '',
  pf_enabled: false,
  esi_enabled: false,
  tds_enabled: false,
  shift_preference: '',
  weekly_off_day: '',
  qualifications: [{ degree: '', institution: '', year: '' }],
  certifications: [{ name: '', issuer: '', year: '' }],
  years_of_experience: '',
  previous_employer: '',
  skill_input: '',
  skills: [],
  username: '',
  password: '',
  confirm_password: '',
  force_password_change: true,
});

const roleOptions = [
  'chef',
  'sous_chef',
  'kitchen_helper',
  'cashier',
  'waiter',
  'cleaner',
  'delivery_rider',
  'store_keeper',
  'shift_supervisor',
];

const employmentOptions = ['full_time', 'part_time', 'contract', 'trainee', 'intern'];
const salaryOptions = ['monthly', 'daily', 'hourly'];
const genderOptions = ['male', 'female', 'other', 'prefer_not_to_say'];
const maritalOptions = ['single', 'married', 'separated', 'widowed'];
const bloodOptions = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
const weeklyOffOptions = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const aadhaarRegex = /^\d{4}\s?\d{4}\s?\d{4}$/;
const panRegex = /^[A-Z]{5}\d{4}[A-Z]$/;

const passwordStrength = (value) => {
  if (!value) return { label: 'Not set', score: 0.08 };
  let score = 0;
  if (value.length >= 8) score += 1;
  if (/[A-Z]/.test(value)) score += 1;
  if (/[a-z]/.test(value)) score += 1;
  if (/\d/.test(value)) score += 1;
  if (/[^A-Za-z0-9]/.test(value)) score += 1;
  return {
    label: score <= 2 ? 'Needs work' : score === 3 ? 'Fair' : score === 4 ? 'Strong' : 'Very strong',
    score: Math.max(.08, score / 5),
  };
};

const randomPassword = () => {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
  return Array.from({ length: 14 }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join('');
};

const maskedAadhaarPreview = (value) => {
  const digits = String(value || '').replace(/\D/g, '');
  if (!digits) return '•••• •••• ••••';
  const visible = digits.slice(-4);
  return `•••• •••• ${visible.padStart(4, '•')}`;
};

const mapDraftFromStaff = (staff, outletCode) => {
  const draft = createEmptyDraft(outletCode);
  const qualificationRows = Array.isArray(staff.qualifications) && staff.qualifications.length
    ? staff.qualifications.map((item) => ({ degree: item.degree || item.title || '', institution: item.institution || '', year: item.year || '' }))
    : draft.qualifications;
  const certificationRows = Array.isArray(staff.certifications) && staff.certifications.length
    ? staff.certifications.map((item) => ({ name: item.name || item.title || '', issuer: item.issuer || '', year: item.year || '' }))
    : draft.certifications;

  return {
    ...draft,
    ...staff,
    phone: staff.phone || staff.mobile || draft.phone,
    employee_code: staff.employee_code || staff.staff_id || draft.employee_code,
    staff_role: staff.staff_role || staff.role || draft.staff_role,
    joining_date: staff.joining_date || staff.date_of_joining || '',
    qualifications: qualificationRows,
    certifications: certificationRows,
    skills: Array.isArray(staff.skills)
      ? staff.skills
      : typeof staff.skills === 'string'
        ? staff.skills.split(',').map((item) => item.trim()).filter(Boolean)
        : [],
    username: staff.username || staff.phone || staff.mobile || '',
    password: '',
    confirm_password: '',
  };
};

export default function StaffTeamPage() {
  const workspace = useOutletContext();
  const outletCode = workspace.outlet?.code || 'OUTLET';
  const [filters, setFilters] = useState({ search: '', role: '', status: '', shift: '' });
  const [state, setState] = useState({ loading: true, stats: null, items: [], error: '' });
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardMode, setWizardMode] = useState('create');
  const [editingStaff, setEditingStaff] = useState(null);
  const [credentials, setCredentials] = useState(null);

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    const params = {};
    if (filters.search.trim()) params.search = filters.search.trim();
    if (filters.role) params.role = filters.role;
    if (filters.status) params.status = filters.status;
    if (filters.shift) params.shift = filters.shift;

    const [statsResult, listResult] = await Promise.allSettled([
      staffApi.getStats(),
      staffApi.list(params),
    ]);

    setState({
      loading: false,
      stats: statsResult.status === 'fulfilled' ? statsResult.value.data : null,
      items: listResult.status === 'fulfilled' ? readCollection(listResult.value.data, ['staff', 'items', 'results']) : [],
      error: listResult.status === 'rejected' ? apiErrorMessage(listResult.reason, 'Staff records could not be loaded.') : '',
    });
  }, [filters]);

  useEffect(() => { void load(); }, [load]);

  const staffMetrics = useMemo(() => {
    const activeCount = state.items.filter((item) => item.is_active !== false && String(item.status || '').toLowerCase() !== 'inactive').length;
    const onShiftCount = state.items.filter((item) => String(item.shift_status || item.on_shift || '').toLowerCase().includes('shift') || item.on_shift === true).length;
    return {
      total: readNumber(state.stats, ['total_staff', 'staff_count', 'total'], state.items.length) ?? state.items.length,
      activeToday: readNumber(state.stats, ['active_today', 'active_staff_today', 'active_staff'], activeCount) ?? activeCount,
      onShift: readNumber(state.stats, ['on_shift_now', 'staff_on_shift', 'on_shift'], onShiftCount) ?? onShiftCount,
      pendingRequests: readNumber(state.stats, ['pending_requests', 'requests_pending'], 0) ?? 0,
    };
  }, [state.items, state.stats]);

  const openCreate = () => {
    setWizardMode('create');
    setEditingStaff(null);
    setWizardOpen(true);
  };

  const openEdit = async (staff) => {
    setWizardMode('edit');
    setWizardOpen(true);
    setEditingStaff(null);
    try {
      const response = await staffApi.get(staff.id || staff.staff_profile_id || staff.user_id);
      setEditingStaff(readRecord(response.data, ['staff', 'member', 'employee']));
    } catch (error) {
      setWizardOpen(false);
      toast.error(apiErrorMessage(error, 'Unable to load this staff record for editing.'));
    }
  };

  const handleResetPassword = async (staff) => {
    if (!window.confirm(`Reset the password for ${staff.full_name || staff.first_name || 'this staff member'}?`)) return;
    try {
      const response = await staffApi.resetPassword(staff.id || staff.staff_profile_id || staff.user_id);
      const payload = response.data || {};
      const details = payload.credentials || payload.data?.credentials || payload;
      setCredentials({
        title: 'Save staff credentials now',
        username: details.username || staff.username || staff.phone || '',
        password: details.password || '',
        loginUrl: details.login_url || `${window.location.origin}/login`,
      });
      toast.success('Password reset complete.');
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to reset this password.'));
    }
  };

  const handleDeactivate = async (staff) => {
    const active = staff.is_active !== false && String(staff.status || '').toLowerCase() !== 'inactive';
    const action = active ? 'deactivate' : 'restore';
    if (!window.confirm(`${action === 'deactivate' ? 'Deactivate' : 'Restore'} ${staff.full_name || staff.first_name || 'this staff member'}?`)) return;
    try {
      if (action === 'deactivate') {
        await staffApi.deactivate(staff.id || staff.staff_profile_id || staff.user_id, 'Manager action from Staff & Team page');
      } else {
        await staffApi.restore(staff.id || staff.staff_profile_id || staff.user_id);
      }
      toast.success(active ? 'Staff account deactivated.' : 'Staff account restored.');
      await load();
    } catch (error) {
      toast.error(apiErrorMessage(error, `Unable to ${action} this staff account.`));
    }
  };

  return (
    <div className="staff-team-page">
      <PageHeader
        eyebrow="Manager · Team"
        title="Staff & Team"
        description="Manage outlet staff records, monitor live staffing coverage, and onboard new team members without leaving the manager workspace."
        action={<button type="button" className="exec-button exec-button-primary" onClick={openCreate}>+ Add Staff</button>}
      />

      <section className="manager-kpi-grid" aria-label="Staff team KPIs">
        <KpiCard label="Total Staff" value={formatCount(staffMetrics.total)} tone="gold" icon={PortfolioIcon} source="Team registry" />
        <KpiCard label="Active Today" value={formatCount(staffMetrics.activeToday)} tone="teal" icon={PulseIcon} source="Attendance summary" />
        <KpiCard label="On Shift Now" value={formatCount(staffMetrics.onShift)} tone="violet" icon={BriefingIcon} source="Shift coverage" />
        <KpiCard label="Pending Requests" value={formatCount(staffMetrics.pendingRequests)} tone="sunset" icon={AuditTrailIcon} source="Self-service queue" />
      </section>

      <section className="manager-panel">
        <div className="manager-section-heading">
          <div>
            <h2>Filter the team directory</h2>
            <p>Search by name, phone, or code, then narrow the view by role, status, or shift.</p>
          </div>
          <button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button>
        </div>
        <div className="staff-team-toolbar">
          <label className="staff-team-search">
            <span className="exec-eyebrow">Search</span>
            <input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Search name, phone, or employee code" />
          </label>
          <label className="staff-form-field">
            <span>Role</span>
            <select value={filters.role} onChange={(event) => setFilters((current) => ({ ...current, role: event.target.value }))}>
              <option value="">All roles</option>
              {roleOptions.map((role) => <option key={role} value={role}>{staffRoleLabel(role)}</option>)}
            </select>
          </label>
          <label className="staff-form-field">
            <span>Status</span>
            <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}>
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
          <label className="staff-form-field">
            <span>Shift</span>
            <input value={filters.shift} onChange={(event) => setFilters((current) => ({ ...current, shift: event.target.value }))} placeholder="Morning, evening…" />
          </label>
        </div>
      </section>

      {state.loading ? <LoadingBlock label="Loading staff directory" /> : null}
      {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Staff directory unavailable.</strong><span>{state.error}</span></div> : null}
      {!state.loading && !state.error && !state.items.length ? (
        <section className="manager-panel staff-empty-panel">
          <EmptyState title="No staff added yet" description="Create the first staff record for this outlet to begin tracking roles, attendance, and self-service access." />
        </section>
      ) : null}
      {!state.loading && !state.error && state.items.length ? (
        <section className="staff-card-grid">
          {state.items.map((staff) => {
            const staffId = staff.id || staff.staff_profile_id || staff.user_id;
            const active = staff.is_active !== false && String(staff.status || '').toLowerCase() !== 'inactive';
            const displayName = staff.full_name || [staff.first_name, staff.last_name].filter(Boolean).join(' ') || staff.username || 'Staff';
            return (
              <article className="staff-team-card" key={staffId}>
                <div className="staff-card-header">
                  <div className="staff-card-identity">
                    <Avatar name={displayName} photoUrl={staff.photo_url} />
                    <div className="staff-card-name">
                      <strong>{displayName}</strong>
                      <span className="staff-card-code">{staff.employee_code || staff.staff_id || 'Code pending'}</span>
                    </div>
                  </div>
                  <RolePill role={staff.staff_role || staff.role || 'staff'} />
                </div>

                <div className="staff-card-facts">
                  <div><span>Phone</span><strong>{staff.phone || staff.mobile || '—'}</strong></div>
                  <div><span>Email</span><strong>{staff.email || '—'}</strong></div>
                  <div><span>Joining date</span><strong>{formatDate(staff.joining_date || staff.date_of_joining || staff.joined_at)}</strong></div>
                  <div><span>Status</span><StatusPill active={active} label={active ? 'Active' : 'Inactive'} /></div>
                </div>

                <div className="staff-card-footer">
                  <div className="staff-card-actions">
                    <Link to={`/manager/team/staff/${staffId}`}>View</Link>
                    <button type="button" onClick={() => void openEdit(staff)}>Edit</button>
                    <Link to={`/manager/team/staff/${staffId}`}>Manage</Link>
                  </div>
                  <details className="staff-action-menu">
                    <summary>More</summary>
                    <div>
                      <button type="button" onClick={() => void handleResetPassword(staff)}>Reset password</button>
                      <button type="button" onClick={() => void handleDeactivate(staff)}>{active ? 'Deactivate' : 'Restore'}</button>
                    </div>
                  </details>
                </div>
              </article>
            );
          })}
        </section>
      ) : null}

      {wizardOpen ? (
        <StaffWizardModal
          mode={wizardMode}
          outletCode={outletCode}
          initialStaff={editingStaff}
          onClose={() => {
            setWizardOpen(false);
            setEditingStaff(null);
          }}
          onSaved={async ({ response, draft }) => {
            setWizardOpen(false);
            setEditingStaff(null);
            const savedStaff = readRecord(response.data, ['staff', 'member', 'employee']);
            const credentialsPayload = response.data?.credentials || response.data?.data?.credentials;
            if (wizardMode === 'create') {
              setCredentials({
                title: 'Save staff credentials now',
                username: credentialsPayload?.username || draft.username,
                password: credentialsPayload?.password || draft.password,
                loginUrl: credentialsPayload?.login_url || `${window.location.origin}/login`,
              });
            } else if (draft.photo_file && savedStaff.id) {
              await staffApi.uploadPhoto(savedStaff.id, draft.photo_file);
            }
            await load();
          }}
        />
      ) : null}

      {credentials ? <CredentialsModal credentials={credentials} onClose={() => setCredentials(null)} /> : null}
    </div>
  );
}

function StaffWizardModal({ mode, outletCode, initialStaff, onClose, onSaved }) {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState(() => initialStaff ? mapDraftFromStaff(initialStaff, outletCode) : createEmptyDraft(outletCode));

  useEffect(() => {
    setDraft(initialStaff ? mapDraftFromStaff(initialStaff, outletCode) : createEmptyDraft(outletCode));
  }, [initialStaff, outletCode]);

  useEffect(() => {
    if (draft.phone && !initialStaff && !draft.username) {
      setDraft((current) => ({ ...current, username: current.phone.replace(/\s+/g, '') }));
    }
  }, [draft.phone, draft.username, initialStaff]);

  const strength = passwordStrength(draft.password);

  const updateDraft = (field, value) => setDraft((current) => ({ ...current, [field]: value }));

  const addSkill = () => {
    const next = draft.skill_input.trim();
    if (!next || draft.skills.includes(next)) return;
    setDraft((current) => ({ ...current, skills: [...current.skills, next], skill_input: '' }));
  };

  const validateStep = () => {
    if (step === 0) {
      if (!draft.first_name.trim() || !draft.last_name.trim() || !draft.phone.trim() || !draft.staff_role) {
        toast.error('Complete the required identity fields before continuing.');
        return false;
      }
    }
    if (step === 2) {
      if (draft.aadhaar_number && !aadhaarRegex.test(draft.aadhaar_number.replace(/\s+/g, ' '))) {
        toast.error('Aadhaar format should be 12 digits.');
        return false;
      }
      if (draft.pan_number && !panRegex.test(draft.pan_number.toUpperCase())) {
        toast.error('PAN format should look like ABCDE1234F.');
        return false;
      }
    }
    if (step === 5) {
      if (!draft.username.trim()) {
        toast.error('Username is required.');
        return false;
      }
      if (mode === 'create' && !draft.password) {
        toast.error('Create a password before proceeding.');
        return false;
      }
      if (draft.password !== draft.confirm_password) {
        toast.error('Password confirmation does not match.');
        return false;
      }
    }
    return true;
  };

  const next = () => {
    if (!validateStep()) return;
    setStep((current) => Math.min(WIZARD_STEPS.length - 1, current + 1));
  };

  const previous = () => setStep((current) => Math.max(0, current - 1));

  const updateRepeatRow = (field, index, key, value) => {
    setDraft((current) => ({
      ...current,
      [field]: current[field].map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: value } : item)),
    }));
  };

  const addRepeatRow = (field, template) => {
    setDraft((current) => ({ ...current, [field]: [...current[field], template] }));
  };

  const removeRepeatRow = (field, index) => {
    setDraft((current) => ({ ...current, [field]: current[field].filter((_, itemIndex) => itemIndex !== index) }));
  };

  const submit = async () => {
    if (!validateStep()) return;
    setSaving(true);
    try {
      const payload = {
        first_name: draft.first_name.trim(),
        last_name: draft.last_name.trim(),
        phone: draft.phone.trim(),
        email: draft.email.trim() || undefined,
        employee_code: draft.employee_code.trim(),
        staff_role: draft.staff_role,
        date_of_birth: draft.date_of_birth || undefined,
        gender: draft.gender || undefined,
        blood_group: draft.blood_group || undefined,
        marital_status: draft.marital_status || undefined,
        current_address: draft.current_address.trim() || undefined,
        permanent_address: draft.permanent_address.trim() || undefined,
        emergency_contact_name: draft.emergency_contact_name.trim() || undefined,
        emergency_contact_phone: draft.emergency_contact_phone.trim() || undefined,
        emergency_contact_relation: draft.emergency_contact_relation.trim() || undefined,
        aadhaar_number: draft.aadhaar_number.replace(/\s+/g, '') || undefined,
        pan_number: draft.pan_number.toUpperCase() || undefined,
        voter_id: draft.voter_id.trim() || undefined,
        driving_license: draft.driving_license.trim() || undefined,
        bank_account_name: draft.bank_account_name.trim() || undefined,
        bank_account_number: draft.bank_account_number.trim() || undefined,
        ifsc_code: draft.ifsc_code.trim() || undefined,
        bank_name: draft.bank_name.trim() || undefined,
        branch_name: draft.branch_name.trim() || undefined,
        upi_id: draft.upi_id.trim() || undefined,
        joining_date: draft.joining_date || undefined,
        employment_type: draft.employment_type || undefined,
        salary_type: draft.salary_type || undefined,
        salary_amount: draft.salary_amount ? Number(draft.salary_amount) : undefined,
        pf_enabled: draft.pf_enabled,
        esi_enabled: draft.esi_enabled,
        tds_enabled: draft.tds_enabled,
        shift_preference: draft.shift_preference.trim() || undefined,
        weekly_off_day: draft.weekly_off_day || undefined,
        qualifications: draft.qualifications.filter((item) => item.degree || item.institution || item.year),
        certifications: draft.certifications.filter((item) => item.name || item.issuer || item.year),
        years_of_experience: draft.years_of_experience ? Number(draft.years_of_experience) : undefined,
        previous_employer: draft.previous_employer.trim() || undefined,
        skills: draft.skills,
        username: draft.username.trim(),
        password: draft.password || undefined,
        force_password_change: true,
      };
      const response = mode === 'edit' && initialStaff?.id
        ? await staffApi.update(initialStaff.id, payload)
        : await staffApi.create(payload);
      const saved = readRecord(response.data, ['staff', 'member', 'employee']);
      if (draft.photo_file && saved.id) {
        await staffApi.uploadPhoto(saved.id, draft.photo_file);
      }
      toast.success(mode === 'edit' ? 'Staff record updated.' : 'Staff record created.');
      onSaved({ response, draft });
    } catch (error) {
      toast.error(apiErrorMessage(error, mode === 'edit' ? 'Unable to update this staff record.' : 'Unable to create this staff record.'));
    } finally {
      setSaving(false);
    }
  };

  const reviewCards = [
    {
      title: 'Identity',
      items: [
        ['Name', `${draft.first_name} ${draft.last_name}`.trim() || '—'],
        ['Phone', draft.phone || '—'],
        ['Email', draft.email || '—'],
        ['Employee code', draft.employee_code || '—'],
        ['Role', staffRoleLabel(draft.staff_role)],
      ],
    },
    {
      title: 'Employment',
      items: [
        ['Joining date', draft.joining_date || '—'],
        ['Employment type', draft.employment_type || '—'],
        ['Salary', draft.salary_amount ? `₹${draft.salary_amount}` : '—'],
        ['Shift preference', draft.shift_preference || '—'],
        ['Weekly off', draft.weekly_off_day || '—'],
      ],
    },
    {
      title: 'Login',
      items: [
        ['Username', draft.username || '—'],
        ['Password', draft.password ? 'Ready to issue' : 'Server-generated or not changed'],
        ['Force password change', 'Enabled'],
      ],
    },
    {
      title: 'Qualifications',
      items: [
        ['Experience', draft.years_of_experience || '—'],
        ['Previous employer', draft.previous_employer || '—'],
        ['Skills', draft.skills.join(', ') || '—'],
      ],
    },
  ];

  return (
    <div className="staff-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="staff-modal" role="dialog" aria-modal="true" aria-labelledby="staff-wizard-title" onClick={(event) => event.stopPropagation()}>
        <header className="staff-modal-header">
          <div>
            <h2 id="staff-wizard-title">{mode === 'edit' ? 'Edit staff record' : 'Create a staff record'}</h2>
            <p>{mode === 'edit' ? 'Update the existing staff record through the guided workflow.' : 'Guide onboarding through identity, compliance, payroll, and login setup before the account goes live.'}</p>
          </div>
          <button type="button" className="exec-button exec-button-secondary" onClick={onClose}>Close</button>
        </header>

        <div className="staff-wizard-layout">
          <aside className="staff-wizard-steps" aria-label="Staff creation steps">
            {WIZARD_STEPS.map((item, index) => (
              <div key={item.id} className={`staff-wizard-step${step === index ? ' is-active' : ''}${step > index ? ' is-complete' : ''}`} aria-current={step === index ? 'step' : undefined}>
                <span>{step > index ? '✓' : String(index + 1).padStart(2, '0')}</span>
                <div>
                  <strong>{item.title}</strong>
                  <small>{item.hint}</small>
                </div>
              </div>
            ))}
          </aside>

          <div className="staff-wizard-panel">
            <header>
              <h3>{WIZARD_STEPS[step].title}</h3>
              <p>{WIZARD_STEPS[step].hint}</p>
            </header>

            {step === 0 ? (
              <div className="staff-form-grid">
                <label className="staff-form-field">
                  <span>First name</span>
                  <input value={draft.first_name} onChange={(event) => updateDraft('first_name', event.target.value)} />
                </label>
                <label className="staff-form-field">
                  <span>Last name</span>
                  <input value={draft.last_name} onChange={(event) => updateDraft('last_name', event.target.value)} />
                </label>
                <label className="staff-form-field">
                  <span>Phone</span>
                  <input value={draft.phone} onChange={(event) => updateDraft('phone', event.target.value)} placeholder="+91 9876543210" />
                </label>
                <label className="staff-form-field">
                  <span>Email</span>
                  <input type="email" value={draft.email} onChange={(event) => updateDraft('email', event.target.value)} />
                </label>
                <label className="staff-form-field">
                  <span>Employee code</span>
                  <input value={draft.employee_code} onChange={(event) => updateDraft('employee_code', event.target.value)} />
                  <small>Suggested from outlet code; uniqueness is enforced server-side.</small>
                </label>
                <label className="staff-form-field">
                  <span>Staff role</span>
                  <select value={draft.staff_role} onChange={(event) => updateDraft('staff_role', event.target.value)}>
                    {roleOptions.map((role) => <option key={role} value={role}>{staffRoleLabel(role)}</option>)}
                  </select>
                </label>
                <label className="staff-form-field is-wide">
                  <span>Profile photo</span>
                  <div className="staff-upload-dropzone">
                    {draft.photo_preview ? <img src={draft.photo_preview} alt="Preview" /> : <Avatar name={`${draft.first_name} ${draft.last_name}`} photoUrl="" className="manager-avatar large" />}
                    <p>Choose a PNG, JPG, WebP, or SVG portrait.</p>
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/svg+xml"
                      onChange={(event) => {
                        const file = event.target.files?.[0] || null;
                        updateDraft('photo_file', file);
                        updateDraft('photo_preview', file ? URL.createObjectURL(file) : '');
                      }}
                    />
                  </div>
                </label>
              </div>
            ) : null}

            {step === 1 ? (
              <div className="staff-form-grid">
                <label className="staff-form-field"><span>Date of birth</span><input type="date" value={draft.date_of_birth} onChange={(event) => updateDraft('date_of_birth', event.target.value)} /></label>
                <label className="staff-form-field"><span>Gender</span><select value={draft.gender} onChange={(event) => updateDraft('gender', event.target.value)}><option value="">Select gender</option>{genderOptions.map((item) => <option key={item} value={item}>{staffRoleLabel(item)}</option>)}</select></label>
                <label className="staff-form-field"><span>Blood group</span><select value={draft.blood_group} onChange={(event) => updateDraft('blood_group', event.target.value)}><option value="">Select blood group</option>{bloodOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <label className="staff-form-field"><span>Marital status</span><select value={draft.marital_status} onChange={(event) => updateDraft('marital_status', event.target.value)}><option value="">Select status</option>{maritalOptions.map((item) => <option key={item} value={item}>{staffRoleLabel(item)}</option>)}</select></label>
                <label className="staff-form-field is-wide"><span>Current address</span><textarea value={draft.current_address} onChange={(event) => updateDraft('current_address', event.target.value)} /></label>
                <label className="staff-form-field is-wide"><span>Permanent address</span><textarea value={draft.permanent_address} onChange={(event) => updateDraft('permanent_address', event.target.value)} /></label>
                <label className="staff-form-field"><span>Emergency contact name</span><input value={draft.emergency_contact_name} onChange={(event) => updateDraft('emergency_contact_name', event.target.value)} /></label>
                <label className="staff-form-field"><span>Emergency contact phone</span><input value={draft.emergency_contact_phone} onChange={(event) => updateDraft('emergency_contact_phone', event.target.value)} /></label>
                <label className="staff-form-field is-wide"><span>Relation</span><input value={draft.emergency_contact_relation} onChange={(event) => updateDraft('emergency_contact_relation', event.target.value)} /></label>
              </div>
            ) : null}

            {step === 2 ? (
              <div className="staff-form-grid">
                <label className="staff-form-field">
                  <span>Aadhaar</span>
                  <input value={draft.aadhaar_number} onChange={(event) => updateDraft('aadhaar_number', event.target.value.replace(/[^\d\s]/g, '').slice(0, 14))} placeholder="1234 5678 9012" />
                  <small>Preview: {maskedAadhaarPreview(draft.aadhaar_number)}</small>
                </label>
                <label className="staff-form-field">
                  <span>PAN</span>
                  <input value={draft.pan_number} onChange={(event) => updateDraft('pan_number', event.target.value.toUpperCase())} placeholder="ABCDE1234F" />
                </label>
                <label className="staff-form-field"><span>Voter ID</span><input value={draft.voter_id} onChange={(event) => updateDraft('voter_id', event.target.value)} /></label>
                <label className="staff-form-field"><span>Driving licence</span><input value={draft.driving_license} onChange={(event) => updateDraft('driving_license', event.target.value)} /></label>
                <label className="staff-form-field is-wide">
                  <span>Supporting document upload</span>
                  <input type="file" accept="image/*,application/pdf" onChange={(event) => updateDraft('document_file', event.target.files?.[0] || null)} />
                  <small>{draft.document_file ? draft.document_file.name : 'Upload image or PDF if available.'}</small>
                </label>
              </div>
            ) : null}

            {step === 3 ? (
              <div className="staff-form-grid">
                <label className="staff-form-field"><span>Bank account name</span><input value={draft.bank_account_name} onChange={(event) => updateDraft('bank_account_name', event.target.value)} /></label>
                <label className="staff-form-field"><span>Bank account number</span><input value={draft.bank_account_number} onChange={(event) => updateDraft('bank_account_number', event.target.value)} /></label>
                <label className="staff-form-field"><span>IFSC</span><input value={draft.ifsc_code} onChange={(event) => updateDraft('ifsc_code', event.target.value.toUpperCase())} /></label>
                <label className="staff-form-field"><span>Bank name</span><input value={draft.bank_name} onChange={(event) => updateDraft('bank_name', event.target.value)} /></label>
                <label className="staff-form-field"><span>Branch</span><input value={draft.branch_name} onChange={(event) => updateDraft('branch_name', event.target.value)} /></label>
                <label className="staff-form-field"><span>UPI ID</span><input value={draft.upi_id} onChange={(event) => updateDraft('upi_id', event.target.value)} /></label>
                <label className="staff-form-field"><span>Joining date</span><input type="date" value={draft.joining_date} onChange={(event) => updateDraft('joining_date', event.target.value)} /></label>
                <label className="staff-form-field"><span>Employment type</span><select value={draft.employment_type} onChange={(event) => updateDraft('employment_type', event.target.value)}>{employmentOptions.map((item) => <option key={item} value={item}>{staffRoleLabel(item)}</option>)}</select></label>
                <label className="staff-form-field"><span>Salary type</span><select value={draft.salary_type} onChange={(event) => updateDraft('salary_type', event.target.value)}>{salaryOptions.map((item) => <option key={item} value={item}>{staffRoleLabel(item)}</option>)}</select></label>
                <label className="staff-form-field"><span>Salary amount</span><input type="number" min="0" step="0.01" value={draft.salary_amount} onChange={(event) => updateDraft('salary_amount', event.target.value)} /></label>
                <label className="staff-form-field"><span>Shift preference</span><input value={draft.shift_preference} onChange={(event) => updateDraft('shift_preference', event.target.value)} placeholder="Morning, mid, closing…" /></label>
                <label className="staff-form-field"><span>Weekly off day</span><select value={draft.weekly_off_day} onChange={(event) => updateDraft('weekly_off_day', event.target.value)}><option value="">Select day</option>{weeklyOffOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
                <div className="staff-form-field is-wide">
                  <span>PF / ESI / TDS</span>
                  <div className="staff-toggle-row">
                    <label className="staff-skill-chip"><input type="checkbox" checked={draft.pf_enabled} onChange={(event) => updateDraft('pf_enabled', event.target.checked)} /> PF</label>
                    <label className="staff-skill-chip"><input type="checkbox" checked={draft.esi_enabled} onChange={(event) => updateDraft('esi_enabled', event.target.checked)} /> ESI</label>
                    <label className="staff-skill-chip"><input type="checkbox" checked={draft.tds_enabled} onChange={(event) => updateDraft('tds_enabled', event.target.checked)} /> TDS</label>
                  </div>
                </div>
              </div>
            ) : null}

            {step === 4 ? (
              <div className="staff-repeat-list">
                <section className="staff-repeat-card">
                  <header>
                    <strong>Qualifications</strong>
                    <button type="button" className="staff-inline-button" onClick={() => addRepeatRow('qualifications', { degree: '', institution: '', year: '' })}>Add qualification</button>
                  </header>
                  {draft.qualifications.map((item, index) => (
                    <div className="staff-form-grid" key={`qualification-row-${index}`}>
                      <label className="staff-form-field"><span>Degree</span><input value={item.degree} onChange={(event) => updateRepeatRow('qualifications', index, 'degree', event.target.value)} /></label>
                      <label className="staff-form-field"><span>Institution</span><input value={item.institution} onChange={(event) => updateRepeatRow('qualifications', index, 'institution', event.target.value)} /></label>
                      <label className="staff-form-field"><span>Year</span><input value={item.year} onChange={(event) => updateRepeatRow('qualifications', index, 'year', event.target.value)} /></label>
                      <button type="button" className="staff-inline-button" onClick={() => removeRepeatRow('qualifications', index)} disabled={draft.qualifications.length === 1}>Remove</button>
                    </div>
                  ))}
                </section>

                <section className="staff-repeat-card">
                  <header>
                    <strong>Certifications</strong>
                    <button type="button" className="staff-inline-button" onClick={() => addRepeatRow('certifications', { name: '', issuer: '', year: '' })}>Add certification</button>
                  </header>
                  {draft.certifications.map((item, index) => (
                    <div className="staff-form-grid" key={`certification-row-${index}`}>
                      <label className="staff-form-field"><span>Name</span><input value={item.name} onChange={(event) => updateRepeatRow('certifications', index, 'name', event.target.value)} /></label>
                      <label className="staff-form-field"><span>Issuer</span><input value={item.issuer} onChange={(event) => updateRepeatRow('certifications', index, 'issuer', event.target.value)} /></label>
                      <label className="staff-form-field"><span>Year</span><input value={item.year} onChange={(event) => updateRepeatRow('certifications', index, 'year', event.target.value)} /></label>
                      <button type="button" className="staff-inline-button" onClick={() => removeRepeatRow('certifications', index)} disabled={draft.certifications.length === 1}>Remove</button>
                    </div>
                  ))}
                </section>

                <div className="staff-form-grid">
                  <label className="staff-form-field"><span>Years of experience</span><input type="number" min="0" step="0.1" value={draft.years_of_experience} onChange={(event) => updateDraft('years_of_experience', event.target.value)} /></label>
                  <label className="staff-form-field"><span>Previous employer</span><input value={draft.previous_employer} onChange={(event) => updateDraft('previous_employer', event.target.value)} /></label>
                  <label className="staff-form-field is-wide">
                    <span>Skills</span>
                    <div className="staff-inline-actions">
                      <input value={draft.skill_input} onChange={(event) => updateDraft('skill_input', event.target.value)} placeholder="Add a skill and press Add" />
                      <button type="button" className="staff-inline-button" onClick={addSkill}>Add</button>
                    </div>
                    <div className="staff-chip-row">
                      {draft.skills.map((skill) => (
                        <span className="staff-skill-chip" key={skill}>{skill}<button type="button" onClick={() => updateDraft('skills', draft.skills.filter((item) => item !== skill))}>×</button></span>
                      ))}
                    </div>
                  </label>
                </div>
              </div>
            ) : null}

            {step === 5 ? (
              <div className="staff-form-grid">
                <label className="staff-form-field"><span>Username</span><input value={draft.username} onChange={(event) => updateDraft('username', event.target.value)} /></label>
                <label className="staff-form-field">
                  <span>Password</span>
                  <div className="staff-inline-actions">
                    <input type="password" value={draft.password} onChange={(event) => updateDraft('password', event.target.value)} />
                    <button type="button" className="staff-inline-button" onClick={() => { const generated = randomPassword(); updateDraft('password', generated); updateDraft('confirm_password', generated); }}>Auto-generate</button>
                  </div>
                </label>
                <label className="staff-form-field"><span>Confirm password</span><input type="password" value={draft.confirm_password} onChange={(event) => updateDraft('confirm_password', event.target.value)} /></label>
                <label className="staff-form-field">
                  <span>Force password change</span>
                  <input type="text" value="Enabled on first login" disabled readOnly />
                </label>
                <div className="staff-form-field is-wide staff-password-meter">
                  <span>Password strength</span>
                  <div className="staff-password-meter-bar" style={{ '--password-strength': `${Math.round(strength.score * 100)}%` }}><i aria-hidden="true" /></div>
                  <small>{strength.label}. Staff will be able to log in immediately with these credentials.</small>
                </div>
              </div>
            ) : null}

            {step === 6 ? (
              <div className="staff-repeat-list">
                <div className="staff-warning-banner">Staff will be able to log in immediately with these credentials.</div>
                <div className="staff-review-grid">
                  {reviewCards.map((card) => (
                    <section className="staff-review-card" key={card.title}>
                      <h4>{card.title}</h4>
                      <dl>
                        {card.items.map(([label, value]) => (
                          <div key={label}>
                            <dt>{label}</dt>
                            <dd>{value || '—'}</dd>
                          </div>
                        ))}
                      </dl>
                    </section>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <footer className="staff-modal-footer">
          <span>Step {step + 1} of {WIZARD_STEPS.length}</span>
          <div className="staff-inline-actions">
            <button type="button" className="exec-button exec-button-secondary" onClick={previous} disabled={step === 0 || saving}>Back</button>
            {step < WIZARD_STEPS.length - 1 ? (
              <button type="button" className="exec-button exec-button-primary" onClick={next} disabled={saving}>Continue</button>
            ) : (
              <button type="button" className="exec-button exec-button-primary" onClick={() => void submit()} disabled={saving}>{saving ? 'Saving…' : mode === 'edit' ? 'Save Staff' : 'Create Staff'}</button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}

function CredentialsModal({ credentials, onClose }) {
  const copy = async (text, label) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${label} copied.`);
    } catch {
      toast.error('Clipboard access is unavailable. Copy the credentials manually.');
    }
  };

  const download = () => {
    const content = `Login URL: ${credentials.loginUrl}\nUsername: ${credentials.username}\nPassword: ${credentials.password}\n\nSave these credentials. Password will not be shown again.`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'staff-credentials.txt';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="staff-modal-backdrop" role="presentation" onClick={onClose}>
      <section className="staff-modal staff-modal-compact" role="dialog" aria-modal="true" aria-labelledby="staff-credentials-title" onClick={(event) => event.stopPropagation()}>
        <header className="staff-modal-header">
          <div>
            <h3 id="staff-credentials-title">{credentials.title}</h3>
            <p>Save these credentials. Password will not be shown again.</p>
          </div>
          <button type="button" className="exec-button exec-button-secondary" onClick={onClose}>Close</button>
        </header>
        <div className="staff-wizard-panel" style={{ padding: '0 24px 24px' }}>
          <div className="staff-warning-banner">Save these credentials. Password will not be shown again.</div>
          <div className="staff-credentials-grid">
            <div className="staff-credentials-card"><span>Login URL</span><code>{credentials.loginUrl}</code></div>
            <div className="staff-credentials-card"><span>Username</span><code>{credentials.username}</code></div>
            <div className="staff-credentials-card"><span>Password</span><code>{credentials.password || 'Password returned without a visible one-time value.'}</code></div>
          </div>
          <div className="staff-copy-actions">
            <button type="button" className="exec-button exec-button-secondary" onClick={() => void copy(credentials.username, 'Username')}>Copy username</button>
            <button type="button" className="exec-button exec-button-secondary" onClick={() => void copy(credentials.password, 'Password')}>Copy password</button>
            <button type="button" className="exec-button exec-button-secondary" onClick={() => void copy(`Login URL: ${credentials.loginUrl}\nUsername: ${credentials.username}\nPassword: ${credentials.password}`, 'Credentials')}>Copy all</button>
            <button type="button" className="exec-button exec-button-secondary" onClick={download}>Download as text</button>
          </div>
        </div>
        <footer className="staff-modal-footer">
          <span>PDF and SMS delivery remain out of scope for this phase.</span>
          <button type="button" className="exec-button exec-button-primary" onClick={onClose}>Done</button>
        </footer>
      </section>
    </div>
  );
}
