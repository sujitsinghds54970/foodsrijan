import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Link, useParams } from 'react-router-dom';
import OrbitalMotif from '../../../components/SuperCEO/common/OrbitalMotif';
import LoginCredentialsPanel from '../../../components/auth/LoginCredentialsPanel';
import {
  AuditTrailIcon,
  BriefingIcon,
  CommandIcon,
  LedgerIcon,
  PulseIcon,
  ShieldIcon,
  SparkIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi, staffRoleLabel } from '../../../services/staffApi';
import { resolveAssetUrl } from '../../../services/superCeoProfileApi';
import '../../../styles/staff.css';
import {
  FieldGrid,
  LoadingBlock,
  RolePill,
  SectionEmpty,
  StatusPill,
  formatCurrency,
  formatDate,
  formatDateTime,
  makeInitials,
  readCollection,
  readRecord,
} from '../../Staff/shared/staffShared';

const TAB_DEFINITIONS = [
  { id: 'overview', label: 'Overview', icon: CommandIcon },
  { id: 'personal', label: 'Personal', icon: PulseIcon },
  { id: 'documents', label: 'Documents', icon: ShieldIcon },
  { id: 'bank', label: 'Bank', icon: LedgerIcon },
  { id: 'employment', label: 'Employment', icon: BriefingIcon },
  { id: 'qualifications', label: 'Qualifications', icon: SparkIcon },
  { id: 'attendance', label: 'Attendance', icon: PulseIcon },
  { id: 'payslips', label: 'Payslips', icon: LedgerIcon },
  { id: 'performance', label: 'Performance', icon: SparkIcon },
  { id: 'activity', label: 'Activity', icon: AuditTrailIcon },
  { id: 'security', label: 'Security', icon: ShieldIcon },
];

const visibleValue = (record, key, fallback = '—') => {
  const maskedKey = `${key}_masked`;
  return record?.[maskedKey] || record?.[key] || fallback;
};

export default function StaffDetailPage() {
  const { staffId } = useParams();
  const [activeTab, setActiveTab] = useState('overview');
  const [state, setState] = useState({ loading: true, staff: null, audit: [], error: '' });
  const [revealed, setRevealed] = useState({});
  const [working, setWorking] = useState({ reset: false, deactivate: false });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    const [staffResult, auditResult] = await Promise.allSettled([
      staffApi.get(staffId),
      staffApi.getAudit(staffId),
    ]);

    if (staffResult.status !== 'fulfilled') {
      setState({ loading: false, staff: null, audit: [], error: apiErrorMessage(staffResult.reason, 'This staff record could not be loaded.') });
      return;
    }

    setState({
      loading: false,
      staff: readRecord(staffResult.value.data, ['staff', 'member', 'employee']),
      audit: auditResult.status === 'fulfilled' ? readCollection(auditResult.value.data, ['events', 'audit', 'items', 'activity']) : [],
      error: '',
    });
  }, [staffId]);

  useEffect(() => { void load(); }, [load]);

  const staff = state.staff;
  const displayName = useMemo(() => {
    if (!staff) return 'Staff';
    return staff.full_name || [staff.first_name, staff.last_name].filter(Boolean).join(' ') || staff.username || 'Staff';
  }, [staff]);

  const active = staff ? staff.is_active !== false && String(staff.status || '').toLowerCase() !== 'inactive' : false;
  const attendanceItems = Array.isArray(staff?.attendance) ? staff.attendance : [];
  const payslipItems = Array.isArray(staff?.payslips) ? staff.payslips : [];
  const performanceItems = Array.isArray(staff?.performance) ? staff.performance : staff?.performance ? [staff.performance] : [];
  const qualificationItems = Array.isArray(staff?.qualifications) ? staff.qualifications : [];
  const certificationItems = Array.isArray(staff?.certifications) ? staff.certifications : [];
  const skillItems = Array.isArray(staff?.skills)
    ? staff.skills
    : typeof staff?.skills === 'string'
      ? staff.skills.split(',').map((item) => item.trim()).filter(Boolean)
      : [];

  const reveal = async (field) => {
    if (!window.confirm(`Reveal ${field.replace(/_/g, ' ')}? This action may be recorded for audit purposes.`)) return;
    try {
      const response = await staffApi.revealField(staffId, field);
      const payload = response.data || {};
      setRevealed((current) => ({ ...current, [field]: payload.value || payload[field] || payload.data?.value || payload.data?.[field] || 'Unavailable' }));
      toast.success(`${field.replace(/_/g, ' ')} revealed for this session.`);
    } catch (error) {
      toast.error(apiErrorMessage(error, `Unable to reveal ${field.replace(/_/g, ' ')}.`));
    }
  };

  const handleStatusToggle = async () => {
    if (!window.confirm(`${active ? 'Deactivate' : 'Restore'} ${displayName}?`)) return;
    setWorking((current) => ({ ...current, deactivate: true }));
    try {
      if (active) {
        await staffApi.deactivate(staffId, 'Manager action from staff detail page');
      } else {
        await staffApi.restore(staffId);
      }
      toast.success(active ? 'Staff account deactivated.' : 'Staff account restored.');
      await load();
    } catch (error) {
      toast.error(apiErrorMessage(error, active ? 'Unable to deactivate this staff account.' : 'Unable to restore this staff account.'));
    } finally {
      setWorking((current) => ({ ...current, deactivate: false }));
    }
  };

  const renderMaskedField = (label, field) => (
    <div key={field}>
      <dt>{label}</dt>
      <dd>
        <div className="staff-masked-row">
          <code>{revealed[field] || visibleValue(staff, field)}</code>
          <button type="button" className="staff-reveal-button" onClick={() => void reveal(field)}>Reveal</button>
        </div>
      </dd>
    </div>
  );

  const tabPanel = !staff ? null : activeTab === 'overview' ? (
    <div className="staff-tab-panel">
      <section className="manager-panel">
        <div className="manager-section-heading">
          <div>
            <h2>Staff overview</h2>
            <p>High-level identity, outlet, and employment information for this staff record.</p>
          </div>
        </div>
        <FieldGrid items={[
          { label: 'Employee code', value: staff.employee_code || staff.staff_id || '—' },
          { label: 'Role', value: staffRoleLabel(staff.staff_role || staff.role || 'staff') },
          { label: 'Outlet', value: staff.outlet_name || '—' },
          { label: 'Phone', value: staff.phone || staff.mobile || '—' },
          { label: 'Email', value: staff.email || '—' },
          { label: 'Joining date', value: formatDate(staff.joining_date || staff.date_of_joining || staff.joined_at) },
        ]} />
      </section>
    </div>
  ) : activeTab === 'personal' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Personal details</h2>
          <p>Current profile, emergency, and demographic details published for this employee.</p>
        </div>
      </div>
      <FieldGrid items={[
        { label: 'Date of birth', value: formatDate(staff.date_of_birth) },
        { label: 'Gender', value: staff.gender || '—' },
        { label: 'Blood group', value: staff.blood_group || '—' },
        { label: 'Marital status', value: staff.marital_status || '—' },
        { label: 'Current address', value: staff.current_address || staff.address || '—' },
        { label: 'Permanent address', value: staff.permanent_address || '—' },
        { label: 'Emergency contact name', value: staff.emergency_contact_name || '—' },
        { label: 'Emergency contact phone', value: staff.emergency_contact_phone || '—' },
        { label: 'Emergency contact relation', value: staff.emergency_contact_relation || '—' },
      ]} />
    </section>
  ) : activeTab === 'documents' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Documents</h2>
          <p>Personally sensitive fields remain masked by default and can be revealed with explicit confirmation.</p>
        </div>
      </div>
      <dl className="manager-stat-list staff-field-grid">
        {renderMaskedField('Aadhaar', 'aadhaar_number')}
        {renderMaskedField('PAN', 'pan_number')}
        {renderMaskedField('Voter ID', 'voter_id')}
        {renderMaskedField('Driving licence', 'driving_license')}
      </dl>
      {!staff.documents ? <div className="staff-empty-subsection"><SectionEmpty title="No uploaded document bundle" description="Supporting files will appear here once the backend starts returning them for this employee." /></div> : null}
    </section>
  ) : activeTab === 'bank' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Bank details</h2>
          <p>Bank account fields stay masked until a manager explicitly reveals them for the current session.</p>
        </div>
      </div>
      <dl className="manager-stat-list staff-field-grid">
        <div><dt>Bank name</dt><dd>{staff.bank_name || '—'}</dd></div>
        {renderMaskedField('Account number', 'bank_account_number')}
        <div><dt>IFSC</dt><dd>{staff.ifsc_code || '—'}</dd></div>
        <div><dt>Branch</dt><dd>{staff.branch_name || '—'}</dd></div>
        {renderMaskedField('UPI ID', 'upi_id')}
        <div><dt>Salary amount</dt><dd>{staff.salary_amount != null ? formatCurrency(staff.salary_amount) : '—'}</dd></div>
      </dl>
    </section>
  ) : activeTab === 'employment' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Employment</h2>
          <p>Joining, shift, payroll, and tax setup for the staff account.</p>
        </div>
      </div>
      <FieldGrid items={[
        { label: 'Joining date', value: formatDate(staff.joining_date || staff.date_of_joining || staff.joined_at) },
        { label: 'Employment type', value: staff.employment_type || '—' },
        { label: 'Salary type', value: staff.salary_type || '—' },
        { label: 'Salary amount', value: staff.salary_amount != null ? formatCurrency(staff.salary_amount) : '—' },
        { label: 'Shift preference', value: staff.shift_preference || staff.shift || '—' },
        { label: 'Weekly off day', value: staff.weekly_off_day || '—' },
        { label: 'PF enabled', value: staff.pf_enabled ? 'Yes' : 'No' },
        { label: 'ESI enabled', value: staff.esi_enabled ? 'Yes' : 'No' },
        { label: 'TDS enabled', value: staff.tds_enabled ? 'Yes' : 'No' },
      ]} />
    </section>
  ) : activeTab === 'qualifications' ? (
    <div className="staff-tab-panel">
      <section className="manager-panel">
        <div className="manager-section-heading">
          <div>
            <h2>Qualifications</h2>
            <p>Education, certifications, experience, and skills currently recorded for this staff member.</p>
          </div>
        </div>
        {!qualificationItems.length ? <SectionEmpty title="No qualifications recorded" description="Qualification rows will appear here once they are returned by the backend." /> : (
          <ol className="staff-audit-list">
            {qualificationItems.map((item, index) => (
              <li key={`qualification-${index}`}>
                <strong>{item.degree || item.title || `Qualification ${index + 1}`}</strong>
                <span>{[item.institution, item.year, item.grade].filter(Boolean).join(' · ') || 'No further detail provided.'}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
      <section className="manager-panel">
        <div className="manager-section-heading">
          <div>
            <h2>Certifications & skills</h2>
            <p>Specialized credentials and recorded strengths for the current role.</p>
          </div>
        </div>
        {certificationItems.length ? (
          <ol className="staff-audit-list">
            {certificationItems.map((item, index) => (
              <li key={`certification-${index}`}>
                <strong>{item.name || item.title || `Certification ${index + 1}`}</strong>
                <span>{[item.issuer, item.year, item.reference].filter(Boolean).join(' · ') || 'No further detail provided.'}</span>
              </li>
            ))}
          </ol>
        ) : <SectionEmpty title="No certifications recorded" description="Certification rows will appear here once they are returned by the backend." />}
        {skillItems.length ? <div className="staff-chip-row">{skillItems.map((skill) => <span key={skill} className="staff-skill-chip">{skill}</span>)}</div> : <p className="staff-profile-activity-note">No skills tags available yet.</p>}
      </section>
    </div>
  ) : activeTab === 'attendance' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Attendance</h2>
          <p>Attendance records appear here only when the employee detail payload includes them.</p>
        </div>
      </div>
      {!attendanceItems.length ? <SectionEmpty title="No attendance data published yet" description="Attendance remains empty until the backend sends detail-level records for this employee." /> : (
        <ol className="staff-record-list">
          {attendanceItems.map((item, index) => (
            <li key={item.id || `attendance-${index}`}>
              <div>
                <strong>{formatDate(item.attendance_date || item.date)}</strong>
                <span>{item.clock_in_time || item.clock_out_time ? `${item.clock_in_time || '—'} → ${item.clock_out_time || '—'}` : 'Shift timings not provided.'}</span>
              </div>
              <div className="manager-list-meta">
                <b>{item.status || item.attendance_type || 'Recorded'}</b>
                <small>{formatDateTime(item.updated_at || item.created_at)}</small>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  ) : activeTab === 'payslips' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Payslips</h2>
          <p>No numbers are fabricated here; this tab only renders published payslip rows when available.</p>
        </div>
      </div>
      {!payslipItems.length ? <SectionEmpty title="No payslips published yet" description="Payslips will appear once payroll data is attached to this employee record." /> : (
        <ol className="staff-record-list">
          {payslipItems.map((item, index) => (
            <li key={item.id || `payslip-${index}`}>
              <div>
                <strong>{item.label || item.month_label || `Payslip ${index + 1}`}</strong>
                <span>{item.reference || item.payslip_number || 'No additional reference provided.'}</span>
              </div>
              <div className="manager-list-meta">
                <b>{item.status || 'Published'}</b>
                <small>{item.net_pay != null ? formatCurrency(item.net_pay) : formatDate(item.generated_at || item.published_at)}</small>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  ) : activeTab === 'performance' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Performance</h2>
          <p>Performance data appears only if the backend provides it for this employee.</p>
        </div>
      </div>
      {!performanceItems.length ? <SectionEmpty title="No performance data published yet" description="Performance scorecards are intentionally empty until the backend returns real figures." /> : (
        <ol className="staff-audit-list">
          {performanceItems.map((item, index) => (
            <li key={`performance-${index}`}>
              <strong>{item.title || item.month || item.label || `Performance ${index + 1}`}</strong>
              <span>{item.summary || [item.attendance_percentage ? `${item.attendance_percentage}% attendance` : null, item.tasks_completed != null ? `${item.tasks_completed} tasks completed` : null].filter(Boolean).join(' · ') || 'No additional detail provided.'}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  ) : activeTab === 'activity' ? (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Activity</h2>
          <p>Audit and lifecycle events tied to this staff record.</p>
        </div>
      </div>
      {!state.audit.length ? <SectionEmpty title="No audit events returned yet" description="The audit stream will appear here once staff audit events are exposed for this record." /> : (
        <ol className="manager-activity-list">
          {state.audit.map((item, index) => (
            <li key={item.id || `audit-${index}`}>
              <i aria-hidden="true" />
              <div>
                <strong>{item.action || item.title || item.event || `Audit ${index + 1}`}</strong>
                <span>{item.description || item.detail || item.resource || 'No further audit detail provided.'}</span>
              </div>
              <time>{formatDateTime(item.timestamp || item.created_at)}</time>
            </li>
          ))}
        </ol>
      )}
    </section>
  ) : (
    <section className="manager-panel">
      <div className="manager-section-heading">
        <div>
          <h2>Security controls</h2>
          <p>Reset credentials or change the active status of the staff account after explicit confirmation.</p>
        </div>
      </div>
      <FieldGrid items={[
        { label: 'Username', value: staff.username || '—' },
        { label: 'Status', value: active ? 'Active' : 'Inactive' },
        { label: 'Force password change', value: staff.force_password_change ? 'Enabled' : 'Not indicated' },
        { label: 'Last updated', value: formatDateTime(staff.updated_at) },
      ]} />
      <div className="staff-detail-actions">
        <button type="button" className={`exec-button ${active ? 'exec-button-danger' : 'exec-button-primary'}`} onClick={() => void handleStatusToggle()} disabled={working.deactivate}>{working.deactivate ? 'Saving…' : active ? 'Deactivate account' : 'Restore account'}</button>
      </div>
      <LoginCredentialsPanel endpoint={`/api/manager/staff/${staffId}/credentials`} onUpdated={(login) => setState((current) => ({ ...current, staff: { ...current.staff, ...login } }))} />
    </section>
  );

  return (
    <div className="staff-detail-page">
      <div className="staff-inline-actions">
        <Link to="/manager/team/staff" className="manager-inline-action">← Back to Staff & Team</Link>
      </div>
      {state.loading ? <LoadingBlock label="Loading staff record" /> : null}
      {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Staff record unavailable.</strong><span>{state.error}</span></div> : null}
      {!state.loading && !state.error && staff ? (
        <>
          <section className="exec-profile-hero staff-detail-hero">
            <div className="exec-profile-hero-cover">
              <div className="exec-profile-hero-wash" />
              <div className="staff-profile-orbital"><OrbitalMotif dots={4} /></div>
              <span className="exec-profile-status"><span /> {active ? 'Staff account active' : 'Staff account inactive'}</span>
            </div>
            <div className="exec-profile-hero-body">
              <div className="exec-profile-avatar">
                {staff.photo_url ? <img src={resolveAssetUrl(staff.photo_url)} alt={`${displayName} profile`} /> : makeInitials(displayName)}
              </div>
              <div className="exec-profile-heading">
                <p className="exec-eyebrow">Staff detail record</p>
                <h1>{displayName}</h1>
                <div className="staff-hero-meta">
                  <RolePill role={staff.staff_role || staff.role || 'staff'} />
                  <StatusPill active={active} label={active ? 'Active' : 'Inactive'} />
                </div>
                <p>{staff.employee_code || staff.staff_id || 'Employee code pending'} · {staffRoleLabel(staff.staff_role || staff.role || 'staff')}</p>
                <p className="manager-profile-subline">{[staff.phone || staff.mobile, staff.email].filter(Boolean).join(' · ') || 'Contact details not available yet.'}</p>
              </div>
            </div>
          </section>

          <div className="exec-routed-tabs" role="tablist" aria-label="Staff detail sections">
            {TAB_DEFINITIONS.map((tab) => {
              const Icon = tab.icon;
              const selected = tab.id === activeTab;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  className={`exec-routed-tab${selected ? ' is-active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <span className="exec-routed-tab-icon" aria-hidden="true"><Icon size={16} /></span>
                  {tab.label}
                </button>
              );
            })}
          </div>

          {tabPanel}
        </>
      ) : null}
    </div>
  );
}
