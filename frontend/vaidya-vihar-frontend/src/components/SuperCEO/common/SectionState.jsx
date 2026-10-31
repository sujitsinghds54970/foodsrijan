import EmptyState from './EmptyState';
import ErrorState from './ErrorState';
import LoadingSkeleton from './LoadingSkeleton';

export default function SectionState({ section, children, unavailableChildren, emptyTitle, emptyDescription, unavailableTitle, unavailableDescription, onRetry }) {
  if (!section || section.state === 'loading') return <LoadingSkeleton />;
  if (section.state === 'error') return <ErrorState message={section.errorMessage || 'This section could not be loaded. Other executive data may still be available.'} onRetry={onRetry} />;
  if (section.state === 'unavailable') {
    return <><EmptyState title={unavailableTitle || 'Data unavailable'} description={unavailableDescription || 'This metric is not configured for the selected scope.'} />{unavailableChildren}</>;
  }
  if (section.state === 'empty') return <EmptyState title={emptyTitle} description={emptyDescription} />;
  return children;
}
