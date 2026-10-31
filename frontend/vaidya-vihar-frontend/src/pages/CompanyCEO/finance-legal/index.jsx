import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

export default function FinanceLegalGroup() {
  return <Routes>{['accounts-finance', 'legal-compliances', 'risk-security-sustainability'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}</Routes>;
}
