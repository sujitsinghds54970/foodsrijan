import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatDateTime, readCollection } from '../shared/staffShared';

const initialPassword = { current_password: '', new_password: '', confirm_password: '' };

export default function SecurityPage() {
  const [form, setForm] = useState(initialPassword);
  const [saving, setSaving] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionsState, setSessionsState] = useState({ loading: true, error: '', unavailable: false });

  const loadSessions = useCallback(async () => {
    setSessionsState({ loading: true, error: '', unavailable: false });
    try {
      const response = await staffApi.getMySessions();
      setSessions(readCollection(response.data, ['sessions', 'items', 'results']));
      setSessionsState({ loading: false, error: '', unavailable: false });
    } catch (error) {
      const status = error?.response?.status;
      if (status === 404 || status === 405 || status === 501) {
        setSessions([]);
        setSessionsState({ loading: false, error: '', unavailable: true });
        return;
      }
      setSessions([]);
      setSessionsState({ loading: false, error: apiErrorMessage(error, 'Sessions could not be loaded.'), unavailable: false });
    }
  }, []);

  useEffect(() => { void loadSessions(); }, [loadSessions]);

  const submit = async (event) => {
    event.preventDefault();
    if (form.new_password !== form.confirm_password) {
      toast.error('New password and confirmation must match.');
      return;
    }
    setSaving(true);
    try {
      await staffApi.changeMyPassword({ current_password: form.current_password, new_password: form.new_password });
      toast.success('Password updated.');
      setForm(initialPassword);
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to change your password.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="staff-page">
      <PageHeader eyebrow="Staff · System" title="Security" description="Manage your password and review active sessions when that endpoint is available." />
      <div className="manager-section-grid manager-detail-grid">
        <form className="manager-panel" onSubmit={submit}>
          <div className="manager-section-heading"><div><h2>Change password</h2><p>Use your current password to set a new one for the staff account.</p></div></div>
          <div className="manager-form-grid">
            <label className="manager-form-field"><span>Current password</span><input type="password" value={form.current_password} onChange={(event) => setForm((current) => ({ ...current, current_password: event.target.value }))} required /></label>
            <label className="manager-form-field"><span>New password</span><input type="password" value={form.new_password} onChange={(event) => setForm((current) => ({ ...current, new_password: event.target.value }))} required minLength={8} /></label>
            <label className="manager-form-field is-wide"><span>Confirm password</span><input type="password" value={form.confirm_password} onChange={(event) => setForm((current) => ({ ...current, confirm_password: event.target.value }))} required minLength={8} /></label>
          </div>
          <footer className="exec-profile-panel-footer staff-form-footer">
            <span>Passwords are submitted using the shared authenticated API client.</span>
            <button type="submit" className="exec-button exec-button-primary" disabled={saving}>{saving ? 'Updating…' : 'Update password'}</button>
          </footer>
        </form>

        <section className="manager-panel">
          <div className="manager-section-heading"><div><h2>Active sessions</h2><p>Current signed-in sessions for your account when the endpoint is available.</p></div><button type="button" className="manager-inline-action" onClick={() => void loadSessions()}>Refresh</button></div>
          {sessionsState.loading ? <LoadingBlock label="Loading sessions" /> : null}
          {!sessionsState.loading && sessionsState.error ? <div className="manager-inline-state" role="alert"><strong>Session feed unavailable.</strong><span>{sessionsState.error}</span></div> : null}
          {!sessionsState.loading && (sessionsState.unavailable || (!sessionsState.error && !sessions.length)) ? <SectionEmpty title={sessionsState.unavailable ? 'Session endpoint not available yet' : 'No active sessions returned'} description={sessionsState.unavailable ? 'The page is prepared to show active sessions once the backend publishes them.' : 'No session rows were returned for this account.'} /> : null}
          {!sessionsState.loading && !sessionsState.error && sessions.length ? (
            <ol className="manager-list">
              {sessions.map((session, index) => (
                <li key={session.id || session.session_id || `session-${index}`} className="manager-list-item">
                  <div>
                    <strong>{session.device_name || session.user_agent || session.ip_address || `Session ${index + 1}`}</strong>
                    <span>{session.location || session.platform || 'No additional session metadata provided.'}</span>
                  </div>
                  <div className="manager-list-meta">
                    <b>{session.current ? 'Current' : session.status || 'Active'}</b>
                    <small>{formatDateTime(session.last_active_at || session.created_at)}</small>
                  </div>
                </li>
              ))}
            </ol>
          ) : null}
        </section>
      </div>
    </div>
  );
}
