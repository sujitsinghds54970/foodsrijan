import { useCallback, useEffect, useMemo, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';
import KpiCard from '../../../components/SuperCEO/common/KpiCard';
import LoadingSkeleton from '../../../components/SuperCEO/common/LoadingSkeleton';
import {
  CommandIcon,
  LedgerIcon,
  PortfolioIcon,
  ShieldIcon,
  SparkIcon,
  VesselIcon,
} from '../../../components/SuperCEO/icons';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { managerApi } from '../../../services/managerApi';

const NO_DATA_STATUSES = new Set(['degraded', 'empty', 'missing', 'no_data', 'not_configured', 'pending', 'unavailable']);

const currency = (value) => value == null ? '—' : new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
}).format(Number(value) || 0);

const integer = (value) => value == null ? '—' : new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 0,
}).format(Number(value) || 0);

const rating = (value) => {
  if (value == null) return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return `${numeric.toFixed(1)} / 5`;
};

const percent = (value) => {
  if (value == null) return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '—';
  return `${Math.round(numeric <= 1 ? numeric * 100 : numeric)}%`;
};

const amount = (value) => {
  if (value == null) return '—';
  const numeric = Number(value);
  return Number.isFinite(numeric) ? currency(numeric) : '—';
};

const asObject = (value) => (value && typeof value === 'object' && !Array.isArray(value) ? value : null);

const firstDefined = (target, keys) => {
  if (!target) return undefined;
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(target, key)) return target[key];
  }
  return undefined;
};

const metricContainers = (payload) => {
  const root = asObject(payload);
  return [root, asObject(root?.kpis), asObject(root?.metrics), asObject(root?.summary), asObject(root?.dashboard)].filter(Boolean);
};

const extractMetric = (payload, keys, fallbackValue = undefined) => {
  const raw = metricContainers(payload).map((container) => firstDefined(container, keys)).find((value) => value !== undefined);
  if (raw === undefined) {
    return { value: fallbackValue ?? null, sourceStatus: fallbackValue == null ? 'unavailable' : 'workspace', source: fallbackValue == null ? 'No data yet' : 'Workspace metrics' };
  }
  if (raw == null || typeof raw === 'number' || typeof raw === 'string') {
    return { value: raw, sourceStatus: raw == null ? 'unavailable' : 'ok', source: 'Live dashboard' };
  }
  const sourceStatus = String(firstDefined(raw, ['source_status', 'status']) || 'ok').toLowerCase();
  const value = firstDefined(raw, ['value', 'count', 'total', 'amount', 'score', 'rating', 'average_rating', 'alerts', 'orders', 'tasks', 'staff']);
  return {
    value: value ?? null,
    sourceStatus,
    source: firstDefined(raw, ['source', 'source_label', 'label', 'summary']) || 'Live dashboard',
    delta: firstDefined(raw, ['delta', 'change']),
    trend: firstDefined(raw, ['trend', 'direction']),
    note: firstDefined(raw, ['note', 'description', 'message']),
  };
};

const noData = (metric) => metric.value == null || NO_DATA_STATUSES.has((metric.sourceStatus || '').toLowerCase());

const payloadItems = (payload, keys) => {
  const root = asObject(payload);
  const candidates = [root, asObject(root?.data), asObject(root?.summary), asObject(root?.dashboard)];
  for (const container of candidates) {
    if (!container) continue;
    for (const key of keys) {
      if (Array.isArray(container[key])) return container[key];
    }
  }
  return [];
};

const payloadObject = (payload, keys) => {
  const root = asObject(payload);
  const candidates = [root, asObject(root?.health), asObject(root?.summary), asObject(root?.dashboard)];
  for (const container of candidates) {
    if (!container) continue;
    for (const key of keys) {
      const value = container[key];
      if (value && typeof value === 'object' && !Array.isArray(value)) return value;
    }
  }
  return null;
};

const readText = (value, keys, fallback = '—') => {
  if (value == null) return fallback;
  if (typeof value === 'string') return value;
  const objectValue = asObject(value);
  if (!objectValue) return fallback;
  const found = firstDefined(objectValue, keys);
  return found == null ? fallback : String(found);
};

const readNumber = (value, keys, fallback = null) => {
  if (value == null) return fallback;
  if (typeof value === 'number') return value;
  const objectValue = asObject(value);
  if (!objectValue) return fallback;
  const found = firstDefined(objectValue, keys);
  return found == null ? fallback : Number(found);
};

const dateTimeLabel = (value) => {
  if (!value) return 'Just now';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
};

function SectionPanel({ title, subtitle, loading, error, emptyTitle, emptyDescription, onRetry, children }) {
  return (
    <section className="manager-panel manager-section-panel">
      <div className="manager-section-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {error && onRetry && (
          <button type="button" className="manager-inline-action" onClick={() => void onRetry()}>
            Retry
          </button>
        )}
      </div>
      {loading ? <LoadingSkeleton /> : null}
      {!loading && error ? (
        <div className="manager-inline-state" role="alert">
          <strong>Unable to load this section.</strong>
          <span>{error}</span>
        </div>
      ) : null}
      {!loading && !error && !children ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : null}
      {!loading && !error ? children : null}
    </section>
  );
}

function HealthCard({ title, tone, metric, formatter = integer, summary }) {
  const empty = noData(metric);
  return (
    <article className={`manager-health-card tone-${tone}`}>
      <span>{title}</span>
      <strong>{empty ? '—' : formatter(metric.value)}</strong>
      <p>{empty ? 'No data yet' : summary || String(metric.source || 'Live dashboard')}</p>
    </article>
  );
}

export default function ManagerOverviewPage() {
  const workspace = useOutletContext();
  const { alerts = [], outlet, manager, metrics } = workspace;
  const [sections, setSections] = useState({
    kpis: { loading: true, data: null, error: '' },
    liveOrders: { loading: true, data: null, error: '' },
    staffOnShift: { loading: true, data: null, error: '' },
    activity: { loading: true, data: null, error: '' },
    health: { loading: true, data: null, error: '' },
  });

  const loadDashboard = useCallback(async () => {
    setSections({
      kpis: { loading: true, data: null, error: '' },
      liveOrders: { loading: true, data: null, error: '' },
      staffOnShift: { loading: true, data: null, error: '' },
      activity: { loading: true, data: null, error: '' },
      health: { loading: true, data: null, error: '' },
    });

    const results = await Promise.allSettled([
      managerApi.kpis(),
      managerApi.liveOrders(),
      managerApi.staffOnShift(),
      managerApi.activity(),
      managerApi.health(),
    ]);

    const [kpis, liveOrders, staffOnShift, activity, health] = results;

    setSections({
      kpis: kpis.status === 'fulfilled'
        ? { loading: false, data: kpis.value.data, error: '' }
        : { loading: false, data: null, error: apiErrorMessage(kpis.reason, 'Dashboard KPIs are unavailable right now.') },
      liveOrders: liveOrders.status === 'fulfilled'
        ? { loading: false, data: liveOrders.value.data, error: '' }
        : { loading: false, data: null, error: apiErrorMessage(liveOrders.reason, 'Live orders could not be loaded.') },
      staffOnShift: staffOnShift.status === 'fulfilled'
        ? { loading: false, data: staffOnShift.value.data, error: '' }
        : { loading: false, data: null, error: apiErrorMessage(staffOnShift.reason, 'Shift staffing could not be loaded.') },
      activity: activity.status === 'fulfilled'
        ? { loading: false, data: activity.value.data, error: '' }
        : { loading: false, data: null, error: apiErrorMessage(activity.reason, 'Recent activity could not be loaded.') },
      health: health.status === 'fulfilled'
        ? { loading: false, data: health.value.data, error: '' }
        : { loading: false, data: null, error: apiErrorMessage(health.reason, 'Health summaries could not be loaded.') },
    });
  }, []);

  useEffect(() => { void loadDashboard(); }, [loadDashboard]);

  const cards = useMemo(() => ([
    {
      label: 'Today’s Sales',
      icon: LedgerIcon,
      tone: 'gold',
      formatter: currency,
      metric: extractMetric(sections.kpis.data, ['today_sales', 'todays_sales', 'sales_today', 'today_sales_total'], metrics.sales_today),
    },
    {
      label: 'Orders Count',
      icon: VesselIcon,
      tone: 'teal',
      formatter: integer,
      metric: extractMetric(sections.kpis.data, ['orders_count', 'order_count', 'orders_today', 'today_order_count'], metrics.orders_today),
    },
    {
      label: 'Active Staff',
      icon: PortfolioIcon,
      tone: 'violet',
      formatter: integer,
      metric: extractMetric(sections.kpis.data, ['active_staff', 'staff_on_shift', 'staff_count', 'active_staff_count'], metrics.team_size),
    },
    {
      label: 'Avg Rating',
      icon: SparkIcon,
      tone: 'sunset',
      formatter: rating,
      metric: extractMetric(sections.kpis.data, ['avg_rating', 'average_rating', 'rating', 'average_customer_rating_30d']),
    },
    {
      label: 'Low Stock Alerts',
      icon: ShieldIcon,
      tone: 'rose',
      formatter: integer,
      metric: extractMetric(sections.kpis.data, ['low_stock_alerts', 'low_stock_items', 'stock_alerts', 'low_stock_items_count'], metrics.low_stock_items),
    },
    {
      label: 'Pending Tasks',
      icon: CommandIcon,
      tone: 'gold',
      formatter: integer,
      metric: extractMetric(sections.kpis.data, ['pending_tasks', 'tasks_pending', 'open_tasks', 'pending_tasks_count']),
    },
  ]), [metrics.low_stock_items, metrics.orders_today, metrics.sales_today, metrics.team_size, sections.kpis.data]);

  const liveOrders = payloadItems(sections.liveOrders.data, ['live_orders', 'orders', 'queue']).slice(0, 10);
  const staffOnShift = payloadItems(sections.staffOnShift.data, ['staff_on_shift', 'staff', 'team']).slice(0, 10);
  const activityItems = payloadItems(sections.activity.data, ['activity', 'events', 'items']).slice(0, 10);

  const inventoryHealthMetric = {
    value: readNumber(payloadObject(sections.health.data, ['inventory_health', 'inventory']), ['total_items', 'count', 'value']),
    sourceStatus: 'ok',
    source: 'Outlet stock file',
  };
  const qualityScoreMetric = extractMetric(sections.health.data, ['quality_score', 'quality', 'food_safety_score', 'quality_food_safety_score']);
  const feedbackMetric = extractMetric(sections.health.data, ['customer_feedback', 'feedback_score', 'feedback', 'feedback_summary']);
  const inventoryHealthObject = payloadObject(sections.health.data, ['inventory_health', 'inventory']);
  const qualityHealthObject = payloadObject(sections.health.data, ['quality_score', 'quality']);
  const feedbackObject = payloadObject(sections.health.data, ['customer_feedback', 'feedback', 'feedback_summary']);

  return (
    <section className="manager-overview" aria-labelledby="manager-overview-title">
      <header className="manager-page-header">
        <p>Command</p>
        <h1 id="manager-overview-title">Good to go, {(manager.full_name || 'Manager').split(' ')[0]}</h1>
        <span>
          {outlet
            ? `Live operating view for ${outlet.name}. Metrics stay empty until each dashboard source starts reporting.`
            : 'No outlet is assigned to your account yet. Ask your Company CEO to assign one.'}
        </span>
      </header>

      {sections.kpis.error && (
        <div className="manager-inline-state" role="status">
          <strong>Using available workspace signals.</strong>
          <span>{sections.kpis.error}</span>
        </div>
      )}

      <div className="manager-kpi-grid">
        {cards.map((card) => {
          const empty = noData(card.metric);
          return (
            <KpiCard
              key={card.label}
              label={card.label}
              value={empty ? '—' : card.formatter(card.metric.value)}
              icon={card.icon}
              tone={card.tone}
              source={empty ? 'No data yet' : String(card.metric.source || 'Live dashboard')}
              delta={empty ? null : card.metric.delta}
              trend={empty ? null : card.metric.trend}
            >
              {empty && <small className="manager-kpi-note">Waiting for this signal to report.</small>}
            </KpiCard>
          );
        })}
      </div>

      <div className="manager-section-grid manager-section-grid-three">
        <SectionPanel
          title="Live Order Queue"
          subtitle="Orders currently moving through service."
          loading={sections.liveOrders.loading}
          error={sections.liveOrders.error}
          emptyTitle="No live orders yet"
          emptyDescription="This queue will populate when the outlet starts sending live order events."
          onRetry={loadDashboard}
        >
          {liveOrders.length ? (
            <ul className="manager-list">
              {liveOrders.map((order, index) => {
                const amountValue = readNumber(order, ['amount', 'bill_amount', 'total_amount']);
                return (
                  <li key={readText(order, ['id', 'order_id', 'order_number'], `live-order-${index}`)} className="manager-list-item">
                    <div>
                      <strong>{readText(order, ['display_number', 'order_number', 'reference', 'id'], `Order ${index + 1}`)}</strong>
                      <span>{[readText(order, ['customer_name', 'patient_name'], ''), readText(order, ['channel', 'source'], '')].filter(Boolean).join(' · ') || 'Awaiting enrichment'}</span>
                    </div>
                    <div className="manager-list-meta">
                      <b>{readText(order, ['status', 'stage'], 'Queued')}</b>
                      <small>{amountValue == null ? readText(order, ['expected_tat_minutes'], '') ? `${readText(order, ['expected_tat_minutes'], '')} min TAT` : dateTimeLabel(firstDefined(asObject(order), ['placed_at', 'created_at', 'updated_at'])) : amount(amountValue)}</small>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </SectionPanel>

        <SectionPanel
          title="Staff on Shift"
          subtitle="Who is active on the current shift right now."
          loading={sections.staffOnShift.loading}
          error={sections.staffOnShift.error}
          emptyTitle="No staff-on-shift data yet"
          emptyDescription="Shift rosters will appear here once the staffing feed is connected."
          onRetry={loadDashboard}
        >
          {staffOnShift.length ? (
            <ul className="manager-list">
              {staffOnShift.map((person, index) => (
                <li key={readText(person, ['id', 'staff_id', 'username'], `shift-staff-${index}`)} className="manager-list-item">
                  <div>
                    <strong>{readText(person, ['full_name', 'name', 'username'], `Staff ${index + 1}`)}</strong>
                    <span>{[readText(person, ['role', 'designation', 'department'], ''), readText(person, ['station', 'section', 'specialization'], '')].filter(Boolean).join(' · ') || 'Shift coverage active'}</span>
                  </div>
                  <div className="manager-list-meta">
                    <b>{readText(person, ['status', 'attendance_status'], 'On shift')}</b>
                    <small>{readText(person, ['clock_in', 'shift_start', 'start_time'], 'Shift timing pending')}</small>
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </SectionPanel>

        <SectionPanel
          title="Recent Activity"
          subtitle="Latest outlet events across service, staffing, and controls."
          loading={sections.activity.loading}
          error={sections.activity.error}
          emptyTitle="No recent activity yet"
          emptyDescription="This feed will show the last 10 manager-facing events once the backend starts emitting them."
          onRetry={loadDashboard}
        >
          {activityItems.length ? (
            <ol className="manager-activity-list">
              {activityItems.map((item, index) => (
                <li key={readText(item, ['id', 'event_id'], `activity-${index}`)}>
                  <i aria-hidden="true" />
                  <div>
                    <strong>{readText(item, ['title', 'action', 'event'], `Activity ${index + 1}`)}</strong>
                    <span>{readText(item, ['description', 'detail', 'resource'], 'No additional detail provided.')}</span>
                  </div>
                  <time>{dateTimeLabel(firstDefined(asObject(item), ['timestamp', 'created_at', 'occurred_at']))}</time>
                </li>
              ))}
            </ol>
          ) : null}
        </SectionPanel>
      </div>

      <div className="manager-section-grid manager-section-grid-three">
        <SectionPanel
          title="Inventory Health"
          subtitle="Stock pressure and replenishment readiness."
          loading={sections.health.loading}
          error={sections.health.error}
          emptyTitle="Inventory health not available"
          emptyDescription="Inventory quality signals will appear here when the health endpoint is live."
          onRetry={loadDashboard}
        >
          <HealthCard
            title="Inventory Health"
            tone="rose"
            metric={inventoryHealthMetric}
            formatter={integer}
            summary={inventoryHealthObject
              ? `Low stock: ${integer(readNumber(inventoryHealthObject, ['low_stock_count']))} · Expiring soon: ${integer(readNumber(inventoryHealthObject, ['expiring_soon_count']))}`
              : readText(inventoryHealthObject, ['summary', 'status_text', 'note'], '')}
          />
        </SectionPanel>

        <SectionPanel
          title="Quality Score"
          subtitle="Food safety and service quality confidence."
          loading={sections.health.loading}
          error={sections.health.error}
          emptyTitle="Quality score not available"
          emptyDescription="Quality scoring will appear when the outlet starts publishing quality summaries."
          onRetry={loadDashboard}
        >
          <HealthCard
            title="Quality Score"
            tone="gold"
            metric={qualityScoreMetric}
            formatter={percent}
            summary={readText(qualityHealthObject, ['summary', 'status_text', 'note'], '')}
          />
        </SectionPanel>

        <SectionPanel
          title="Customer Feedback"
          subtitle="High-level pulse from recent customer responses."
          loading={sections.health.loading}
          error={sections.health.error}
          emptyTitle="Customer feedback summary unavailable"
          emptyDescription="Review and satisfaction signals will show here when the feedback feed is ready."
          onRetry={loadDashboard}
        >
          <HealthCard
            title="Customer Feedback"
            tone="sunset"
            metric={feedbackMetric}
            formatter={rating}
            summary={feedbackObject
              ? `Responses: ${integer(readNumber(feedbackObject, ['feedback_count', 'count', 'total']))}`
              : readText(feedbackObject, ['summary', 'status_text', 'note'], '')}
          />
        </SectionPanel>
      </div>

      <section className="manager-panel" aria-labelledby="manager-alerts-title">
        <div className="manager-section-heading">
          <div>
            <h2 id="manager-alerts-title">Open alerts</h2>
            <p>Workspace alerts already available from the manager workspace bootstrap.</p>
          </div>
        </div>
        {alerts.length === 0 ? (
          <EmptyState
            title="No open alerts"
            description="No alert feed is available for this outlet yet."
          />
        ) : (
          <ul className="manager-alert-list">
            {alerts.map((alert) => (
              <li key={alert.id} className={`severity-${alert.severity}`}>
                <strong>{alert.title}</strong>
                {alert.detail && <span>{alert.detail}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
