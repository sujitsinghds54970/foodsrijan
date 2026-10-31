export default function TrendIndicator({ value, direction = 'flat' }) {
  const icon = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→';
  return <span className={`trend-indicator ${direction}`}>{icon} {value}</span>;
}
