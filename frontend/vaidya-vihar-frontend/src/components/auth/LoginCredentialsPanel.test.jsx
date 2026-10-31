import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import api from '../../services/api';
import LoginCredentialsPanel from './LoginCredentialsPanel';

jest.mock('../../services/api', () => ({ get: jest.fn(), patch: jest.fn() }));
jest.mock('react-hot-toast', () => ({ success: jest.fn(), error: jest.fn() }));
jest.mock('../../services/companyManagementApi', () => ({
  apiErrorMessage: (_error, fallback) => fallback,
}));

const endpoint = '/api/manager/staff/7/credentials';
const login = { username: 'staff_login', force_password_change: false, is_active: true };
let root;
let container;

beforeEach(async () => {
  jest.useFakeTimers();
  jest.clearAllMocks();
  window.IS_REACT_ACT_ENVIRONMENT = true;
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  api.get.mockResolvedValue({ data: { data: { login } } });
  api.patch.mockResolvedValue({ data: { data: {
    login: { ...login, username: 'new_login', force_password_change: true },
    credentials: { username: 'new_login', password: 'OneTimePassword9!' },
  } } });
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => { root.render(<LoginCredentialsPanel endpoint={endpoint} />); });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  jest.useRealTimers();
  jest.restoreAllMocks();
});

const button = (text) => Array.from(container.querySelectorAll('button')).find((node) => node.textContent === text);
const click = async (text) => { await act(async () => { Simulate.click(button(text)); }); };
const change = async (selector, value) => {
  await act(async () => { Simulate.change(container.querySelector(selector), { target: { value } }); });
};
const submit = async () => { await act(async () => { Simulate.submit(container.querySelector('form')); }); };

test('shows current username but never pretends to reveal an existing password', () => {
  expect(api.get).toHaveBeenCalledWith(endpoint);
  expect(container.textContent).toContain('staff_login');
  expect(container.textContent).toContain('Protected - not retrievable');
  expect(container.querySelector('input[type="password"]')).toBeNull();
});

test('refreshes current login details within five seconds', async () => {
  api.get.mockResolvedValue({ data: { data: { login: { ...login, username: 'changed_elsewhere' } } } });
  await act(async () => { jest.advanceTimersByTime(5000); });
  expect(container.textContent).toContain('changed_elsewhere');
});

test('generates credentials, displays once and removes them after dismissal', async () => {
  await click('Edit login credentials');
  await change('input', 'new_login');
  await change('select', 'generate');
  await submit();
  expect(api.patch).toHaveBeenCalledWith(endpoint, { username: 'new_login', reset_password: true });
  expect(container.textContent).toContain('OneTimePassword9!');
  await click('I have saved these credentials');
  expect(container.textContent).not.toContain('OneTimePassword9!');
  await click('Refresh');
  expect(container.textContent).not.toContain('OneTimePassword9!');
  expect(localStorage.getItem('password')).toBeNull();
});

test('sets a custom password using matching confirmation', async () => {
  await click('Edit login credentials');
  await change('select', 'custom');
  const inputs = container.querySelectorAll('input[type="password"]');
  await act(async () => {
    Simulate.change(inputs[0], { target: { value: 'CustomLoginPass9!' } });
    Simulate.change(inputs[1], { target: { value: 'CustomLoginPass9!' } });
  });
  await submit();
  expect(api.patch).toHaveBeenCalledWith(endpoint, {
    username: 'staff_login', reset_password: false,
    password: 'CustomLoginPass9!', password_confirm: 'CustomLoginPass9!',
  });
  expect(container.querySelector('input[type="password"]')).toBeNull();
});

test('username-only edit does not send a password', async () => {
  await click('Edit login credentials');
  await change('input', 'new_login');
  await submit();
  expect(api.patch).toHaveBeenCalledWith(endpoint, { username: 'new_login', reset_password: false });
});

test('mismatched passwords are rejected before sending a request', async () => {
  await click('Edit login credentials');
  await change('select', 'custom');
  await change('input[type="password"]', 'CustomLoginPass9!');
  await submit();
  expect(api.patch).not.toHaveBeenCalled();
  expect(container.querySelector('[role="alert"]').textContent).toBe('Passwords do not match.');
});

test('cancelling confirmation does not update credentials', async () => {
  window.confirm.mockReturnValue(false);
  await click('Edit login credentials');
  await submit();
  expect(api.patch).not.toHaveBeenCalled();
});

test('API failure is visible and clears password inputs', async () => {
  api.patch.mockRejectedValue(new Error('Server unavailable'));
  await click('Edit login credentials');
  await change('select', 'custom');
  const inputs = container.querySelectorAll('input[type="password"]');
  await act(async () => {
    Simulate.change(inputs[0], { target: { value: 'CustomLoginPass9!' } });
    Simulate.change(inputs[1], { target: { value: 'CustomLoginPass9!' } });
  });
  await submit();
  expect(container.querySelector('[role="alert"]').textContent).toBe('Login credentials could not be updated.');
  expect(Array.from(container.querySelectorAll('input[type="password"]')).every((node) => node.value === '')).toBe(true);
});
