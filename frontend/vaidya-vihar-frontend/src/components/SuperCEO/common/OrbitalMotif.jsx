export default function OrbitalMotif({ compact = false, dots = 3 }) {
  const positions = [
    [50, 10], [84, 34], [78, 78], [24, 84], [12, 38], [50, 50],
  ];
  return (
    <svg className={`exec-orbital-motif ${compact ? 'exec-orbital-motif-compact' : ''}`} viewBox="0 0 240 240" aria-hidden="true">
      <g className="exec-orbital-rings">
        <circle cx="120" cy="120" r="92" />
        <circle cx="120" cy="120" r="66" />
        <circle cx="120" cy="120" r="38" />
      </g>
      {!compact && positions.slice(0, dots).map(([cx, cy], index) => <circle className="exec-orbital-dot" cx={`${cx}%`} cy={`${cy}%`} r={index === 0 ? 3 : 2} key={`${cx}-${cy}`} />)}
      <circle className="exec-orbital-core" cx="120" cy="120" r="6" />
    </svg>
  );
}
