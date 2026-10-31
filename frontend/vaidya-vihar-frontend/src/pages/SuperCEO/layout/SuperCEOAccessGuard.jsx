import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';

export default function SuperCEOAccessGuard({ children, requiredPermission }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  const normalizedRole = (user?.role || '').trim().toLowerCase().replace(/[- ]/g, '_');
  const isSuperCEO = Boolean(user?.is_super_ceo || user?.is_super_admin || normalizedRole === 'super_admin' || normalizedRole === 'super_ceo');
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  const hasRequiredPermission = !requiredPermission || isSuperCEO || permissions.some((permission) => (
    typeof permission === 'string'
      ? permission === requiredPermission
      : permission?.code === requiredPermission || permission?.permission_code === requiredPermission
  ));

  if (loading) return <div className="super-ceo-route-state">Checking executive authority…</div>;
  if (!user) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  if (!isSuperCEO) {
    return (
      <div className="super-ceo-route-state" role="alert">
        <h1>403 — Executive access required</h1>
        <p>Your current authority does not include the Super CEO workspace.</p>
      </div>
    );
  }
  if (requiredPermission && !hasRequiredPermission) {
    return (
      <div className="super-ceo-route-state" role="alert">
        <h1>403 — Permission required</h1>
        <p>Your authority does not include <strong>{requiredPermission}</strong>.</p>
      </div>
    );
  }
  return children;
}
