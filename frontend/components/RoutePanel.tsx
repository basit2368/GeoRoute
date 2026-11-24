"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Navigation, Play, Route as RouteIcon } from "lucide-react";
import { apiPost } from "@/lib/api";
import { formatDistance, formatDuration, formatInteger, formatNumber } from "@/lib/format";
import type {
  DistanceMetric,
  GeoPoint,
  RouteOptimizeResponse,
  TourAlgorithm,
  TourResult,
} from "@/lib/types";
import { EmptyState, Panel, Spinner } from "./ui";

interface RoutePanelProps {
  points: GeoPoint[];
  depotIndex: number;
  limits?: Record<string, number>;
  onResult: (response: RouteOptimizeResponse) => void;
  onError: (message: string | null) => void;
}

const ALGORITHMS: { value: TourAlgorithm; label: string; note: string }[] = [
  { value: "exact", label: "Exact TSP", note: "small instances" },
  { value: "nearest_neighbor", label: "Nearest neighbour", note: "O(n²)" },
  { value: "two_opt", label: "2-Opt", note: "local search" },
];

const METRICS: { value: DistanceMetric; label: string }[] = [
  { value: "straight_line", label: "Straight line (Haversine)" },
  { value: "road_distance", label: "Road distance (OSRM)" },
  { value: "road_duration", label: "Road duration (OSRM)" },
  { value: "precomputed", label: "Precomputed matrix" },
];

export default function RoutePanel({
  points,
  depotIndex,
  limits,
  onResult,
  onError,
}: RoutePanelProps) {
  const [metric, setMetric] = useState<DistanceMetric>("straight_line");
  const [algorithms, setAlgorithms] = useState<TourAlgorithm[]>([
    "nearest_neighbor",
    "two_opt",
  ]);
  const [includeGeometry, setIncludeGeometry] = useState(true);
  const [matrixText, setMatrixText] = useState("");
  const [response, setResponse] = useState<RouteOptimizeResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const maxExact = limits?.max_exact_locations ?? 10;
  const maxOsrm = limits?.max_osrm_locations ?? 25;

  function toggle(algorithm: TourAlgorithm) {
    setAlgorithms((current) =>
      current.includes(algorithm)
        ? current.length === 1
          ? current
          : current.filter((item) => item !== algorithm)
        : [...current, algorithm],
    );
  }

  function parseMatrix(): number[][] | undefined {
    if (metric !== "precomputed" || !matrixText.trim()) return undefined;
    try {
      const parsed = JSON.parse(matrixText) as number[][];
      if (
        !Array.isArray(parsed) ||
        parsed.length !== points.length ||
        parsed.some((row) => !Array.isArray(row) || row.length !== points.length)
      ) {
        throw new Error(`Matrix must be ${points.length}×${points.length}`);
      }
      return parsed;
    } catch (error) {
      throw new Error(
        error instanceof Error ? `Invalid matrix: ${error.message}` : "Invalid matrix",
      );
    }
  }

  async function run() {
    setBusy(true);
    onError(null);
    try {
      const result = await apiPost<RouteOptimizeResponse>("/api/route/optimize", {
        locations: points,
        depot_index: depotIndex,
        metric,
        algorithms,
        include_geometry: includeGeometry,
        ...(metric === "precomputed" ? { matrix: parseMatrix() } : {}),
      });
      setResponse(result);
      onResult(result);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Route request failed");
    } finally {
      setBusy(false);
    }
  }

  function formatCost(result: TourResult): string {
    if (response?.unit === "s") return formatDuration(result.cost);
    if (response?.unit === "m") return formatDistance(result.cost);
    return formatNumber(result.cost, 2);
  }

  const exactDisabled = points.length > maxExact;
  const roadDisabled = points.length > maxOsrm;

  return (
    <Panel
      title="Route optimization"
      subtitle="Compare an exact TSP baseline with scalable heuristics on a single cost matrix."
      icon={<Navigation className="h-4 w-4 text-sky-400" />}
      action={<span className="chip">{points.length} locations</span>}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <label className="label" htmlFor="metric">
            Cost metric
          </label>
          <select
            id="metric"
            className="input"
            value={metric}
            onChange={(event) => setMetric(event.target.value as DistanceMetric)}
          >
            {METRICS.map((item) => (
              <option
                key={item.value}
                value={item.value}
                disabled={item.value.startsWith("road") && roadDisabled}
              >
                {item.label}
                {item.value.startsWith("road") && roadDisabled ? ` (max ${maxOsrm})` : ""}
              </option>
            ))}
          </select>
          <p className="mt-1.5 text-[10px] leading-relaxed text-slate-500">
            {metric === "straight_line" && "Haversine metres. Never presented as road distance."}
            {metric === "road_distance" && "OSRM driving distance in metres; road geometry is requested separately."}
            {metric === "road_duration" && "OSRM driving duration in seconds; failures are reported, not replaced."}
            {metric === "precomputed" && "Paste a JSON square symmetric matrix. Units are your own."}
          </p>
        </div>

        <div>
          <span className="label">Algorithms</span>
          <div className="space-y-1.5">
            {ALGORITHMS.map((item) => {
              const active = algorithms.includes(item.value);
              const disabled = item.value === "exact" && exactDisabled;
              return (
                <button
                  key={item.value}
                  type="button"
                  disabled={disabled}
                  onClick={() => toggle(item.value)}
                  className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-xs transition disabled:cursor-not-allowed disabled:opacity-35 ${
                    active
                      ? "border-sky-400/40 bg-sky-500/10 text-sky-200"
                      : "border-white/10 bg-white/[0.02] text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <span className="flex items-center gap-2 font-semibold">
                    <span
                      className={`flex h-3.5 w-3.5 items-center justify-center rounded border ${
                        active ? "border-sky-400 bg-sky-500" : "border-slate-600"
                      }`}
                    >
                      {active && <CheckCircle2 className="h-3 w-3 text-ink-950" />}
                    </span>
                    {item.label}
                  </span>
                  <span className="font-mono text-[10px] opacity-70">
                    {item.value === "exact" && exactDisabled ? `max ${maxExact}` : item.note}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {metric === "precomputed" && (
        <div className="mt-4">
          <label className="label" htmlFor="matrix">
            Cost matrix (JSON)
          </label>
          <textarea
            id="matrix"
            className="input h-28 resize-y font-mono text-[11px]"
            placeholder='[[0, 100, 250], [100, 0, 180], [250, 180, 0]]'
            value={matrixText}
            onChange={(event) => setMatrixText(event.target.value)}
          />
        </div>
      )}

      <label className="mt-4 flex items-center gap-2 text-xs text-slate-400">
        <input
          type="checkbox"
          checked={includeGeometry}
          onChange={(event) => setIncludeGeometry(event.target.checked)}
          className="h-4 w-4 accent-sky-500"
        />
        Draw the selected route on the map
      </label>

      <button
        className="btn btn-primary mt-4 w-full"
        onClick={() => void run()}
        disabled={busy || points.length < 2}
      >
        {busy ? <Spinner label="Optimizing" /> : <><Play className="h-4 w-4" /> Optimize route</>}
      </button>

      {!response && (
        <div className="mt-4"><EmptyState message="Run an optimization to see route metrics." /></div>
      )}

      {response && (
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="chip">Matrix: {response.matrix_source}</span>
            <span className="chip">Unit: {response.unit}</span>
            <span className="chip">Depot: #{response.depot_index + 1}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Algorithm</th>
                  <th>Tour order</th>
                  <th>Cost</th>
                  <th>Dist. evals</th>
                  <th>Time</th>
                  <th>Gap</th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((result) => (
                  <tr key={result.algorithm}>
                    <td className="font-medium text-slate-200">
                      {ALGORITHMS.find((item) => item.value === result.algorithm)?.label}
                    </td>
                    <td className="font-mono text-[10px]">
                      {result.route.map((index) => index + 1).join(" → ")} → {result.route[0] + 1}
                    </td>
                    <td className="font-mono font-semibold text-slate-100">{formatCost(result)}</td>
                    <td className="font-mono">{formatInteger(result.distance_evaluations)}</td>
                    <td className="font-mono text-brand-300">{formatNumber(result.runtime_ms, 3)} ms</td>
                    <td className="font-mono">
                      {result.optimality_gap_percent === null
                        ? "—"
                        : `${formatNumber(result.optimality_gap_percent, 2)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {response.geometry_source && (
            <p className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-[10px] leading-relaxed text-slate-500">
              <RouteIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {response.geometry_source}
            </p>
          )}

          {response.warnings.map((warning) => (
            <p
              key={warning}
              className="flex items-start gap-2 rounded-lg border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-300"
            >
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {warning}
            </p>
          ))}
        </div>
      )}
    </Panel>
  );
}
