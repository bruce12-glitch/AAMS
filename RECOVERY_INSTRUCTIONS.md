# AAMS — Recovery & Push Instructions

**Written: 2026-09-17**

---

## What happened

The GitHub repository `bruce12-glitch/AAMS` has been **overwritten by an unrelated
project**. Its `main` branch now contains only four files:

```
README.md    index.html    package.json    server.js
```

Everything else is gone from the remote — the FastAPI backend
(`fablab-face-attendance/`), the React console (`src/`), the Docker packaging,
the deploy configs, the docs. 96 files removed.

The remote history shows an unrelated line of development force-pushed over the
top, with no shared ancestor with the real project:

```
87310dd  Initial commit                       (a 1-line README)
e8ca1cf  Add files via upload                 (an uploaded .html)
e02ace6  Rename Qwen_html_20260822_...html to index.html
edd39db  Add live static server for the progress report
1c5416d  Serve the AAMS console and fix quote/tag bugs
c986566  Update index.html
1f03823  Merge pull request #1 from .../arena/01a02a95-aams
f992562  Update index.html                    ← current remote HEAD
```

`origin/arena/01a02a95-aams` is an automated agent branch that merged into it.

**Nothing was pushed from this machine.** A push was prepared and verified but
deliberately not sent, because force-pushing would destroy the other history and
that is a decision for the repository owner.

---

## Your work is intact locally

Local `main` in `C:\Users\iambr\OneDrive\Desktop\AAMS` holds **28 commits** and
**100 tracked files** — the complete project, including the audit fixes made
today.

```
bbde0a1  feat(ci): add Pages deploy + gating lint; fix lockfile drift
2ccdb2d  fix(console): repair runtime crash + full audit pass
545417d  docs(pilot): complete pilot kit - runbook, consent form, go-live gates
53c933b  feat(ops): Redis rate-limit backend (opt-in) + one-flag TLS profile
   ...   (24 earlier commits: backend, CV pipeline, security, retention, Docker)
dd3c60e  chore: project foundation - gitignore, README, Vite/React tooling
```

A verified bundle of the full branch is written to:

```
C:\Users\iambr\OneDrive\Desktop\aams-restore.bundle
```

---

## Before you push — decide one thing

**Was the static "AAMS console" that replaced the repo intentional?**

- **No, it was accidental** → Option A. Restore your real project over `main`.
- **Yes, someone else wants it** → Option B. Put your project on its own branch.

Do not guess on this. Force-pushing over someone else's work is destructive and
not recoverable by ordinary means.

---

## Option A — restore over `main`

Only if the 4-file static site is unwanted.

```bash
cd "C:\Users\iambr\OneDrive\Desktop\AAMS"

# Sanity: confirm local really has everything
git ls-tree -r --name-only main | wc -l        # expect 100
git log --oneline -3

# Save the current remote state first, so this stays reversible.
git fetch origin
git branch remote-state-backup origin/main

# Publish the backup branch so it exists server-side too.
git push origin remote-state-backup

# Now restore. This replaces main's history with your project's.
git push --force-with-lease origin main
```

`--force-with-lease` (not plain `--force`) refuses the push if the remote moved
since your last fetch. That is the safety catch — keep it.

---

## Option B — recover to a new branch (non-destructive)

Recommended if you are unsure, or if the other work matters.

```bash
cd "C:\Users\iambr\OneDrive\Desktop\AAMS"
git push origin main:restore/aams-full
```

Then open on GitHub:

```
https://github.com/bruce12-glitch/AAMS/compare/main...restore/aams-full
```

Review the diff, and only then decide whether to promote it to `main` via a pull
request (which keeps both histories intact and reviewable).

---

## Pushing requires a login

The push was blocked because Git Credential Manager needs an interactive login
that could not be completed from an automated session. Run the push yourself in
a normal terminal — it will prompt once and cache the credential.

If you are asked for credentials, use a **fine-grained personal access token**
with `Contents: Read and write` scoped to this repository only. Do not paste a
token into a chat or a file that gets committed.

If a push hangs with no prompt:

```bash
GIT_TERMINAL_PROMPT=1 git push origin main:restore/aams-full
```

---

## Recovering from the bundle instead

If the local clone is ever lost, the bundle alone can rebuild the branch.

```bash
git clone "C:\Users\iambr\OneDrive\Desktop\aams-restore.bundle" AAMS-recovered
cd AAMS-recovered
git remote set-url origin https://github.com/bruce12-glitch/AAMS.git
git log --oneline -3        # should end at bbde0a1
```

---

## What was fixed today (already in local `main`)

The blank-page fault is resolved. Commit `2ccdb2d`.

**Root cause:** `src/components/Sidebar.jsx` used `<IconFace />` without
importing it. `IconFace` is exported from `./icons`. Vite does not resolve JSX
identifiers, so the build passed (452 modules transformed) and the error only
threw at runtime, unmounting the React tree to a black page.

Alongside it, a full audit pass fixed:

- **Stale fallback** — `useApi.js` read `fallback` but omitted it from the
  dependency list, so the closure captured the first value forever.
- **0 ms request aborts** — `client.js` passed `undefined` to `setTimeout`,
  which fires on the next tick. Callers that omitted the timeout had every
  request aborted immediately.
- **Timestamps always "—"** — `isNaN(d)` on a `Date` reports the inverse of the
  expected result. Now `Number.isNaN(d.getTime())`.
- **Banner remount every poll** — the decision banner key embedded
  `Math.random()`, so React tore it down and replayed its animation each cycle.
- **Invisible errors** — `Users.jsx` set error state that was only rendered
  inside a modal that never opened on failure.
- **Blank deep links** — the Pages base must be the absolute `/AAMS/`. A
  relative base resolved `./assets/x.js` against the route depth and 404'd.
- **Zero backend requests in the static build** — one `IS_STATIC_DEMO` flag
  compiles out the health probe and disables every data hook. Verified: 0
  occurrences of `/health` in the Pages bundle, 1 in the lab bundle.
- **Privacy** — `src/api/mock.js` held realistic student names, register
  numbers and phone numbers, compiled into the public bundle. Replaced with
  obvious placeholders.

**Tooling added:** `eslint.config.js` with `react/jsx-no-undef`, which catches
precisely the bug that shipped. Verified by re-planting the missing import and
confirming the rule fires. Lint is clean at 0 errors.

**Latent break caught:** `package.json` declared the ESLint devDependencies but
`package-lock.json` did not contain them, so adding lint to CI would have failed
on `npm ci`. Lockfile regenerated (64 → 270 packages).

**Verification performed:**

| Check | Result |
|---|---|
| `npm ci` in a clean copy | 244 packages, no mismatch |
| `npm run lint` | 0 errors, 0 warnings |
| Pages build | 452 modules, base `/AAMS/` |
| Lab build | 452 modules, base `/` |
| `/health` in Pages bundle | 0 (tree-shaken) |
| `/health` in lab bundle | 1 (active) |
| Deep links + assets under `/AAMS/` | all HTTP 200 |

---

## Still outstanding

- **The push itself** — needs your credentials and a decision between A and B.
- **GitHub Pages** — the repo needs Settings → Pages → Source: "GitHub Actions"
  for `deploy-pages.yml` to publish to
  `https://bruce12-glitch.github.io/AAMS/`.
- **Token revocation** — the two GitHub PATs shared earlier in this conversation
  (`ghp_exvmq...` and `ghp_1O3KX...`) should be revoked at
  https://github.com/settings/tokens. They were never used by me, but they were
  exposed in plain text and must be treated as compromised.
- **About panel** — description, topics and website URL are documented in
  `aams-about-fields.md` and still need to be applied on GitHub.
- **`Notin/`** — an unrelated project with its own `.git` sitting inside the
  working directory. Left untouched; consider excluding it from this repo.
