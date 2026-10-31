import { Link } from 'react-router-dom';
import { useMemo } from 'react';
import ScopeBadge from '../../../components/SuperCEO/common/ScopeBadge';
import SectionState from '../../../components/SuperCEO/common/SectionState';
import { executiveMetricsApi } from '../../../services/executiveMetricsApi';
import { useExecutiveMetricSections } from '../useExecutiveMetricSections';

export default function StrategyPage() {
  const requests = useMemo(() => ({ okrs: () => executiveMetricsApi.getStrategyOkrs() }), []);
  const { sections, refresh } = useExecutiveMetricSections(requests);
  const okrs = sections.okrs?.data;

  return <section>
    <header className="exec-hero"><div><p className="eyebrow">Command</p><h2>Strategy &amp; OKRs</h2><p className="page-subtitle">Approved objectives and key results for the current executive scope.</p></div><div className="page-actions"><ScopeBadge scope={sections.okrs?.meta?.scope} /><button className="ghost-button compact" onClick={refresh}>Refresh</button></div></header>
    <article className="panel"><SectionState section={sections.okrs} unavailableTitle="OKR tracking is not configured" unavailableDescription={okrs?.unavailable_reason || 'Configure the approved OKR model before progress can be shown.'} unavailableChildren={<Link className="primary-button section-cta" to="/super-ceo/system/okr-setup">{okrs?.next_action?.label || 'Configure OKRs'}</Link>}><div className="objective-list">{(okrs?.okrs || []).map((okr) => <div className="objective-item" key={okr.id}><div className="objective-topline"><strong>{okr.title}</strong><span>{okr.progress}%</span></div><div className="objective-bottomline"><span>{okr.owner}</span><span>{okr.status.replace('_', ' ')}</span></div><div className="progress-bar"><span style={{ width: `${okr.progress}%` }} /></div></div>)}</div></SectionState></article>
  </section>;
}
