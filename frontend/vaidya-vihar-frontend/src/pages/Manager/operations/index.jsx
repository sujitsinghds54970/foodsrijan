import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['daily-operations', 'roster', 'production', 'maintenance'];

export default function OperationsGroup() {
  return (
    <Routes>
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
    </Routes>
  );
}
