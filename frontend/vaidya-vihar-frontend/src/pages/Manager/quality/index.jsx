import { Navigate, Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['food-safety', 'security', 'maintenance'];

export default function QualityGroup() {
  return (
    <Routes>
      <Route index element={<Navigate to="/manager/quality/food-safety" replace />} />
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
      <Route path="*" element={<Navigate to="/manager/quality/food-safety" replace />} />
    </Routes>
  );
}
