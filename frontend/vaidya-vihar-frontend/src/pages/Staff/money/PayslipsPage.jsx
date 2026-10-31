import { useCallback, useEffect, useState } from 'react';
import { apiErrorMessage } from '../../../services/companyManagementApi';
import { staffApi } from '../../../services/staffApi';
import { LoadingBlock, PageHeader, SectionEmpty, formatCurrency, formatDate, readCollection } from '../shared/staffShared';

export default function PayslipsPage() {
  const [state, setState] = useState({ loading: true, items: [], error: '', unavailable: false });

  const load = useCallback(async () => {
    setState({ loading: true, items: [], error: '', unavailable: false });
    try {
      const response = await staffApi.getMyPayslips();
      setState({ loading: false, items: readCollection(response.data, ['payslips', 'items', 'history']), error: '', unavailable: false });
    } catch (error) {
      const status = error?.response?.status;
      if (status === 404 || status === 405 || status === 501) {
        setState({ loading: false, items: [], error: '', unavailable: true });
        return;
      }
      setState({ loading: false, items: [], error: apiErrorMessage(error, 'Payslips could not be loaded.'), unavailable: false });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="staff-page">
      <PageHeader eyebrow="Staff · Money" title="Payslips" description="Published payroll outputs for your own account. This page never fabricates salary numbers." action={<button type="button" className="manager-inline-action" onClick={() => void load()}>Refresh</button>} />
      {state.loading ? <LoadingBlock label="Loading payslips" /> : null}
      {!state.loading && state.error ? <div className="manager-inline-state" role="alert"><strong>Payslip feed unavailable.</strong><span>{state.error}</span></div> : null}
      {!state.loading && (state.unavailable || (!state.error && !state.items.length)) ? (
        <section className="manager-panel"><SectionEmpty title={state.unavailable ? 'Payslip endpoint not available yet' : 'No payslips published yet'} description={state.unavailable ? 'The self-service payslip page is wired to the documented endpoint and will light up when payroll data is exposed.' : 'No payslip rows were returned for this account.'} /></section>
      ) : null}
      {!state.loading && !state.error && state.items.length ? (
        <section className="staff-payslips-grid">
          {state.items.map((payslip, index) => (
            <article className="manager-panel" key={payslip.id || `payslip-${index}`}>
              <h2>{payslip.label || payslip.month_label || `${payslip.month || 'Month'} ${payslip.year || ''}`.trim()}</h2>
              <dl className="manager-stat-list staff-field-grid">
                <div><dt>Net pay</dt><dd>{formatCurrency(payslip.net_pay || payslip.amount || payslip.net_amount)}</dd></div>
                <div><dt>Generated</dt><dd>{formatDate(payslip.generated_at || payslip.published_at || payslip.date)}</dd></div>
                <div><dt>Status</dt><dd>{payslip.status || 'Published'}</dd></div>
                <div><dt>Reference</dt><dd>{payslip.reference || payslip.payslip_number || '—'}</dd></div>
              </dl>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
