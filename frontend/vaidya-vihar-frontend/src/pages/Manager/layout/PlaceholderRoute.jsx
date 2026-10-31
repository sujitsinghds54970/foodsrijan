import { Navigate, useLocation } from 'react-router-dom';
import ComingSoonPlaceholder from './ComingSoonPlaceholder';
import { MANAGER_DEFAULT_PATH, findManagerTab } from './tabConfig';

export default function PlaceholderRoute() {
  const location = useLocation();
  const tab = findManagerTab(location.pathname);
  if (!tab) return <Navigate to={MANAGER_DEFAULT_PATH} replace />;
  return (
    <ComingSoonPlaceholder
      icon={tab.icon}
      tone={tab.tone}
      title={tab.title || tab.label}
      description={tab.description}
      features={tab.features}
      eta={tab.eta}
    />
  );
}
