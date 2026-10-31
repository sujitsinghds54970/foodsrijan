import { Navigate, Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['operations', 'kitchen', 'delivery', 'cleaning'];

export default function DailyOpsGroup() {
  return (
    <Routes>
      <Route index element={<Navigate to="/manager/daily-ops/operations" replace />} />
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
      <Route path="*" element={<Navigate to="/manager/daily-ops/operations" replace />} />
    </Routes>
  );
}
