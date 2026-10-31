import { useCallback, useEffect, useRef, useState } from 'react';

const metricStatus = (envelope) => envelope?.data?.source_status || envelope?.meta?.source_status;

const errorMessage = (reason) => {
  if (!reason) return 'The request failed without an error response.';
  if (reason.response) {
    const detail = reason.response.data?.detail || reason.response.data?.message;
    return detail ? `${reason.response.status}: ${detail}` : `Request failed with status ${reason.response.status}.`;
  }
  return reason.message || String(reason);
};

const getState = (envelope) => {
  const status = metricStatus(envelope);
  if (status === 'unavailable') return 'unavailable';
  if (status === 'empty') return 'empty';
  if (Array.isArray(envelope?.data) && envelope.data.length === 0) return 'empty';
  return 'ready';
};

export function useExecutiveMetricSections(requests, defaultRefreshMs = 300000) {
  const [sections, setSections] = useState(() => Object.fromEntries(
    Object.keys(requests).map((key) => [key, { state: 'loading', data: null, meta: null }]),
  ));
  const refreshTimer = useRef(null);

  const load = useCallback(async () => {
    setSections((current) => Object.fromEntries(Object.entries(current).map(([key, section]) => [
      key,
      { ...section, state: section.data ? section.state : 'loading', error: null },
    ])));

    const entries = Object.entries(requests);
    const settled = await Promise.allSettled(entries.map(([, request]) => request()));
    let refreshMs = defaultRefreshMs;

    setSections(Object.fromEntries(settled.map((result, index) => {
      const [key] = entries[index];
      if (result.status === 'rejected') {
        return [key, {
          state: 'error',
          data: null,
          meta: null,
          error: result.reason,
          errorMessage: errorMessage(result.reason),
        }];
      }

      const { data, meta } = result.value;
      if (meta?.refresh_after_seconds) {
        refreshMs = Math.min(refreshMs, meta.refresh_after_seconds * 1000);
      }
      return [key, { state: getState(result.value), data, meta, error: null }];
    })));

    if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    if (!document.hidden) {
      refreshTimer.current = window.setTimeout(load, refreshMs);
    }
  }, [defaultRefreshMs, requests]);

  useEffect(() => {
    const onVisibilityChange = () => {
      if (!document.hidden) load();
      if (document.hidden && refreshTimer.current) window.clearTimeout(refreshTimer.current);
    };

    load();
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    };
  }, [load]);

  return { sections, refresh: load };
}
