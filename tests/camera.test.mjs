import assert from 'node:assert/strict'
import { log } from 'node:console'
import { configureCamera, CAMERA_SETTLE_MS, nextScanDelay } from '../src/utils/camera.js'

const applied = []
await configureCamera({ getVideoTracks: () => [{
  getCapabilities: () => ({ focusMode: ['continuous', 'manual'], exposureMode: ['continuous'] }),
  applyConstraints: async (value) => applied.push(value),
}] })
assert.deepEqual(applied, [{ advanced: [{ focusMode: 'continuous', exposureMode: 'continuous' }] }])
await configureCamera({ getVideoTracks: () => [{ getCapabilities: () => ({}) }] })
await configureCamera({ getVideoTracks: () => [{ getCapabilities: () => { throw new Error('unsupported') } }] })
await configureCamera({ getVideoTracks: () => [{
  getCapabilities: () => ({ focusMode: ['continuous'] }),
  applyConstraints: async () => { throw new Error('camera rejected constraint') },
}] })
assert.equal(CAMERA_SETTLE_MS, 1500)
for (const tag of ['quality', 'noface', 'liveness', 'ambiguous']) assert.equal(nextScanDelay({ tag }), 2000)
for (const tag of ['authorized', 'unknown', 'unpaid', undefined]) assert.equal(nextScanDelay({ tag }), 10000)
log('Camera controls, unsupported hardware and bounded retry timing: PASS')
