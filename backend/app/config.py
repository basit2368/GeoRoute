from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _default_engine_path() -> Path:
    native_dir = BACKEND_DIR / "native"
    active_file = native_dir / "active.txt"
    if active_file.exists():
        name = active_file.read_text(encoding="utf-8").strip()
        candidate = native_dir / name
        if name and candidate.exists():
            return candidate
    return native_dir / (
        "georoute_engine.dll" if os.name == "nt" else "libgeoroute_engine.so"
    )


class Settings:
    """Runtime configuration, all overridable with environment variables."""

    app_name = "GeoRoute API"
    version = "1.0.0"

    engine_path = Path(os.getenv("GEOROUTE_ENGINE_PATH", str(_default_engine_path())))

    max_closest_pair_points = _int_env("GEOROUTE_MAX_CLOSEST_POINTS", 10_000)
    max_exact_locations = _int_env("GEOROUTE_MAX_EXACT_LOCATIONS", 10)
    max_nearest_neighbor_locations = _int_env("GEOROUTE_MAX_NN_LOCATIONS", 250)
    max_osrm_locations = _int_env("GEOROUTE_MAX_OSRM_LOCATIONS", 25)

    osrm_base_url = os.getenv(
        "GEOROUTE_OSRM_BASE_URL", "https://router.project-osrm.org"
    ).rstrip("/")
    osrm_profile = os.getenv("GEOROUTE_OSRM_PROFILE", "driving")
    osrm_timeout_seconds = float(os.getenv("GEOROUTE_OSRM_TIMEOUT", "12"))
    osrm_cache_ttl_seconds = _int_env("GEOROUTE_OSRM_CACHE_TTL", 900)

    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "GEOROUTE_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]


settings = Settings()
