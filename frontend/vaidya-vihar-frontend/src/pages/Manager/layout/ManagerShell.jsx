import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import ManagerContent from './ManagerContent';
import ManagerSidebar from './ManagerSidebar';
import ManagerTopbar from './ManagerTopbar';
import { MANAGER_TABS } from './tabConfig';

export default function ManagerShell({ workspace, refreshWorkspace, onWorkspaceChange }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => MANAGER_TABS.filter((item) => (
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
    <div className="manager-shell">
      <a className="manager-skip" href="#manager-content">Skip to content</a>
      {paletteOpen && (
        <div className="manager-palette-backdrop" role="presentation" onClick={() => setPaletteOpen(false)}>
          <section
            className="manager-palette"
            role="dialog"
            aria-modal="true"
            aria-label="Outlet manager command palette"
            onClick={(event) => event.stopPropagation()}
          >
            <header><span>Outlet command palette</span><kbd>Esc</kbd></header>
            <input
              autoFocus
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search outlet workspace tabs…"
              aria-label="Search outlet manager workspace"
            />
            <div>
              {filtered.map((item) => (
                <Link key={item.path} to={item.path} onClick={() => setPaletteOpen(false)}>
                  <span>{item.label}</span><small>{item.groupLabel}</small>
                </Link>
              ))}
              {filtered.length === 0 && <p className="manager-palette-empty">No matching tab.</p>}
            </div>
          </section>
        </div>
      )}
      {sidebarOpen && (
        <button
          type="button"
          className="manager-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <ManagerSidebar
        manager={workspace.manager}
        outlet={workspace.outlet}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="manager-main">
        <ManagerTopbar
          pathname={location.pathname}
          outlet={workspace.outlet}
          alertCount={workspace.alerts?.length || 0}
          onOpenSidebar={() => setSidebarOpen(true)}
          onOpenPalette={() => setPaletteOpen(true)}
        />
        <ManagerContent workspace={workspace} refreshWorkspace={refreshWorkspace} onWorkspaceChange={onWorkspaceChange} />
      </div>
    </div>
  );
}
