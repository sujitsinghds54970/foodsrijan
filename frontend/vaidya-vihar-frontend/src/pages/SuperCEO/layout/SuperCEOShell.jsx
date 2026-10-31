import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import SuperCEOSidebar from './SuperCEOSidebar';
import SuperCEOTopbar from './SuperCEOTopbar';
import SuperCEOContent from './SuperCEOContent';
import { TAB_GROUPS } from './tabConfig';

export default function SuperCEOShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [query, setQuery] = useState('');
  const actions = useMemo(() => TAB_GROUPS.flatMap((group) => group.tabs), []);
  const filtered = actions.filter((action) => !query || action.label.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen(true);
      }
      if (event.key === 'Escape') setPaletteOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <div className="super-ceo-shell">
      {paletteOpen && (
        <div className="command-palette-backdrop" role="presentation" onClick={() => setPaletteOpen(false)}>
          <section className="command-palette" role="dialog" aria-modal="true" aria-label="Command palette" onClick={(event) => event.stopPropagation()}>
            <div className="command-palette-header"><span>Command palette</span><kbd>Esc</kbd></div>
            <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Jump to a section or action…" aria-label="Search workspace actions" />
            <div className="command-results">
              {filtered.map((action) => <Link key={action.id} to={action.path} className="command-result" onClick={() => setPaletteOpen(false)}><span>{action.label}</span><small>{action.path}</small></Link>)}
              {!filtered.length && <div className="command-empty">No actions match your search.</div>}
            </div>
          </section>
        </div>
      )}
      <a className="skip-link" href="#super-ceo-content">Skip to content</a>
      {sidebarOpen && <button type="button" className="mobile-sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close navigation" />}
      <SuperCEOSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="super-ceo-main"><SuperCEOTopbar onOpenPalette={() => setPaletteOpen(true)} onOpenSidebar={() => setSidebarOpen(true)} /><SuperCEOContent /></div>
    </div>
  );
}
