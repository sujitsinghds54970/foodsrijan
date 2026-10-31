import { NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { CommandIcon, IconBadge } from '../../../components/SuperCEO/icons';
import { useAuth } from '../../../contexts/AuthContext';
import { resolveAssetUrl, superCeoProfileApi } from '../../../services/superCeoProfileApi';
import { COMPANY_CEO_TAB_GROUPS } from './tabConfig';

export default function CompanyCEOSidebar({ company, open, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Company CEO';
  const initials = fullName.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  const profilePhoto = user?.profilePhoto || user?.profile_photo || user?.photo_url || user?.photo;

  const signOut = async () => {
    if (!window.confirm('Sign out of the Company CEO workspace?')) return;
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
    <aside className={`company-ceo-sidebar ${open ? 'open' : ''}`} aria-label="Company CEO workspace">
      <button type="button" className="company-ceo-close" aria-label="Close navigation" onClick={onClose}>×</button>
      <div className="company-ceo-brand">
        <div>{company.logo_url ? <img src={resolveAssetUrl(company.logo_url)} alt="" /> : company.name.slice(0, 2).toUpperCase()}</div>
        <span><strong>{company.name}</strong><small>Executive Command</small></span>
      </div>
      <section className="company-ceo-identity">
        <div className="company-ceo-avatar">{profilePhoto ? <img src={resolveAssetUrl(profilePhoto)} alt="" /> : initials}</div>
        <div><strong>{fullName}</strong><span>Company CEO</span></div><i />
      </section>
      <nav aria-label="Company CEO navigation">
        {COMPANY_CEO_TAB_GROUPS.map((group) => {
          const GroupIcon = group.icon;
          return (
            <section className={`company-ceo-nav-group tone-${group.tone}`} data-group-id={group.id} key={group.id}>
              <header><IconBadge tone={group.tone}><GroupIcon size={15} /></IconBadge><span>{group.label}</span></header>
              <div>
                {group.tabs.map((item) => {
                  const TabIcon = item.icon;
                  return (
                    <NavLink key={item.id} to={item.path} onClick={onClose} className={({ isActive }) => isActive ? 'active' : ''}>
                      <TabIcon size={16} /><span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            </section>
          );
        })}
      </nav>
      <div className="company-ceo-sidebar-footer">
        <NavLink to="/company-ceo/governance-tech/settings" onClick={onClose}><CommandIcon size={17} /> Settings</NavLink>
        <button type="button" onClick={signOut} disabled={signingOut}>{signingOut ? 'Signing out…' : 'Sign out'}</button>
      </div>
    </aside>
  );
}
