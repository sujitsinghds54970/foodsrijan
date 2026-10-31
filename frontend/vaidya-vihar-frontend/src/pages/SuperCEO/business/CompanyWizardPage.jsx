import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { apiErrorMessage, companyManagementApi } from '../../../services/companyManagementApi';
import '../../../styles/company-management.css';

const STEPS = [
  { label: 'Company identity', hint: 'Name and operating model' },
  { label: 'Legal & compliance', hint: 'Registration identifiers' },
  { label: 'Location & contact', hint: 'Headquarters and support' },
];

const INITIAL_VALUES = {
  name: '',
  tagline: '',
  description: '',
  business_domain: '',
  funding_stage: '',
  founded_date: '',
  legal_name: '',
  registration_number: '',
  gstin: '',
  pan_number: '',
  fssai_license: '',
  headquarters_city: '',
  headquarters_state: '',
  headquarters_country: 'India',
  headquarters_pincode: '',
  number_of_branches: '',
  operating_regions: '',
  website_url: '',
  support_email: '',
  support_phone: '',
};

function Field({ label, name, value, onChange, required = false, type = 'text', hint, maxLength }) {
  return (
    <label className="company-form-field">
      <span>{label}{required && <b aria-hidden="true"> *</b>}</span>
      {type === 'textarea' ? (
        <textarea name={name} value={value} onChange={onChange} required={required} maxLength={maxLength} rows={3} />
      ) : (
        <input name={name} type={type} value={value} onChange={onChange} required={required} maxLength={maxLength} min={type === 'number' ? 0 : undefined} />
      )}
      {hint && <small>{hint}</small>}
    </label>
  );
}

function SelectField({ label, name, value, onChange, options }) {
  return (
    <label className="company-form-field">
      <span>{label}</span>
      <select name={name} value={value} onChange={onChange}>
        <option value="">Select {label.toLowerCase()}</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

export default function CompanyWizardPage() {
  const navigate = useNavigate();
  const { companyId } = useParams();
  const editId = Number(companyId);
  const isEditing = Number.isInteger(editId) && editId > 0;
  const [step, setStep] = useState(0);
  const [values, setValues] = useState(INITIAL_VALUES);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(isEditing);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isEditing) return undefined;
    let active = true;
    companyManagementApi.get(editId)
      .then((response) => {
        if (!active) return;
        const company = response.data.company;
        setValues(Object.fromEntries(Object.keys(INITIAL_VALUES).map((key) => [
          key,
          Array.isArray(company[key])
            ? company[key].join(', ')
            : company[key] == null ? '' : String(company[key]),
        ])));
      })
      .catch((requestError) => {
        if (active) setError(apiErrorMessage(requestError, 'Unable to load this company for editing.'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [editId, isEditing]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value }));
    setError('');
  };

  const handleNext = (event) => {
    if (!event.currentTarget.form.reportValidity()) return;
    setStep((current) => Math.min(STEPS.length - 1, current + 1));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (step < STEPS.length - 1) {
      setStep((current) => current + 1);
      return;
    }

    const payload = Object.fromEntries(
      Object.entries(values)
        .map(([key, value]) => {
          const trimmed = value.trim();
          if (!trimmed) return [key, undefined];
          if (key === 'number_of_branches') return [key, Number(trimmed)];
          if (key === 'operating_regions') return [key, trimmed.split(',').map((region) => region.trim()).filter(Boolean)];
          return [key, trimmed];
        })
        .filter(([key, value]) => key === 'name' || value !== undefined),
    );
    setSaving(true);
    setError('');
    try {
      const response = isEditing
        ? await companyManagementApi.update(editId, payload)
        : await companyManagementApi.create(payload);
      const company = response.data.company;
      toast.success(isEditing ? `${company.name} updated` : `${company.name} added to the portfolio`);
      navigate(`/super-ceo/business/companies/${company.id}/details`, { replace: true });
    } catch (requestError) {
      const message = apiErrorMessage(requestError, isEditing ? 'Unable to update this company.' : 'Unable to create this company.');
      setError(message);
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="company-admin">
      <header className="exec-hero company-admin-hero">
        <div>
          <p className="eyebrow">Business · Company register</p>
          <h2>{isEditing ? 'Edit company' : 'Add a company'}</h2>
          <p className="page-subtitle">{isEditing ? 'Review and update the company record through the guided workflow.' : 'Set up a company record. You can assign its CEO and complete the rest of its profile after creation.'}</p>
        </div>
        <Link className="ghost-button" to="/super-ceo/business/companies">Back to companies</Link>
      </header>

      <div className="company-wizard-layout">
        <aside className="company-wizard-steps" aria-label="Company setup progress">
          <p className="eyebrow">Setup sequence</p>
          {STEPS.map((item, index) => (
            <div className={`company-wizard-step ${step === index ? 'current' : ''} ${step > index ? 'complete' : ''}`} key={item.label} aria-current={step === index ? 'step' : undefined}>
              <span>{step > index ? '✓' : `0${index + 1}`}</span>
              <div><strong>{item.label}</strong><small>{item.hint}</small></div>
            </div>
          ))}
          <div className="company-wizard-note"><strong>Good to know</strong><p>Unique legal identifiers are checked when you save. Existing companies are not changed by this setup.</p></div>
        </aside>

        <form className="panel company-wizard-form" onSubmit={handleSubmit} aria-busy={loading}>
          <div className="panel-header company-wizard-header">
            <div><p className="eyebrow">Step {step + 1} of {STEPS.length}</p><h3>{STEPS[step].label}</h3></div>
            <span className="company-step-progress">{Math.round(((step + 1) / STEPS.length) * 100)}%</span>
          </div>

          {loading ? <p className="company-inline-note" role="status">Loading company details…</p> : step === 0 && (
            <div className="company-form-grid">
              <Field label="Company name" name="name" value={values.name} onChange={handleChange} required maxLength={150} hint="The name shown across the executive portfolio." />
              <Field label="Tagline" name="tagline" value={values.tagline} onChange={handleChange} maxLength={255} />
              <SelectField label="Business domain" name="business_domain" value={values.business_domain} onChange={handleChange} options={['Restaurant', 'Cafe', 'Cloud Kitchen', 'Bakery', 'QSR', 'Fine Dine', 'Catering', 'Food Manufacturing', 'Food Delivery', 'Other']} />
              <SelectField label="Funding stage" name="funding_stage" value={values.funding_stage} onChange={handleChange} options={['Bootstrapped', 'Seed', 'Series A', 'Series B', 'Series C', 'IPO', 'Other']} />
              <Field label="Founded date" name="founded_date" type="date" value={values.founded_date} onChange={handleChange} />
              <div className="company-form-field full-span"><Field label="Company description" name="description" type="textarea" value={values.description} onChange={handleChange} /></div>
            </div>
          )}

          {step === 1 && (
            <div className="company-form-grid">
              <Field label="Legal entity name" name="legal_name" value={values.legal_name} onChange={handleChange} maxLength={255} />
              <Field label="Registration number" name="registration_number" value={values.registration_number} onChange={handleChange} maxLength={100} />
              <Field label="GSTIN" name="gstin" value={values.gstin} onChange={handleChange} maxLength={15} hint="Indian Goods and Services Tax Identification Number." />
              <Field label="PAN" name="pan_number" value={values.pan_number} onChange={handleChange} maxLength={10} />
              <Field label="FSSAI license" name="fssai_license" value={values.fssai_license} onChange={handleChange} maxLength={14} />
            </div>
          )}

          {step === 2 && (
            <div className="company-form-grid">
              <Field label="Headquarters city" name="headquarters_city" value={values.headquarters_city} onChange={handleChange} maxLength={120} />
              <Field label="State / region" name="headquarters_state" value={values.headquarters_state} onChange={handleChange} maxLength={120} />
              <Field label="Country" name="headquarters_country" value={values.headquarters_country} onChange={handleChange} maxLength={120} />
              <Field label="Postal code" name="headquarters_pincode" value={values.headquarters_pincode} onChange={handleChange} maxLength={20} />
              <Field label="Number of branches" name="number_of_branches" type="number" value={values.number_of_branches} onChange={handleChange} hint="Use 0 if the company has not opened a branch yet." />
              <Field label="Operating regions" name="operating_regions" value={values.operating_regions} onChange={handleChange} hint="Separate regions with commas." />
              <Field label="Website" name="website_url" type="url" value={values.website_url} onChange={handleChange} maxLength={2048} />
              <Field label="Support email" name="support_email" type="email" value={values.support_email} onChange={handleChange} />
              <Field label="Support phone" name="support_phone" type="tel" value={values.support_phone} onChange={handleChange} />
            </div>
          )}

          {error && <div className="company-inline-error company-form-error" role="alert">{error}</div>}

          <footer className="company-wizard-footer">
            <button type="button" className="ghost-button" onClick={() => setStep((current) => Math.max(0, current - 1))} disabled={step === 0 || saving || loading}>Previous</button>
            <span>Required fields are marked with an asterisk.</span>
            {step < STEPS.length - 1 ? (
              <button type="button" className="primary-button" onClick={handleNext} disabled={loading}>Continue <span aria-hidden="true">→</span></button>
            ) : (
              <button type="submit" className="primary-button" disabled={saving || loading}>{saving ? 'Saving…' : isEditing ? 'Save company' : 'Create company'}</button>
            )}
          </footer>
        </form>
      </div>
    </section>
  );
}
