import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import StaffContent from './StaffContent';
import StaffSidebar from './StaffSidebar';
import StaffTopbar from './StaffTopbar';
import { STAFF_TABS } from './tabConfig';

export default function StaffShell({ workspace, refreshWorkspace, onWorkspaceChange }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => STAFF_TABS.filter((item) => (
    !query || `${item.label} ${item.groupLabel}`.toLowerCase().includes(query.toLowerCase())
  )), [query]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if (event.key === 'Escape') {
        setPaletteOpen(false);
        setSidebarOpen(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => { setSidebarOpen(false); }, [location.pathname]);

  return (
    <div className="manager-shell staff-shell">
      <a className="manager-skip" href="#manager-content">Skip to content</a>
      {paletteOpen && (
        <div className="manager-palette-backdrop" role="presentation" onClick={() => setPaletteOpen(false)}>
          <section className="manager-palette" role="dialog" aria-modal="true" aria-label="Staff workspace command palette" onClick={(event) => event.stopPropagation()}>
            <header><span>Staff workspace palette</span><kbd>Esc</kbd></header>
            <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search staff workspace tabs…" aria-label="Search staff workspace" />
            <div>
              {filtered.map((item) => <Link key={item.path} to={item.path} onClick={() => setPaletteOpen(false)}><span>{item.label}</span><small>{item.groupLabel}</small></Link>)}
              {filtered.length === 0 && <p className="manager-palette-empty">No matching tab.</p>}
            </div>
          </section>
        </div>
      )}
      {sidebarOpen && <button type="button" className="manager-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <StaffSidebar profile={workspace.me} outlet={workspace.outlet} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="manager-main">
        <StaffTopbar pathname={location.pathname} outlet={workspace.outlet} alertCount={workspace.alertCount || 0} onOpenSidebar={() => setSidebarOpen(true)} onOpenPalette={() => setPaletteOpen(true)} />
        <StaffContent workspace={workspace} refreshWorkspace={refreshWorkspace} onWorkspaceChange={onWorkspaceChange} />
      </div>
    </div>
  );
}
