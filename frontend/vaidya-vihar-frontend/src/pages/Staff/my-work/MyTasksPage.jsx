import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatDateTime, readCollection } from '../shared/staffShared';

export default function MyTasksPage() {
  const [state, setState] = useState({ loading: true, items: [], error: '', unavailable: false });

  const load = useCallback(async () => {
    setState({ loading: true, items: [], error: '', unavailable: false });
    try {
      const response = await staffApi.getMyTasks();
      setState({ loading: false, items: readCollection(response.data, ['tasks', 'items', 'results']), error: '', unavailable: false });
    } catch (error) {
      const status = error?.response?.status;
      if (status === 404 || status === 405 || status === 501) {
        setState({ loading: false, items: [], error: '', unavailable: true });
        return;
      }
      setState({ loading: false, items: [], error: apiErrorMessage(error, 'Tasks could not be loaded.'), unavailable: false });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="staff-page">
      <PageHeader eyebrow="Staff · My work" title="My tasks" description="Track assigned tasks, deadlines, and completion status from the staff task feed." action={<button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button>} />
      {state.loading ? <LoadingBlock label="Loading tasks" /> : null}
      {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Task feed unavailable.</strong><span>{state.error}</span></div> : null}
      {!state.loading && (state.unavailable || !state.items.length) ? (
        <section className="manager-panel"><SectionEmpty title={state.unavailable ? 'Task endpoint not available yet' : 'No tasks assigned right now'} description={state.unavailable ? 'This phase wires the task page to the documented endpoint; once the backend exposes it, your task list will appear here automatically.' : 'You are clear for the moment. New tasks will appear here when assigned.'} /></section>
      ) : null}
      {!state.loading && !state.error && state.items.length ? (
        <section className="manager-panel">
          <ol className="staff-task-list">
            {state.items.map((task, index) => (
              <li key={task.id || `task-row-${index}`}>
                <div>
                  <strong>{task.title || task.task_name || `Task ${index + 1}`}</strong>
                  <span>{task.description || task.detail || 'No additional detail available for this task yet.'}</span>
                </div>
                <div className="manager-list-meta">
                  <b>{task.status || 'Pending'}</b>
                  <small>{task.deadline || task.due_date ? formatDateTime(task.deadline || task.due_date) : 'No deadline'}</small>
                </div>
              </li>
            ))}
          </ol>
          <footer className="staff-task-footer"><Link to="/staff/activity">See activity log</Link></footer>
        </section>
      ) : null}
    </div>
  );
}
