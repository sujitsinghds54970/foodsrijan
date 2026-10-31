export default function ComingSoonPage({ eyebrow = 'Executive command', title }) {
  return (
    <section className="exec-hero" aria-labelledby="super-ceo-page-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1 id="super-ceo-page-title">{title}</h1>
        <p className="page-subtitle">This workspace surface is being connected to the governed ERP data layer.</p>
      </div>
      <span className="active-tag">Phase A foundation</span>
    </section>
  );
}
