import {
  AuditTrailIcon,
  BriefingIcon,
  CommandIcon,
  CompassIcon,
  CrownIcon,
  EmpireIcon,
  GavelIcon,
  LedgerIcon,
  LedgerRiskIcon,
  OrbitIcon,
  PortfolioIcon,
  PulseIcon,
  ShieldIcon,
  SparkIcon,
  VesselIcon,
} from '../../../components/SuperCEO/icons';

const tab = (id, label, path, icon, description, features, eta = 'Phase 3B') => ({
  id, label, path, icon, description, features, eta,
});

export const COMPANY_CEO_TAB_GROUPS = [
  {
    id: 'command',
    label: 'Command',
    tone: 'gold',
    icon: CrownIcon,
    tabs: [
      tab('profile', 'CEO Profile', '/company-ceo/command/profile', CrownIcon, 'Manage your executive identity, qualifications, preferences, and activity.', ['Executive profile and contact record', 'Qualifications and achievements', 'Security and personal preferences'], 'Available now'),
      tab('overview', 'Overview', '/company-ceo/command/overview', BriefingIcon, 'See the company-wide signals that need executive attention today.', ['Company performance summary', 'Operating network health', 'Recent governance activity']),
      tab('strategy', 'Strategy & OKRs', '/company-ceo/command/strategy', CompassIcon, 'Define long-term priorities and track measurable company outcomes.', ['Strategic objective portfolio', 'Key-result progress', 'Leadership alignment']),
    ],
  },
  {
    id: 'operations',
    label: 'Operations',
    tone: 'teal',
    icon: OrbitIcon,
    tabs: [
      tab('outlets', 'Outlets', '/company-ceo/operations/outlets', PortfolioIcon, 'Manage every outlet, location, and operating unit in your company.', ['Outlet directory with locations', 'Performance comparison', 'Operational KPIs per outlet']),
      tab('outlet-operations', 'Outlets Operations', '/company-ceo/operations/outlet-operations', PulseIcon, 'Monitor the day-to-day health and execution quality of each outlet.', ['Shift and service signals', 'Outlet exception management', 'Daily performance scorecards']),
      tab('production', 'Production & Manufacturing', '/company-ceo/operations/production', CommandIcon, 'Oversee kitchens, factories, production plans, and batch execution.', ['Production planning', 'Batch traceability', 'Capacity and yield analysis']),
      tab('supply-chain', 'Supply Chain & Procurement', '/company-ceo/operations/supply-chain', VesselIcon, 'Direct supplier, purchasing, and logistics performance.', ['Supplier portfolio', 'Purchase order control', 'Inbound logistics visibility']),
      tab('inventory', 'Inventory', '/company-ceo/operations/inventory', LedgerIcon, 'Control stock, movements, expiry exposure, and replenishment.', ['Real-time stock position', 'Expiry and wastage alerts', 'Transfer and reorder planning']),
      tab('quality', 'Quality & Food Safety', '/company-ceo/operations/quality', ShieldIcon, 'Govern food safety, quality audits, and corrective action.', ['FSSAI compliance', 'Quality incident command', 'Audit and CAPA tracking']),
      tab('assets', 'Assets', '/company-ceo/operations/assets', EmpireIcon, 'Manage equipment, vehicles, property, and maintenance exposure.', ['Asset register', 'Maintenance planning', 'Utilization and lifecycle cost']),
    ],
  },
  {
    id: 'commercial',
    label: 'Commercial',
    tone: 'sunset',
    icon: PulseIcon,
    tabs: [
      tab('products', 'Products', '/company-ceo/commercial/products', PortfolioIcon, 'Shape the menu, product portfolio, recipes, and pricing strategy.', ['Product and menu catalogue', 'Recipe economics', 'Pricing and margin controls']),
      tab('sales', 'Sales', '/company-ceo/commercial/sales', LedgerIcon, 'Track orders, revenue, channels, and commercial execution.', ['Revenue performance', 'Channel mix', 'Sales targets and forecasts']),
      tab('customers', 'Customers', '/company-ceo/commercial/customers', EmpireIcon, 'Understand customer segments, behavior, and lifetime value.', ['Customer intelligence', 'Segmentation', 'Retention and value analysis']),
      tab('customer-experience', 'Customer Experience', '/company-ceo/commercial/customer-experience', SparkIcon, 'Monitor satisfaction, feedback, service recovery, and loyalty.', ['NPS and satisfaction', 'Feedback themes', 'Service recovery workflow']),
      tab('marketing', 'Advertising & Marketing', '/company-ceo/commercial/marketing', CompassIcon, 'Direct campaigns, channel investments, brand reach, and ROI.', ['Campaign portfolio', 'Audience and channel performance', 'Marketing ROI']),
    ],
  },
  {
    id: 'people',
    label: 'People',
    tone: 'violet',
    icon: EmpireIcon,
    tabs: [
      tab('attendance', 'Attendance', '/company-ceo/people/attendance', PulseIcon, 'Company-wide outlet attendance and reporting availability.', ['Outlet coverage', 'Attendance reporting status'], 'Available now'),
      tab('department-head', 'Department Head', '/company-ceo/people/department-head', CommandIcon, 'Lead the company through a clear roster of accountable department heads.', ['Leadership roster', 'Department mandates', 'Performance and succession signals']),
      tab('employees', 'Employee & People', '/company-ceo/people/employees', EmpireIcon, 'Manage the workforce, employee services, and organizational health.', ['Workforce directory', 'Attendance and employee services', 'People analytics']),
      tab('executive-team', 'Executive Team', '/company-ceo/people/executive-team', CrownIcon, 'Coordinate the C-suite and the leaders who report directly to the CEO.', ['Executive roster', 'Decision ownership', 'Leadership operating cadence']),
      tab('talent', 'Talent & Culture', '/company-ceo/people/talent', SparkIcon, 'Build hiring strength, retention, engagement, and company culture.', ['Talent pipeline', 'Retention risk', 'Culture and engagement']),
    ],
  },
  {
    id: 'finance-legal',
    label: 'Finance & Legal',
    tone: 'rose',
    icon: LedgerRiskIcon,
    tabs: [
      tab('accounts-finance', 'Accounts & Finance', '/company-ceo/finance-legal/accounts-finance', LedgerIcon, 'Govern profit, cash flow, budgets, and financial discipline.', ['P&L and cash flow', 'Budget control', 'Management reporting']),
      tab('legal-compliances', 'Legal & Compliances', '/company-ceo/finance-legal/legal-compliances', GavelIcon, 'Control contracts, licenses, regulatory obligations, and disputes.', ['Contract register', 'License compliance', 'Dispute and obligation tracking']),
      tab('risk-security-sustainability', 'Risk, Security & Sustainability', '/company-ceo/finance-legal/risk-security-sustainability', ShieldIcon, 'Unify enterprise risk, safety, security, and ESG oversight.', ['Enterprise risk register', 'Security and safety posture', 'Sustainability commitments']),
    ],
  },
  {
    id: 'growth',
    label: 'Growth',
    tone: 'sunset',
    icon: CompassIcon,
    tabs: [
      tab('franchise-management', 'Franchise Management', '/company-ceo/growth/franchise-management', EmpireIcon, 'Scale franchise relationships, standards, and royalty performance.', ['Franchise partner portfolio', 'Royalty and compliance controls', 'Network performance']),
      tab('real-estate-expansion', 'Real Estate & Expansion', '/company-ceo/growth/real-estate-expansion', PortfolioIcon, 'Prioritize sites, leases, development projects, and expansion capital.', ['Site pipeline', 'Lease and project milestones', 'Expansion investment cases']),
      tab('international-business', 'International Business', '/company-ceo/growth/international-business', OrbitIcon, 'Direct overseas markets, entities, partners, and operating exposure.', ['Market-entry portfolio', 'International operating signals', 'Cross-border compliance']),
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    tone: 'violet',
    icon: BriefingIcon,
    tabs: [
      tab('analytics', 'Analytics', '/company-ceo/intelligence/analytics', PulseIcon, 'Explore cross-functional performance and executive decision signals.', ['Executive dashboards', 'Cross-functional trends', 'Predictive alerts']),
      tab('data-bi', 'Data & Business Intelligence', '/company-ceo/intelligence/data-bi', CommandIcon, 'Govern trusted data products, reports, and business intelligence.', ['Certified data products', 'BI report catalogue', 'Data quality and lineage']),
      tab('partnerships', 'Partnerships & Alliances', '/company-ceo/intelligence/partnerships', VesselIcon, 'Manage strategic partners, alliances, and joint ventures.', ['Partner portfolio', 'Alliance value realization', 'Joint-venture governance']),
    ],
  },
  {
    id: 'governance-tech',
    label: 'Governance & Tech',
    tone: 'gold',
    icon: ShieldIcon,
    tabs: [
      tab('technology-it', 'Technology & IT', '/company-ceo/governance-tech/technology-it', CommandIcon, 'Oversee systems, integrations, cyber posture, and technology investments.', ['Application portfolio', 'Integration health', 'Technology risk']),
      tab('board-governance', 'Board & Governance', '/company-ceo/governance-tech/board-governance', GavelIcon, 'Manage board matters, shareholders, resolutions, and governance cadence.', ['Board calendar and packs', 'Resolution tracking', 'Shareholder governance']),
      tab('corporate-communications', 'Corporate Communications', '/company-ceo/governance-tech/corporate-communications', SparkIcon, 'Coordinate public relations, media engagement, and company voice.', ['Media and PR calendar', 'Corporate messaging', 'Reputation monitoring']),
      tab('settings', 'Settings', '/company-ceo/governance-tech/settings', AuditTrailIcon, 'Configure personal workspace behavior and company-level preferences.', ['Workspace preferences', 'Notification controls', 'Connected services'], 'Phase 3A foundation'),
    ],
  },
];

export const COMPANY_CEO_TABS = COMPANY_CEO_TAB_GROUPS.flatMap((group) => (
  group.tabs.map((item) => ({ ...item, groupId: group.id, groupLabel: group.label, tone: group.tone }))
));

export const COMPANY_CEO_DEFAULT_PATH = '/company-ceo/command/overview';

export const findCompanyCeoTab = (pathname) => COMPANY_CEO_TABS.find((item) => (
  pathname === item.path || pathname.startsWith(`${item.path}/`)
));
