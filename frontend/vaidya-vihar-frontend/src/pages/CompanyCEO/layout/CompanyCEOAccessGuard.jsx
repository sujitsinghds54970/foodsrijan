import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';

export default function CompanyCEOAccessGuard({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  const normalizedRole = (user?.role || '').trim().toLowerCase().replace(/[- ]/g, '_');
  const isCompanyCEO = Boolean(user?.is_company_ceo || normalizedRole === 'company_ceo');
  const companyId = user?.current_company_id ?? user?.company_id;

  if (loading) return <main className="company-ceo-route-state">Checking company authority…</main>;
  if (!user) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  if (!isCompanyCEO || !companyId) {
    return (
      <main className="company-ceo-route-state" role="alert">
        <h1>403 — Company CEO access required</h1>
        <p>This workspace requires an active Company CEO assignment.</p>
      </main>
    );
  }
  return children;
}
