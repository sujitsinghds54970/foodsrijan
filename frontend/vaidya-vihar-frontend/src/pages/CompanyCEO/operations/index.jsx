import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';
import OutletsPage from './OutletsPage';
import OutletWizardPage from './OutletWizardPage';
import OutletDetailPage from './OutletDetailPage';

export default function OperationsGroup() {
  return <Routes>
    <Route path="outlets" element={<OutletsPage />} />
    <Route path="outlets/new" element={<OutletWizardPage />} />
    <Route path="outlets/:outletId/edit" element={<OutletWizardPage />} />
    <Route path="outlets/:outletId/:outletTab?" element={<OutletDetailPage />} />
    {['outlet-operations', 'production', 'supply-chain', 'inventory', 'quality', 'assets'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
  </Routes>;
}
