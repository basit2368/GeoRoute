# API reference

Base URL in development: `http://localhost:8000`. Interactive Swagger docs: `/docs`.

All request/response bodies are JSON except `/api/datasets/import`, which accepts `multipart/form-data` with a `file` field.

---

## `GET /api/health`

Returns the active engine, version, configured limits and routing service.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "engine": { "mode": "native-cpp17", "version": "1.0.0", "path": "..." },
  "limits": {
    "max_closest_pair_points": 10000,
    "max_exact_locations": 10,
    "max_nearest_neighbor_locations": 250,
    "max_osrm_locations": 25
  },
  "routing": { "base_url": "https://router.project-osrm.org", "profile": "driving" }
}
```

`engine.mode` is either `native-cpp17` or `python-fallback`.

---

## `POST /api/datasets/synthetic`

Generate a deterministic clustered dataset around Karachi neighbourhoods.

```json
{
  "count": 100,
  "seed": 42,
  "clustered": true,
  "name": "Karachi synthetic (100)"
}
```

Optional `bounds`: `{"min_lat":24.70,"max_lat":24.98,"min_lon":66.90,"max_lon":67.35}`.

Response: a `DatasetOut` object with an `id` and `points[]`.

---

## `POST /api/datasets/import`

CSV columns may be `lat,lng` / `latitude,longitude` / `y,x`. Optional `name` and `id` columns are preserved.

```bash
curl -F "file=@data/sample_karachi.csv" http://localhost:8000/api/datasets/import
```

---

## `GET /api/datasets` and `GET /api/datasets/{id}`

List or retrieve datasets stored in the process memory. Datasets do not persist across backend restarts.

---

## `POST /api/closest-pair`

Runs one or both algorithms on identical UTM-projected coordinates.

```json
{
  "points": [
    {"id": "a", "name": "DHA", "lat": 24.7905, "lng": 67.0308},
    {"id": "b", "name": "Clifton", "lat": 24.8205, "lng": 67.0055}
  ],
  "algorithms": ["brute_force", "divide_conquer"]
}
```

Response highlights:

```json
{
  "model": "planar Euclidean closest pair on WGS84 / UTM zone 42N",
  "projection": "UTM zone 42N (metres, k0=0.9996)",
  "unit": "m",
  "agree": true,
  "results": [
    {
      "algorithm": "brute_force",
      "pair": [0, 1],
      "pair_ids": ["a", "b"],
      "distance_m": 4194.04,
      "haversine_m": 4201.09,
      "distance_evaluations": 1,
      "comparisons": 1,
      "runtime_ms": 0.004
    }
  ]
}
```

The `distance_m` value is the projected Euclidean result; `haversine_m` is a separate geodesic reference.

---

## `POST /api/route/optimize`

```json
{
  "locations": [
    {"id": "depot", "lat": 24.86, "lng": 67.0},
    {"id": "a", "lat": 24.861, "lng": 67.001},
    {"id": "b", "lat": 24.862, "lng": 67.002}
  ],
  "depot_index": 0,
  "metric": "straight_line",
  "algorithms": ["exact", "nearest_neighbor", "two_opt"],
  "include_geometry": true
}
```

`metric` options:

| Value | Matrix source | Unit |
| --- | --- | --- |
| `straight_line` | Haversine | `m` |
| `road_distance` | OSRM table | `m` |
| `road_duration` | OSRM table | `s` |
| `precomputed` | `matrix` field | caller-defined |

For `precomputed`, send a square symmetric matrix, for example `[[0,100,250],[100,0,180],[250,180,0]]`. Asymmetric matrices are rejected because the tour-comparison model is undirected unless internal reversals are explicitly used by the 2-Opt implementation.

Response highlights:

```json
{
  "metric": "straight_line",
  "unit": "m",
  "matrix_source": "haversine great-circle distance",
  "depot_index": 0,
  "results": [
    {
      "algorithm": "two_opt",
      "route": [0, 2, 1],
      "cost": 320.5,
      "runtime_ms": 0.031,
      "optimality_gap_percent": 0.0
    }
  ],
  "geometry": [[67.0, 24.86], [67.002, 24.862], [67.001, 24.861], [67.0, 24.86]],
  "geometry_source": "straight segments between selected locations (not road geometry)",
  "warnings": []
}
```

For OSRM metrics, `geometry_source` begins with `OSRM` when road geometry was retrieved. If the service fails, the response still returns the algorithm results but sets `warnings` and leaves `geometry` as `null`.

---

## `POST /api/benchmarks/closest-pair`

```json
{"sizes":[100,500,1000],"repetitions":3,"seed":42,"algorithms":["brute_force","divide_conquer"]}
```

Returns `config` and `series[]`. Each row contains size, algorithm, runtime summary, operation counters and the resulting distance.

---

## `POST /api/benchmarks/route`

```json
{"sizes":[5,8,10,25],"repetitions":3,"seed":42,"algorithms":["exact","nearest_neighbor","two_opt"]}
```

Uses a Haversine matrix so results are reproducible without network access. Runs above configured limits appear in `skipped[]` with a reason.

---

## `POST /api/reports/export`

```json
{
  "title": "GeoRoute closest-pair benchmark",
  "format": "csv",
  "payload": { "series": [ ... ] }
}
```

`format` can be `csv`, `markdown` or `json`. Returns a downloadable response with an appropriate `Content-Disposition` header.

---

## Error handling

| Status | Meaning |
| --- | --- |
| `400` / `422` | Invalid coordinates, count, depot, matrix or limit violation |
| `500` | Native engine error |
| `502` | OSRM-compatible service unavailable or returned an unusable response |

Every error includes a `detail` string suitable for display in the UI.
