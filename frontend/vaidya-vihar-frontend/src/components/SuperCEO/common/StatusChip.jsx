export default function StatusChip({ label, tone = 'stable' }) { return <span className={`status-chip ${tone}`}>{label}</span>; }
