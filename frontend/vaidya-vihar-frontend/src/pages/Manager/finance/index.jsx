import { Navigate, Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['cash', 'inventory', 'purchasing', 'recipes'];

export default function FinanceGroup() {
  return (
    <Routes>
      <Route index element={<Navigate to="/manager/finance/cash" replace />} />
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
      <Route path="*" element={<Navigate to="/manager/finance/cash" replace />} />
    </Routes>
  );
}
