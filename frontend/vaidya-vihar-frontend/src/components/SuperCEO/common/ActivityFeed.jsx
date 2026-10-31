export default function ActivityFeed({ items = [], filter_types = [], onFilterTypesChange, empty_message = 'No recent activity.' }) {
  const types = [...new Set(items.map((item) => item.type).filter(Boolean))];
  const visibleItems = filter_types.length ? items.filter((item) => filter_types.includes(item.type)) : items;
  return <div className="feed-list">
    {onFilterTypesChange && types.length > 1 && <div className="feed-filters">{types.map((type) => <button className={`ghost-button compact ${filter_types.includes(type) ? 'active' : ''}`} key={type} onClick={() => onFilterTypesChange(filter_types.includes(type) ? filter_types.filter((selected) => selected !== type) : [...filter_types, type])}>{type}</button>)}</div>}
    {visibleItems.length ? visibleItems.map((item) => <div className="feed-item" key={item.id || `${item.time}-${item.title}`}><span className="feed-time">{item.time}</span><div><div className="feed-title">{item.title}</div><div className="feed-detail">{item.detail}</div></div></div>) : <p className="mini-meta">{empty_message}</p>}
  </div>;
}
