import { useOutletContext } from 'react-router-dom';
import ProfilePage from '../../SuperCEO/people/ProfilePage';

const formatCurrency = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  notation: 'compact',
  maximumFractionDigits: 1,
}).format(value || 0);

export default function CEOProfilePage() {
  const workspace = useOutletContext();
  return (
    <ProfilePage
      basePath="/company-ceo/command/profile"
      authorityLabel="Company CEO"
      organizationName={workspace.company.name}
      idPrefix="company-ceo-profile"
      metrics={[
        { label: 'Branches', value: workspace.metrics.branches },
        { label: 'Employees', value: workspace.metrics.employees },
        { label: 'Customers', value: workspace.metrics.customers },
        { label: 'Revenue', value: formatCurrency(workspace.metrics.revenue) },
      ]}
    />
  );
}
