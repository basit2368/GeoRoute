"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Download, Gauge, Play } from "lucide-react";
import { apiExport, apiPost } from "@/lib/api";
import { formatInteger, formatNumber, parseSizes } from "@/lib/format";
import type { BenchmarkPayload, BenchmarkRow } from "@/lib/types";
import { EmptyState, ErrorBanner, Panel, Spinner } from "./ui";

type ChartMode = "runtime" | "operations";

interface BenchmarkPanelProps {
  limits?: Record<string, number>;
}

function chartData(payload: BenchmarkPayload | null, mode: ChartMode) {
  if (!payload) return [];
  const grouped = new Map<number, Record<string, string | number>>();
  const field = mode === "runtime" ? "median_runtime_ms" : "distance_evaluations";
  for (const row of payload.series) {
    const size = Number(row.input_size);
    if (!Number.isFinite(size)) continue;
    const entry = grouped.get(size) ?? { size };
    entry[String(row.algorithm)] = Number(row[field] ?? 0);
    grouped.set(size, entry);
  }
  return [...grouped.values()].sort((a, b) => Number(a.size) - Number(b.size));
}

const TOOLTIP_STYLE = {
  backgroundColor: "#0b1224",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 10,
  fontSize: 11,
};

export default function BenchmarkPanel({ limits }: BenchmarkPanelProps) {
  const [closestSizes, setClosestSizes] = useState("100,500,1000,5000,10000");
  const [routeSizes, setRouteSizes] = useState("5,8,10,25,50,100");
  const [repetitions, setRepetitions] = useState("3");
  const [mode, setMode] = useState<ChartMode>("runtime");
  const [closest, setClosest] = useState<BenchmarkPayload | null>(null);
  const [route, setRoute] = useState<BenchmarkPayload | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const maxClosest = limits?.max_closest_pair_points ?? 10_000;
  const maxRoute = limits?.max_nearest_neighbor_locations ?? 250;
  const closestChart = useMemo(() => chartData(closest, mode), [closest, mode]);
  const routeChart = useMemo(() => chartData(route, mode), [route, mode]);

  async function run(kind: "closest" | "route") {
    const sizes = parseSizes(kind === "closest" ? closestSizes : routeSizes, kind === "closest" ? maxClosest : maxRoute);
    const reps = Number.parseInt(repetitions, 10);
    if (!sizes || !Number.isFinite(reps) || reps < 1 || reps > 10) {
      setError(`Enter valid sizes (2–${kind === "closest" ? maxClosest : maxRoute}) and 1–10 repetitions.`);
      return;
    }
    setBusy(kind);
    setError(null);
    try {
      if (kind === "closest") {
        setClosest(
          await apiPost<BenchmarkPayload>("/api/benchmarks/closest-pair", {
            sizes,
            repetitions: reps,
            seed: 42,
          }),
        );
      } else {
        setRoute(
          await apiPost<BenchmarkPayload>("/api/benchmarks/route", {
            sizes,
            repetitions: reps,
            seed: 42,
            algorithms: ["exact", "nearest_neighbor", "two_opt"],
          }),
        );
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Benchmark request failed");
    } finally {
      setBusy(null);
    }
  }

  async function download(kind: "closest" | "route", payload: BenchmarkPayload) {
    setError(null);
    try {
      await apiExport(
        `GeoRoute ${kind === "closest" ? "closest-pair" : "route"} benchmark`,
        "csv",
        payload,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Export failed");
    }
  }

  function table(payload: BenchmarkPayload, routeBench: boolean) {
    if (!payload.series.length) return <EmptyState message="No runs were recorded." />;
    const columns: { key: string; label: string; render: (row: BenchmarkRow) => string }[] = [
      { key: "input_size", label: "n", render: (row) => formatInteger(Number(row.input_size)) },
      { key: "algorithm", label: "Algorithm", render: (row) => String(row.algorithm) },
      {
        key: "median_runtime_ms",
        label: "Median ms",
        render: (row) => formatNumber(Number(row.median_runtime_ms), 3),
      },
      {
        key: "distance_evaluations",
        label: "Dist. evals",
        render: (row) => formatInteger(Number(row.distance_evaluations)),
      },
      routeBench
        ? { key: "route_cost_m", label: "Cost (m)", render: (row) => formatNumber(Number(row.route_cost_m), 1) }
        : { key: "distance_m", label: "Distance (m)", render: (row) => formatNumber(Number(row.distance_m), 2) },
      {
        key: "gap",
        label: "Gap",
        render: (row) =>
          row.optimality_gap_percent === null || row.optimality_gap_percent === undefined
            ? "—"
            : `${formatNumber(Number(row.optimality_gap_percent), 2)}%`,
      },
    ];

    return (
      <div className="max-h-64 overflow-auto">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {payload.series.map((row, index) => (
              <tr key={`${row.input_size}-${row.algorithm}-${index}`}>
                {columns.map((column) => (
                  <td key={column.key} className="font-mono text-[11px]">
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      <Panel
        title="Benchmark controls"
        subtitle="Repeatable experiments with identical generated inputs. Network and rendering time are excluded."
        icon={<Gauge className="h-4 w-4 text-brand-400" />}
      >
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="label" htmlFor="closest-sizes">Closest-pair sizes</label>
            <input
              id="closest-sizes"
              className="input font-mono text-xs"
              value={closestSizes}
              onChange={(event) => setClosestSizes(event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="route-sizes">Route sizes</label>
            <input
              id="route-sizes"
              className="input font-mono text-xs"
              value={routeSizes}
              onChange={(event) => setRouteSizes(event.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="repetitions">Repetitions</label>
            <input
              id="repetitions"
              className="input font-mono"
              value={repetitions}
              inputMode="numeric"
              onChange={(event) => setRepetitions(event.target.value)}
            />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className="btn btn-primary"
            disabled={busy !== null}
            onClick={() => void run("closest")}
          >
            {busy === "closest" ? <Spinner label="Running" /> : <><Play className="h-4 w-4" /> Closest pair</>}
          </button>
          <button
            className="btn btn-success"
            disabled={busy !== null}
            onClick={() => void run("route")}
          >
            {busy === "route" ? <Spinner label="Running" /> : <><Play className="h-4 w-4" /> Route optimizer</>}
          </button>
          <div className="ml-auto flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.02] p-1">
            {(["runtime", "operations"] as ChartMode[]).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setMode(item)}
                className={`rounded-md px-3 py-1.5 text-[11px] font-medium capitalize transition ${
                  mode === item ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel
          title="Closest-pair scaling"
          subtitle="Brute force O(n²) versus divide and conquer O(n log n)."
          icon={<BarChart3 className="h-4 w-4 text-amber-400" />}
          action={
            closest && (
              <button className="btn px-2.5 py-1.5 text-[11px]" onClick={() => void download("closest", closest)}>
                <Download className="h-3.5 w-3.5" /> CSV
              </button>
            )
          }
        >
          {closestChart.length ? (
            <>
              <ResponsiveContainer width="100%" height={230}>
                <LineChart data={closestChart} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 4" />
                  <XAxis dataKey="size" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="brute_force" name="Brute force" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="divide_conquer" name="Divide & conquer" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
              <div className="mt-3">{table(closest!, false)}</div>
            </>
          ) : (
            <EmptyState message="Run the closest-pair benchmark to plot scaling." />
          )}
        </Panel>

        <Panel
          title="Route optimization scaling"
          subtitle="Exact factorial growth versus heuristic scaling, with optimality gaps on small instances."
          icon={<BarChart3 className="h-4 w-4 text-sky-400" />}
          action={
            route && (
              <button className="btn px-2.5 py-1.5 text-[11px]" onClick={() => void download("route", route)}>
                <Download className="h-3.5 w-3.5" /> CSV
              </button>
            )
          }
        >
          {routeChart.length ? (
            <>
              <ResponsiveContainer width="100%" height={230}>
                <BarChart data={routeChart} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 4" />
                  <XAxis dataKey="size" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="nearest_neighbor" name="Nearest neighbour" fill="#0ea5e9" />
                  <Bar dataKey="two_opt" name="2-Opt" fill="#10b981" />
                  <Bar dataKey="exact" name="Exact" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-3">{table(route!, true)}</div>
              {route!.skipped && route!.skipped.length > 0 && (
                <p className="mt-3 text-[10px] text-slate-500">
                  {route!.skipped.length} run(s) skipped by configured exact/heuristic limits.
                </p>
              )}
            </>
          ) : (
            <EmptyState message="Run the route benchmark to plot scaling." />
          )}
        </Panel>
      </div>
    </div>
  );
}
