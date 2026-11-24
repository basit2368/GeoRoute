from __future__ import annotations

import math
import random
from typing import Iterable, Sequence

from .models import Bounds, PointIn, PointOut

WGS84_A = 6_378_137.0
WGS84_F = 1.0 / 298.257223563
HAVERSINE_R = 6_371_008.8  # Earth mean radius in metres
KARACHI_BOUNDS = Bounds(
    min_lat=24.70, max_lat=24.98, min_lon=66.90, max_lon=67.35
)

KARACHI_CENTERS = [
    ("DHA", 24.790, 67.030),
    ("Clifton", 24.820, 67.000),
    ("Saddar", 24.860, 67.010),
    ("PECHS", 24.850, 67.060),
    ("Gulshan-e-Iqbal", 24.880, 67.090),
    ("North Nazimabad", 24.930, 67.030),
    ("Korangi", 24.800, 67.180),
    ("Malir", 24.770, 67.160),
]


def utm_zone(longitude: float) -> int:
    return int(math.floor((longitude + 180.0) / 6.0)) + 1


def utm_forward(latitude: float, longitude: float, zone: int | None = None) -> tuple[float, float]:
    """WGS84 UTM forward projection. Returns easting/northing in metres.

    The planar closest-pair algorithm needs Euclidean coordinates. UTM is a
    local conformal projection, so distances are in metres with a documented
    scale factor (k0 = 0.9996) rather than being exact geodesics.
    """
    if not -80.0 <= latitude <= 84.0:
        raise ValueError("UTM is only defined for latitudes between -80 and 84")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("Longitude must be between -180 and 180")

    zone = zone or utm_zone(longitude)
    if not 1 <= zone <= 60:
        raise ValueError("UTM zone must be between 1 and 60")

    phi = math.radians(latitude)
    lam = math.radians(longitude)
    lam0 = math.radians(6.0 * zone - 183.0)

    e2 = WGS84_F * (2.0 - WGS84_F)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    tan_phi = math.tan(phi)

    n = WGS84_A / math.sqrt(1.0 - e2 * sin_phi * sin_phi)
    t = tan_phi * tan_phi
    c = ep2 * cos_phi * cos_phi
    a = cos_phi * (lam - lam0)

    m = WGS84_A * (
        (1.0 - e2 / 4.0 - 3.0 * e2**2 / 64.0 - 5.0 * e2**3 / 256.0) * phi
        - (3.0 * e2 / 8.0 + 3.0 * e2**2 / 32.0 + 45.0 * e2**3 / 1024.0)
        * math.sin(2.0 * phi)
        + (15.0 * e2**2 / 256.0 + 45.0 * e2**3 / 1024.0) * math.sin(4.0 * phi)
        - (35.0 * e2**3 / 3072.0) * math.sin(6.0 * phi)
    )

    easting = k0 * n * (
        a
        + (1.0 - t + c) * a**3 / 6.0
        + (5.0 - 18.0 * t + t * t + 72.0 * c - 58.0 * ep2) * a**5 / 120.0
    ) + 500_000.0

    northing = k0 * (
        m
        + n
        * tan_phi
        * (
            a * a / 2.0
            + (5.0 - t + 9.0 * c + 4.0 * c * c) * a**4 / 24.0
            + (61.0 - 58.0 * t + t * t + 600.0 * c - 330.0 * ep2)
            * a**6
            / 720.0
        )
    )
    if latitude < 0:
        northing += 10_000_000.0
    return easting, northing


def project_points(points: Sequence[PointIn | PointOut], zone: int = 42) -> list[tuple[float, float]]:
    return [utm_forward(point.lat, point.lng, zone) for point in points]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = phi2 - phi1
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    a = min(1.0, max(0.0, a))
    return 2.0 * HAVERSINE_R * math.asin(math.sqrt(a))


def straight_line_matrix(points: Sequence[PointIn | PointOut]) -> list[list[float]]:
    count = len(points)
    matrix = [[0.0] * count for _ in range(count)]
    for i in range(count):
        for j in range(i + 1, count):
            distance = haversine_m(points[i].lat, points[i].lng, points[j].lat, points[j].lng)
            matrix[i][j] = distance
            matrix[j][i] = distance
    return matrix


def generate_synthetic_points(
    count: int,
    seed: int,
    clustered: bool,
    bounds: Bounds | None,
) -> list[PointOut]:
    bounds = bounds or KARACHI_BOUNDS
    if bounds.min_lat >= bounds.max_lat or bounds.min_lon >= bounds.max_lon:
        raise ValueError("Bounds must satisfy min < max")

    rng = random.Random(seed)
    points: list[PointOut] = []
    for index in range(count):
        if clustered and rng.random() < 0.8:
            _, center_lat, center_lng = rng.choice(KARACHI_CENTERS)
            lat = rng.gauss(center_lat, 0.011)
            lng = rng.gauss(center_lng, 0.014)
        else:
            lat = rng.uniform(bounds.min_lat, bounds.max_lat)
            lng = rng.uniform(bounds.min_lon, bounds.max_lon)

        lat = min(bounds.max_lat, max(bounds.min_lat, lat))
        lng = min(bounds.max_lon, max(bounds.min_lon, lng))
        points.append(
            PointOut(
                id=f"p{index + 1:05d}",
                name=f"Point {index + 1:05d}",
                lat=round(lat, 7),
                lng=round(lng, 7),
            )
        )
    return points


def points_from_rows(rows: Iterable[dict[str, str]]) -> list[PointOut]:
    points: list[PointOut] = []
    for index, row in enumerate(rows, start=1):
        normalized = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        lat_raw = (
            normalized.get("lat")
            or normalized.get("latitude")
            or normalized.get("y")
        )
        lng_raw = (
            normalized.get("lng")
            or normalized.get("lon")
            or normalized.get("longitude")
            or normalized.get("x")
        )
        if not lat_raw or not lng_raw:
            raise ValueError(
                "CSV must contain latitude/longitude columns (lat/lng, latitude/longitude, or y/x)"
            )
        try:
            lat, lng = float(lat_raw), float(lng_raw)
        except ValueError as exc:
            raise ValueError(f"Invalid coordinate on CSV row {index}") from exc
        if not -90 <= lat <= 90 or not -180 <= lng <= 180:
            raise ValueError(f"Coordinate out of range on CSV row {index}")

        name = normalized.get("name") or normalized.get("id") or f"Point {index:05d}"
        points.append(
            PointOut(
                id=normalized.get("id") or f"p{index:05d}",
                name=name,
                lat=lat,
                lng=lng,
            )
        )
    if len(points) < 2:
        raise ValueError("CSV must contain at least two valid locations")
    return points
