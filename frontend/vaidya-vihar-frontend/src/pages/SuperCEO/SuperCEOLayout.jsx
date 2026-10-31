import { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import '../../styles/super-ceo.css';

export const TAB_GROUPS = [
  {
    label: 'Command',
    icon: '◈',
    tabs: [
      { id: 'overview', label: 'Overview', icon: '◎' },
      { id: 'strategy', label: 'Strategy & OKRs', icon: '◈' },
      { id: 'performance', label: 'Performance', icon: '◭' },
    ],
  },
  {
    label: 'People',
    icon: '◆',
    tabs: [
      { id: 'profile', label: 'Super CEO Profile', icon: '◉' },
      { id: 'departments', label: 'Departments', icon: '⬢' },
      { id: 'department-heads', label: 'Department Heads', icon: '⬡' },
      { id: 'talent', label: 'Talent & HR', icon: '◈' },
    ],
  },
  {
    label: 'Business',
    icon: '◐',
    tabs: [
      { id: 'companies', label: 'Companies', icon: '▣' },
      { id: 'customers', label: 'Customers', icon: '◍' },
      { id: 'investors', label: 'Investors', icon: '◈' },
      { id: 'market-intelligence', label: 'Market Intel', icon: '◎' },
    ],
  },
  {
    label: 'Operations',
    icon: '◑',
    tabs: [
      { id: 'finance', label: 'Finance', icon: '₹' },
      { id: 'supply-chain', label: 'Supply Chain', icon: '⛓' },
      { id: 'innovation', label: 'Innovation & R&D', icon: '✦' },
    ],
  },
  {
    label: 'Governance',
    icon: '◒',
    tabs: [
      { id: 'board', label: 'Board & Governance', icon: '◫' },
      { id: 'legal', label: 'Law & Dispute', icon: '⚖' },
      { id: 'risk', label: 'Risk & Compliance', icon: '⚠' },
      { id: 'sustainability', label: 'Sustainability & ESG', icon: '♻' },
      { id: 'audit', label: 'Audit & Security', icon: '🔒' },
    ],
  },
];

const QUICK_ACTIONS = [
  { label: 'Open overview', path: '/super-ceo/overview' },
  { label: 'Review strategy', path: '/super-ceo/strategy' },
  { label: 'Open performance', path: '/super-ceo/performance' },
  { label: 'Inspect companies', path: '/super-ceo/companies' },
  { label: 'Open risk register', path: '/super-ceo/risk' },
  { label: 'Board packet', path: '/super-ceo/board' },
];

export default function SuperCEOLayout({ activeTab = 'overview', children }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const allTabs = useMemo(
    () => TAB_GROUPS.flatMap((group) => group.tabs),
    []
  );

  const activeLabel = useMemo(
    () => allTabs.find((tab) => tab.id === activeTab)?.label || 'Overview',
    [activeTab, allTabs]
  );

  const filteredActions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return QUICK_ACTIONS;
    return QUICK_ACTIONS.filter(
      (action) => action.label.toLowerCase().includes(query) || action.path.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      const modifierPressed = event.metaKey || event.ctrlKey;
      if (modifierPressed && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
      if (event.key === 'Escape') {
        setPaletteOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="super-ceo-shell">
      {paletteOpen && (
        <div className="command-palette-backdrop" onClick={() => setPaletteOpen(false)}>
          <div className="command-palette" onClick={(event) => event.stopPropagation()}>
            <div className="command-palette-header">
              <span>Command palette</span>
              <kbd>Esc</kbd>
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Jump to a section or action..."
              autoFocus
            />
            <div className="command-results">
              {filteredActions.map((action) => (
                <a key={action.label} href={action.path} className="command-result" onClick={() => setPaletteOpen(false)}>
                  <span>{action.label}</span>
                  <small>{action.path}</small>
                </a>
              ))}
              {!filteredActions.length && <div className="command-empty">No quick actions match your search.</div>}
            </div>
          </div>
        </div>
      )}

      <aside className="super-ceo-sidebar">
        <div className="brand-lockup">
          <div className="crest">FS</div>
          <div className="brand-text">
            <div className="brand-name">FoodSrijan Group</div>
            <div className="brand-sub">Executive Command</div>
          </div>
        </div>

        <div className="super-ceo-card">
          <div className="avatar">SS</div>
          <div className="info">
            <div className="name">Sujit Singh</div>
            <div className="title">Super CEO</div>
          </div>
          <div className="status-dot" />
        </div>

        {TAB_GROUPS.map((group) => (
          <nav className="tab-group" key={group.label}>
            <div className="group-label">
              <span className="group-icon">{group.icon}</span>
              {group.label}
            </div>
            {group.tabs.map((tab) => (
              <NavLink
                key={tab.id}
                to={`/super-ceo/${tab.id}`}
                className={({ isActive }) => `tab-item ${isActive || activeTab === tab.id ? 'active' : ''}`}
              >
                <span className="tab-icon">{tab.icon}</span>
                <span className="tab-label">{tab.label}</span>
              </NavLink>
            ))}
          </nav>
        ))}

        <div className="command-hint">
          <kbd>⌘</kbd> <kbd>K</kbd> for quick actions
        </div>
      </aside>

      <main className="super-ceo-main">
        <header className="super-ceo-topbar">
          <div className="breadcrumb">Super CEO · {activeLabel}</div>
          <div className="topbar-actions">
            <button type="button" className="ghost-button" onClick={() => setPaletteOpen(true)}>Search</button>
            <button type="button" className="ghost-button">Alerts</button>
            <button type="button" className="primary-button">Quick actions</button>
          </div>
        </header>

        <div className="super-ceo-content">{children}</div>
      </main>
    </div>
  );
}
