import { IconBadge } from '../../../components/SuperCEO/icons';
import OrbitalMotif from '../../../components/SuperCEO/common/OrbitalMotif';

export default function ComingSoonPlaceholder({ icon: Icon, tone, title, description, features, eta }) {
  return (
    <section className={`company-ceo-placeholder tone-${tone}`}>
      <OrbitalMotif />
      <div className="company-ceo-placeholder-copy">
        <IconBadge tone={tone} size="large"><Icon size={28} /></IconBadge>
        <p>Executive module foundation</p>
        <h1>{title}</h1>
        <span>{description}</span>
        <ul>{features.map((feature) => <li key={feature}><i aria-hidden="true">✓</i>{feature}</li>)}</ul>
        <small>{eta === 'Available now' ? eta : `This tab will be built in ${eta}`}</small>
      </div>
    </section>
  );
}
