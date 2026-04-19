from pathlib import Path

from app.config import STATIC_DIR

FRONTEND_DIST_DIR = STATIC_DIR / "dist"
FRONTEND_ENTRY_JS = FRONTEND_DIST_DIR / "assets" / "index.js"
FRONTEND_ENTRY_CSS = FRONTEND_DIST_DIR / "assets" / "index.css"


def get_frontend_asset_version() -> str:
    timestamps = []
    for path in (FRONTEND_ENTRY_JS, FRONTEND_ENTRY_CSS):
        if path.exists():
            timestamps.append(str(int(path.stat().st_mtime)))
    return "-".join(timestamps) if timestamps else "dev"
