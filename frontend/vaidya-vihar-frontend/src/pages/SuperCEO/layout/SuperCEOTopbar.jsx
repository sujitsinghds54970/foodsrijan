import { useLocation } from 'react-router-dom';
import { useMemo } from 'react';
import { TAB_GROUPS } from './tabConfig';
import { BriefingIcon, CrownIcon, PulseIcon, CompassIcon, EmpireIcon, PortfolioIcon, OrbitIcon, LedgerIcon, VesselIcon, SparkIcon, GavelIcon, ShieldIcon, CommandIcon } from '../../../components/SuperCEO/icons';

const pageIcons = { Overview: BriefingIcon, 'Strategy & OKRs': CompassIcon, Performance: PulseIcon, Companies: PortfolioIcon, 'Parent Company': EmpireIcon, Finance: LedgerIcon, 'Supply Chain': VesselIcon, 'Innovation & R&D': SparkIcon, 'Board & Governance': GavelIcon, 'Law & Dispute': GavelIcon, 'Risk & Compliance': ShieldIcon, 'Super CEO Profile': CrownIcon, Departments: EmpireIcon, 'Market Intel': OrbitIcon };

export default function SuperCEOTopbar({ onOpenPalette, onOpenSidebar }) {
  const location = useLocation();
  const label = useMemo(() => TAB_GROUPS.flatMap((group) => group.tabs).find((tab) => location.pathname.startsWith(tab.path))?.label || 'Overview', [location.pathname]);
  const PageIcon = pageIcons[label] || CommandIcon;
  return (
    <header className="super-ceo-topbar">
      <div className="topbar-title"><button type="button" className="mobile-menu-button" onClick={onOpenSidebar} aria-label="Open navigation"><CommandIcon size={18} /></button><div className="breadcrumb"><PageIcon size={16} /> Super CEO · Executive Command</div><strong>{label}</strong></div>
      <div className="topbar-actions">
        <button type="button" className="ghost-button topbar-search" onClick={onOpenPalette}><CommandIcon size={16} /> Search <kbd>⌘K</kbd></button>
        <button type="button" className="ghost-button alert-button" aria-label="Open alerts"><PulseIcon size={17} /><span className="alert-badge">0</span></button>
        <button type="button" className="primary-button quick-action"><CrownIcon size={16} /> Quick actions</button>
      </div>
    </header>
  );
}
