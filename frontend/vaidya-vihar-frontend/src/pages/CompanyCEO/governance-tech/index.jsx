import { Route, Routes } from 'react-router-dom';
import PlaceholderRoute from '../layout/PlaceholderRoute';

export default function GovernanceTechGroup() {
  return <Routes>{['technology-it', 'board-governance', 'corporate-communications', 'settings'].map((path) => <Route key={path} path={path} element={<PlaceholderRoute />} />)}</Routes>;
}
