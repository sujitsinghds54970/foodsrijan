import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['stock', 'indents', 'wastage'];

export default function InventoryGroup() {
  return (
    <Routes>
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
    </Routes>
  );
}
