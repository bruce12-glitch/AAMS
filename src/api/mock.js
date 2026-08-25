const nowIso = () => new Date().toISOString()

export const MOCK_STATS = {
  total_entries: 42,
  inside_count: 7,
  alert_count: 3,
  member_count: 28
}

export const MOCK_ACTIVITY = [
  { id: 1, event_time: nowIso(), claimed_id: 'RA2111003010123', recognized_id: 'RA2111003010123', similarity: 0.81, decision: 'GRANTED', tag: 'authorized', payment_status: 'active' },
  { id: 2, event_time: nowIso(), claimed_id: 'RA2111003010456', recognized_id: null, similarity: 0.22, decision: 'DENIED', tag: 'proxy', payment_status: 'expired' },
  { id: 3, event_time: nowIso(), claimed_id: 'RA2111003010789', recognized_id: 'RA2111003010789', similarity: 0.74, decision: 'GRANTED', tag: 'authorized', payment_status: 'active' },
  { id: 4, event_time: nowIso(), claimed_id: null, recognized_id: null, similarity: 0.11, decision: 'DENIED', tag: 'unknown', payment_status: 'inactive' },
  { id: 5, event_time: nowIso(), claimed_id: 'RA2111003010321', recognized_id: 'RA2111003010321', similarity: 0.68, decision: 'DENIED', tag: 'unpaid', payment_status: 'expired' }
]

export const MOCK_ALERTS = [
  { id: 1, alert_type: 'PROXY_ALERT', severity: 'high', message: "Someone tried using Rahul Kumar's ID at the entrance.", created_at: nowIso(), acked: 0 },
  { id: 2, alert_type: 'UNPAID_ENTRY_ATTEMPT', severity: 'medium', message: 'Arun S — payment expired 12 Aug 2026.', created_at: nowIso(), acked: 0 },
  { id: 3, alert_type: 'UNKNOWN_PERSON', severity: 'high', message: 'Unrecognized face captured at entrance.', created_at: nowIso(), acked: 0 },
  { id: 4, alert_type: 'AUTHORIZED_ENTRY', severity: 'low', message: 'Priya M entered at 10:32 AM.', created_at: nowIso(), acked: 1 }
]

export const MOCK_USERS = [
  { user_id: 'RA2111003010123', name: 'Rahul Kumar', phone: '+91 98400 11223', payment_status: 'active', payment_expiry: '2026-12-01', active: 1, consent_given: 1 },
  { user_id: 'RA2111003010456', name: 'Arun S', phone: '+91 98400 44556', payment_status: 'expired', payment_expiry: '2026-08-12', active: 1, consent_given: 1 },
  { user_id: 'RA2111003010789', name: 'Priya M', phone: '+91 98400 77889', payment_status: 'active', payment_expiry: '2026-11-15', active: 1, consent_given: 1 },
  { user_id: 'RA2111003010321', name: 'Vikram Singh', phone: '+91 98400 33445', payment_status: 'pending', payment_expiry: null, active: 1, consent_given: 0 },
  { user_id: 'RA2111003010654', name: 'Sneha R', phone: '+91 98400 66778', payment_status: 'active', payment_expiry: '2027-01-20', active: 1, consent_given: 1 }
]

export const MOCK_OCCUPANTS = [
  { user_id: 'RA2111003010123', entry_time: nowIso(), status: 'inside', duration_minutes: 164 },
  { user_id: 'RA2111003010789', entry_time: nowIso(), status: 'inside', duration_minutes: 96 },
  { user_id: 'RA2111003010654', entry_time: nowIso(), status: 'inside', duration_minutes: 41 }
]

export const MOCK_LIVE = {
  camera: { status: 'offline', source: 0, fps: 0 },
  current_event: null,
  steps: ['IDLE']
}

export const MOCK_DAILY_REPORT = {
  date: new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }),
  total_entries: 42,
  unique_users: 28,
  authorized: 39,
  proxy_attempts: 1,
  unpaid_attempts: 2,
  unknown_attempts: 0
}
