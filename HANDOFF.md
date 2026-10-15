# AAMS current handoff

Read [SHOWCASE_READINESS.md](SHOWCASE_READINESS.md) for the source review, completed checks and external setup. [README.md](README.md) contains current private launch instructions.

The code uses React/Vite and FastAPI with SQLite WAL, image/model storage, administrator/member sessions and private Telegram settings. Use one API process. No database service needs to be provisioned for the single-host showcase.

PR #8 is merged into `main`. The hosted-image update adds a complete single-service target; [deploy/HOSTING.md](deploy/HOSTING.md) selects Oracle Cloud Always Free and describes the HTTPS, volume and manual GitHub deployment setup. It preserves the existing local nginx/Compose stack.

All existing branches are preserved. Public deployment remains pending an Oracle Cloud account and private authentication variables. The user has deferred Telegram setup; do not request bot credentials or test real group delivery as part of this release.
