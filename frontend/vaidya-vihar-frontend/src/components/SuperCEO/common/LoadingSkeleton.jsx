export default function LoadingSkeleton({ rows = 3 }) { return <div className="loading-skeleton" aria-label="Loading">{Array.from({ length: rows }, (_, index) => <span key={index} />)}</div>; }
