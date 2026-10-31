export default function IconBadge({ children, tone = 'authority', size = 'medium', label = undefined }) {
  return <span className={`exec-icon-badge exec-icon-badge-${tone} exec-icon-badge-${size}`} aria-label={label} role={label ? 'img' : undefined}>{children}</span>;
}
