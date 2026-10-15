"""Optional same-origin console hosting for the complete showcase image."""
from pathlib import Path

from fastapi.staticfiles import StaticFiles


def mount_console(app, directory) -> None:
    directory = Path(directory).resolve()
    if not (directory / 'index.html').is_file():
        raise RuntimeError('SPA_DIST_DIR must contain the built website')
    # Always mount LAST: API/health routes must retain their behavior, including
    # auth guards. Hash-based UI routing needs no catch-all HTML fallback.
    app.mount('/', StaticFiles(directory=str(directory), html=True), name='console')
