# Benchmarking methodology

GeoRoute treats benchmarking as an experiment, not as a demo animation. Every plotted point comes from the same controlled harness that generated the input, prepared the matrix and called the native engine.

## Controls

| Control | Implementation |
| --- | --- |
| Identical inputs | One generated dataset/matrix per size, reused by every algorithm and every repetition |
| Determinism | Python `random.Random(seed)`; default seed `42` |
| Fair timing | Timer starts inside the C++ engine after input has been prepared and copied |
| Excluded work | Dataset generation, UTM projection, matrix construction, network requests, JSON serialisation and map rendering |
| Repeated runs | 1–10 repetitions; median is plotted, mean/min/max are recorded |
| Build consistency | All compared algorithms run from the same shared library, compiled once with `-O3` |
| Failed runs | Reported/skipped explicitly; never silently removed or replaced |
| Versioning | Engine version, mode and configuration are exposed by `/api/health` and recorded in report config blocks |

## Metrics

| Metric | Meaning |
| --- | --- |
| `median_runtime_ms` | Median algorithm-only wall-clock time |
| `mean_runtime_ms` | Mean algorithm-only wall-clock time |
| `min_runtime_ms`, `max_runtime_ms` | Observed range across repetitions |
| `distance_evaluations` | Closest-pair Euclidean computations or TSP matrix lookups |
| `comparisons` | Primitive comparison operations defined in `ALGORITHMS.md` |
| `distance_m` / `route_cost_m` | Solution value in metres |
| `optimality_gap_percent` | Heuristic excess over an exact cost on the same matrix |

## Sample local results

The table below was recorded on the development machine using the default seed and three repetitions. It is illustrative; rerun the benchmarks on your own hardware before drawing conclusions.

### Closest pair

| n | Brute force median | Divide & conquer median | Brute evals | D&C evals |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 0.050 ms | 0.036 ms | 4,950 | 266 |
| 500 | 0.863 ms | 0.183 ms | 124,750 | 1,715 |
| 1,000 | 2.971 ms | 0.542 ms | 499,500 | 3,428 |
| 5,000 | 143.724 ms | 2.824 ms | 12,497,500 | 9,787 |
| 10,000 | 417.158 ms | 6.668 ms | 49,995,000 | 19,536 |

The runtime ratio grows with `n`, matching the `O(n²)` versus `O(n log n)` expectation. The operation counter makes the difference visible even at small sizes where wall-clock noise dominates.

### Route optimization

| n | Algorithm | Median | Cost | Gap |
| ---: | --- | ---: | ---: | ---: |
| 5 | Exact | 0.011 ms | 47.7 km | — |
| 5 | Nearest neighbour | 0.003 ms | 48.9 km | 2.43% |
| 5 | 2-Opt | 0.003 ms | 47.7 km | 0.00% |
| 8 | Exact | 1.655 ms | 82.7 km | — |
| 8 | Nearest neighbour | 0.002 ms | 86.9 km | 5.04% |
| 8 | 2-Opt | 0.004 ms | 82.7 km | 0.00% |
| 10 | Exact | 106.297 ms | 96.2 km | — |
| 10 | Nearest neighbour | 0.002 ms | 103.2 km | 7.26% |
| 10 | 2-Opt | 0.005 ms | 96.2 km | 0.00% |
| 25 | Nearest neighbour | 0.005 ms | 136.4 km | — |
| 25 | 2-Opt | 0.029 ms | 116.9 km | — |

Exact TSP grows factorially: the jump from 8 to 10 locations is roughly two orders of magnitude. Nearest neighbour remains flat, and 2-Opt improves the tour at a small additional cost. Gaps are omitted above 10 locations because no exact reference was computed.

## Reproduce in the dashboard

1. Open the **Benchmarks** tab.
2. Leave sizes at `100,500,1000,5000,10000` for closest pair and `5,8,10,25,50,100` for routing.
3. Set repetitions to 3 and seed to 42.
4. Run both suites.
5. Switch between **Runtime** and **Operations** to compare time growth and primitive-work growth.
6. Download CSV reports with the buttons on each panel.

## Reproduce through the API

```bash
curl -X POST http://localhost:8000/api/benchmarks/closest-pair \
  -H "Content-Type: application/json" \
  -d '{"sizes":[100,500,1000,5000,10000],"repetitions":3,"seed":42}'

curl -X POST http://localhost:8000/api/benchmarks/route \
  -H "Content-Type: application/json" \
  -d '{"sizes":[5,8,10,25,50,100],"repetitions":3,"seed":42}'
```

## Interpretation rules

- Do not compare a road-network matrix with a Haversine matrix as if they were the same objective.
- Do not call a nearest-neighbour or 2-Opt tour optimal unless an exact solver proved it on that matrix.
- Report the seed, size, metric, repetitions, engine mode and build flags alongside any result.
- For external services, measure network latency separately; it is not part of algorithm runtime.
