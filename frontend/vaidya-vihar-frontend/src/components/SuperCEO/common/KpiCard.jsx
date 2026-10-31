import TrendIndicator from './TrendIndicator';

import { CommandIcon } from '../icons';
import Sparkline from './Sparkline';

export default function KpiCard({ label, value, delta = null, trend = null, tone = 'gold', source = 'Executive signal', children = null, icon: Icon = CommandIcon, sparklinePoints = [] }) {
  return <article className={`metric-card metric-${tone} exec-kpi-card`}><div className="exec-kpi-top"><span className="exec-kpi-icon"><Icon size={18} /></span><div className="metric-label">{label}</div></div><div className="metric-value">{value ?? '—'}</div><div className="exec-kpi-bottom">{delta !== undefined && delta !== null ? <div className="metric-delta"><TrendIndicator value={typeof delta === 'number' ? `${delta > 0 ? '+' : ''}${delta}%` : delta} direction={trend} /></div> : <span className="exec-kpi-source">{source}</span>}{sparklinePoints.length > 0 && <Sparkline values={sparklinePoints} />}</div>{children}</article>;
}
