export default function Sparkline({ values = [] }) {
  const numericValues = values.map((value) => Number(value?.value ?? value)).filter(Number.isFinite);
  const maximum = Math.max(...numericValues, 1);
  return <span className="sparkline" aria-label={`Trend with ${numericValues.length} points`}>
    {numericValues.map((value, index) => <span key={`${value}-${index}`} style={{ height: `${Math.max(10, (value / maximum) * 100)}%` }} />)}
  </span>;
}
