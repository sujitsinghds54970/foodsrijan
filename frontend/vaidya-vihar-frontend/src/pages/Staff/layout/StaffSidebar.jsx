import { useMemo, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { IconBadge } from '../../../components/SuperCEO/icons';
import { useAuth } from '../../../contexts/AuthContext';
import { resolveAssetUrl, superCeoProfileApi } from '../../../services/superCeoProfileApi';
import { STAFF_TAB_GROUPS } from './tabConfig';

export default function StaffSidebar({ profile, outlet, open, onClose }) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  const displayName = useMemo(() => profile.full_name || [profile.first_name, profile.last_name].filter(Boolean).join(' ') || profile.username || 'Staff', [profile]);
  const initials = useMemo(() => displayName.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase(), [displayName]);
  const outletInitials = useMemo(() => (outlet?.name || 'ST').slice(0, 2).toUpperCase(), [outlet?.name]);

  const signOut = async () => {
    if (!window.confirm('Sign out of the staff workspace?')) return;
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
    <aside className={`manager-sidebar staff-sidebar ${open ? 'open' : ''}`} aria-label="Staff self-service workspace">
      <button type="button" className="manager-close" aria-label="Close navigation" onClick={onClose}>×</button>
      <div className="manager-brand">
        <div>{outlet?.logo_url ? <img src={resolveAssetUrl(outlet.logo_url)} alt="" /> : outletInitials}</div>
        <span><strong>{outlet?.name || 'Staff Self-Service'}</strong><small>Workspace</small></span>
      </div>
      <section className="manager-identity staff-identity">
        <div className="manager-avatar">
          {profile.photo_url ? <img src={resolveAssetUrl(profile.photo_url)} alt="" /> : initials}
        </div>
        <div><strong>{displayName}</strong><span>{profile.role_label || 'Staff'}</span></div>
        <i aria-hidden="true" />
      </section>
      <nav aria-label="Staff navigation">
        {STAFF_TAB_GROUPS.map((group) => {
          const GroupIcon = group.icon;
          return (
            <section className={`manager-nav-group tone-${group.tone}`} key={group.id}>
              <header>
                <IconBadge tone={group.tone}><GroupIcon size={15} /></IconBadge>
                <span>{group.label}</span>
              </header>
              <div>
                {group.tabs.map((item) => {
                  const TabIcon = item.icon;
                  return (
                    <NavLink key={item.id} to={item.path} onClick={onClose} className={({ isActive }) => (isActive ? 'active' : '')}>
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
        <NavLink to="/staff/profile/about" onClick={onClose}>My profile</NavLink>
        <button type="button" onClick={signOut} disabled={signingOut}>{signingOut ? 'Signing out…' : 'Sign out'}</button>
      </div>
    </aside>
  );
}
