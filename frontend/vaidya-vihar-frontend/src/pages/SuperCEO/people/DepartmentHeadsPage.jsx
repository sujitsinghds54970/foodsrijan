import { useMemo } from 'react';
import ScopeBadge from '../../../components/SuperCEO/common/ScopeBadge';
import SectionState from '../../../components/SuperCEO/common/SectionState';
import { executiveMetricsApi } from '../../../services/executiveMetricsApi';
import { useExecutiveMetricSections } from '../useExecutiveMetricSections';

export default function DepartmentHeadsPage() {
  const requests = useMemo(() => ({
    users: () => executiveMetricsApi.getUsers(),
    companies: () => executiveMetricsApi.getCompanies(),
  }), []);
  const { sections, refresh } = useExecutiveMetricSections(requests);
  const leadershipRoles = new Set(['ceo', 'company_admin', 'department_head', 'head_of_department']);
  const leaders = (sections.users?.data || []).filter((user) => user.is_active && leadershipRoles.has((user.role || '').toLowerCase()));
  const activeCompanyCount = (sections.companies?.data || []).filter((company) => company.is_active).length;

  return <section>
    <header className="exec-hero"><div><p className="eyebrow">People</p><h2>Department heads</h2><p className="page-subtitle">Legacy-derived leadership roster from active user roles and company assignments.</p></div><div className="page-actions"><ScopeBadge label="Group scope" /><button className="ghost-button compact" onClick={refresh}>Refresh</button></div></header>
    <article className="panel"><div className="panel-header"><h3>Leadership roster</h3><span className="mini-meta">Read-only legacy data · {activeCompanyCount} active companies</span></div><SectionState section={sections.users} emptyTitle="No leadership roles found" emptyDescription="Active users with a leadership role will appear here."><div className="table-shell"><div className="table-header department-head-row"><span>Leader</span><span>Role</span><span>Company assignments</span></div>{leaders.map((user) => <div className="table-row department-head-row" key={user.id}><div><strong>{`${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username}</strong><div className="mini-meta">{user.email}</div></div><span className="status-chip stable">{(user.role || 'leader').replace('_', ' ')}</span><span>{user.companies?.map((company) => company.name).join(', ') || 'No company assignment'}</span></div>)}</div></SectionState></article>
  </section>;
}
