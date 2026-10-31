import { useMemo } from 'react';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import ScopeBadge from '../../../components/SuperCEO/common/ScopeBadge';
import SectionState from '../../../components/SuperCEO/common/SectionState';
import { executiveMetricsApi } from '../../../services/executiveMetricsApi';
import { useExecutiveMetricSections } from '../useExecutiveMetricSections';

export default function PerformancePage() {
  const requests = useMemo(() => ({
    summary: () => executiveMetricsApi.getPerformanceSummary(),
    bundle: () => executiveMetricsApi.getDerivedBundle(),
  }), []);
  const { sections, refresh } = useExecutiveMetricSections(requests);
  const summary = sections.summary?.data;
  const bundle = sections.bundle?.data;
  const performanceRows = [
    ['Revenue', summary?.metrics?.revenue == null ? '—' : `₹${summary.metrics.revenue.toLocaleString()}`],
    ['Portfolio health', summary?.metrics?.portfolio_health == null ? '—' : `${summary.metrics.portfolio_health}/100`],
    ['Active customers', summary?.metrics?.active_customers ?? '—'],
    ['Critical alerts', summary?.metrics?.critical_alerts ?? '—'],
    ['Cash conversion', summary?.metrics?.cash_conversion == null ? '—' : `${summary.metrics.cash_conversion}%`],
  ];

  return <section>
    <header className="exec-hero"><div><p className="eyebrow">Command</p><h2>Performance</h2><p className="page-subtitle">Cross-company operational, customer, collection, and alert signals.</p></div><div className="page-actions"><ScopeBadge scope={sections.summary?.meta?.scope} /><button className="ghost-button compact" onClick={refresh}>Refresh</button></div></header>
    <SectionState section={sections.summary} unavailableTitle="Performance summary unavailable">
      <div className="metric-grid four-up"><KpiCard label="Cash conversion" value={summary?.metrics?.cash_conversion == null ? '—' : `${summary.metrics.cash_conversion}%`} tone="gold" /><KpiCard label="Portfolio health" value={summary?.metrics?.portfolio_health == null ? '—' : `${summary.metrics.portfolio_health}/100`} tone="emerald" /><KpiCard label="Active customers" value={summary?.metrics?.active_customers ?? '—'} tone="blue" /><KpiCard label="Critical alerts" value={summary?.metrics?.critical_alerts ?? '—'} tone="rose" /></div>
      <article className="panel performance-summary"><div className="panel-header"><h3>{summary?.period || 'Current period'} assessment</h3><span className={`status-chip ${summary?.status === 'healthy' ? 'strong' : 'watchlist'}`}>{summary?.status || 'unknown'}</span></div><p className="page-subtitle">{summary?.summary}</p></article>
      <article className="panel"><div className="panel-header"><h3>Cross-company performance</h3></div><div className="table-shell"><div className="table-header performance-table-row"><span>Metric</span><span>Current value</span></div>{performanceRows.map(([label, value]) => <div className="table-row performance-table-row" key={label}><strong>{label}</strong><span>{value}</span></div>)}</div></article>
    </SectionState>
    <article className="panel"><div className="panel-header"><h3>Performance data quality</h3></div><SectionState section={sections.bundle}><div className="metric-grid three-up"><KpiCard label="Revenue source" value={bundle?.group_revenue?.source || '—'} /><KpiCard label="Customer source status" value={bundle?.customer_metrics?.source_status || '—'} tone="blue" /><KpiCard label="Reconciliation" value={bundle?.cash_conversion?.reconciled ? 'Reconciled' : 'Derived'} tone="emerald" /></div></SectionState></article>
  </section>;
}
