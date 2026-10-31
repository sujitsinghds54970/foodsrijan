export default function ScopeBadge({ label, scope }) {
  const scopeLabel = label || (
    scope?.level === 'company' && scope.company_id ? `Company ${scope.company_id}` :
      scope?.level ? `${scope.level} scope` : 'Group scope'
  );
  return <span className="scope-badge">{scopeLabel}</span>;
}
