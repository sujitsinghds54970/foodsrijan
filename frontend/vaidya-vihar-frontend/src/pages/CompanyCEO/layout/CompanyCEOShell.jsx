import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import CompanyCEOContent from './CompanyCEOContent';
import CompanyCEOSidebar from './CompanyCEOSidebar';
import CompanyCEOTopbar from './CompanyCEOTopbar';
import { COMPANY_CEO_TABS } from './tabConfig';

export default function CompanyCEOShell({ workspace }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [query, setQuery] = useState('');
  const filtered = useMemo(() => COMPANY_CEO_TABS.filter((item) => (
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

  return (
    <div className="company-ceo-shell">
      <a className="company-ceo-skip" href="#company-ceo-content">Skip to content</a>
      {paletteOpen && (
        <div className="company-ceo-palette-backdrop" role="presentation" onClick={() => setPaletteOpen(false)}>
          <section className="company-ceo-palette" role="dialog" aria-modal="true" aria-label="Company CEO command palette" onClick={(event) => event.stopPropagation()}>
            <header><span>Executive command palette</span><kbd>Esc</kbd></header>
            <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search all workspace tabs…" aria-label="Search company CEO workspace" />
            <div>{filtered.map((item) => <Link key={item.path} to={item.path} onClick={() => setPaletteOpen(false)}><span>{item.label}</span><small>{item.groupLabel}</small></Link>)}</div>
          </section>
        </div>
      )}
      {sidebarOpen && <button type="button" className="company-ceo-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <CompanyCEOSidebar company={workspace.company} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="company-ceo-main">
        <CompanyCEOTopbar pathname={location.pathname} company={workspace.company} onOpenSidebar={() => setSidebarOpen(true)} onOpenPalette={() => setPaletteOpen(true)} />
        <CompanyCEOContent workspace={workspace} />
      </div>
    </div>
  );
}
