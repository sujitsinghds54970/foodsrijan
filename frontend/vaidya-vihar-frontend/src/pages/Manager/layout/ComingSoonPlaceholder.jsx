import { IconBadge } from '../../../components/SuperCEO/icons';
import OrbitalMotif from '../../../components/SuperCEO/common/OrbitalMotif';

export default function ComingSoonPlaceholder({ icon: Icon, tone, title, description, features = [], eta }) {
  return (
    <section className={`manager-placeholder tone-${tone}`} aria-labelledby="manager-placeholder-title">
      <OrbitalMotif />
      <div className="manager-placeholder-copy">
        <IconBadge tone={tone} size="large"><Icon size={28} /></IconBadge>
        <p>Outlet manager foundation</p>
        <h1 id="manager-placeholder-title">{title}</h1>
        <span>{description}</span>
        <ul>{features.map((feature) => <li key={feature}><i aria-hidden="true">✓</i>{feature}</li>)}</ul>
        <small>{eta === 'Available now' ? eta : `This tab will be built in ${eta}`}</small>
      </div>
    </section>
  );
}
