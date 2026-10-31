import { useOutletContext } from 'react-router-dom';
import EmptyState from '../../../components/SuperCEO/common/EmptyState';

const STATUS_LABEL = {
  active: 'Active',
  planned: 'Planned',
  delegated: 'Delegated',
};

export default function ManagerResponsibilitiesPage() {
  const { responsibilities = [], outlet } = useOutletContext();

  return (
    <section className="manager-responsibilities" aria-labelledby="manager-responsibilities-title">
      <header className="manager-page-header">
        <p>Command</p>
        <h1 id="manager-responsibilities-title">Responsibilities</h1>
        <span>
          What you own{outlet ? ` at ${outlet.name}` : ''}, what you may decide, and where a
          decision escalates when it exceeds your authority.
        </span>
        <span>Illustrative responsibilities; a live responsibility register is not available yet.</span>
      </header>

      {responsibilities.length === 0 ? (
        <EmptyState
          title="No responsibilities recorded"
          description="Your responsibility register has not been published for this outlet yet."
        />
      ) : (
        <ul className="manager-responsibility-list">
          {responsibilities.map((item) => (
            <li key={item.id} className={`status-${item.status}`}>
              <header>
                <strong>{item.title}</strong>
                <span className="manager-chip">{item.domain}</span>
                <span className={`manager-status manager-status-${item.status}`}>
                  {STATUS_LABEL[item.status] || item.status}
                </span>
              </header>
              <p>{item.description}</p>
              <dl>
                <div><dt>Authority</dt><dd>{item.authority}</dd></div>
                <div><dt>Escalates to</dt><dd>{item.escalates_to || '—'}</dd></div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
