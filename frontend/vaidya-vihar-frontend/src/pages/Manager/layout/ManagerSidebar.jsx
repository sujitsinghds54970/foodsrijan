import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { CommandIcon, IconBadge } from '../../../components/SuperCEO/icons';
import { useAuth } from '../../../contexts/AuthContext';
import { resolveAssetUrl, superCeoProfileApi } from '../../../services/superCeoProfileApi';
import { MANAGER_TAB_GROUPS } from './tabConfig';

export default function ManagerSidebar({ manager, outlet, open, onClose }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  const outletName = outlet?.name || 'No outlet assigned';
  const outletInitials = (outlet?.name || 'NA').slice(0, 2).toUpperCase();
  const initials = (manager.full_name || 'Manager')
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  const signOut = async () => {
    if (!window.confirm('Sign out of the outlet manager workspace?')) return;
    setSigningOut(true);
    try {
      await superCeoProfileApi.logout();
      logout();
      navigate('/login', { replace: true });
    } catch {
      toast.error('Unable to sign out securely. Please try again.');
      setSigningOut(false);
    }
  };

  return (
    <aside
      className={`manager-sidebar ${open ? 'open' : ''}`}
      aria-label="Outlet manager workspace"
    >
      <button type="button" className="manager-close" aria-label="Close navigation" onClick={onClose}>×</button>
      <div className="manager-brand">
        <div>{outlet?.logo_url ? <img src={resolveAssetUrl(outlet.logo_url)} alt="" /> : outletInitials}</div>
        <span><strong>{outletName}</strong><small>Outlet Command</small></span>
      </div>
      <section className="manager-identity">
        <div className="manager-avatar">
          {manager.photo_url ? <img src={resolveAssetUrl(manager.photo_url)} alt="" /> : initials}
        </div>
        <div><strong>{manager.full_name}</strong><span>{manager.role_label}</span></div>
        <i aria-hidden="true" />
      </section>
      <nav aria-label="Outlet manager navigation">
        {MANAGER_TAB_GROUPS.map((group) => {
          const GroupIcon = group.icon;
          return (
            <section className={`manager-nav-group tone-${group.tone}`} data-group-id={group.id} key={group.id}>
              <header>
                <IconBadge tone={group.tone}><GroupIcon size={15} /></IconBadge>
                <span>{group.label}</span>
              </header>
              <div>
                {group.tabs.map((item) => {
                  const TabIcon = item.icon;
                  return (
                    <NavLink
                      key={item.id}
                      to={item.path}
                      onClick={onClose}
                      className={({ isActive }) => (isActive ? 'active' : '')}
                    >
                      <TabIcon size={16} /><span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            </section>
          );
        })}
      </nav>
      <div className="manager-sidebar-footer">
        <NavLink to="/manager/profile/about" onClick={onClose}><CommandIcon size={17} /> My profile</NavLink>
        <button type="button" onClick={signOut} disabled={signingOut}>
          {signingOut ? 'Signing out…' : 'Sign out'}
        </button>
      </div>
    </aside>
  );
}
