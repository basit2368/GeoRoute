from __future__ import annotations

import csv
import io
import math
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response

from . import __version__
from .benchmarks import run_closest_pair_benchmark, run_route_benchmark
from .config import settings
from .datasets import dataset_store
from .engine import (
    ENGINE_MODE,
    ENGINE_PATH,
    ENGINE_VERSION,
    EngineError,
    engine,
)
from .geo import (
    generate_synthetic_points,
    haversine_m,
    points_from_rows,
    project_points,
    straight_line_matrix,
)
from .models import (
    ClosestPairRequest,
    ClosestPairResponse,
    ClosestPairResult,
    DatasetGenerateRequest,
    DatasetOut,
    PointIn,
    PointOut,
    ReportExportRequest,
    RouteOptimizeRequest,
    RouteOptimizeResponse,
    TourResult,
    BenchmarkClosestRequest,
    BenchmarkRouteRequest,
)
from .osrm import RoutingServiceError, build_cost_matrix, build_route_geometry
from .reports import export_report

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="GeoRoute: geographic route optimization and algorithm benchmarking API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _normalize_points(points: list[PointIn]) -> list[PointOut]:
    return [
        PointOut(
            id=point.id or f"p{index + 1:05d}",
            name=point.name or f"Point {index + 1:05d}",
            lat=point.lat,
            lng=point.lng,
        )
        for index, point in enumerate(points)
    ]


def _validate_matrix(matrix: list[list[float]] | None, count: int) -> list[list[float]]:
    if matrix is None:
        raise HTTPException(
            status_code=422, detail="A square cost matrix is required when metric='precomputed'"
        )
    if len(matrix) != count or any(len(row) != count for row in matrix):
        raise HTTPException(
            status_code=422, detail=f"The cost matrix must be {count}x{count}"
        )
    for row in matrix:
        for value in row:
            if not math.isfinite(value) or value < 0:
                raise HTTPException(
                    status_code=422,
                    detail="Cost matrix entries must be finite and non-negative",
                )
    for i in range(count):
        for j in range(i + 1, count):
            left, right = matrix[i][j], matrix[j][i]
            if abs(left - right) > 1e-6 * max(1.0, abs(left), abs(right)):
                raise HTTPException(
                    status_code=422,
                    detail="The cost matrix must be symmetric for TSP tour comparison",
                )
    return matrix


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "engine": {
            "mode": ENGINE_MODE,
            "version": ENGINE_VERSION,
            "path": ENGINE_PATH,
        },
        "limits": {
            "max_closest_pair_points": settings.max_closest_pair_points,
            "max_exact_locations": settings.max_exact_locations,
            "max_nearest_neighbor_locations": settings.max_nearest_neighbor_locations,
            "max_osrm_locations": settings.max_osrm_locations,
        },
        "routing": {
            "base_url": settings.osrm_base_url,
            "profile": settings.osrm_profile,
        },
    }


@app.post("/api/datasets/synthetic", response_model=DatasetOut)
def create_synthetic_dataset(request: DatasetGenerateRequest) -> DatasetOut:
    try:
        points = generate_synthetic_points(
            count=request.count,
            seed=request.seed,
            clustered=request.clustered,
            bounds=request.bounds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return dataset_store.create(
        points=points,
        name=request.name or f"Karachi synthetic ({request.count} points)",
        source="synthetic",
        seed=request.seed,
        bounds=request.bounds,
    )


@app.post("/api/datasets/import", response_model=DatasetOut)
async def import_dataset(file: UploadFile = File(...)) -> DatasetOut:
    content = (await file.read()).decode("utf-8-sig")
    try:
        rows = list(csv.DictReader(io.StringIO(content)))
        points = points_from_rows(rows)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return dataset_store.create(
        points=points,
        name=file.filename or "Imported CSV",
        source="csv",
    )


@app.get("/api/datasets", response_model=list[DatasetOut])
def list_datasets() -> list[DatasetOut]:
    return dataset_store.list()


@app.get("/api/datasets/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str) -> DatasetOut:
    dataset = dataset_store.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@app.post("/api/closest-pair", response_model=ClosestPairResponse)
def closest_pair(request: ClosestPairRequest) -> ClosestPairResponse:
    if len(request.points) > settings.max_closest_pair_points:
        raise HTTPException(
            status_code=422,
            detail=f"At most {settings.max_closest_pair_points} points are supported",
        )

    points = _normalize_points(request.points)
    projected = project_points(points)
    algorithms = _dedupe(list(request.algorithms))
    results: list[ClosestPairResult] = []

    try:
        for algorithm in algorithms:
            raw = engine.closest_pair(projected, algorithm)
            first, second = points[raw.index_a], points[raw.index_b]
            results.append(
                ClosestPairResult(
                    algorithm=algorithm,
                    pair=[raw.index_a, raw.index_b],
                    pair_ids=[first.id, second.id],
                    pair_names=[first.name, second.name],
                    distance_m=raw.distance,
                    haversine_m=haversine_m(
                        first.lat, first.lng, second.lat, second.lng
                    ),
                    distance_evaluations=raw.distance_evaluations,
                    comparisons=raw.comparisons,
                    runtime_ms=raw.runtime_ms,
                )
            )
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    agree = None
    if len(results) > 1:
        agree = all(
            abs(result.distance_m - results[0].distance_m) <= 1e-6
            for result in results[1:]
        )

    return ClosestPairResponse(
        model="planar Euclidean closest pair on WGS84 / UTM zone 42N",
        projection="UTM zone 42N (metres, k0=0.9996)",
        unit="m",
        point_count=len(points),
        results=results,
        agree=agree,
    )


@app.post("/api/route/optimize", response_model=RouteOptimizeResponse)
def optimize_route(request: RouteOptimizeRequest) -> RouteOptimizeResponse:
    locations = _normalize_points(request.locations)
    count = len(locations)
    if request.depot_index >= count:
        raise HTTPException(status_code=422, detail="depot_index is out of range")

    algorithms = _dedupe(list(request.algorithms))
    if "exact" in algorithms and count > settings.max_exact_locations:
        raise HTTPException(
            status_code=422,
            detail=f"Exact TSP is limited to {settings.max_exact_locations} locations",
        )
    if any(item != "exact" for item in algorithms) and count > settings.max_nearest_neighbor_locations:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Heuristic routing is limited to "
                f"{settings.max_nearest_neighbor_locations} locations"
            ),
        )
    if request.metric in {"road_distance", "road_duration"} and count > settings.max_osrm_locations:
        raise HTTPException(
            status_code=422,
            detail=f"Road-network requests are limited to {settings.max_osrm_locations} locations",
        )

    warnings: list[str] = []
    if request.metric == "straight_line":
        matrix = straight_line_matrix(locations)
        matrix_source = "haversine great-circle distance"
        unit = "m"
    elif request.metric == "precomputed":
        matrix = _validate_matrix(request.matrix, count)
        matrix_source = "client-provided symmetric matrix"
        unit = "matrix units"
    else:
        try:
            matrix = build_cost_matrix(
                locations, metric=request.metric, profile=request.profile
            )
        except (RoutingServiceError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        matrix_source = f"OSRM {request.profile} table"
        unit = "s" if request.metric == "road_duration" else "m"

    results: list[TourResult] = []
    exact_cost: float | None = None
    try:
        for algorithm in algorithms:
            raw = engine.tsp(matrix, request.depot_index, algorithm)
            if algorithm == "exact":
                exact_cost = raw.cost
            gap = None
            if exact_cost is not None and algorithm != "exact" and exact_cost > 0:
                gap = ((raw.cost - exact_cost) / exact_cost) * 100.0
            results.append(
                TourResult(
                    algorithm=algorithm,
                    route=raw.route,
                    ordered_ids=[locations[index].id for index in raw.route],
                    cost=raw.cost,
                    distance_evaluations=raw.distance_evaluations,
                    comparisons=raw.comparisons,
                    improvement_passes=raw.improvement_passes,
                    runtime_ms=raw.runtime_ms,
                    optimality_gap_percent=gap,
                )
            )
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    geometry: list[list[float]] | None = None
    geometry_source: str | None = None
    if request.include_geometry and results:
        display = next(
            (item for item in results if item.algorithm == "two_opt"),
            next(
                (item for item in results if item.algorithm == "nearest_neighbor"),
                results[0],
            ),
        )
        if request.metric in {"road_distance", "road_duration"}:
            try:
                geometry = build_route_geometry(
                    locations, display.route, profile=request.profile
                )
                geometry_source = f"OSRM {request.profile} road geometry"
            except RoutingServiceError as exc:
                warnings.append(f"Road geometry unavailable: {exc}")
        else:
            geometry = [
                [locations[index].lng, locations[index].lat] for index in display.route
            ]
            geometry.append(geometry[0])
            geometry_source = "straight segments between selected locations (not road geometry)"

    return RouteOptimizeResponse(
        metric=request.metric,
        unit=unit,
        matrix_source=matrix_source,
        depot_index=request.depot_index,
        location_count=count,
        results=results,
        geometry=geometry,
        geometry_source=geometry_source,
        warnings=warnings,
    )


@app.post("/api/benchmarks/closest-pair")
def benchmark_closest_pair(request: BenchmarkClosestRequest) -> dict[str, Any]:
    try:
        return run_closest_pair_benchmark(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/benchmarks/route")
def benchmark_route(request: BenchmarkRouteRequest) -> dict[str, Any]:
    return run_route_benchmark(request)


@app.post("/api/reports/export")
def export_benchmark_report(request: ReportExportRequest) -> Response:
    content = export_report(request.title, request.format, request.payload)
    extension = {"csv": "csv", "markdown": "md", "json": "json"}[request.format]
    media_type = {
        "csv": "text/csv",
        "markdown": "text/markdown",
        "json": "application/json",
    }[request.format]
    safe_title = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in request.title
    ).strip("-") or "georoute-report"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.{extension}"'
        },
    )
