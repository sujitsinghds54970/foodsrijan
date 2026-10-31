import { useEffect, useRef } from 'react';
import { toast } from 'react-hot-toast';

export default function CredentialsModal({ credentials, onClose }) {
  const doneRef = useRef(null);
  const dialogRef = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    doneRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
      if (event.key !== 'Tab') return;
      const buttons = [...dialogRef.current.querySelectorAll('button:not(:disabled)')];
      const first = buttons[0];
      const last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => { document.removeEventListener('keydown', onKeyDown); previous?.focus?.(); };
  }, [onClose]);

  const copy = async (text, label) => {
    try { await navigator.clipboard.writeText(text); toast.success(`${label} copied`); }
    catch { toast.error('Clipboard unavailable. Select and copy the credentials manually.'); }
  };
  const all = `Login URL: ${credentials.login_url}\nUsername: ${credentials.username}\nPassword: ${credentials.password}`;
  const printPdf = () => {
    const page = window.open('', '_blank');
    if (!page) { toast.error('Allow pop-ups to print or save credentials as PDF.'); return; }
    const doc = page.document;
    doc.title = 'Manager credentials';
    const heading = doc.createElement('h1');
    heading.textContent = 'Manager credentials';
    doc.body.appendChild(heading);
    for (const [label, value] of [['Login URL', credentials.login_url], ['Username', credentials.username], ['Temporary password', credentials.password]]) {
      const row = doc.createElement('p');
      const strong = doc.createElement('strong');
      strong.textContent = `${label}: `;
      row.append(strong, doc.createTextNode(value));
      doc.body.appendChild(row);
    }
    const note = doc.createElement('p');
    note.textContent = 'Store securely. This password is shown only once.';
    doc.body.appendChild(note);
    page.onafterprint = () => page.close();
    page.focus();
    page.print();
  };
  return <div className="outlet-modal-backdrop"><div ref={dialogRef} className="panel outlet-modal" role="dialog" aria-modal="true" aria-labelledby="outlet-credentials-title">
    <h3 id="outlet-credentials-title">Save manager credentials now</h3><p>The password is only shown once. Share it securely; it cannot be retrieved later.</p>
    <dl><div><dt>Login URL</dt><dd>{credentials.login_url}</dd></div><div><dt>Username</dt><dd>{credentials.username}</dd></div><div><dt>Temporary password</dt><dd><code>{credentials.password}</code></dd></div></dl>
    {credentials.note && <p>{credentials.note}</p>}
    <div className="outlet-form-actions">
      <button type="button" className="ghost-button" onClick={() => void copy(credentials.username, 'Username')}>Copy username</button>
      <button type="button" className="ghost-button" onClick={() => void copy(credentials.password, 'Password')}>Copy password</button>
      <button type="button" className="ghost-button" onClick={() => void copy(all, 'Credentials')}>Copy All</button>
      <button type="button" className="ghost-button" onClick={printPdf}>Download PDF</button>
      <button ref={doneRef} type="button" className="primary-button" onClick={onClose}>Done</button>
    </div>
  </div></div>;
}
