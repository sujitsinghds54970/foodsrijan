import { NavLink, useNavigate } from 'react-router-dom';
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import { TAB_GROUPS } from './tabConfig';
import OrbitalMotif from '../../../components/SuperCEO/common/OrbitalMotif';
import { AuditTrailIcon, BriefingIcon, CommandIcon, CompassIcon, CrownIcon, EmpireIcon, GavelIcon, IconBadge, LedgerIcon, LedgerRiskIcon, LeafIcon, OrbitIcon, PortfolioIcon, PulseIcon, ShieldIcon, SparkIcon, VesselIcon } from '../../../components/SuperCEO/icons';
import { superCeoProfileApi } from '../../../services/superCeoProfileApi';
import { parentCompanyApi, resolveAssetUrl } from '../../../services/superCeoProfileApi';
import useExecutiveEventStream from '../../../hooks/useExecutiveEventStream';
import toast from 'react-hot-toast';

const iconMap = {
  overview: BriefingIcon, strategy: CompassIcon, performance: PulseIcon, profile: CrownIcon,
  departments: EmpireIcon, 'department-heads': CommandIcon, talent: PulseIcon, 'parent-company': EmpireIcon, companies: PortfolioIcon,
  customers: CommandIcon, investors: LedgerIcon, 'market-intelligence': OrbitIcon, finance: LedgerIcon,
  'supply-chain': VesselIcon, innovation: SparkIcon, board: GavelIcon, legal: GavelIcon,
  risk: LedgerRiskIcon, sustainability: LeafIcon, audit: ShieldIcon, 'software-ui': CommandIcon,
};
const groupTones = { Command: 'gold', People: 'violet', Business: 'teal', Operations: 'sunset', Governance: 'rose', System: 'gold' };

export default function SuperCEOSidebar({ open = false, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [confirmSignOut, setConfirmSignOut] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [parentBrand, setParentBrand] = useState(null);
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Executive';
  const initials = fullName.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  const role = user?.is_super_ceo || user?.is_super_admin ? 'Super CEO' : user?.role || 'Executive';
  const loadParentBrand = useCallback(async () => {
    try {
      const result = await parentCompanyApi.get();
      setParentBrand(result.published);
    } catch {
      // The workspace remains usable with the built-in FoodSrijan lockup.
    }
  }, []);

  useEffect(() => { void loadParentBrand(); }, [loadParentBrand]);
  useExecutiveEventStream(['parent_company.published'], loadParentBrand);

  const handleSignOut = async () => {
    setSigningOut(true);
    try {
      await superCeoProfileApi.logout();
      logout();
      navigate('/login', { replace: true });
    } catch {
      toast.error('Unable to sign out securely. Please try again.');
      setSigningOut(false);
      return;
    }
    setSigningOut(false);
    setConfirmSignOut(false);
  };

  return (
    <aside className={`super-ceo-sidebar ${open ? 'is-open' : ''}`} aria-label="Super CEO navigation">
      <button type="button" className="mobile-sidebar-close" onClick={onClose} aria-label="Close navigation">×</button>
      <div className="brand-lockup">
        <div
          className="crest"
          style={{
            background: `linear-gradient(135deg, ${parentBrand?.primary_color || '#D6A84F'}, ${parentBrand?.secondary_color || '#8C78F5'})`,
          }}
        >
          {parentBrand?.logo_url
            ? <img src={resolveAssetUrl(parentBrand.logo_url)} alt={`${parentBrand.name || 'FoodSrijan Group'} logo`} />
            : 'FS'}
        </div>
        <div className="brand-text"><div className="brand-name">{parentBrand?.name || 'FoodSrijan Group'}</div><div className="brand-sub">Executive Command</div></div>
      </div>
      <div className="super-ceo-card">
        <OrbitalMotif compact />
        <div className="avatar" aria-hidden="true">{initials}</div>
        <div className="info"><div className="name">{fullName}</div><div className="title">{role}</div></div>
        <div className="status-dot" aria-label="Online" />
      </div>
      {TAB_GROUPS.map((group) => (
        <nav className="tab-group" key={group.label} aria-label={`${group.label} navigation`}>
          <div className={`group-label group-${groupTones[group.label] || 'gold'}`}><span className="group-icon" aria-hidden="true">{group.icon}</span>{group.label}</div>
          {group.tabs.map((tab) => (
            <NavLink key={tab.id} to={tab.path} onClick={onClose} className={({ isActive }) => `tab-item ${isActive ? 'active' : ''}`} end={tab.id === 'overview'}>
              <IconBadge tone={groupTones[group.label] || 'gold'} size="medium"><span className="tab-icon" aria-hidden="true">{(() => { const Icon = iconMap[tab.id] || AuditTrailIcon; return <Icon size={18} />; })()}</span></IconBadge><span className="tab-label">{tab.label}</span>
            </NavLink>
          ))}
        </nav>
      ))}
      <div className="super-ceo-sidebar-footer">
        <div className="command-hint"><kbd>⌘</kbd> <kbd>K</kbd> for quick actions</div>
        <button type="button" className="super-ceo-signout-button" onClick={() => setConfirmSignOut(true)}>
          <ShieldIcon size={16} /> Sign out
        </button>
      </div>
      {confirmSignOut && (
        <div className="profile-dialog-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !signingOut) setConfirmSignOut(false);
        }}>
          <section
            className="profile-confirm-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="signout-title"
            aria-describedby="signout-description"
            tabIndex={-1}
            onKeyDown={(event) => {
              if (event.key === 'Escape' && !signingOut) setConfirmSignOut(false);
            }}
          >
            <div className="profile-dialog-icon"><ShieldIcon size={22} /></div>
            <h2 id="signout-title">Sign out of Executive Command?</h2>
            <p id="signout-description">Your session will be securely ended on this device.</p>
            <div className="profile-dialog-actions">
              <button type="button" className="exec-button exec-button-secondary" autoFocus onClick={() => setConfirmSignOut(false)} disabled={signingOut}>Stay signed in</button>
              <button type="button" className="exec-button exec-button-danger" onClick={handleSignOut} disabled={signingOut}>
                {signingOut ? 'Signing out…' : 'Sign out'}
              </button>
            </div>
          </section>
        </div>
      )}
    </aside>
  );
}
