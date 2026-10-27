import { alertTitle, sourceLabel, formatEventTime, readableText } from '../utils/records'

/** Shared, factual review rows for the full page and dashboard summary. */
export default function AlertList({ items, compact = false, onReview, busyId }) {
  return (
    <ul className={`event-list ${compact ? 'compact' : ''}`} aria-label="Security review records">
      {items.map((item) => (
        <li key={item.id} className="event-row">
          <div className="event-row-main">
            <div className="event-row-heading">
              <strong>{alertTitle(item.alert_type)}</strong>
              <span className={`review-state ${item.acked ? 'reviewed' : ''}`}>{item.acked ? 'Reviewed' : 'Needs review'}</span>
            </div>
            <p className="event-reason">{readableText(item.decision_reason || item.message) || 'No additional details were recorded.'}</p>
            {(item.recognized_id || item.claimed_id) && <p className="event-meta">
              {item.recognized_id ? `Matched: ${item.recognized_name || item.recognized_id}` : 'Not identified'}
              {item.claimed_id && item.claimed_id !== item.recognized_id ? ` · Pass: ${item.claimed_name || item.claimed_id}` : ''}
            </p>}
            <p className="event-meta">{formatEventTime(item.created_at)} · {sourceLabel(item.event_source)}
              {item.entry_log_id ? ` · Attempt #${item.entry_log_id}` : ' · No linked capture record'}</p>
            {!compact && <p className="event-meta">Priority: {item.severity || 'Not recorded'} · Evidence: {item.image_path ? 'image stored' : 'no image stored'}</p>}
          </div>
          {!compact && onReview && !item.acked && <button className="btn sm ghost" type="button" disabled={busyId === item.id}
            onClick={() => onReview(item.id)}>{busyId === item.id ? 'Saving…' : 'Mark reviewed'}</button>}
        </li>
      ))}
    </ul>
  )
}
