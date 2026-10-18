import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { randomBytes } from 'node:crypto'
import { chromium } from 'playwright'

const directory = await mkdtemp(path.join(tmpdir(), 'aams-e2e-'))
const credentials = { email: 'admin@srmist.edu.in', password: randomBytes(24).toString('hex'), member_password: randomBytes(24).toString('hex') }
await writeFile(path.join(directory, 'credentials.json'), JSON.stringify(credentials), { mode: 0o600 })
const api = spawn(process.env.AAMS_TEST_PYTHON || 'python', ['tests/e2e/backend.py'], {
  env: { ...process.env, PYTHONPATH: path.resolve('fablab-face-attendance'), AAMS_E2E_DIR: directory }, stdio: 'ignore',
})
const web = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--strictPort'], { stdio: 'ignore' })
let browser
const errors = []
async function waitFor(url) {
  const deadline = Date.now() + 30000
  while (Date.now() < deadline) {
    try { if ((await fetch(url)).ok) return } catch { /* server still starting */ }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  throw new Error(`Test server did not become ready: ${url}`)
}
try {
  await Promise.all([waitFor('http://127.0.0.1:8000/health'), waitFor('http://127.0.0.1:3000')])
  browser = await chromium.launch({ headless: true,
    ...(process.env.AAMS_BROWSER_EXECUTABLE ? { executablePath: process.env.AAMS_BROWSER_EXECUTABLE } : {}),
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--enable-unsafe-swiftshader', '--use-fake-device-for-media-stream'],
  })
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, reducedMotion: 'reduce', permissions: ['camera'] })
  const page = await context.newPage()
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('http://127.0.0.1:3000')
  await page.getByLabel('SRMIST email', { exact: true }).fill('outsider@example.org')
  await page.getByLabel('Password', { exact: true }).fill(credentials.password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('alert').filter({ hasText: 'Only @srmist.edu.in' }).waitFor()
  await page.getByLabel('SRMIST email', { exact: true }).fill(credentials.email)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('heading', { name: 'Mission Overview' }).waitFor()
  await page.getByRole('button', { name: 'Members', exact: true }).click()
  await page.getByRole('button', { name: '＋ Add student' }).click()
  const dialog = page.getByRole('dialog', { name: 'Add student' })
  await dialog.getByLabel('Student ID').fill('E2E-STUDENT')
  await dialog.getByLabel('Full name').fill('Showcase Student')
  await dialog.getByLabel('SRMIST email').fill('showcase.student@srmist.edu.in')
  await dialog.getByLabel('Phone').fill('9000000000')
  await dialog.getByLabel('Department').fill('Computer Science')
  await dialog.getByLabel(/^Year/).selectOption('3')
  await dialog.getByLabel('Section').fill('A')
  await dialog.getByRole('button', { name: 'Save student' }).click()
  await page.getByRole('cell', { name: 'E2E-STUDENT', exact: true }).waitFor()
  let row = page.getByRole('row').filter({ hasText: 'E2E-STUDENT' })
  await row.getByRole('button', { name: 'Edit', exact: true }).click()
  await page.getByRole('dialog', { name: 'Edit student' }).getByLabel('Full name').fill('Updated Showcase Student')
  await page.getByRole('button', { name: 'Save student', exact: true }).click()
  await page.getByRole('cell').filter({ hasText: 'Updated Showcase Student' }).waitFor()
  const photo = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAPAAAADwCAIAAACxN37FAAAClElEQVR4nO3SwQkAIBDAMHXyG90lBKEkE/TRPTMLKs7vAHjJ0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJMTQphibF0KQYmhRDk2JoUgxNiqFJuZqeA2DPlVf/AAAAAElFTkSuQmCC', 'base64')
  await row.getByRole('button', { name: 'Enroll face' }).click()
  const enrollment = page.getByRole('dialog', { name: 'Enroll Member' })
  await enrollment.locator('input[type=file]').setInputFiles({ name: 'fixture.png', mimeType: 'image/png', buffer: photo })
  await enrollment.getByRole('checkbox').check()
  await enrollment.getByRole('button', { name: 'Enroll', exact: true }).click()
  await page.getByRole('heading', { name: /Enrolled Updated Showcase Student/ }).waitFor()
  await page.getByRole('button', { name: 'Done', exact: true }).click()
  await row.getByRole('button', { name: 'QR', exact: true }).click()
  await page.getByRole('dialog').getByAltText('QR pass').waitFor()
  await page.getByRole('button', { name: 'Done', exact: true }).click()
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export CSV', exact: true }).click()
  assert.equal((await download).suggestedFilename(), 'aams-students.csv')
  await page.screenshot({ path: path.join(directory, 'students.png'), fullPage: true })
  await page.getByRole('button', { name: 'Live Monitor', exact: true }).click()
  await page.getByRole('heading', { name: 'Live Monitor', exact: true }).waitFor()
  await page.locator('input[type=file]').first().setInputFiles({ name: 'fixture.png', mimeType: 'image/png', buffer: photo })
  await page.getByPlaceholder(/user ID|signed QR/i).fill('E2E-STUDENT')
  await page.getByRole('button', { name: /Process entry/i }).click()
  await page.getByText('Authorized entry - verified face', { exact: false }).waitFor()
  await page.getByRole('button', { name: 'Dashboard', exact: true }).click()
  await page.getByText('Updated Showcase Student', { exact: true }).first().waitFor()
  await page.getByRole('button', { name: 'Check out', exact: true }).click()
  await page.getByRole('button', { name: 'Live Monitor', exact: true }).click()
  const webcam = page.getByRole('region', { name: 'Laptop webcam attendance' })
  await webcam.getByRole('checkbox').check()
  const firstScan = page.waitForResponse((response) => response.url().endsWith('/api/entry/face-only') && response.request().method() === 'POST')
  await webcam.getByRole('button', { name: 'Start webcam attendance' }).click()
  assert.equal((await (await firstScan).json()).recorded, true)
  const repeatScan = await page.waitForResponse((response) => response.url().endsWith('/api/entry/face-only') && response.request().method() === 'POST', { timeout: 20000 })
  assert.equal((await repeatScan.json()).duplicate, true)
  await webcam.getByRole('status').filter({ hasText: 'Already recorded' }).waitFor()
  await webcam.getByRole('button', { name: 'Stop webcam attendance' }).click()
  assert.ok(await webcam.locator('video').evaluate((video) => video.srcObject.getTracks().every((track) => track.readyState === 'ended')), 'Stop must release webcam tracks')
  await webcam.getByRole('button', { name: 'Start webcam attendance' }).click()
  await webcam.getByRole('button', { name: 'Stop webcam attendance' }).waitFor()
  await page.getByRole('button', { name: 'Dashboard', exact: true }).click()
  await page.getByRole('button', { name: 'Check out', exact: true }).click()
  await page.getByRole('button', { name: 'Communicate', exact: true }).click()
  await page.getByRole('heading', { name: 'Communicate', exact: true }).waitFor()
  await page.getByLabel('Message', { exact: true }).fill('AAMS browser validation announcement')
  await page.getByRole('button', { name: 'Send via Telegram' }).click()
  await page.getByRole('status').filter({ hasText: 'Saved in the delivery queue' }).waitFor()
  await page.getByRole('cell', { name: 'ANNOUNCE', exact: true }).first().waitFor()
  await page.screenshot({ path: path.join(directory, 'communicate.png'), fullPage: true })
  for (const [button, title] of [['Dashboard', 'Mission Overview'], ['Live Monitor', 'Live Monitor'], ['Entry Logs', 'Entry Logs'], ['Alerts', 'Security Alerts'], ['Reports', 'Reports']]) {
    await page.getByRole('button', { name: button, exact: true }).click()
    await page.getByRole('heading', { name: title, exact: true }).waitFor()
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(directory, 'mobile-reports.png'), fullPage: true })
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'Mobile page must not overflow viewport')
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await page.getByLabel('SRMIST email', { exact: true }).fill('member@srmist.edu.in')
  await page.getByLabel('Password', { exact: true }).fill(credentials.member_password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.getByRole('button', { name: 'Members', exact: true }).click()
  await page.getByRole('heading', { name: 'Members', exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: '＋ Add student' }).count(), 0)
  assert.equal(await page.getByRole('button', { name: 'Edit', exact: true }).count(), 0)
  assert.deepEqual(errors, [], 'No browser runtime errors')
  console.log('Browser showcase flows: PASS (domain gate, student add/edit, photo enrollment boundary, QR, CSV, notifications queue, seven pages, mobile layout, member role).')
  console.log(`Screenshots: ${directory}`)
} catch (error) {
  const page = browser?.contexts()[0]?.pages()[0]
  if (page) await page.screenshot({ path: path.join(directory, 'failure.png'), fullPage: true }).catch(() => {})
  console.log(`Failure screenshot: ${directory}/failure.png`)
  throw error
} finally {
  await browser?.close()
  api.kill('SIGTERM')
  web.kill('SIGTERM')
}
