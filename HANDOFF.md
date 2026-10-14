# AAMS current handoff

Read [SHOWCASE_READINESS.md](SHOWCASE_READINESS.md) for the source review, completed checks and external setup. [README.md](README.md) contains current private launch instructions.

The code uses React/Vite, nginx and FastAPI with SQLite WAL, image/model volumes, administrator/member sessions and private Telegram settings. Use one API process. No database service needs to be provisioned for the single-host showcase.

Changes are prepared for a separate GitHub review branch. Main/public deployment and all existing branches remain untouched. Telegram bot/group credentials and hosting approval remain external requirements.
