import { Navigate, Route, Routes } from 'react-router-dom';
import ManagerOverviewPage from './ManagerOverviewPage';
import ManagerProfilePage from './ManagerProfilePage';

export default function CommandGroup() {
  return (
    <Routes>
      <Route path="dashboard" element={<ManagerOverviewPage />} />
      <Route path="overview" element={<Navigate to="/manager/dashboard" replace />} />
      <Route path="profile" element={<Navigate to="/manager/profile/about" replace />} />
      <Route path="profile/:profileTab" element={<ManagerProfilePage />} />
      <Route path="command/overview" element={<Navigate to="/manager/dashboard" replace />} />
      <Route path="command/profile" element={<Navigate to="/manager/profile/about" replace />} />
      <Route path="command/profile/:profileTab" element={<Navigate to="/manager/profile/about" replace />} />
      <Route path="command/responsibilities" element={<Navigate to="/manager/intelligence/tasks" replace />} />
      <Route path="*" element={<Navigate to="/manager/dashboard" replace />} />
    </Routes>
  );
}
