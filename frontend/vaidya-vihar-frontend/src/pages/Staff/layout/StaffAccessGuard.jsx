import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { isStaffRole, staffRoleLabel } from '../../../services/staffApi';

export default function StaffAccessGuard({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <main className="manager-route-state" role="status" aria-live="polite">Checking staff workspace access…</main>;
  }

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  if (!isStaffRole(user.role)) {
    return (
      <main className="manager-route-state" role="alert">
        <h1>403 — Staff access required</h1>
        <p>This workspace is only available to staff accounts. Your current role is <strong>{staffRoleLabel(user.role)}</strong>.</p>
      </main>
    );
  }

  return children;
}
