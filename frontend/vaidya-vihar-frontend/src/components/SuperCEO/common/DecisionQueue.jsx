export default function DecisionQueue({ items = [], max_items, empty_message = 'No decisions are waiting.' }) {
  const visibleItems = max_items ? items.slice(0, max_items) : items;
  if (!visibleItems.length) return <p className="mini-meta">{empty_message}</p>;
  return <div className="mini-list">{visibleItems.map((item) => <div className="mini-item" key={item.id || item.title}><div><div className="mini-title">{item.title}</div><div className="mini-meta">{item.owner}</div></div>{item.priority && <span className={`priority-badge ${item.priority.toLowerCase()}`}>{item.priority}</span>}</div>)}</div>;
}
