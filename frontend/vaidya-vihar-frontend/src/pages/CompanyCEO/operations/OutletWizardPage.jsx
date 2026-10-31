import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { outletApi } from '../../../services/outletApi';
import CredentialsModal from './CredentialsModal';
import '../../../styles/outlets.css';

const base = '/company-ceo/operations/outlets';
const types = ['dine_in', 'takeaway', 'cloud_kitchen', 'kiosk', 'food_truck', 'cafe', 'bakery', 'bar', 'fine_dine', 'qsr', 'buffet', 'drive_through', 'other'];
const statuses = ['planning', 'setup', 'active', 'temporarily_closed', 'permanently_closed'];
const regions = ['north_india', 'south_india', 'east_india', 'west_india', 'international'];
const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const labelFor = (value) => value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const field = (name, label, options = {}) => ({ name, label, ...options });
const steps = [
  { title: 'Identity', hint: 'Name and operating model', fields: [
    field('name', 'Outlet name', { required: true, maxLength: 100 }), field('code', 'Outlet code', { required: true, maxLength: 12, pattern: '[A-Za-z0-9\\-]{2,12}', hint: '2–12 letters, digits or hyphens' }),
    field('outlet_type', 'Outlet type', { required: true, options: types }), field('status', 'Status', { options: statuses }),
    field('brand_id', 'Brand ID', { type: 'number', min: 1 }), field('opening_date', 'Opening date', { type: 'date' }), field('description', 'Description', { type: 'textarea', wide: true }),
  ] },
  { title: 'Location', hint: 'Address and region', fields: [
    field('address_line_1', 'Address line 1', { required: true }), field('address_line_2', 'Address line 2'),
    field('city', 'City', { required: true }), field('state', 'State', { required: true }), field('country', 'Country code', { maxLength: 2, hint: 'Two-letter ISO code, e.g. IN' }),
    field('pincode', 'Postal code', { required: true, minLength: 3, maxLength: 10 }), field('region', 'Region', { options: regions }), field('timezone', 'Timezone', { hint: 'IANA timezone, e.g. Asia/Kolkata' }),
    field('latitude', 'Latitude', { type: 'number', step: 'any', min: -90, max: 90 }), field('longitude', 'Longitude', { type: 'number', step: 'any', min: -180, max: 180 }),
    field('google_maps_url', 'Google Maps URL', { type: 'url' }),
  ] },
  { title: 'Operations', hint: 'Hours and capacity', fields: [
    field('opening_time', 'Opening time', { type: 'time' }), field('closing_time', 'Closing time', { type: 'time' }),
    field('seating_capacity', 'Seating capacity', { type: 'number', min: 0 }), field('kitchen_capacity', 'Kitchen capacity', { type: 'number', min: 0 }),
    field('delivery_radius_km', 'Delivery radius (km)', { type: 'number', min: 0, max: 100, step: 'any' }),
    field('operating_days', 'Operating days', { type: 'days', wide: true }),
    field('is_delivery_enabled', 'Delivery enabled', { type: 'checkbox' }), field('is_dine_in_enabled', 'Dine-in enabled', { type: 'checkbox' }), field('is_takeaway_enabled', 'Takeaway enabled', { type: 'checkbox' }),
    field('outlet_email', 'Outlet email', { type: 'email' }), field('outlet_phone', 'Outlet phone', { type: 'tel' }),
    field('manager_contact_email', 'Manager contact email', { type: 'email' }), field('manager_contact_phone', 'Manager contact phone', { type: 'tel' }),
    field('swiggy_store_id', 'Swiggy store ID'), field('zomato_store_id', 'Zomato store ID'),
    field('logo_url', 'Logo URL', { hint: 'HTTPS URL or uploaded media path' }), field('cover_photo_url', 'Cover photo URL', { hint: 'HTTPS URL or uploaded media path' }),
  ] },
  { title: 'Compliance', hint: 'Licences and permits', fields: [
    field('fssai_license', 'FSSAI licence'), field('gstin', 'GSTIN'), field('trade_license', 'Trade licence'),
    field('fire_safety_certificate', 'Fire safety certificate'), field('health_permit', 'Health permit'),
    field('license_expiry_date', 'Licence expiry', { type: 'date' }),
  ] },
  { title: 'Finance & lease', hint: 'Costs and banking', fields: [
    field('rent_amount', 'Rent amount', { type: 'number', min: 0, step: 'any' }), field('security_deposit', 'Security deposit', { type: 'number', min: 0, step: 'any' }),
    field('lease_start_date', 'Lease start', { type: 'date' }), field('lease_end_date', 'Lease end', { type: 'date' }),
    field('bank_account_name', 'Account name'), field('bank_account_number', 'Account number', { pattern: '[0-9]{9,18}' }),
    field('ifsc_code', 'IFSC'), field('bank_name', 'Bank name'), field('branch_name', 'Branch name'), field('upi_id', 'UPI ID'), field('cost_center_code', 'Cost centre code'),
  ] },
  { title: 'Assign Manager', hint: 'Optional outlet leadership', fields: [] },
  { title: 'Review', hint: 'Confirm and save', fields: [] },
];
const editableFields = steps.flatMap((step) => step.fields);
const numericFields = new Set(editableFields.filter((item) => item.type === 'number').map((item) => item.name));
const booleanFields = new Set(editableFields.filter((item) => item.type === 'checkbox').map((item) => item.name));
const initial = Object.fromEntries(editableFields.map((item) => [item.name, item.type === 'days' ? [] : item.type === 'checkbox' ? false : item.name === 'country' ? 'IN' : '']));
const managerFields = [
  field('first_name', 'First name'), field('last_name', 'Last name'),
  field('email', 'Email', { type: 'email' }), field('phone', 'Phone', { type: 'tel' }),
  field('manager_photo_url', 'Photo URL'), field('username', 'Username (optional)'),
  field('password', 'Password (optional)', { type: 'password' }), field('password_confirm', 'Confirm password', { type: 'password' }),
  field('manager_address', 'Address', { type: 'textarea', wide: true }),
  field('manager_bank_account_name', 'Bank account name'), field('manager_bank_account_number', 'Bank account number', { pattern: '[0-9]{9,18}' }),
  field('manager_ifsc_code', 'IFSC'), field('manager_bank_name', 'Bank name'),
];
const emptyManager = Object.fromEntries(managerFields.map(({ name }) => [name, '']));

export default function OutletWizardPage() {
  const navigate = useNavigate();
  const { outletId } = useParams();
  const id = Number(outletId);
  const editing = Number.isInteger(id) && id > 0;
  const [values, setValues] = useState(initial);
  const [original, setOriginal] = useState(initial);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [assignManager, setAssignManager] = useState(false);
  const [existingManager, setExistingManager] = useState(null);
  const [managerValues, setManagerValues] = useState(emptyManager);
  const [createdId, setCreatedId] = useState(null);
  const [credentials, setCredentials] = useState(null);

  useEffect(() => {
    if (!editing) return undefined;
    let active = true;
    outletApi.get(id).then(({ data }) => {
      if (!active) return;
      const next = Object.fromEntries(editableFields.map((item) => [item.name, data.outlet[item.name] ?? initial[item.name]]));
      setValues(next);
      setOriginal(next);
      setExistingManager(data.outlet.manager ?? null);
    }).catch((requestError) => { if (active) setError(apiErrorMessage(requestError, 'Unable to load outlet for editing.')); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, editing]);

  const change = (name, value) => { setValues((current) => ({ ...current, [name]: value })); setError(''); };
  const changeManager = (name, value) => { setManagerValues((current) => ({ ...current, [name]: value })); setError(''); };
  const submit = async (event) => {
    event.preventDefault();
    if (step < steps.length - 1) { setStep(step + 1); return; }
    if (values.lease_start_date && values.lease_end_date && values.lease_end_date < values.lease_start_date) {
      setError('Lease end must be on or after lease start.'); setStep(4); return;
    }
    const requiredMissing = editableFields.find((item) => item.required && !String(values[item.name]).trim());
    if (requiredMissing) { setError(`${requiredMissing.label} is required.`); setStep(steps.findIndex((item) => item.fields.includes(requiredMissing))); return; }
    if (assignManager && !existingManager && ['first_name', 'last_name', 'email', 'phone'].some((name) => !managerValues[name].trim())) {
      setError('Manager first name, last name, email and phone are required.'); setStep(5); return;
    }
    if (assignManager && !existingManager && managerValues.password !== managerValues.password_confirm) {
      setError('Manager passwords do not match.'); setStep(5); return;
    }
    const payload = {};
    editableFields.forEach(({ name }) => {
      if ((editing || createdId) && JSON.stringify(values[name]) === JSON.stringify(original[name])) return;
      const value = values[name];
      payload[name] = booleanFields.has(name) || name === 'operating_days' ? value
        : value === '' ? (editing ? null : undefined)
          : numericFields.has(name) ? Number(value) : typeof value === 'string' ? value.trim() : value;
    });
    setSaving(true); setError('');
    try {
      const outletId = editing || createdId
        ? (Object.keys(payload).length ? (await outletApi.update(createdId || id, payload)).data.outlet.id : createdId || id)
        : (await outletApi.create(payload)).data.outlet.id;
      setCreatedId(outletId);
      setOriginal(values);
      if (assignManager && !existingManager) {
        const managerPayload = Object.fromEntries(Object.entries(managerValues).filter(([, value]) => value.trim() !== ''));
        const response = await outletApi.createManager(outletId, managerPayload);
        if (!response.data.credentials) throw new Error('Manager created but credentials were not returned. Contact support before closing this page.');
        setCredentials(response.data.credentials);
      } else {
        toast.success(editing ? 'Outlet updated' : 'Outlet created');
        navigate(`${base}/${outletId}/overview`, { replace: true });
      }
    } catch (requestError) {
      const message = apiErrorMessage(requestError, requestError instanceof Error ? requestError.message : 'Unable to save outlet.');
      setError(message); toast.error(message);
    } finally { setSaving(false); }
  };
  const renderManagerField = (item) => <label className={`outlet-field ${item.wide ? 'outlet-wide' : ''}`} key={item.name}><span>{item.label}{['first_name', 'last_name', 'email', 'phone'].includes(item.name) && ' *'}</span>
    {item.type === 'textarea' ? <textarea value={managerValues[item.name]} onChange={(event) => changeManager(item.name, event.target.value)} rows={3} /> :
      <input type={item.type || 'text'} value={managerValues[item.name]} required={['first_name', 'last_name', 'email', 'phone'].includes(item.name) || (item.name === 'password_confirm' && Boolean(managerValues.password))} pattern={item.pattern} autoComplete="off" onChange={(event) => changeManager(item.name, event.target.value)} />}
  </label>;

  const renderField = (item) => {
    const value = values[item.name];
    if (item.type === 'checkbox') return <label className="outlet-checkbox" key={item.name}><input type="checkbox" checked={Boolean(value)} onChange={(event) => change(item.name, event.target.checked)} />{item.label}</label>;
    if (item.type === 'days') return <fieldset className="outlet-days" key={item.name}><legend>{item.label}</legend>{days.map((day) => <label key={day}><input type="checkbox" checked={value.includes(day)} onChange={(event) => change(item.name, event.target.checked ? [...value, day] : value.filter((current) => current !== day))} />{day}</label>)}</fieldset>;
    return <label className={`outlet-field ${item.wide ? 'outlet-wide' : ''}`} key={item.name}><span>{item.label}{item.required && ' *'}</span>
      {item.options ? <select required={item.required} value={value} onChange={(event) => change(item.name, event.target.value)}><option value="">Select {item.label.toLowerCase()}</option>{item.options.map((option) => <option key={option} value={option}>{labelFor(option)}</option>)}</select>
        : item.type === 'textarea' ? <textarea value={value} onChange={(event) => change(item.name, event.target.value)} rows={3} />
          : <input type={item.type || 'text'} value={value} required={item.required} minLength={item.minLength} maxLength={item.maxLength} pattern={item.pattern} min={item.min} max={item.max} step={item.step} onChange={(event) => change(item.name, event.target.value)} />}
      {item.hint && <small>{item.hint}</small>}</label>;
  };

  return <section className="company-admin outlet-admin">
    <header className="exec-hero company-admin-hero"><div><p className="eyebrow">Operations · Outlet setup</p><h2>{editing ? 'Edit outlet' : 'Create outlet'}</h2><p className="page-subtitle">Complete the seven-step operating profile and optionally assign a manager.</p></div><Link className="ghost-button" to={base}>Back to outlets</Link></header>
    {createdId && error && <p className="outlet-error" role="status">Outlet #{createdId} was saved. Manager assignment can be retried here or from <Link to={`${base}/${createdId}/manager`}>its manager tab</Link>.</p>}
    <div className="outlet-wizard-layout"><nav className="panel outlet-steps" aria-label="Outlet setup progress">{steps.map((item, index) => <div key={item.title} className={step === index ? 'current' : ''} aria-current={step === index ? 'step' : undefined}><span>{index < step ? '✓' : String(index + 1).padStart(2, '0')}</span><div><strong>{item.title}</strong><small>{item.hint}</small></div></div>)}</nav>
      <form className="panel outlet-form" onSubmit={submit} aria-busy={saving || loading}><div className="panel-header"><div><p className="eyebrow">Step {step + 1} of {steps.length}</p><h3>{steps[step].title}</h3></div><span>{Math.round(((step + 1) / steps.length) * 100)}%</span></div>
        {loading ? <LoadingSkeleton /> : <>{step === 6 ? <div className="outlet-review">{steps.slice(0, -1).map((section) => <section key={section.title}><h4>{section.title}</h4>{section.title === 'Assign Manager' ? <p>{existingManager ? `Existing: ${existingManager.first_name} ${existingManager.last_name}` : assignManager ? `${managerValues.first_name} ${managerValues.last_name} — credentials issued after save` : 'No manager assigned'}</p> : <dl>{section.fields.filter((item) => item.type !== 'checkbox' && item.name !== 'bank_account_number').map((item) => <div key={item.name}><dt>{item.label}</dt><dd>{Array.isArray(values[item.name]) ? values[item.name].join(', ') || '—' : values[item.name] || '—'}</dd></div>)}</dl>}</section>)}</div> : step === 5 ? <div>{existingManager ? <p>Manager {existingManager.first_name} {existingManager.last_name} is already assigned. Manage this account from the outlet manager tab after saving.</p> : <><label className="outlet-checkbox"><input type="checkbox" checked={assignManager} onChange={(event) => setAssignManager(event.target.checked)} />Assign a manager now</label>{assignManager && <div className="outlet-form-grid outlet-manager-fields">{managerFields.map(renderManagerField)}</div>}</>}</div> : <div className="outlet-form-grid">{steps[step].fields.map(renderField)}</div>}
          {error && <p role="alert" className="outlet-error">{error}</p>}
          <div className="outlet-form-actions"><button type="button" className="ghost-button" disabled={step === 0 || saving} onClick={() => { setStep(step - 1); setError(''); }}>Previous</button><span>Required fields marked *</span><button className="primary-button" type="submit" disabled={saving}>{saving ? 'Saving…' : step === 6 ? editing ? 'Save changes' : 'Create outlet' : 'Continue →'}</button></div></>}
      </form></div>{credentials && <CredentialsModal credentials={credentials} onClose={() => { setCredentials(null); navigate(`${base}/${createdId}/manager`, { replace: true }); }} />}
  </section>;
}
