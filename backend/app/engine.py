from __future__ import annotations

import ctypes
import itertools
import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .config import settings

logger = logging.getLogger("georoute.engine")

CLOSEST_CODES = {"brute_force": 0, "divide_conquer": 1}
TOUR_CODES = {"exact": 0, "nearest_neighbor": 1, "two_opt": 2}

REVERSE_CLOSEST = {value: key for key, value in CLOSEST_CODES.items()}
REVERSE_TOUR = {value: key for key, value in TOUR_CODES.items()}


class EngineError(RuntimeError):
    pass


@dataclass
class ClosestPairEngineResult:
    algorithm: str
    index_a: int
    index_b: int
    distance: float
    distance_evaluations: int
    comparisons: int
    runtime_ms: float


@dataclass
class TourEngineResult:
    algorithm: str
    route: list[int]
    cost: float
    distance_evaluations: int
    comparisons: int
    improvement_passes: int
    runtime_ms: float


class GRPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


class GRClosestResult(ctypes.Structure):
    _fields_ = [
        ("index_a", ctypes.c_int),
        ("index_b", ctypes.c_int),
        ("distance", ctypes.c_double),
        ("distance_evaluations", ctypes.c_ulonglong),
        ("comparisons", ctypes.c_ulonglong),
        ("elapsed_ms", ctypes.c_double),
        ("status", ctypes.c_int),
    ]


class GRTourResult(ctypes.Structure):
    _fields_ = [
        ("route", ctypes.POINTER(ctypes.c_int)),
        ("route_length", ctypes.c_int),
        ("cost", ctypes.c_double),
        ("distance_evaluations", ctypes.c_ulonglong),
        ("comparisons", ctypes.c_ulonglong),
        ("improvement_passes", ctypes.c_int),
        ("elapsed_ms", ctypes.c_double),
        ("status", ctypes.c_int),
    ]


class NativeEngine:
    mode = "native-cpp17"

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lib = ctypes.CDLL(str(path))
        self._lib.gr_closest_pair.argtypes = [
            ctypes.POINTER(GRPoint),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(GRClosestResult),
        ]
        self._lib.gr_closest_pair.restype = ctypes.c_int
        self._lib.gr_tsp.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(GRTourResult),
        ]
        self._lib.gr_tsp.restype = ctypes.c_int
        self._lib.gr_free_tour.argtypes = [ctypes.POINTER(GRTourResult)]
        self._lib.gr_free_tour.restype = None
        self._lib.gr_version.argtypes = []
        self._lib.gr_version.restype = ctypes.c_char_p
        self.version = (self._lib.gr_version() or b"unknown").decode("utf-8")

    def closest_pair(
        self, points: Sequence[tuple[float, float]], algorithm: str
    ) -> ClosestPairEngineResult:
        if algorithm not in CLOSEST_CODES:
            raise EngineError(f"Unknown closest-pair algorithm: {algorithm}")
        array = (GRPoint * len(points))(*(GRPoint(x, y) for x, y in points))
        result = GRClosestResult()
        status = self._lib.gr_closest_pair(
            array, len(points), CLOSEST_CODES[algorithm], ctypes.byref(result)
        )
        if status != 0:
            raise EngineError(f"C++ closest-pair engine returned status {status}")
        return ClosestPairEngineResult(
            algorithm=algorithm,
            index_a=result.index_a,
            index_b=result.index_b,
            distance=result.distance,
            distance_evaluations=int(result.distance_evaluations),
            comparisons=int(result.comparisons),
            runtime_ms=result.elapsed_ms,
        )

    def tsp(
        self, matrix: Sequence[Sequence[float]], depot: int, algorithm: str
    ) -> TourEngineResult:
        if algorithm not in TOUR_CODES:
            raise EngineError(f"Unknown tour algorithm: {algorithm}")
        count = len(matrix)
        flat = (ctypes.c_double * (count * count))(
            *(float(value) for row in matrix for value in row)
        )
        result = GRTourResult()
        status = self._lib.gr_tsp(
            flat, count, depot, TOUR_CODES[algorithm], ctypes.byref(result)
        )
        if status != 0:
            raise EngineError(f"C++ TSP engine returned status {status}")
        try:
            route = [result.route[i] for i in range(result.route_length)]
        finally:
            self._lib.gr_free_tour(ctypes.byref(result))
        return TourEngineResult(
            algorithm=algorithm,
            route=route,
            cost=result.cost,
            distance_evaluations=int(result.distance_evaluations),
            comparisons=int(result.comparisons),
            improvement_passes=int(result.improvement_passes),
            runtime_ms=result.elapsed_ms,
        )


class FallbackEngine:
    """Pure-Python reference implementation used only when no binary is built."""

    mode = "python-fallback"
    version = "1.0.0-reference"

    def __init__(self) -> None:
        self.path = None

    @staticmethod
    def _closest_pair(
        points: Sequence[tuple[float, float]], algorithm: str
    ) -> ClosestPairEngineResult:
        start = time.perf_counter_ns()
        evaluations = 0
        comparisons = 0
        best = (math.inf, -1, -1)

        def evaluate(index_a: int, index_b: int) -> None:
            nonlocal best, evaluations, comparisons
            evaluations += 1
            distance = math.hypot(
                points[index_a][0] - points[index_b][0],
                points[index_a][1] - points[index_b][1],
            )
            comparisons += 1
            if distance < best[0]:
                best = (distance, index_a, index_b)

        if algorithm == "brute_force":
            for i in range(len(points)):
                for j in range(i + 1, len(points)):
                    evaluate(i, j)
        else:
            order_x = sorted(range(len(points)), key=lambda i: (points[i][0], points[i][1]))
            order_y = list(order_x)

            def solve(left: int, right: int) -> None:
                nonlocal order_y
                if right - left <= 8:
                    order_y[left:right] = sorted(
                        order_y[left:right],
                        key=lambda i: (points[i][1], points[i][0]),
                    )
                    for a in range(left, right):
                        for b in range(a + 1, right):
                            evaluate(order_x[a], order_x[b])
                    return

                middle = (left + right) // 2
                middle_x = points[order_x[middle]][0]
                solve(left, middle)
                solve(middle, right)
                order_y[left:right] = sorted(
                    order_y[left:right],
                    key=lambda i: (points[i][1], points[i][0]),
                )
                strip = [i for i in order_y[left:right] if abs(points[i][0] - middle_x) <= best[0]]
                for offset, index_a in enumerate(strip):
                    for index_b in strip[offset + 1 :]:
                        comparisons += 1
                        if points[index_b][1] - points[index_a][1] > best[0]:
                            break
                        evaluate(index_a, index_b)

            solve(0, len(points))

        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
        return ClosestPairEngineResult(
            algorithm=algorithm,
            index_a=best[1],
            index_b=best[2],
            distance=best[0],
            distance_evaluations=evaluations,
            comparisons=comparisons,
            runtime_ms=elapsed_ms,
        )

    def closest_pair(
        self, points: Sequence[tuple[float, float]], algorithm: str
    ) -> ClosestPairEngineResult:
        if algorithm not in CLOSEST_CODES:
            raise EngineError(f"Unknown closest-pair algorithm: {algorithm}")
        if len(points) < 2:
            raise EngineError("At least two points are required")
        return self._closest_pair(points, algorithm)

    @staticmethod
    def _cost(
        matrix: Sequence[Sequence[float]],
        route: Sequence[int],
        evaluations: list[int],
    ) -> float:
        count = len(matrix)
        total = 0.0
        for i in range(count):
            evaluations[0] += 1
            total += matrix[route[i]][route[(i + 1) % count]]
        return total

    @staticmethod
    def _nearest_neighbour(
        matrix: Sequence[Sequence[float]],
        depot: int,
        evaluations: list[int],
        comparisons: list[int],
    ) -> list[int]:
        count = len(matrix)
        visited = {depot}
        route = [depot]
        current = depot
        for _ in range(1, count):
            best = -1
            best_cost = math.inf
            for candidate in range(count):
                if candidate in visited:
                    continue
                evaluations[0] += 1
                cost = matrix[current][candidate]
                comparisons[0] += 1
                if cost < best_cost:
                    best_cost, best = cost, candidate
            visited.add(best)
            route.append(best)
            current = best
        return route

    def tsp(
        self, matrix: Sequence[Sequence[float]], depot: int, algorithm: str
    ) -> TourEngineResult:
        if algorithm not in TOUR_CODES:
            raise EngineError(f"Unknown tour algorithm: {algorithm}")
        count = len(matrix)
        start = time.perf_counter_ns()
        evaluations = [0]
        comparisons = [0]
        passes = 0

        if algorithm == "exact":
            others = [i for i in range(count) if i != depot]
            best_route = [depot] + others
            best_cost = math.inf
            for permutation in itertools.permutations(others):
                candidate = [depot, *permutation]
                cost = self._cost(matrix, candidate, evaluations)
                comparisons[0] += 1
                if cost < best_cost:
                    best_cost, best_route = cost, candidate
            route = best_route
        else:
            route = self._nearest_neighbour(matrix, depot, evaluations, comparisons)
            if algorithm == "two_opt":
                symmetric = all(
                    abs(matrix[i][j] - matrix[j][i])
                    <= 1e-9 * max(1.0, abs(matrix[i][j]), abs(matrix[j][i]))
                    for i in range(count)
                    for j in range(i + 1, count)
                )
                for pass_index in range(100):
                    passes = pass_index + 1
                    improved = False
                    for i in range(count - 1):
                        for k in range(i + 1, count):
                            a, b = route[i], route[i + 1]
                            c, d = route[k], route[(k + 1) % count]
                            evaluations[0] += 4
                            old_edges = matrix[a][b] + matrix[c][d]
                            new_edges = matrix[a][c] + matrix[b][d]
                            if not symmetric:
                                for p in range(i + 1, k):
                                    evaluations[0] += 2
                                    old_edges += matrix[route[p]][route[p + 1]]
                                    new_edges += matrix[route[p + 1]][route[p]]
                            delta = new_edges - old_edges
                            comparisons[0] += 1
                            if delta < -1e-9:
                                route[i + 1 : k + 1] = reversed(route[i + 1 : k + 1])
                                improved = True
                    if not improved:
                        break

        cost = self._cost(matrix, route, evaluations)
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000.0
        return TourEngineResult(
            algorithm=algorithm,
            route=route,
            cost=cost,
            distance_evaluations=evaluations[0],
            comparisons=comparisons[0],
            improvement_passes=passes,
            runtime_ms=elapsed_ms,
        )


def _create_engine() -> NativeEngine | FallbackEngine:
    try:
        return NativeEngine(settings.engine_path)
    except Exception as exc:  # pragma: no cover - depends on local build
        logger.warning(
            "Native C++ engine unavailable at %s (%s); using Python reference engine.",
            settings.engine_path,
            exc,
        )
        return FallbackEngine()


engine = _create_engine()

ENGINE_MODE = engine.mode
ENGINE_VERSION = engine.version
ENGINE_PATH = str(engine.path) if engine.path else None
