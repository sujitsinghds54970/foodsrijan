import { Navigate, Route, Routes } from 'react-router-dom';
import ComingSoonPlaceholder from '../Manager/layout/ComingSoonPlaceholder';
import { AuditTrailIcon, BriefingIcon, OrbitIcon } from '../../components/SuperCEO/icons';
import DashboardPage from './my-work/DashboardPage';
import MyTasksPage from './my-work/MyTasksPage';
import AttendancePage from './me/AttendancePage';
import StaffProfilePage from './me/StaffProfilePage';
import PayslipsPage from './money/PayslipsPage';
import RequestsPage from './money/RequestsPage';
import SecurityPage from './system/SecurityPage';
import ActivityPage from './system/ActivityPage';

const OrdersPage = () => <ComingSoonPlaceholder icon={OrbitIcon} tone="sunset" title="Orders" description="Role-based order views for staff arrive in a later phase." features={['Workstation queues', 'Role-specific order actions', 'Shift-linked order visibility']} eta="Phase 5" />;
const TrainingPage = () => <ComingSoonPlaceholder icon={BriefingIcon} tone="teal" title="Training" description="Training plans, learning records, and course completions are planned for a later phase." features={['Course catalogue', 'Completion history', 'Readiness sign-off']} eta="Phase 5" />;
const PerformancePage = () => <ComingSoonPlaceholder icon={AuditTrailIcon} tone="gold" title="Performance" description="Performance scorecards and coaching notes are intentionally deferred to a later phase." features={['Recognition highlights', 'Coaching log', 'Performance scorecards']} eta="Phase 5" />;
export default function StaffRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="/staff/dashboard" replace />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="tasks" element={<MyTasksPage />} />
      <Route path="orders" element={<OrdersPage />} />
      <Route path="profile" element={<Navigate to="/staff/profile/about" replace />} />
      <Route path="profile/:profileTab" element={<StaffProfilePage />} />
      <Route path="attendance" element={<AttendancePage />} />
      <Route path="attendance/clock" element={<AttendancePage />} />
      <Route path="attendance/history" element={<AttendancePage />} />
      <Route path="training" element={<TrainingPage />} />
      <Route path="performance" element={<PerformancePage />} />
      <Route path="payslips" element={<PayslipsPage />} />
      <Route path="requests" element={<RequestsPage />} />
      <Route path="security" element={<SecurityPage />} />
      <Route path="activity" element={<ActivityPage />} />
      <Route path="*" element={<Navigate to="/staff/dashboard" replace />} />
    </Routes>
  );
}
