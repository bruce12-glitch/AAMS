# Publishing the Console to GitHub Pages

A **static build of the React console** with sample data. Gives you a public URL
for a report, viva, README, or the repo's About panel — with **no backend, no
database, and no biometric data** in the deployment.

This is the safe way to have a public link. The lab deployment (see
`aams-deploy/DOCKER_DEPLOY.md`) is what actually runs access control; this is the
part that is safe to show anyone.

---

## What changes vs. the repository

| File | Change |
|---|---|
| `vite.config.js` | Adds `VITE_TARGET` handling. `base: './'` for Pages so assets resolve under `/<repo-name>/`; the dev proxy is untouched. |
| `src/hooks/useBackendStatus.js` | **New.** Single shared connection signal for the shell. |
| `src/App.jsx` | Passes `isLive` to `Sidebar` and `TopBar`. |
| `src/components/TopBar.jsx` | Shows a "Demo mode" banner when there's no backend. |
| `src/styles/global.css` | Styles for that banner, using existing design tokens. |
| `.github/workflows/deploy-pages.yml` | Builds and publishes to Pages on push to `main`. |

### Bug this fixes

`Sidebar` accepts an `isLive` prop to drive its status pill:

```jsx
<span className={`conn-dot ${isLive ? 'live' : 'demo'}`} />
{isLive ? 'API Connected' : 'Demo Data'}
```

But `App.jsx` called `<Sidebar active={page} onSelect={setPage} />`, never
passing `isLive`. Since each page owns its own `usePolling` instance, there was
no shared connection state either. The prop was therefore always `undefined`, so
**the pill read "Demo Data" even when the API was genuinely connected** — on
your lab deployment, not just here. `useBackendStatus` fixes that by probing
`/health` once on mount and every 15 s, and feeding one boolean to the shell.

`/health` is cheap and side-effect free by design (`app/main.py` documents it as
orchestrator-safe), so this probe never touches the CV engine.

---

## One-time setup

1. Push these files to `main` (see the note at the bottom — this needs a token).
2. In the repository: **Settings → Pages → Build and deployment → Source**,
   choose **GitHub Actions**. Do not pick "Deploy from a branch".
3. The workflow runs on push, or manually from the **Actions** tab.

Your URL will be:

```
https://bruce12-glitch.github.io/AAMS/
```

Put that in the repo's About panel → Website.

---

## How the demo mode works

`vite build` with `VITE_TARGET=pages` sets `base: './'` and makes
`useBackendStatus` skip probing entirely — so the static build generates no
failed `/api/*` requests in the browser console. The sidebar pill reads
"Demo Data" and the topbar shows a banner, both truthfully.

Every page also has its own inline note when offline, e.g. `Logs.jsx`:

```jsx
{!isLive && (
  <!-- "Backend offline — sample feed shown." -->
)}
```

Data comes from `src/api/mock.js` — 42 entries, 7 occupants inside, 3 alerts,
28 members, records for Rahul Kumar, Arun S, Priya M, Vikram Singh, Sneha R.

> **Note on the sample data.** The mock records look like real student names and
> ID numbers. If this repo is public, consider whether you want realistic-looking
> personal identifiers on a public page. Swapping them for obvious placeholders
> (`Student A`, `RA0000000001`) avoids any chance of someone reading them as real
> people's data.

---

## Deep links

Pages is a static file server, so `/AAMS/alerts` would 404 on a direct hit or a
refresh. The workflow copies `dist/index.html` to `dist/404.html`, which Pages
serves for unknown paths — the SPA then routes correctly. This is why the
`Add SPA fallback` step exists; don't remove it.

---

## Verifying the published build locally

Before pushing, reproduce exactly what Pages will serve:

```bash
npm ci
VITE_TARGET=pages npm run build
cp dist/index.html dist/404.html
npx serve dist        # or: python -m http.server 8000 -d dist
```

Open it. You should see the console, the "Demo mode" banner, and the sidebar
pill reading "Demo Data". If assets 404, `base` is wrong — check that
`VITE_TARGET=pages` was actually set in the build environment.

---

## What this deliberately does not do

- **No API.** The published site cannot reach your lab backend, and shouldn't.
  Pointing a public static page at a face-matching endpoint would expose it.
- **No camera, no enrollment, no database.** `LiveMonitor` reads
  `status: 'offline'` from `MOCK_LIVE`, which is accurate.
- **No secrets.** Nothing in this build needs `API_ADMIN_PASSWORD` or
  `QR_SECRET_KEY`, and neither should ever be added to the workflow.

If someone clicks around the demo and asks to enroll a face, the answer is that
the demo is read-only — that's what the lab deployment is for.

---

## Pushing this

The workflow file and source changes need to reach GitHub. Either:

**Use the GitHub web UI.** Create each file via *Add file → Create new file* and
paste the contents. Tedious for six files, but needs no token.

**Or push with a token.** Create a **fine-grained** token at
https://github.com/settings/personal-access-tokens/new — repository access
*only* `bruce12-glitch/AAMS`, permission **Contents: Read and write**. Revoke it
when the push is done.

Do not use a classic token with broad scope, and do not paste any token into a
chat window. See the credential note in `aams-about-fields.md`.
