export default function ErrorState({ message = 'Unable to load this workspace surface.', onRetry }) {
  return <div className="error-state" role="alert"><h3>Something went wrong</h3><p>{message}</p>{onRetry && <button type="button" className="ghost-button compact" onClick={onRetry}>Retry</button>}</div>;
}
