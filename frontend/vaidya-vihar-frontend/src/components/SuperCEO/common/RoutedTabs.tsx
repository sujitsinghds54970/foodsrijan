import { KeyboardEvent, ReactNode, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export interface RoutedTab {
  id: string;
  label: string;
  icon?: ReactNode;
}

interface RoutedTabsProps {
  basePath: string;
  activeTabId: string;
  tabs: RoutedTab[];
  idPrefix: string;
  ariaLabel?: string;
  onSelect?: () => void;
}

export default function RoutedTabs({ basePath, activeTabId, tabs, idPrefix, ariaLabel = 'Profile sections', onSelect }: RoutedTabsProps) {
  const navigate = useNavigate();
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const selectTab = (tabId: string, replace = false) => {
    navigate(`${basePath}/${tabId}`, { replace });
    onSelect?.();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
    let nextIndex: number;
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      nextIndex = (currentIndex + 1) % tabs.length;
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    } else if (event.key === 'Home') {
      nextIndex = 0;
    } else if (event.key === 'End') {
      nextIndex = tabs.length - 1;
    } else {
      return;
    }
    event.preventDefault();
    tabRefs.current[nextIndex]?.focus();
    selectTab(tabs[nextIndex].id);
  };

  return (
    <div className="exec-routed-tabs" role="tablist" aria-label={ariaLabel}>
      {tabs.map((tab, index) => {
        const selected = tab.id === activeTabId;
        return (
          <button
            key={tab.id}
            ref={(element) => { tabRefs.current[index] = element; }}
            id={`${idPrefix}-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`${idPrefix}-tabpanel`}
            tabIndex={selected ? 0 : -1}
            className={`exec-routed-tab${selected ? ' is-active' : ''}`}
            onClick={() => selectTab(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {tab.icon && <span className="exec-routed-tab-icon" aria-hidden="true">{tab.icon}</span>}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
