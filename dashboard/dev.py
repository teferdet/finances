"""
Local development server for the dashboard.
Mounts static files directly from FastAPI (no NGINX needed).

Usage:
    cd d:\\dev\\finances
    python dashboard/dev.py

Dashboard: http://localhost:8080
API:       http://localhost:8080/api/...
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env if present
from pathlib import Path
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

from fastapi.staticfiles import StaticFiles
from dashboard.api.main import app

# Mount static/built files so NGINX isn't needed locally
_frontend_dist = Path(__file__).parent / "frontend" / "dist"
_static_dir = _frontend_dist if _frontend_dist.exists() else Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*52)
    print("  💰 Finances Dashboard — Dev Server")
    print("="*52)
    print(f"  🌐 Open: http://localhost:8080")
    print(f"  🔌 API:  http://localhost:8080/api/health")
    print(f"  📁 Static: {_static_dir}")
    print(f"  🔑 Admin IDs: {os.environ.get('BOT_ADMIN_IDS', 'NOT SET ⚠️')}")
    print("="*52 + "\n")

    uvicorn.run(
        "dashboard.dev:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
        log_level="info",
    )
