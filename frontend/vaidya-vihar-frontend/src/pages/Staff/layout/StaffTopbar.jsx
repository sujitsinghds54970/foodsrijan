import { CommandIcon, OrbitIcon, PulseIcon } from '../../../components/SuperCEO/icons';
import { resolveAssetUrl } from '../../../services/superCeoProfileApi';
import { findStaffTab } from './tabConfig';

export default function StaffTopbar({ pathname, outlet, alertCount = 0, onOpenSidebar, onOpenPalette }) {
  const active = findStaffTab(pathname);
  return (
    <header className="manager-topbar staff-topbar">
      <button type="button" className="manager-menu-button" aria-label="Open navigation" onClick={onOpenSidebar}>
        <CommandIcon size={19} />
      </button>
      <div className="manager-breadcrumb">
        <span>Staff <b>·</b> {active?.groupLabel || 'Workspace'} <b>·</b> {active?.label || 'Dashboard'}</span>
        <strong>{active?.label || 'Staff Dashboard'}</strong>
      </div>
      <div className="manager-topbar-actions">
        <button type="button" aria-label="Search workspace" onClick={onOpenPalette}>
          <CommandIcon size={17} /><span>Search</span><kbd>⌘K</kbd>
        </button>
        <button type="button" aria-label={alertCount ? `Alerts, ${alertCount} open` : 'Alerts, none open'}>
          <PulseIcon size={18} />
          {alertCount > 0 && <i className="manager-alert-dot" aria-hidden="true">{alertCount}</i>}
        </button>
        <div className="manager-outlet-chip">
          {outlet?.logo_url ? <img src={resolveAssetUrl(outlet.logo_url)} alt="" /> : <OrbitIcon size={17} />}
          <span>{outlet?.name || 'Staff workspace'}</span>
        </div>
      </div>
    </header>
  );
}
