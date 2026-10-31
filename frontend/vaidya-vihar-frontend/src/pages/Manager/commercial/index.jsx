import { Navigate, Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['orders', 'customers', 'reviews', 'marketing'];

export default function CommercialGroup() {
  return (
    <Routes>
      <Route index element={<Navigate to="/manager/commercial/orders" replace />} />
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
      <Route path="*" element={<Navigate to="/manager/commercial/orders" replace />} />
    </Routes>
  );
}
