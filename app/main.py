import os
import platform
import subprocess
import sys
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def get_cors_allowed_origins() -> List[str]:
    raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not raw_origins:
        return []

    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def create_app() -> FastAPI:
    app = FastAPI(title="Desktop Companion API", version="0.1.0")

    allowed_origins = get_cors_allowed_origins()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health_check() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/active-app")
    def get_active_application() -> Dict[str, Any]:
        return get_active_app_info()

    return app


app = create_app()


def get_active_app_info() -> Dict[str, Any]:
    if sys.platform != "darwin":
        return {
            "name": None,
            "bundle_id": None,
            "pid": None,
            "platform": platform.system(),
        }

    script = """
tell application \"System Events\"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    set appBundleID to bundle identifier of frontApp
    set appPID to unix id of frontApp
    return appName & \"\\n\" & appBundleID & \"\\n\" & appPID
end tell
"""

    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "name": None,
            "bundle_id": None,
            "pid": None,
            "platform": platform.system(),
        }

    parts = [part.strip() for part in completed.stdout.splitlines() if part.strip()]
    if len(parts) >= 3:
        return {
            "name": parts[0],
            "bundle_id": parts[1],
            "pid": int(parts[2]),
            "platform": platform.system(),
        }

    return {
        "name": None,
        "bundle_id": None,
        "pid": None,
        "platform": platform.system(),
    }
