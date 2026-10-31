import api from './api';

export function authenticatedSocketUrl(path) {
  const token = window.localStorage.getItem('token');
  if (!token) return null;
  const url = new URL(path, api.defaults.baseURL || window.location.origin);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.searchParams.set('token', token);
  return url.toString();
}
