import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

export default function IntelligenceGroup() {
  return <Routes>{['analytics', 'data-bi', 'partnerships'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}</Routes>;
}
