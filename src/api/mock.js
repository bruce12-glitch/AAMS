/**
 * Sample data for the console's offline / demo mode.
 *
 * IMPORTANT — this file is compiled into the public static build. It must
 * never contain real personal data.
 *
 * It previously carried realistic-looking student records (real-format
 * register numbers, full names, Indian mobile numbers). Once the console is
 * deployed publicly and real enrolment begins, sample data that *looks*
 * genuine is a liability: it is indistinguishable from a data leak, and it
 * would sit alongside actual student records in the same UI. Every
 * identifier below is therefore obviously synthetic.
 *
 * Replace these placeholders with neutral values only. Real data belongs in
 * the database behind the API, never in the frontend bundle.
 */

const nowIso = () => new Date().toISOString()

/** Sample register IDs — clearly not real register numbers. */
const SAMPLE_IDS = ['SAMPLE-0001', 'SAMPLE-0002', 'SAMPLE-0003', 'SAMPLE-0004', 'SAMPLE-0005']

export const MOCK_STATS = {
  total_entries: 42,
  inside_count: 7,
  alert_count: 3,
  member_count: 28
}

export const MOCK_ACTIVITY = [
  { id: 1, event_time: nowIso(), claimed_id: SAMPLE_IDS[0], recognized_id: SAMPLE_IDS[0], similarity: 0.81, decision: 'GRANTED', tag: 'authorized', payment_status: 'active' },
  { id: 2, event_time: nowIso(), claimed_id: SAMPLE_IDS[1], recognized_id: null, similarity: 0.22, decision: 'DENIED', tag: 'proxy', payment_status: 'expired' },
  { id: 3, event_time: nowIso(), claimed_id: SAMPLE_IDS[2], recognized_id: SAMPLE_IDS[2], similarity: 0.74, decision: 'GRANTED', tag: 'authorized', payment_status: 'active' },
  { id: 4, event_time: nowIso(), claimed_id: null, recognized_id: null, similarity: 0.11, decision: 'DENIED', tag: 'unknown', payment_status: 'inactive' },
  { id: 5, event_time: nowIso(), claimed_id: SAMPLE_IDS[3], recognized_id: SAMPLE_IDS[3], similarity: 0.68, decision: 'DENIED', tag: 'unpaid', payment_status: 'expired' }
]

export const MOCK_ALERTS = [
  { id: 1, alert_type: 'PROXY_ALERT', severity: 'high', message: 'A pass token was presented by a different face than the one on record.', created_at: nowIso(), acked: 0 },
  { id: 2, alert_type: 'UNPAID_ENTRY_ATTEMPT', severity: 'medium', message: 'Entry attempted on a membership whose payment has expired.', created_at: nowIso(), acked: 0 },
  { id: 3, alert_type: 'UNKNOWN_PERSON', severity: 'high', message: 'Unrecognized face captured at entrance.', created_at: nowIso(), acked: 0 },
  { id: 4, alert_type: 'AUTHORIZED_ENTRY', severity: 'low', message: 'Authorized entry recorded at the main entrance.', created_at: nowIso(), acked: 1 }
]

export const MOCK_USERS = [
  { user_id: SAMPLE_IDS[0], name: 'Sample Member A', phone: '+00 00000 00001', payment_status: 'active', payment_expiry: '2026-12-01', active: 1, consent_given: 1 },
  { user_id: SAMPLE_IDS[1], name: 'Sample Member B', phone: '+00 00000 00002', payment_status: 'expired', payment_expiry: '2026-08-12', active: 1, consent_given: 1 },
  { user_id: SAMPLE_IDS[2], name: 'Sample Member C', phone: '+00 00000 00003', payment_status: 'active', payment_expiry: '2026-11-15', active: 1, consent_given: 1 },
  { user_id: SAMPLE_IDS[3], name: 'Sample Member D', phone: '+00 00000 00004', payment_status: 'pending', payment_expiry: null, active: 1, consent_given: 0 },
  { user_id: SAMPLE_IDS[4], name: 'Sample Member E', phone: '+00 00000 00005', payment_status: 'active', payment_expiry: '2027-01-20', active: 1, consent_given: 1 }
]

export const MOCK_OCCUPANTS = [
  { user_id: SAMPLE_IDS[0], entry_time: nowIso(), status: 'inside', duration_minutes: 164 },
  { user_id: SAMPLE_IDS[2], entry_time: nowIso(), status: 'inside', duration_minutes: 96 },
  { user_id: SAMPLE_IDS[4], entry_time: nowIso(), status: 'inside', duration_minutes: 41 }
]

/**
 * `camera.source: 0` is the lab's physical USB camera index. It is correct
 * for the on-premises deployment and meaningless in the static build — this
 * block describes the *expected* state so the UI renders its standby view.
 */
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
