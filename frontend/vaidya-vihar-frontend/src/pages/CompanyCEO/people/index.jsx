import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';
import AttendanceOverviewPage from './AttendanceOverviewPage';

export default function PeopleGroup() {
  return <Routes>
    <Route path="attendance" element={<AttendanceOverviewPage />} />
    {['department-head', 'employees', 'executive-team', 'talent'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
  </Routes>;
}
