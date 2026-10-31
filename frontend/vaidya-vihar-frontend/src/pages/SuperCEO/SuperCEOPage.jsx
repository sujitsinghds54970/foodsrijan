import { Navigate } from 'react-router-dom';

/**
 * Compatibility entry point for imports that still reference the former
 * monolithic page. The canonical workspace is now mounted by nested routes.
 */
export default function SuperCEOPage() {
  return <Navigate to="/super-ceo/overview" replace />;
}
