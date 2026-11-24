from __future__ import annotations

import math
import threading
import time
from typing import Any, Sequence

import httpx

from .config import settings
from .models import PointIn, PointOut

CoordinatePoint = PointIn | PointOut


class RoutingServiceError(RuntimeError):
    """Raised when an OSRM-compatible service cannot satisfy a request."""


_client = httpx.Client(timeout=settings.osrm_timeout_seconds)
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()


def _coordinate_path(points: Sequence[CoordinatePoint]) -> str:
    return ";".join(f"{point.lng:.7f},{point.lat:.7f}" for point in points)


def _cached_json(key: str, url: str, params: dict[str, Any]) -> dict[str, Any]:
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    try:
        response = _client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise RoutingServiceError(f"Routing service request failed: {exc}") from exc
    except ValueError as exc:
        raise RoutingServiceError("Routing service returned invalid JSON") from exc

    code = payload.get("code")
    if code != "Ok":
        message = payload.get("message") or "unknown error"
        raise RoutingServiceError(f"Routing service returned {code}: {message}")

    with _cache_lock:
        _cache[key] = (now + settings.osrm_cache_ttl_seconds, payload)
    return payload


def _validate_count(points: Sequence[CoordinatePoint]) -> None:
    if len(points) > settings.max_osrm_locations:
        raise RoutingServiceError(
            f"Road-network requests are limited to {settings.max_osrm_locations} "
            "locations. Use straight-line or a precomputed matrix for larger tests."
        )


def build_cost_matrix(
    points: Sequence[CoordinatePoint],
    *,
    metric: str,
    profile: str = "driving",
) -> list[list[float]]:
    if metric not in {"road_distance", "road_duration"}:
        raise ValueError(f"Unsupported road metric: {metric}")
    _validate_count(points)

    coordinate_path = _coordinate_path(points)
    cache_key = f"table:{profile}:{coordinate_path}"
    url = f"{settings.osrm_base_url}/table/v1/{profile}/{coordinate_path}"
    payload = _cached_json(cache_key, url, {"annotations": "distance,duration"})

    field = "distances" if metric == "road_distance" else "durations"
    raw = payload.get(field)
    if not isinstance(raw, list) or len(raw) != len(points):
        raise RoutingServiceError(f"Routing service did not return a complete {field} matrix")

    matrix: list[list[float]] = []
    for row in raw:
        if not isinstance(row, list) or len(row) != len(points):
            raise RoutingServiceError("Routing service returned a malformed cost matrix")
        converted: list[float] = []
        for value in row:
            if value is None or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise RoutingServiceError(
                    "Some locations cannot be connected on the road network; "
                    "no straight-line substitute was applied"
                )
            converted.append(float(value))
        matrix.append(converted)
    return matrix


def build_route_geometry(
    points: Sequence[CoordinatePoint],
    route: Sequence[int],
    *,
    profile: str = "driving",
) -> list[list[float]]:
    _validate_count(points)
    ordered = [points[index] for index in route]
    if len(ordered) < 2:
        return []

    coordinate_path = _coordinate_path(ordered)
    cache_key = f"route:{profile}:{coordinate_path}"
    url = f"{settings.osrm_base_url}/route/v1/{profile}/{coordinate_path}"
    payload = _cached_json(
        cache_key,
        url,
        {"overview": "full", "geometries": "geojson", "steps": "false"},
    )

    routes = payload.get("routes")
    if not routes:
        raise RoutingServiceError("Routing service found no route for the selected order")
    geometry = routes[0].get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list):
        raise RoutingServiceError("Routing service returned no route geometry")
    return [[float(lng), float(lat)] for lng, lat in coordinates]
