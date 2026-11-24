from __future__ import annotations

import statistics
from typing import Any

from .config import settings
from .engine import engine
from .geo import generate_synthetic_points, project_points, straight_line_matrix
from .models import BenchmarkClosestRequest, BenchmarkRouteRequest


def _summarize(values: list[float]) -> dict[str, float]:
    return {
        "mean": round(statistics.fmean(values), 6),
        "median": round(statistics.median(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
    }


def run_closest_pair_benchmark(request: BenchmarkClosestRequest) -> dict[str, Any]:
    if any(size > settings.max_closest_pair_points for size in request.sizes):
        raise ValueError(
            f"Closest-pair benchmark sizes cannot exceed {settings.max_closest_pair_points}"
        )

    series: list[dict[str, Any]] = []
    for size in request.sizes:
        points = generate_synthetic_points(
            count=size, seed=request.seed, clustered=True, bounds=None
        )
        projected = project_points(points)
        for algorithm in request.algorithms:
            timings: list[float] = []
            last = None
            for _ in range(request.repetitions):
                last = engine.closest_pair(projected, algorithm)
                timings.append(last.runtime_ms)
            if last is None:
                continue
            summary = _summarize(timings)
            series.append(
                {
                    "input_size": size,
                    "algorithm": algorithm,
                    "median_runtime_ms": summary["median"],
                    "mean_runtime_ms": summary["mean"],
                    "min_runtime_ms": summary["min"],
                    "max_runtime_ms": summary["max"],
                    "distance_evaluations": last.distance_evaluations,
                    "comparisons": last.comparisons,
                    "distance_m": round(last.distance, 6),
                    "repetitions": request.repetitions,
                }
            )

    return {
        "benchmark": "closest_pair",
        "config": {
            "sizes": request.sizes,
            "repetitions": request.repetitions,
            "seed": request.seed,
            "algorithms": request.algorithms,
            "generator": "clustered Karachi synthetic points",
            "model": "UTM zone 42N Euclidean plane",
            "unit": "metres / milliseconds",
            "excluded_from_timing": [
                "dataset generation",
                "coordinate projection",
                "JSON serialisation",
            ],
        },
        "series": series,
    }


def run_route_benchmark(request: BenchmarkRouteRequest) -> dict[str, Any]:
    series: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for size in request.sizes:
        points = generate_synthetic_points(
            count=size, seed=request.seed, clustered=True, bounds=None
        )
        matrix = straight_line_matrix(points)
        exact_cost: float | None = None
        ordered_algorithms = [item for item in request.algorithms if item == "exact"] + [
            item for item in request.algorithms if item != "exact"
        ]

        for algorithm in ordered_algorithms:
            if algorithm == "exact" and size > settings.max_exact_locations:
                skipped.append(
                    {
                        "input_size": size,
                        "algorithm": algorithm,
                        "reason": f"exact solver limited to {settings.max_exact_locations} locations",
                    }
                )
                continue
            if algorithm != "exact" and size > settings.max_nearest_neighbor_locations:
                skipped.append(
                    {
                        "input_size": size,
                        "algorithm": algorithm,
                        "reason": (
                            f"route benchmark limited to "
                            f"{settings.max_nearest_neighbor_locations} locations"
                        ),
                    }
                )
                continue

            timings: list[float] = []
            last = None
            for _ in range(request.repetitions):
                last = engine.tsp(matrix, 0, algorithm)
                timings.append(last.runtime_ms)
            if last is None:
                continue
            if algorithm == "exact":
                exact_cost = last.cost

            summary = _summarize(timings)
            gap = None
            if algorithm != "exact" and exact_cost is not None and exact_cost > 0:
                gap = round(((last.cost - exact_cost) / exact_cost) * 100.0, 6)

            series.append(
                {
                    "input_size": size,
                    "algorithm": algorithm,
                    "median_runtime_ms": summary["median"],
                    "mean_runtime_ms": summary["mean"],
                    "min_runtime_ms": summary["min"],
                    "max_runtime_ms": summary["max"],
                    "route_cost_m": round(last.cost, 6),
                    "distance_evaluations": last.distance_evaluations,
                    "comparisons": last.comparisons,
                    "optimality_gap_percent": gap,
                    "repetitions": request.repetitions,
                }
            )

    return {
        "benchmark": "route_optimization",
        "config": {
            "sizes": request.sizes,
            "repetitions": request.repetitions,
            "seed": request.seed,
            "algorithms": request.algorithms,
            "metric": "straight_line",
            "unit": "metres / milliseconds",
            "excluded_from_timing": [
                "dataset generation",
                "distance-matrix construction",
                "network calls",
                "JSON serialisation",
            ],
        },
        "series": series,
        "skipped": skipped,
    }
