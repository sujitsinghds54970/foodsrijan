import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { isManagerRole, managerRoleLabel } from '../../../services/managerApi';

export default function ManagerAccessGuard({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <main className="manager-route-state" role="status" aria-live="polite">
        Checking outlet authority…
      </main>
    );
  }

  if (!user) return <Navigate to="/" replace state={{ from: location.pathname }} />;

  if (!isManagerRole(user.role)) {
    return (
      <main className="manager-route-state" role="alert">
        <h1>403 — Manager access required</h1>
        <p>
          This workspace requires an active outlet manager assignment. Your current role is
          {' '}
          <strong>{managerRoleLabel(user.role)}</strong>.
        </p>
      </main>
    );
  }

  return children;
}
