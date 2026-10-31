import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { apiErrorMessage } from '../../services/companyManagementApi';
import '../../styles/login-credentials.css';

export default function LoginCredentialsPanel({ endpoint, onUpdated }) {
  const [login, setLogin] = useState(null);
  const [username, setUsername] = useState('');
  const [editing, setEditing] = useState(false);
  const [mode, setMode] = useState('keep');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [issued, setIssued] = useState(null);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const requestVersion = useRef(0);
  const saving = useRef(false);

  const refresh = useCallback(async () => {
    if (saving.current) return;
    const version = requestVersion.current;
    try {
      const response = await api.get(endpoint);
      if (version !== requestVersion.current) return;
      setLogin(response.data.data.login);
      setLoadError('');
    } catch (requestError) {
      if (version === requestVersion.current) setLoadError(apiErrorMessage(requestError, 'Login details could not be loaded.'));
    }
  }, [endpoint]);

  useEffect(() => {
    setIssued(null);
    setLogin(null);
    setEditing(false);
    setPassword('');
    setConfirmation('');
    void refresh();
    const timer = setInterval(() => { if (!document.hidden) void refresh(); }, 5000);
    const onFocus = () => void refresh();
    window.addEventListener('focus', onFocus);
    return () => { requestVersion.current += 1; clearInterval(timer); window.removeEventListener('focus', onFocus); };
  }, [refresh]);

  const cancel = () => {
    setEditing(false); setPassword(''); setConfirmation(''); setMode('keep');
  };
  const save = async (event) => {
    event.preventDefault();
    if (busy) return;
    if (mode === 'custom' && password !== confirmation) {
      setError('Passwords do not match.'); return;
    }
    if (!window.confirm('Apply these login changes now? Existing sessions will be signed out. A password reset requires a new password at next sign-in.')) return;
    saving.current = true;
    requestVersion.current += 1;
    setBusy(true); setError(''); setIssued(null);
    try {
      const payload = { username: username.trim(), reset_password: mode === 'generate' };
      if (mode === 'custom') { payload.password = password; payload.password_confirm = confirmation; }
      const response = await api.patch(endpoint, payload);
      setLogin(response.data.data.login);
      setIssued(response.data.data.credentials || null);
      cancel();
      toast.success('Login credentials updated.');
      if (onUpdated) onUpdated(response.data.data.login);
    } catch (requestError) {
      setPassword(''); setConfirmation('');
      setError(apiErrorMessage(requestError, 'Login credentials could not be updated.'));
    } finally { saving.current = false; setBusy(false); }
  };
  const copy = async () => {
    try { await navigator.clipboard.writeText(issued.password); toast.success('New password copied.'); }
    catch { toast.error('Clipboard unavailable. Select and copy the password manually.'); }
  };

  return <section className="login-credentials-panel" aria-label="Login credentials">
    <h3>Login credentials</h3>
    <p>Passwords are securely hashed and cannot be viewed. Issue a new password when access needs to change.</p>
    {error && <p role="alert">{error}</p>}
    {loadError && <p role="alert">{loadError}</p>}
    {!login && !loadError && <p role="status">Loading login details...</p>}
    {login && !editing && <>
      <dl><div><dt>Current username</dt><dd><code>{login.username}</code></dd></div>
        <div><dt>Password</dt><dd>Protected - not retrievable</dd></div>
        <div><dt>Change at next sign-in</dt><dd>{login.force_password_change ? 'Required' : 'Not required'}</dd></div></dl>
      <div className="login-credentials-actions"><button type="button" onClick={() => { setUsername(login.username); setMode('keep'); setEditing(true); setIssued(null); }}>Edit login credentials</button><button type="button" onClick={() => void refresh()}>Refresh</button></div>
      <small>Current login details refresh automatically every 5 seconds.</small>
    </>}
    {login && editing && <form onSubmit={save}>
      <fieldset disabled={busy}>
        <label>Username<input autoComplete="off" required minLength={4} maxLength={30} pattern="[A-Za-z0-9_]+" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
        <label>Password action<select value={mode} onChange={(event) => { setMode(event.target.value); setPassword(''); setConfirmation(''); }}>
          <option value="keep">Keep existing password</option><option value="generate">Generate a secure temporary password</option><option value="custom">Set a temporary password</option>
        </select></label>
        {mode === 'custom' && <>
          <label>New temporary password<input type="password" autoComplete="new-password" required minLength={12} maxLength={72} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <label>Confirm new password<input type="password" autoComplete="new-password" required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label>
          <small>At least 12 characters with uppercase, lowercase, number and symbol; maximum 72 UTF-8 bytes.</small>
        </>}
        <div className="login-credentials-actions"><button type="submit">{busy ? 'Saving...' : 'Apply login changes'}</button><button type="button" onClick={cancel}>Cancel</button></div>
      </fieldset>
    </form>}
    {issued && <div className="login-credentials-issued" role="status">
      <strong>New temporary credentials - save now</strong><p>This password is displayed only for this operation. Dismissing or leaving this page removes it.</p>
      <dl><div><dt>Username</dt><dd><code>{issued.username}</code></dd></div><div><dt>New password</dt><dd><code>{issued.password}</code></dd></div></dl>
      <div className="login-credentials-actions"><button type="button" onClick={() => void copy()}>Copy new password</button><button type="button" onClick={() => setIssued(null)}>I have saved these credentials</button></div>
    </div>}
  </section>;
}
