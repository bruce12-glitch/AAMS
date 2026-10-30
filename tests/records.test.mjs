import assert from 'node:assert/strict'
import { log } from 'node:console'
import { matchScore, sourceLabel, paymentLabel, readableText, formatEventTime, historyCount } from '../src/utils/records.js'

assert.equal(matchScore({ similarity: 0, comparison_performed: false }), 'Not compared')
assert.equal(matchScore({ similarity: .93 }), 'Not recorded')
assert.equal(matchScore({ similarity: .9365, comparison_performed: true }), '0.936')
assert.equal(matchScore({ similarity: .9, comparison_performed: 1, event_source: 'sample' }), 'Demo value')
assert.equal(paymentLabel(null), 'Not evaluated')
assert.equal(sourceLabel('legacy'), 'Older · source unrecorded')
assert.equal(readableText('A â€” B'), 'A — B')
assert.equal(formatEventTime('invalid'), 'Time not recorded')
assert.match(formatEventTime('2026-10-27T00:00:00Z'), /IST$/)
assert.equal(historyCount({ legacy: 7, sample: 5, webcam: 3 }), 12)
log('Operational record formatting: PASS')
