import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

const PATHS = ['team', 'attendance', 'training'];

export default function PeopleGroup() {
  return (
    <Routes>
      {PATHS.map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}
    </Routes>
  );
}
