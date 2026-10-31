import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

export default function GrowthGroup() {
  return <Routes>{['franchise-management', 'real-estate-expansion', 'international-business'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}</Routes>;
}
