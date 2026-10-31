import { useLocation, Navigate } from 'react-router-dom';
import ComingSoonPlaceholder from './ComingSoonPlaceholder';
import { findCompanyCeoTab, COMPANY_CEO_DEFAULT_PATH } from './tabConfig';

export default function PlaceholderRoute() {
  const location = useLocation();
  const tab = findCompanyCeoTab(location.pathname);
  if (!tab) return <Navigate to={COMPANY_CEO_DEFAULT_PATH} replace />;
  return <ComingSoonPlaceholder icon={tab.icon} tone={tab.tone} title={tab.label} description={tab.description} features={tab.features} eta={tab.eta} />;
}
