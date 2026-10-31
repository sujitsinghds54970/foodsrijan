const statusClass = (status) => ({ strong: 'strong', healthy: 'strong', watch: 'watchlist', at_risk: 'watchlist', critical: 'watchlist' }[status] || 'stable');

export default function CompanyHealthCard({ company }) {
  const details = company.metrics || {};
  return <article className="panel company-health-card"><div className="panel-header"><h3>{company.company?.name || company.name}</h3><span className={`status-chip ${statusClass(company.health_status || company.health)}`}>{(company.health_status || company.health || 'unknown').replace('_', ' ')}</span></div><div className="mini-meta">Portfolio health</div><strong>{company.health_score == null ? '—' : `${company.health_score}/100`}</strong>{Object.keys(details).length > 0 && <div className="company-health-metrics">{Object.entries(details).map(([name, metric]) => <span key={name}>{name.replace('_', ' ')}: {metric.score == null ? '—' : `${Math.round(metric.score)}%`}</span>)}</div>}</article>;
}
