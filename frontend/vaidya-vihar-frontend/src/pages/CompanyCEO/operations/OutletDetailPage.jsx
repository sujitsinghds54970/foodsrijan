import { useCallback, useEffect, useState } from 'react';
import { Link, NavLink, Navigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { outletApi } from '../../../services/outletApi';
import CredentialsModal from './CredentialsModal';
import LoginCredentialsPanel from '../../../components/auth/LoginCredentialsPanel';
import '../../../styles/outlets.css';

const base = '/company-ceo/operations/outlets';
const tabs = ['overview', 'details', 'manager', 'operations', 'financials', 'legal', 'staff', 'inventory', 'orders', 'analytics', 'audit'];
const groups = {
  details: [['Name', 'name'], ['Code', 'code'], ['Slug', 'slug'], ['Type', 'outlet_type'], ['Status', 'status'], ['Brand ID', 'brand_id'], ['Opening date', 'opening_date'], ['Description', 'description'], ['Address', 'address_line_1'], ['Address line 2', 'address_line_2'], ['City', 'city'], ['State', 'state'], ['Country', 'country'], ['Postal code', 'pincode'], ['Region', 'region'], ['Timezone', 'timezone'], ['Latitude', 'latitude'], ['Longitude', 'longitude'], ['Outlet email', 'outlet_email'], ['Outlet phone', 'outlet_phone'], ['Google Maps', 'google_maps_url'], ['Swiggy store ID', 'swiggy_store_id'], ['Zomato store ID', 'zomato_store_id'], ['Logo URL', 'logo_url'], ['Cover photo URL', 'cover_photo_url']],
  operations: [['Opening time', 'opening_time'], ['Closing time', 'closing_time'], ['Operating days', 'operating_days'], ['Seating capacity', 'seating_capacity'], ['Kitchen capacity', 'kitchen_capacity'], ['Delivery enabled', 'is_delivery_enabled'], ['Dine-in enabled', 'is_dine_in_enabled'], ['Takeaway enabled', 'is_takeaway_enabled'], ['Delivery radius (km)', 'delivery_radius_km']],
  legal: [['FSSAI licence', 'fssai_license'], ['GSTIN', 'gstin'], ['Trade licence', 'trade_license'], ['Fire safety certificate', 'fire_safety_certificate'], ['Health permit', 'health_permit'], ['Licence expiry', 'license_expiry_date']],
  financials: [['Rent amount', 'rent_amount'], ['Security deposit', 'security_deposit'], ['Lease start', 'lease_start_date'], ['Lease end', 'lease_end_date'], ['Account name', 'bank_account_name'], ['Bank', 'bank_name'], ['Bank branch', 'branch_name'], ['Cost centre', 'cost_center_code']],
};
const label = (value) => value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const display = (value) => Array.isArray(value) ? value.join(', ') || 'Not provided' : value === null || value === undefined || value === '' ? 'Not provided' : typeof value === 'boolean' ? value ? 'Yes' : 'No' : String(value);
const emptyManager = {
  first_name: '', last_name: '', email: '', phone: '', username: '', password: '', password_confirm: '',
  manager_photo_url: '', manager_address: '', manager_bank_account_name: '', manager_bank_account_number: '',
  manager_ifsc_code: '', manager_bank_name: '',
};
const managerProfileFields = ['first_name', 'last_name', 'email', 'phone', 'manager_photo_url', 'manager_address', 'manager_bank_account_name', 'manager_bank_account_number', 'manager_ifsc_code', 'manager_bank_name'];

function ManagerPanel({ id, manager, refresh, onLoginUpdated }) {
  const [values, setValues] = useState(emptyManager);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [credentials, setCredentials] = useState(null);
  const [testPassword, setTestPassword] = useState('');
  const [testResult, setTestResult] = useState('');
  const update = (name, value) => setValues((current) => ({ ...current, [name]: value }));
  useEffect(() => {
    setValues(manager ? Object.fromEntries(Object.keys(emptyManager).map((key) => [key, manager[key] ?? (key === 'username' ? manager.username : '')])) : emptyManager);
    setEditing(false); setTestPassword(''); setTestResult('');
  }, [manager]);
  const run = async (callback, fallback, shouldRefresh = true) => {
    setBusy(true); setError('');
    try { await callback(); if (shouldRefresh) await refresh(); }
    catch (requestError) { setError(apiErrorMessage(requestError, fallback)); }
    finally { setBusy(false); }
  };
  const submit = (event) => {
    event.preventDefault();
    if (manager && !editing) return;
    void run(async () => {
      if (manager) {
        await outletApi.updateManager(id, Object.fromEntries(managerProfileFields
          .filter((name) => values[name] !== (manager[name] ?? ''))
          .map((name) => [name, values[name] || null])));
      } else {
        const payload = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''));
        const { data } = await outletApi.createManager(id, payload);
        if (data.credentials) setCredentials(data.credentials);
      }
      setEditing(false); toast.success(manager ? 'Manager updated' : 'Manager assigned');
    }, 'Unable to save the manager.');
  };
  const reset = () => {
    if (!window.confirm('Reset the manager password? The current password will stop working.')) return;
    void run(async () => {
    const { data } = await outletApi.resetManagerPassword(id);
    setCredentials(data.credentials); toast.success('Password reset');
    }, 'Unable to reset the manager password.');
  };
  const remove = () => {
    if (!window.confirm('Remove this manager from the outlet?')) return;
    void run(async () => { await outletApi.removeManager(id); toast.success('Manager removed'); }, 'Unable to remove the manager.');
  };
  return <section className="panel outlet-panel"><div className="panel-header"><div><p className="eyebrow">Outlet leadership</p><h3>Manager</h3></div>{manager && <span>{manager.is_active ? 'Active' : 'Inactive'}</span>}</div>
    {manager && !editing ? <><dl className="outlet-facts">{[['Name', `${manager.first_name} ${manager.last_name}`], ['Username', manager.username], ['Email', manager.email], ['Phone', manager.phone], ['Assigned', manager.manager_assigned_at]].map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{display(value)}</dd></div>)}</dl>
      <div className="outlet-card-actions"><button className="ghost-button compact" type="button" onClick={() => setEditing(true)}>Edit manager</button><button className="ghost-button compact" disabled={busy} type="button" onClick={reset}>Reset password</button><button className="ghost-button compact" disabled={busy} type="button" onClick={remove}>Remove manager</button></div>
      <form className="outlet-login-test" onSubmit={(event) => { event.preventDefault(); setTestResult(''); void run(async () => { const { data } = await outletApi.testManagerLogin(id, { username: manager.username, password: testPassword }); setTestResult(data.valid ? 'Credentials verified' : 'Credentials are invalid'); setTestPassword(''); }, 'Unable to verify login.', false); }}>
        <label>Test manager login<input type="password" autoComplete="off" required value={testPassword} onChange={(event) => setTestPassword(event.target.value)} placeholder="Enter password to verify" /></label><button className="ghost-button compact" disabled={busy} type="submit">Verify</button>{testResult && <span role="status">{testResult}</span>}
      </form><LoginCredentialsPanel endpoint={`/api/company-ceo/outlets/${id}/manager/credentials`} onUpdated={onLoginUpdated} /></> : <form className="outlet-manager-form" onSubmit={submit}><p>{manager ? 'Update manager contact details.' : 'Assign a manager and issue one-time login credentials.'}</p>
      <div className="outlet-form-grid">{[
        ['first_name', 'First name'], ['last_name', 'Last name'], ['email', 'Email'], ['phone', 'Phone'],
        ['manager_photo_url', 'Photo URL'], ['manager_address', 'Address'],
        ['manager_bank_account_name', 'Bank account name'], ['manager_bank_account_number', 'Bank account number'],
        ['manager_ifsc_code', 'IFSC'], ['manager_bank_name', 'Bank name'],
        ...(!manager ? [['username', 'Username (optional)'], ['password', 'Password (optional)'], ['password_confirm', 'Confirm password']] : []),
      ].map(([name, text]) => <label className="outlet-field" key={name}>{text}<input type={name.includes('password') ? 'password' : name === 'email' ? 'email' : 'text'} autoComplete="off" required={['first_name', 'last_name', 'email', 'phone'].includes(name) || (name === 'password_confirm' && Boolean(values.password))} value={values[name]} onChange={(event) => update(name, event.target.value)} /></label>)}</div>
      <div className="outlet-form-actions">{editing && <button className="ghost-button" type="button" onClick={() => setEditing(false)}>Cancel</button>}<button className="primary-button" disabled={busy} type="submit">{busy ? 'Saving…' : manager ? 'Save manager' : 'Assign manager'}</button></div>
    </form>}
    {error && <p role="alert" className="outlet-error">{error}</p>}
    {credentials && <CredentialsModal credentials={credentials} onClose={() => setCredentials(null)} />}
  </section>;
}

export default function OutletDetailPage() {
  const { outletId, outletTab = 'overview' } = useParams();
  const id = Number(outletId);
  const [record, setRecord] = useState(null);
  const [manager, setManager] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState(null);
  const [auditError, setAuditError] = useState('');
  const [managerError, setManagerError] = useState('');
  const [managerLoading, setManagerLoading] = useState(false);
  const managerId = record?.manager?.id;
  const refresh = useCallback(async () => {
    const { data } = await outletApi.get(id);
    setRecord(data.outlet);
    if (data.outlet.manager) {
      const managerResponse = await outletApi.manager(id);
      setManager(managerResponse.data.manager);
    } else setManager(null);
  }, [id]);
  useEffect(() => {
    if (outletTab !== 'manager' || !Number.isInteger(id) || id < 1 || !record) return undefined;
    let active = true;
    setManagerError(''); setManagerLoading(true);
    const request = managerId ? outletApi.manager(id).then(({ data }) => data.manager) : Promise.resolve(null);
    request.then((value) => { if (active) setManager(value); })
      .catch((requestError) => { if (active) setManagerError(apiErrorMessage(requestError, 'Unable to load manager details.')); })
      .finally(() => { if (active) setManagerLoading(false); });
    return () => { active = false; };
  }, [id, outletTab, record, managerId]);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setRecord(null);
    outletApi.get(id).then(({ data }) => { if (active) { setRecord(data.outlet); setManager(data.outlet.manager ?? null); } })
      .catch((requestError) => { if (active) setError(apiErrorMessage(requestError, 'Unable to load this outlet.')); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);
  useEffect(() => {
    if (outletTab !== 'audit' || !Number.isInteger(id)) return undefined;
    let active = true;
    setAuditError(''); setEvents(null);
    outletApi.audit(id, { page: 1, page_size: 50 })
      .then(({ data }) => { if (active) setEvents(data.events); })
      .catch((requestError) => { if (active) setAuditError(apiErrorMessage(requestError, 'Unable to load audit history.')); });
    return () => { active = false; };
  }, [id, outletTab]);
  if (!tabs.includes(outletTab)) return <Navigate to={`${base}/${outletId}/overview`} replace />;
  if (loading) return <main className="outlet-admin"><LoadingSkeleton /></main>;
  if (error || !record) return <section className="outlet-admin panel" role="alert"><p>{error || 'Outlet not found.'}</p><button type="button" className="ghost-button" onClick={() => { setLoading(true); refresh().catch((requestError) => setError(apiErrorMessage(requestError, 'Unable to load this outlet.'))).finally(() => setLoading(false)); }}>Retry</button></section>;
  return <section className="company-admin outlet-admin">
    <header className="exec-hero company-admin-hero"><div><p className="eyebrow">Operations · {record.code}</p><h2>{record.name}</h2><p className="page-subtitle">{[record.city, record.state].filter(Boolean).join(', ')} · {label(record.status)}</p></div><div className="outlet-card-actions"><Link className="ghost-button" to={base}>All outlets</Link><Link className="primary-button" to={`${base}/${id}/edit`}>Edit outlet</Link></div></header>
    <nav className="outlet-tabs" aria-label="Outlet details">{tabs.map((tab) => <NavLink key={tab} to={`${base}/${id}/${tab}`} aria-current={outletTab === tab ? 'page' : undefined}>{label(tab)}</NavLink>)}</nav>
    {outletTab === 'manager' ? managerLoading ? <LoadingSkeleton /> : managerError ? <section className="panel outlet-panel" role="alert"><p>{managerError}</p><button className="ghost-button" type="button" onClick={() => refresh().then(() => setManagerError('')).catch((requestError) => setManagerError(apiErrorMessage(requestError, 'Unable to load manager details.')))}>Retry</button></section> : <ManagerPanel id={id} manager={manager} refresh={refresh} onLoginUpdated={(login) => setManager((current) => ({ ...current, ...login }))} /> :
      outletTab === 'audit' ? <section className="panel outlet-panel"><h3>Audit history</h3>{auditError ? <p role="alert">{auditError}</p> : events === null ? <LoadingSkeleton /> : events.length ? <ul className="outlet-audit">{events.map((event) => <li key={event.id}><strong>{event.action}</strong><span>{event.created_at ? new Date(event.created_at).toLocaleString() : 'Date unavailable'}</span></li>)}</ul> : <EmptyState title="No recorded changes" description="Outlet changes will appear here." />}</section> :
        ['staff', 'inventory', 'orders', 'analytics'].includes(outletTab) ? <section className="panel outlet-panel"><EmptyState title={`${label(outletTab)} coming soon`} description={`${label(outletTab)} reporting will appear when outlet-scoped data is available.`} /></section> :
          <section className="panel outlet-panel"><div className="panel-header"><div><p className="eyebrow">Outlet record</p><h3>{label(outletTab)}</h3></div></div>
            <dl className="outlet-facts">{(outletTab === 'overview' ? [['Type', 'outlet_type'], ['Status', 'status'], ['Address', 'address_line_1'], ['City', 'city'], ['Opening time', 'opening_time'], ['Closing time', 'closing_time'], ['Manager', 'manager']] : groups[outletTab]).map(([name, key]) => <div key={name}><dt>{name}</dt><dd>{key === 'manager' ? manager ? `${manager.first_name} ${manager.last_name}` : <Link to={`${base}/${id}/manager`}>Assign manager</Link> : display(record[key])}</dd></div>)}</dl>
          </section>}
  </section>;
}
