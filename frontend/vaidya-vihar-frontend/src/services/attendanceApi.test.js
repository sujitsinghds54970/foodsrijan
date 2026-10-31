import api from './api';
import { attendanceApi, localDate, monthBounds } from './attendanceApi';

jest.mock('./api', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

const get = api.get;
const post = api.post;

beforeEach(() => {
  jest.clearAllMocks();
  get.mockResolvedValue({ data: { data: { records: [] } } });
  post.mockResolvedValue({ data: { data: { id: 1 } } });
});

test('month bounds include leap day without changing the local date', () => {
  expect(monthBounds('2024-02')).toEqual({ start: '2024-02-01', end: '2024-02-29' });
  expect(localDate(new Date(2024, 1, 29))).toBe('2024-02-29');
});

test('staff, outlet, company and portfolio reads use scoped endpoints', async () => {
  const dates = { start: '2024-02-01', end: '2024-02-29' };
  await attendanceApi.mine(dates);
  await attendanceApi.managerRecords(dates);
  await attendanceApi.companyRecords({ ...dates, outlet_id: 9 });
  await attendanceApi.portfolioRecords({ ...dates, company_id: 3 });
  expect(get.mock.calls).toEqual([
    ['/api/staff/attendance', { params: dates }],
    ['/api/manager/attendance', { params: dates }],
    ['/api/company-ceo/attendance', { params: { ...dates, outlet_id: 9 } }],
    ['/api/super-ceo/attendance', { params: { ...dates, company_id: 3 } }],
  ]);
});

test('review decision and note are sent to the matching request', async () => {
  await attendanceApi.reviewCorrection(17, 'approved', 'Confirmed times');
  await attendanceApi.reviewLeave(8, 'rejected', 'Coverage required');
  expect(post.mock.calls).toEqual([
    ['/api/manager/attendance/corrections/17/review', { decision: 'approved', note: 'Confirmed times' }],
    ['/api/manager/attendance/leaves/8/review', { decision: 'rejected', note: 'Coverage required' }],
  ]);
});
