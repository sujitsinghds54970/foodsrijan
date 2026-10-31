import {
  AuditTrailIcon,
  BriefingIcon,
  CommandIcon,
  LedgerIcon,
  OrbitIcon,
  PortfolioIcon,
  PulseIcon,
  ShieldIcon,
} from '../../../components/SuperCEO/icons';

const tab = (id, label, path, icon, title, description, features, eta = 'Available now') => ({
  id,
  label,
  path,
  icon,
  title,
  description,
  features,
  eta,
});

export const STAFF_TAB_GROUPS = [
  {
    id: 'my-work',
    label: 'My Work',
    tone: 'gold',
    icon: CommandIcon,
    tabs: [
      tab('dashboard', 'Dashboard', '/staff/dashboard', BriefingIcon, 'My Dashboard', 'Shift, task, request, and service signals for the current day.', ['Today’s shift signal', 'Tasks and quick actions', 'Attendance and payslip highlights'], 'Available now'),
      tab('tasks', 'My Tasks', '/staff/tasks', PulseIcon, 'My Tasks', 'Assigned work, due dates, and completion tracking.', ['Task list', 'Priorities and deadlines', 'Completion status'], 'Available now'),
      tab('orders', 'Orders', '/staff/orders', OrbitIcon, 'Orders', 'Role-based order views will be introduced in a later phase.', ['Outlet role views', 'Workstation cues', 'Task-linked order actions'], 'Phase 5'),
    ],
  },
  {
    id: 'me',
    label: 'Me',
    tone: 'teal',
    icon: PortfolioIcon,
    tabs: [
      tab('profile', 'My Profile', '/staff/profile/about', PortfolioIcon, 'My Profile', 'Your self-service profile, qualifications, work profile, and settings.', ['Profile hero', 'Contact and qualification tabs', 'Security and activity sections'], 'Available now'),
      tab('attendance', 'Attendance', '/staff/attendance', PulseIcon, 'Attendance', 'Attendance history and shift logging for the current outlet assignment.', ['Monthly records', 'Clock status', 'Coverage highlights'], 'Available now'),
      tab('training', 'Training', '/staff/training', BriefingIcon, 'Training', 'Training records and learning workflows are planned for a later phase.', ['Learning plans', 'Course completions', 'Readiness tracking'], 'Phase 5'),
      tab('performance', 'Performance', '/staff/performance', AuditTrailIcon, 'Performance', 'Performance coaching, feedback, and scorecards arrive in a later phase.', ['Performance scorecards', 'Coaching notes', 'Recognition highlights'], 'Phase 5'),
    ],
  },
  {
    id: 'money',
    label: 'Money',
    tone: 'violet',
    icon: LedgerIcon,
    tabs: [
      tab('payslips', 'Payslips', '/staff/payslips', LedgerIcon, 'Payslips', 'Payslip history and salary visibility when payroll data is published.', ['Published payslips', 'Salary snapshot', 'Payroll empties when not yet available'], 'Available now'),
      tab('requests', 'Requests', '/staff/requests', CommandIcon, 'Requests', 'Submit leave or advance requests and track their own approval status.', ['Leave requests', 'Advance requests', 'Request history'], 'Available now'),
    ],
  },
  {
    id: 'system',
    label: 'System',
    tone: 'rose',
    icon: ShieldIcon,
    tabs: [
      tab('security', 'Security', '/staff/security', ShieldIcon, 'Security', 'Password and session controls for the staff account.', ['Password change', 'Session visibility when available', 'Account safety guidance'], 'Available now'),
      tab('activity', 'Activity', '/staff/activity', AuditTrailIcon, 'Activity', 'Personal audit trail of profile, request, and login activity.', ['Audit feed', 'Timestamped actions', 'System-originated events'], 'Available now'),
    ],
  },
];

export const STAFF_TABS = STAFF_TAB_GROUPS.flatMap((group) => (
  group.tabs.map((item) => ({ ...item, groupId: group.id, groupLabel: group.label, tone: group.tone }))
));

export const STAFF_DEFAULT_PATH = '/staff/dashboard';

export const findStaffTab = (pathname) => STAFF_TABS.find((item) => pathname === item.path || pathname.startsWith(`${item.path}/`));
