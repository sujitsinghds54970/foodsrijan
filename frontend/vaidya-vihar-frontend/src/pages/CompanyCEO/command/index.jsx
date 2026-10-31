import { Route, Routes } from 'react-router-dom';
import CEOProfilePage from './CEOProfilePage';
import PlaceholderRoute from '../layout/PlaceholderRoute';

export default function CommandGroup() {
  return (
    <Routes>
      <Route path="profile/:profileTab?" element={<CEOProfilePage />} />
      <Route path="overview" element={<PlaceholderRoute />} />
      <Route path="strategy" element={<PlaceholderRoute />} />
    </Routes>
  );
}
