import { Navigate, Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['reports', 'tasks'];

export default function IntelligenceGroup() {
  return (
    <Routes>
      <Route index element={<Navigate to="/manager/intelligence/reports" replace />} />
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
      <Route path="*" element={<Navigate to="/manager/intelligence/reports" replace />} />
    </Routes>
  );
}
