import { Navigate, Route, Routes } from 'react-router-dom';
import StaffDetailPage from './StaffDetailPage';
import StaffTeamPage from './StaffTeamPage';
import AttendanceBoardPage from './AttendanceBoardPage';
import AttendanceReviewPage from './AttendanceReviewPage';

export default function TeamGroup() {
  return (
    <Routes>
      <Route index element={<Navigate to="/manager/team/staff" replace />} />
      <Route path="staff" element={<StaffTeamPage />} />
      <Route path="staff/:staffId" element={<StaffDetailPage />} />
      <Route path="attendance" element={<AttendanceBoardPage />} />
      <Route path="attendance/suspicious" element={<AttendanceReviewPage />} />
      <Route path="*" element={<Navigate to="/manager/team/staff" replace />} />
    </Routes>
  );
}
