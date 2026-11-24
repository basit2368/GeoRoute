# Algorithm notes

This document explains what the GeoRoute engine actually computes, which distance model each module uses, and what the reported operation counters mean.

## 1. Closest pair of points

**Input:** `n` planar points `(x, y)` produced by projecting latitude/longitude into UTM zone 42N metres.

**Output:** two distinct point indices with the minimum Euclidean distance.

### 1.1 Brute force

Every unordered pair is compared once:

```text
compare(i, j) for 0 <= i < j < n
distance(p, q) = sqrt((px - qx)^2 + (py - qy)^2)
```

- Distance evaluations: `n(n − 1) / 2`
- Time: `O(n²)`
- Auxiliary space: `O(1)` beyond the input

It is the correctness baseline: every other closest-pair result can be checked against it on identical input.

### 1.2 Divide and conquer

The implementation follows the standard planar algorithm:

1. Sort points by `x`, keeping an auxiliary order sorted by `y`.
2. Recursively solve the left and right halves.
3. Let `δ` be the smaller distance returned by the halves.
4. Merge the `y` orders in linear time.
5. Build a vertical strip of points whose `x` distance from the dividing line is at most `δ`.
6. For each strip point, check following strip points while their `y` difference is at most `δ`.

The planar packing argument bounds the number of strip comparisons per point by a constant, so:

```text
T(n) = 2T(n/2) + O(n)   =>   O(n log n)
```

The initial sort costs `O(n log n)` and does not change the asymptotic bound. The implementation preserves the `y` order through a linear merge instead of re-sorting subproblems at every recursive level.

> The strip comparison uses `<= δ` rather than `< δ`. This keeps exact duplicate points visible when the current best distance is zero and the duplicate lies across the recursion boundary.

### 1.3 Why projection matters

The classical closest-pair proof assumes Euclidean planar coordinates. Latitude/longitude are angular coordinates on a curved surface, so GeoRoute projects them first:

- Datum: WGS84
- Zone: UTM 42N (central meridian 69°E, `k0 = 0.9996`)
- Units: metres
- Demo region: Karachi, Pakistan

UTM is conformal and locally accurate, but it is not a geodesic. The reported closest-pair distance is a **projected Euclidean distance**, not a road distance. A Haversine value for the returned pair is shown separately as a reference.

---

## 2. Multi-destination routing

**Model:** a depot plus destinations, represented by a square cost matrix `C[i][j]`. A tour starts at the depot, visits every other location once and returns to the depot.

The selected cost matrix determines the objective:

| Metric | Source | Unit | Notes |
| --- | --- | --- | --- |
| `straight_line` | Haversine | metres | Great-circle estimate; not drivable |
| `road_distance` | OSRM table | metres | Road-network distance |
| `road_duration` | OSRM table | seconds | Can be asymmetric because of one-way streets |
| `precomputed` | Client JSON | arbitrary | Must be square, finite, non-negative and symmetric |

### 2.1 Exact brute-force TSP

With the depot fixed, the solver enumerates permutations of the remaining `n − 1` destinations:

```text
permutations = (n − 1)!
cost per tour = n matrix lookups
time = O(n · n!)
space = O(n) for the current/best route
```

The exact solver is restricted to small instances. The API default guard is 10 locations; the native engine also rejects more than 11. At 10 locations the engine evaluates roughly 3.6 million tours, which is still suitable for a controlled demonstration.

### 2.2 Nearest neighbour

Starting from the depot, repeatedly choose the closest unvisited destination, then return to the depot.

- With a prepared matrix: `O(n²)` time
- Matrix storage: `O(n²)` space
- Guarantee: none. The result is a heuristic baseline, not an optimal tour.

### 2.3 2-Opt local search

Starting from a nearest-neighbour tour, consider replacing two tour edges `(a, b)` and `(c, d)` with `(a, c)` and `(b, d)` by reversing the segment between `b` and `c`.

For a symmetric matrix:

```text
delta = C[a][c] + C[b][d] - C[a][b] - C[c][d]
```

A reversal is accepted when `delta < -1e-9`. One full pass is `O(n²)`; the engine runs at most 100 passes or until no improving move exists.

For an asymmetric matrix, reversing a segment also reverses its internal directed edges. The engine detects asymmetry and includes those internal edges in the delta calculation, so road-duration matrices are handled correctly.

### 2.4 Optimality gap

When an exact tour cost is available for the **same matrix**:

```text
gap (%) = (heuristic_cost - optimal_cost) / optimal_cost × 100
```

A gap of `0%` means the heuristic matched the exact optimum on that instance. It does not prove optimality on a different matrix or a larger instance.

---

## 3. Operation counters

All algorithms are implemented with explicit primitive-operation counters.

| Counter | Closest pair | TSP |
| --- | --- | --- |
| `distance_evaluations` | Number of Euclidean distance computations (engine) or matrix lookups used as distance evaluations | Number of cost-matrix lookups |
| `comparisons` | Strip boundary checks and best-distance updates | Candidate selections, best-cost updates, 2-Opt acceptance tests |
| `improvement_passes` | n/a | Number of 2-Opt passes executed |
| `elapsed_ms` | `std::chrono::high_resolution_clock` measured inside the C++ call | Same |

These counters are implementation-specific primitives, not universal operation definitions. They are useful for comparing algorithms on this implementation under identical inputs.

---

## 4. Geographic separation of concerns

GeoRoute deliberately separates three questions:

1. **Which two points are geometrically nearest?** → projected Euclidean closest pair.
2. **How long is a great-circle hop?** → Haversine matrix.
3. **How would a vehicle actually travel?** → OSRM road matrix and road geometry.

The system never silently substitutes one answer for another. If an OSRM table or geometry request fails, the API returns an explicit error or warning, and the UI labels the geometry as straight segments when no road geometry was used.

---

## 5. References

- Cormen, Leiserson, Rivest & Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022.
- Kleinberg & Tardos, *Algorithm Design*, Pearson, 2005.
- OpenStreetMap contributors, copyright and license: https://www.openstreetmap.org/copyright
- Project OSRM API documentation: https://project-osrm.org/docs/
- Snyder, *Map Projections: A Working Manual*, USGS Professional Paper 1395 (UTM formulae).
