from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ClosestAlgorithm = Literal["brute_force", "divide_conquer"]
TourAlgorithm = Literal["exact", "nearest_neighbor", "two_opt"]
DistanceMetric = Literal[
    "straight_line", "road_distance", "road_duration", "precomputed"
]
RoutingProfile = Literal["driving", "walking", "cycling"]


class PointIn(BaseModel):
    id: str | None = None
    name: str | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class PointOut(BaseModel):
    id: str
    name: str
    lat: float
    lng: float


class Bounds(BaseModel):
    min_lat: float = Field(ge=-90, le=90)
    max_lat: float = Field(ge=-90, le=90)
    min_lon: float = Field(ge=-180, le=180)
    max_lon: float = Field(ge=-180, le=180)


class DatasetGenerateRequest(BaseModel):
    count: int = Field(default=100, ge=2, le=10_000)
    seed: int = 42
    clustered: bool = True
    bounds: Bounds | None = None
    name: str | None = None


class DatasetOut(BaseModel):
    id: str
    name: str
    source: str
    seed: int | None = None
    bounds: Bounds | None = None
    points: list[PointOut]


class ClosestPairRequest(BaseModel):
    points: list[PointIn] = Field(min_length=2, max_length=10_000)
    algorithms: list[ClosestAlgorithm] = Field(
        default_factory=lambda: ["brute_force", "divide_conquer"],
        min_length=1,
    )


class ClosestPairResult(BaseModel):
    algorithm: ClosestAlgorithm
    pair: list[int]
    pair_ids: list[str]
    pair_names: list[str]
    distance_m: float
    haversine_m: float
    distance_evaluations: int
    comparisons: int
    runtime_ms: float


class ClosestPairResponse(BaseModel):
    model: str
    projection: str
    unit: str
    point_count: int
    results: list[ClosestPairResult]
    agree: bool | None = None


class RouteOptimizeRequest(BaseModel):
    locations: list[PointIn] = Field(min_length=2, max_length=250)
    depot_index: int = Field(default=0, ge=0)
    metric: DistanceMetric = "straight_line"
    algorithms: list[TourAlgorithm] = Field(
        default_factory=lambda: ["nearest_neighbor", "two_opt"],
        min_length=1,
    )
    matrix: list[list[float]] | None = None
    profile: RoutingProfile = "driving"
    include_geometry: bool = True


class TourResult(BaseModel):
    algorithm: TourAlgorithm
    route: list[int]
    ordered_ids: list[str]
    cost: float
    distance_evaluations: int
    comparisons: int
    improvement_passes: int
    runtime_ms: float
    optimality_gap_percent: float | None = None


class RouteOptimizeResponse(BaseModel):
    metric: DistanceMetric
    unit: str
    matrix_source: str
    depot_index: int
    location_count: int
    results: list[TourResult]
    geometry: list[list[float]] | None = None
    geometry_source: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BenchmarkClosestRequest(BaseModel):
    sizes: list[int] = Field(
        default_factory=lambda: [100, 500, 1_000, 5_000, 10_000],
        min_length=1,
    )
    repetitions: int = Field(default=3, ge=1, le=10)
    seed: int = 42
    algorithms: list[ClosestAlgorithm] = Field(
        default_factory=lambda: ["brute_force", "divide_conquer"],
        min_length=1,
    )


class BenchmarkRouteRequest(BaseModel):
    sizes: list[int] = Field(
        default_factory=lambda: [5, 8, 10, 25, 50, 100],
        min_length=1,
    )
    repetitions: int = Field(default=3, ge=1, le=10)
    seed: int = 42
    algorithms: list[TourAlgorithm] = Field(
        default_factory=lambda: ["nearest_neighbor", "two_opt"],
        min_length=1,
    )


class ReportExportRequest(BaseModel):
    title: str = "GeoRoute benchmark report"
    format: Literal["csv", "markdown", "json"] = "csv"
    payload: dict[str, Any] = Field(default_factory=dict)
