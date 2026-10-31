import {
  AuditTrailIcon, BriefingIcon, CommandIcon, CompassIcon, CrownIcon, EmpireIcon,
  GavelIcon, IconBadge, LedgerIcon, LedgerRiskIcon, LeafIcon, OrbitIcon,
  PortfolioIcon, PulseIcon, ShieldIcon, SparkIcon, VesselIcon,
} from '../../../components/SuperCEO/icons';

const icons = [
  ['Crown', CrownIcon, 'authority'], ['Empire', EmpireIcon, 'sunset'],
  ['Command', CommandIcon, 'violet'], ['Briefing', BriefingIcon, 'gold'],
  ['Portfolio', PortfolioIcon, 'blue'], ['Pulse', PulseIcon, 'teal'],
  ['Orbit', OrbitIcon, 'violet'], ['Shield', ShieldIcon, 'teal'],
  ['Compass', CompassIcon, 'violet'], ['Ledger', LedgerIcon, 'gold'],
  ['Vessel', VesselIcon, 'teal'], ['Spark', SparkIcon, 'sunset'],
  ['Gavel', GavelIcon, 'rose'], ['Ledger risk', LedgerRiskIcon, 'rose'],
  ['Leaf', LeafIcon, 'teal'], ['Audit trail', AuditTrailIcon, 'gold'],
];

export default function IconPreviewPage() {
  return <section className="exec-icon-preview"><p className="eyebrow">System / development preview</p><h2 style={{ fontFamily: 'var(--font-display)' }}>Executive iconography</h2><p className="page-subtitle">Bespoke 24px marks for the Command Gold workspace.</p><div className="exec-icon-preview-grid">{icons.map(([name, Icon, tone]) => <article className="exec-icon-preview-card" key={name}><IconBadge tone={tone} size="large"><Icon gradient /></IconBadge><strong>{name}</strong><small>24px · 1.5px stroke</small></article>)}</div></section>;
}
