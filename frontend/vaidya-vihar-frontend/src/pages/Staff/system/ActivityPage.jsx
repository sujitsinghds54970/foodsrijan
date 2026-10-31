import { useCallback, useEffect, useState } from 'react';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatDateTime, readCollection } from '../shared/staffShared';

export default function ActivityPage() {
  const [state, setState] = useState({ loading: true, items: [], error: '' });

  const load = useCallback(async () => {
    setState({ loading: true, items: [], error: '' });
    try {
      const response = await staffApi.getMyActivity();
      setState({ loading: false, items: readCollection(response.data, ['activity', 'events', 'items']), error: '' });
    } catch (error) {
      setState({ loading: false, items: [], error: apiErrorMessage(error, 'Activity could not be loaded.') });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="staff-page">
      <PageHeader eyebrow="Staff · System" title="Activity" description="Your personal audit log, request updates, and workspace events returned by the self-service activity feed." action={<button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button>} />
      <section className="manager-panel">
        {state.loading ? <LoadingBlock label="Loading activity" /> : null}
        {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Activity feed unavailable.</strong><span>{state.error}</span></div> : null}
        {!state.loading && !state.error && !state.items.length ? <SectionEmpty title="No activity returned yet" description="Your personal activity log will appear here once the backend starts publishing events for this account." /> : null}
        {!state.loading && !state.error && state.items.length ? (
          <ol className="manager-activity-list">
            {state.items.map((item, index) => (
              <li key={item.id || `activity-row-${index}`}>
                <i aria-hidden="true" />
                <div>
                  <strong>{item.title || item.action || item.event || `Activity ${index + 1}`}</strong>
                  <span>{item.description || item.detail || item.resource || 'No additional detail provided.'}</span>
                </div>
                <time>{formatDateTime(item.timestamp || item.created_at)}</time>
              </li>
            ))}
          </ol>
        ) : null}
      </section>
    </div>
  );
}
