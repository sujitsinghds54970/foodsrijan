import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import {
  AuditTrailIcon,
  BriefingIcon,
  CommandIcon,
  LedgerIcon,
  PulseIcon,
  ShieldIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import {
  PageHeader,
  QuickAction,
  SectionEmpty,
  LoadingBlock,
  formatCount,
  formatCurrency,
  formatDateTime,
  formatPercent,
  readCollection,
  readNumber,
  readText,
  readValue,
} from '../shared/staffShared';

const asShiftState = (payload) => {
  const clockedIn = Boolean(readValue(payload, ['clocked_in', 'is_clocked_in', 'shift_live'], false));
  const clockedOut = Boolean(readValue(payload, ['clocked_out', 'is_clocked_out'], false));
  const label = readText(payload, ['shift_label', 'shift_status', 'clock_state', 'status'], clockedIn && !clockedOut ? 'On shift now' : 'Not clocked in');
  return { clockedIn, clockedOut, label };
};

export default function DashboardPage() {
  const workspace = useOutletContext();
  const [state, setState] = useState({
    loading: true,
    dashboard: null,
    tasks: [],
    activity: [],
    requests: [],
    error: '',
  });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    const results = await Promise.allSettled([
      staffApi.getMyDashboard(),
      staffApi.getMyTasks(),
      staffApi.getMyActivity(),
      staffApi.getMyRequests(),
    ]);
    const [dashboard, tasks, activity, requests] = results;

    setState({
      loading: false,
      dashboard: dashboard.status === 'fulfilled' ? dashboard.value.data : null,
      tasks: tasks.status === 'fulfilled' ? readCollection(tasks.value.data, ['tasks', 'items', 'results']) : [],
      activity: activity.status === 'fulfilled' ? readCollection(activity.value.data, ['activity', 'events', 'items']) : [],
      requests: requests.status === 'fulfilled' ? readCollection(requests.value.data, ['requests', 'items', 'results']) : [],
      error: dashboard.status === 'rejected' ? apiErrorMessage(dashboard.reason, 'The dashboard feed could not be loaded.') : '',
    });
  }, []);

  useEffect(() => { void load(); }, [load]);

  const shift = useMemo(() => asShiftState(state.dashboard), [state.dashboard]);
  const todayTasks = state.tasks.slice(0, 5);
  const recentActivity = state.activity.slice(0, 6);
  const pendingRequests = state.requests.filter((item) => String(item.status || '').toLowerCase().includes('pending')).length;

  const metrics = useMemo(() => ([
    {
      label: "Today's Shift",
      value: shift.label,
      tone: 'gold',
      icon: CommandIcon,
      source: 'Staff dashboard',
    },
    {
      label: 'My Tasks Today',
      value: formatCount(readNumber(state.dashboard, ['tasks_today', 'today_tasks', 'tasks_count'], todayTasks.length)),
      tone: 'teal',
      icon: BriefingIcon,
      source: 'Task feed',
    },
    {
      label: 'Attendance This Month',
      value: formatPercent(readNumber(state.dashboard, ['attendance_percentage', 'attendance_rate', 'attendance_month_percent'], null)),
      tone: 'violet',
      icon: PulseIcon,
      source: 'Attendance summary',
    },
    {
      label: 'Pending Requests',
      value: formatCount(readNumber(state.dashboard, ['pending_requests', 'requests_pending'], pendingRequests)),
      tone: 'sunset',
      icon: AuditTrailIcon,
      source: 'Request queue',
    },
    {
      label: 'Last Payslip',
      value: formatCurrency(readValue(state.dashboard, ['last_payslip_amount', 'latest_payslip_amount', 'last_salary_amount'], null)),
      tone: 'rose',
      icon: LedgerIcon,
      source: 'Payroll summary',
    },
    {
      label: 'Rating',
      value: readValue(state.dashboard, ['rating', 'average_rating', 'performance_rating'], null) == null ? '—' : `${Number(readValue(state.dashboard, ['rating', 'average_rating', 'performance_rating'], 0)).toFixed(1)} / 5`,
      tone: 'gold',
      icon: ShieldIcon,
      source: 'Performance summary',
    },
  ]), [pendingRequests, shift.label, state.dashboard, todayTasks.length]);

  return (
    <div className="staff-page">
      <PageHeader
        eyebrow="Staff · My work"
        title={`Welcome back, ${workspace.me.first_name || workspace.me.full_name || 'team member'}`}
        description="Track your shift, tasks, payroll highlights, and request status from a single self-service command view."
        action={<Link className="exec-button exec-button-secondary" to="/staff/requests">Open requests</Link>}
      />

      <section className="manager-kpi-grid" aria-label="Staff dashboard KPIs">
        {metrics.map((metric) => (
          <KpiCard key={metric.label} label={metric.label} value={metric.value} tone={metric.tone} icon={metric.icon} source={metric.source} />
        ))}
      </section>

      {state.loading ? <LoadingBlock label="Loading dashboard" /> : null}
      {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Dashboard signal unavailable.</strong><span>{state.error}</span></div> : null}

      <div className="manager-section-grid manager-detail-grid">
        <section className="manager-panel manager-section-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Live shift status</h2>
              <p>Clock status and shift context from the staff self-service feed.</p>
            </div>
            <Link className="exec-button exec-button-primary" to="/staff/attendance/clock">Open attendance clock</Link>
          </div>
          <div className="staff-highlight-card">
            <strong>{shift.label}</strong>
            <span>{readText(state.dashboard, ['shift_name', 'today_shift_name', 'shift_window'], workspace.outlet?.name || 'Your outlet shift')}</span>
            <small>{readText(state.dashboard, ['clock_note', 'shift_note'], 'Use the clock button at the start and end of your duty period.')}</small>
          </div>
        </section>

        <section className="manager-panel manager-section-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Quick actions</h2>
              <p>Open the most common staff workflows with one click.</p>
            </div>
          </div>
          <div className="staff-quick-actions-grid">
            <QuickAction to="/staff/tasks">Review today’s tasks</QuickAction>
            <QuickAction to="/staff/attendance">Check attendance log</QuickAction>
            <QuickAction to="/staff/requests">Submit leave or advance request</QuickAction>
            <QuickAction to="/staff/security">Update password</QuickAction>
          </div>
        </section>
      </div>

      <div className="manager-section-grid manager-detail-grid">
        <section className="manager-panel manager-section-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Today’s tasks</h2>
              <p>Your next operational priorities published to the staff task feed.</p>
            </div>
            <Link className="manager-inline-action" to="/staff/tasks">View all</Link>
          </div>
          {!todayTasks.length ? (
            <SectionEmpty title="No tasks published yet" description="Tasks will appear here when the staff task endpoint starts returning records for this account." />
          ) : (
            <ol className="manager-list">
              {todayTasks.map((task, index) => (
                <li key={task.id || `task-${index}`} className="manager-list-item">
                  <div>
                    <strong>{task.title || task.task_name || `Task ${index + 1}`}</strong>
                    <span>{task.description || task.detail || 'No additional task detail has been provided.'}</span>
                  </div>
                  <div className="manager-list-meta">
                    <b>{task.priority || 'Task'}</b>
                    <small>{task.deadline ? formatDateTime(task.deadline) : task.status || 'Pending'}</small>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="manager-panel manager-section-panel">
          <div className="manager-section-heading">
            <div>
              <h2>Recent activity</h2>
              <p>Your latest personal audit events and request activity.</p>
            </div>
            <Link className="manager-inline-action" to="/staff/activity">Open activity</Link>
          </div>
          {!recentActivity.length ? (
            <SectionEmpty title="No recent activity yet" description="Recent activity will appear here once the self-service activity feed starts emitting events." />
          ) : (
            <ol className="manager-activity-list">
              {recentActivity.map((item, index) => (
                <li key={item.id || `activity-${index}`}>
                  <i aria-hidden="true" />
                  <div>
                    <strong>{item.title || item.action || item.event || `Activity ${index + 1}`}</strong>
                    <span>{item.description || item.detail || item.resource || 'No additional detail provided.'}</span>
                  </div>
                  <time>{formatDateTime(item.timestamp || item.created_at)}</time>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}
