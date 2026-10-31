import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['food-safety', 'audits'];

export default function ComplianceGroup() {
  return (
    <Routes>
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
    </Routes>
  );
}
