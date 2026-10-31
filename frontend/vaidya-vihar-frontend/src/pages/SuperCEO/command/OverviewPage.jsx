import { useMemo, useState } from 'react';
import ActivityFeed from '../../../components/SuperCEO/common/ActivityFeed';
import CompanyHealthCard from '../../../components/SuperCEO/common/CompanyHealthCard';
import DecisionQueue from '../../../components/SuperCEO/common/DecisionQueue';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import ScopeBadge from '../../../components/SuperCEO/common/ScopeBadge';
import SectionState from '../../../components/SuperCEO/common/SectionState';
import Sparkline from '../../../components/SuperCEO/common/Sparkline';
import OrbitalMotif from '../../../components/SuperCEO/common/OrbitalMotif';
import { CompassIcon, LedgerIcon, PortfolioIcon, PulseIcon, ShieldIcon, CrownIcon } from '../../../components/SuperCEO/icons';
import { executiveMetricsApi } from '../../../services/executiveMetricsApi';
import { useExecutiveMetricSections } from '../useExecutiveMetricSections';

const activityItems = (events) => events.map((event) => ({
  id: event.id,
  type: event.type,
  time: event.timestamp ? new Date(event.timestamp).toLocaleDateString() : 'Now',
  title: event.description || event.type,
  detail: event.actor?.name || event.source || 'System',
}));

export default function OverviewPage() {
  const [activityTypes, setActivityTypes] = useState([]);
  const requests = useMemo(() => ({
    bundle: () => executiveMetricsApi.getDerivedBundle(),
    activity: () => executiveMetricsApi.getActivityFeed(activityTypes),
    portfolio: () => executiveMetricsApi.getPortfolioHealth(),
    decisions: () => executiveMetricsApi.getDecisionQueue(),
    definitions: () => executiveMetricsApi.getDefinitions(),
    overview: () => executiveMetricsApi.getOverviewMetrics(),
  }), [activityTypes]);
  const { sections, refresh } = useExecutiveMetricSections(requests);
  const bundle = sections.bundle?.data;
  const definitions = sections.definitions?.data?.metrics || [];
  const unavailableReason = (name) => definitions.find((definition) => definition.name === name)?.unavailable_reason;

  const scopeLabel = sections.bundle?.meta?.scope?.scope_type === 'system' ? 'Group scope' : 'Authorized portfolio';
  return <section>
    <header className="exec-hero exec-hero-command"><OrbitalMotif dots={Math.min(6, Number(sections.overview?.data?.active_companies?.value || 3))} /><div className="exec-hero-copy"><p className="eyebrow">FoodSrijan Group · Executive briefing</p><h2>Good evening, Sujit.</h2><p className="page-subtitle">Here is the current pulse of your group.</p><p className="exec-hero-meta">{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })} · {scopeLabel}</p></div><div className="exec-hero-stats"><div className="exec-hero-stat"><PortfolioIcon size={18} /><span>Active companies</span><strong>{sections.overview?.data?.active_companies?.display_value || '—'}</strong></div><div className="exec-hero-stat"><LedgerIcon size={18} /><span>Group revenue</span><strong>{bundle?.group_revenue?.display_value || '—'}</strong></div><div className="exec-hero-stat"><ShieldIcon size={18} /><span>Critical alerts</span><strong>{bundle?.critical_alerts?.display_value || '—'}</strong></div><small className="exec-hero-current"><i /> Portfolio data current</small></div><div className="page-actions exec-hero-actions"><ScopeBadge scope={sections.bundle?.meta?.scope} /><button className="ghost-button compact" onClick={refresh}>Refresh</button></div></header>
    <SectionState section={sections.bundle} unavailableTitle="Executive metrics unavailable">
      <div className="metric-grid four-up">
        <KpiCard label="Group revenue" icon={LedgerIcon} value={bundle?.group_revenue?.display_value} delta={bundle?.revenue_trend?.delta} trend={bundle?.revenue_trend?.trend} tone="gold" sparklinePoints={bundle?.revenue_trend?.sparkline_points || []} />
        <KpiCard label="Operating margin" icon={LedgerIcon} value="Awaiting policy" tone="neutral"><div className="metric-delta">{unavailableReason('operating_margin') || 'Pending accounting policy definition'}</div></KpiCard>
        <KpiCard label="Active companies" icon={PortfolioIcon} value={sections.overview?.data?.active_companies?.display_value} tone="violet" />
        <KpiCard label="Critical alerts" icon={ShieldIcon} value={bundle?.critical_alerts?.display_value} delta={bundle?.critical_alerts?.delta} trend={bundle?.critical_alerts?.trend} tone="rose" />
        <KpiCard label="Customer activity" icon={PulseIcon} value={bundle?.customer_metrics?.value?.active_customers ?? '—'} tone="teal"><div className="metric-delta">{bundle?.customer_metrics?.value?.total_customers ?? '—'} total · {bundle?.customer_metrics?.value?.repeat_rate == null ? '—' : `${bundle.customer_metrics.value.repeat_rate}%`} repeat</div></KpiCard>
        <KpiCard label="Cash conversion" icon={CompassIcon} value={bundle?.cash_conversion?.display_value} delta={bundle?.cash_conversion?.delta} trend={bundle?.cash_conversion?.trend} tone="sunset" />
      </div>
    </SectionState>
    <div className="panel-grid">
      <article className="panel"><div className="panel-header"><h3>Decision queue</h3></div><SectionState section={sections.decisions} emptyTitle="No decisions pending" emptyDescription="There are no supported approval records awaiting review."><DecisionQueue items={(sections.decisions?.data?.details?.items || []).map((item) => ({ ...item, owner: item.requested_by?.name || 'Unassigned' }))} max_items={5} empty_message="No decisions are waiting in the current scope." /></SectionState></article>
      <article className="panel"><div className="panel-header"><h3>Executive activity</h3></div><SectionState section={sections.activity} emptyTitle="No recent activity" emptyDescription="New executive and workspace activity will appear here."><ActivityFeed items={activityItems(sections.activity?.data || [])} filter_types={activityTypes} onFilterTypesChange={setActivityTypes} empty_message="No activity matches the selected types." /></SectionState></article>
    </div>
    <article className="panel"><div className="panel-header"><h3>Company health</h3><ScopeBadge scope={sections.portfolio?.meta?.scope} /></div><SectionState section={sections.portfolio} emptyTitle="No active companies" emptyDescription="Active companies in the current scope will appear here."><div className="company-health-grid">{(sections.portfolio?.data?.details?.companies || []).map((company) => <CompanyHealthCard key={company.company.id} company={company} />)}</div></SectionState></article>
    <article className="panel"><div className="panel-header"><h3>Leadership pulse</h3><span className="governance-chip"><CrownIcon size={13} /> Governed data</span></div><div className="metric-grid three-up"><KpiCard label="NPS" icon={PulseIcon} value="Awaiting survey" tone="violet"><div className="metric-delta">{unavailableReason('leadership_pulse_nps') || 'Survey definition not approved'}</div></KpiCard><KpiCard label="Exit risk" icon={ShieldIcon} value="Awaiting model" tone="rose"><div className="metric-delta">{unavailableReason('leadership_pulse_exit_risk') || 'HR risk model not yet defined'}</div></KpiCard></div></article>
    {bundle?.revenue_trend?.sparkline_points?.length > 0 && <div className="overview-trend"><span>Revenue trend</span><Sparkline values={bundle.revenue_trend.sparkline_points} /></div>}
  </section>;
}
