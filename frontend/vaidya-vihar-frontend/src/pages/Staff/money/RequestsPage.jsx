import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatCurrency, formatDate, readCollection } from '../shared/staffShared';

const initialForm = {
  request_type: 'advance',
  amount: '',
  reason: '',
  notes: '',
};

export default function RequestsPage() {
  const [form, setForm] = useState(initialForm);
  const [saving, setSaving] = useState(false);
  const [state, setState] = useState({ loading: true, items: [], error: '' });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: '' }));
    try {
      const response = await staffApi.getMyRequests();
      setState({ loading: false, items: readCollection(response.data, ['requests', 'items', 'results']), error: '' });
    } catch (error) {
      setState({ loading: false, items: [], error: apiErrorMessage(error, 'Requests could not be loaded.') });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await staffApi.submitRequest({
        type: form.request_type,
        reason: [form.reason.trim(), form.notes.trim(), form.amount ? `Amount requested: ${form.amount}` : ''].filter(Boolean).join('\n'),
      });
      toast.success('Request submitted.');
      setForm(initialForm);
      await load();
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Unable to submit your request.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="staff-page">
      <PageHeader eyebrow="Staff · Money" title="Requests" description="Submit general and salary-advance requests, then track their status." />
      <Link className="staff-quick-action" to="/staff/attendance">For dated leave and manager approval, open attendance leave requests</Link>
      <div className="manager-section-grid manager-detail-grid">
        <form className="manager-panel" onSubmit={submit}>
          <div className="manager-section-heading"><div><h2>New request</h2><p>Submit an advance or general request with the details your manager needs.</p></div></div>
          <div className="manager-form-grid">
            <label className="manager-form-field"><span>Request type</span><select value={form.request_type} onChange={(event) => setForm((current) => ({ ...current, request_type: event.target.value }))}><option value="advance">Advance</option><option value="other">Other</option></select></label>
            <label className="manager-form-field"><span>Amount</span><input type="number" min="0" step="0.01" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))} disabled={form.request_type !== 'advance'} placeholder="Optional unless advance" /></label>
            <label className="manager-form-field is-wide"><span>Reason</span><input value={form.reason} onChange={(event) => setForm((current) => ({ ...current, reason: event.target.value }))} placeholder="Briefly describe the request" required /></label>
            <label className="manager-form-field is-wide"><span>Notes</span><textarea value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} rows={4} placeholder="Anything your manager should know?" /></label>
          </div>
          <footer className="exec-profile-panel-footer staff-form-footer">
            <span>Requests are submitted through <code>/api/staff/me/requests</code>.</span>
            <button type="submit" className="exec-button exec-button-primary" disabled={saving}>{saving ? 'Submitting…' : 'Submit request'}</button>
          </footer>
        </form>

        <section className="manager-panel">
          <div className="manager-section-heading"><div><h2>My requests</h2><p>Your own leave and advance requests returned by the self-service request feed.</p></div><button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button></div>
          {state.loading ? <LoadingBlock label="Loading requests" /> : null}
          {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Requests unavailable.</strong><span>{state.error}</span></div> : null}
          {!state.loading && !state.error && !state.items.length ? <SectionEmpty title="No requests submitted yet" description="Once you submit a request, its approval status will appear here." /> : null}
          {!state.loading && !state.error && state.items.length ? (
            <ol className="manager-list">
              {state.items.map((item, index) => (
                <li key={item.id || `request-${index}`} className="manager-list-item">
                  <div>
                    <strong>{item.title || item.request_type || item.type || `Request ${index + 1}`}</strong>
                    <span>{item.reason || item.notes || item.description || 'No additional detail provided.'}</span>
                  </div>
                  <div className="manager-list-meta">
                    <b>{item.status || 'Pending'}</b>
                    <small>{item.amount ? formatCurrency(item.amount) : [formatDate(item.start_date), formatDate(item.end_date)].filter((value) => value !== '—').join(' → ') || 'No dates supplied'}</small>
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
