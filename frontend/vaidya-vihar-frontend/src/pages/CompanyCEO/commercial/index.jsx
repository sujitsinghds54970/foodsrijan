import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

export default function CommercialGroup() {
  return <Routes>{['products', 'sales', 'customers', 'customer-experience', 'marketing'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}</Routes>;
}
