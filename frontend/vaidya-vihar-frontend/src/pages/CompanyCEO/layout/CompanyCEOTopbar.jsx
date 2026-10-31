import { CommandIcon, CrownIcon, PulseIcon } from '../../../components/SuperCEO/icons';
import { resolveAssetUrl } from '../../../services/superCeoProfileApi';
import { findCompanyCeoTab } from './tabConfig';

export default function CompanyCEOTopbar({ pathname, company, onOpenSidebar, onOpenPalette }) {
  const active = findCompanyCeoTab(pathname);
  return (
    <header className="company-ceo-topbar">
      <button type="button" className="company-ceo-menu-button" aria-label="Open navigation" onClick={onOpenSidebar}><CommandIcon size={19} /></button>
      <div className="company-ceo-breadcrumb">
        <span>Company CEO <b>·</b> {active?.groupLabel || 'Command'} <b>·</b> {active?.label || 'Overview'}</span>
        <strong>{active?.label || 'Executive Overview'}</strong>
      </div>
      <div className="company-ceo-topbar-actions">
        <button type="button" aria-label="Search workspace" onClick={onOpenPalette}><CommandIcon size={17} /><span>Search</span><kbd>⌘K</kbd></button>
        <button type="button" aria-label="Notifications"><PulseIcon size={18} /></button>
        <div className="company-ceo-company-chip">
          {company.logo_url ? <img src={resolveAssetUrl(company.logo_url)} alt="" /> : <CrownIcon size={17} />}
          <span>{company.name}</span>
        </div>
      </div>
    </header>
  );
}
