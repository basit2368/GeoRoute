export interface GeoPoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
}

export type ClosestAlgorithm = "brute_force" | "divide_conquer";
export type TourAlgorithm = "exact" | "nearest_neighbor" | "two_opt";
export type DistanceMetric =
  | "straight_line"
  | "road_distance"
  | "road_duration"
  | "precomputed";

export interface DatasetOut {
  id: string;
  name: string;
  source: string;
  seed: number | null;
  points: GeoPoint[];
}

export interface ClosestPairResult {
  algorithm: ClosestAlgorithm;
  pair: number[];
  pair_ids: string[];
  pair_names: string[];
  distance_m: number;
  haversine_m: number;
  distance_evaluations: number;
  comparisons: number;
  runtime_ms: number;
}

export interface ClosestPairResponse {
  model: string;
  projection: string;
  unit: string;
  point_count: number;
  results: ClosestPairResult[];
  agree: boolean | null;
}

export interface TourResult {
  algorithm: TourAlgorithm;
  route: number[];
  ordered_ids: string[];
  cost: number;
  distance_evaluations: number;
  comparisons: number;
  improvement_passes: number;
  runtime_ms: number;
  optimality_gap_percent: number | null;
}

export interface RouteOptimizeResponse {
  metric: DistanceMetric;
  unit: string;
  matrix_source: string;
  depot_index: number;
  location_count: number;
  results: TourResult[];
  geometry: number[][] | null;
  geometry_source: string | null;
  warnings: string[];
}

export type BenchmarkRow = Record<string, string | number | null | undefined>;

export interface BenchmarkPayload {
  benchmark: string;
  config: Record<string, unknown>;
  series: BenchmarkRow[];
  skipped?: Array<Record<string, string | number>>;
}

export interface HealthPayload {
  status: string;
  version: string;
  engine: { mode: string; version: string; path: string | null };
  limits: Record<string, number>;
  routing: { base_url: string; profile: string };
}
