export default function Toast({ message, tone = 'info' }) { return <div className={`super-ceo-toast ${tone}`} role="status">{message}</div>; }
