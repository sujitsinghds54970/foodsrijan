import { Link } from 'react-router-dom';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import { IconBadge } from '../../../components/SuperCEO/icons';
import { resolveAssetUrl } from '../../../services/superCeoProfileApi';
import { staffRoleLabel, staffRoleTone } from '../../../services/staffApi';

export const asObject = (value) => (value && typeof value === 'object' && !Array.isArray(value) ? value : null);
export const asArray = (value) => (Array.isArray(value) ? value : []);

export const firstDefined = (sources, keys) => {
  for (const source of sources) {
    if (!source || typeof source !== 'object') continue;
    for (const key of keys) {
      if (source[key] != null) return source[key];
    }
  }
  return undefined;
};

export const readCollection = (payload, keys = ['items', 'staff', 'requests', 'activity', 'tasks', 'payslips', 'events']) => {
  const root = asObject(payload);
  const candidates = [root, asObject(root?.data), asObject(root?.summary), asObject(root?.dashboard), asObject(root?.results)].filter(Boolean);
  for (const candidate of candidates) {
    for (const key of keys) {
      if (Array.isArray(candidate[key])) return candidate[key];
    }
  }
  return [];
};

export const readRecord = (payload, keys = ['staff', 'member', 'employee', 'profile', 'me', 'outlet', 'request']) => {
  const root = asObject(payload);
  const candidates = [root, asObject(root?.data), asObject(root?.summary)].filter(Boolean);
  for (const candidate of candidates) {
    for (const key of keys) {
      const value = asObject(candidate[key]);
      if (value) return value;
    }
  }
  return root || {};
};

export const readValue = (payload, keys, fallback = null) => {
  const root = asObject(payload);
  const candidates = [root, asObject(root?.data), asObject(root?.summary), asObject(root?.dashboard), asObject(root?.metrics), asObject(root?.kpis)].filter(Boolean);
  const value = firstDefined(candidates, keys);
  return value == null ? fallback : value;
};

export const readNumber = (payload, keys, fallback = null) => {
  const value = readValue(payload, keys, fallback);
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};

export const readText = (payload, keys, fallback = '—') => {
  const value = readValue(payload, keys, fallback);
  if (value == null) return fallback;
  const text = String(value).trim();
  return text || fallback;
};

export const formatDate = (value) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString();
};

export const formatDateTime = (value) => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
};

export const formatCurrency = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(numeric)
    : '—';
};

export const formatCount = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(numeric)
    : '—';
};

export const formatPercent = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return `${Math.round(numeric <= 1 ? numeric * 100 : numeric)}%`;
};

export const makeInitials = (name = 'Staff') => name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'ST';

export const toneClass = (tone) => `tone-${tone || 'teal'}`;

export function Avatar({ name, photoUrl, className = 'manager-avatar' }) {
  return (
    <div className={className}>
      {photoUrl ? <img src={resolveAssetUrl(photoUrl)} alt={`${name} profile`} /> : makeInitials(name)}
    </div>
  );
}

export function RolePill({ role, icon: Icon = null }) {
  const tone = staffRoleTone(role);
  return (
    <span className={`staff-pill ${toneClass(tone)}`}>
      {Icon ? <IconBadge tone={tone}><Icon size={14} /></IconBadge> : null}
      {staffRoleLabel(role)}
    </span>
  );
}

export function StatusPill({ active, label }) {
  return <span className={`staff-pill ${active ? 'is-success' : 'is-muted'}`}>{label || (active ? 'Active' : 'Inactive')}</span>;
}

export function FieldGrid({ items }) {
  return (
    <dl className="manager-stat-list staff-field-grid">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

export function SectionEmpty({ title, description }) {
  return <EmptyState title={title} description={description} />;
}

export function LoadingBlock({ label = 'Loading…' }) {
  return <div className="manager-inline-state" role="status"><strong>{label}</strong><span>Please wait while the latest staff signals load.</span></div>;
}

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <header className="manager-page-header staff-page-header">
      <p>{eyebrow}</p>
      <div className="staff-page-header-row">
        <div>
          <h1>{title}</h1>
          <span>{description}</span>
        </div>
        {action}
      </div>
    </header>
  );
}

export function QuickAction({ to, children }) {
  return <Link className="staff-quick-action" to={to}>{children}</Link>;
}
