"use client";

import { useState } from "react";
import { CheckCircle2, GitCompareArrows, Play, Ruler } from "lucide-react";
import { apiPost } from "@/lib/api";
import { formatDistance, formatInteger, formatNumber } from "@/lib/format";
import type { ClosestAlgorithm, ClosestPairResponse } from "@/lib/types";
import { EmptyState, Panel, Spinner } from "./ui";

interface ClosestPairPanelProps {
  points: { id: string }[];
  onResult: (response: ClosestPairResponse) => void;
  onError: (message: string | null) => void;
}

const ALGORITHMS: { value: ClosestAlgorithm; label: string; complexity: string }[] = [
  { value: "brute_force", label: "Brute force", complexity: "O(n²)" },
  { value: "divide_conquer", label: "Divide & conquer", complexity: "O(n log n)" },
];

export default function ClosestPairPanel({
  points,
  onResult,
  onError,
}: ClosestPairPanelProps) {
  const [algorithms, setAlgorithms] = useState<ClosestAlgorithm[]>([
    "brute_force",
    "divide_conquer",
  ]);
  const [response, setResponse] = useState<ClosestPairResponse | null>(null);
  const [busy, setBusy] = useState(false);

  function toggle(algorithm: ClosestAlgorithm) {
    setAlgorithms((current) =>
      current.includes(algorithm)
        ? current.length === 1
          ? current
          : current.filter((item) => item !== algorithm)
        : [...current, algorithm],
    );
  }

  async function run() {
    setBusy(true);
    onError(null);
    try {
      const result = await apiPost<ClosestPairResponse>("/api/closest-pair", {
        points,
        algorithms,
      });
      setResponse(result);
      onResult(result);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Closest-pair request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title="Closest pair"
      subtitle="Find the two nearest projected points and compare both algorithms on identical input."
      icon={<Ruler className="h-4 w-4 text-amber-400" />}
      action={<span className="chip">{points.length} points</span>}
    >
      <div className="flex flex-wrap gap-2">
        {ALGORITHMS.map((item) => {
          const active = algorithms.includes(item.value);
          return (
            <button
              key={item.value}
              type="button"
              onClick={() => toggle(item.value)}
              className={`rounded-lg border px-3 py-2 text-left text-xs transition ${
                active
                  ? "border-amber-400/40 bg-amber-500/10 text-amber-200"
                  : "border-white/10 bg-white/[0.02] text-slate-500 hover:text-slate-300"
              }`}
            >
              <span className="flex items-center gap-2 font-semibold">
                <span
                  className={`flex h-3.5 w-3.5 items-center justify-center rounded border ${
                    active ? "border-amber-400 bg-amber-500" : "border-slate-600"
                  }`}
                >
                  {active && <CheckCircle2 className="h-3 w-3 text-ink-950" />}
                </span>
                {item.label}
              </span>
              <span className="mt-1 block font-mono text-[10px] opacity-70">{item.complexity}</span>
            </button>
          );
        })}
      </div>

      <button
        className="btn btn-primary mt-4 w-full"
        onClick={() => void run()}
        disabled={busy || points.length < 2}
      >
        {busy ? <Spinner label="Running" /> : <><Play className="h-4 w-4" /> Run comparison</>}
      </button>

      <p className="mt-3 text-[10px] leading-relaxed text-slate-500">
        Distance model: planar Euclidean in WGS84 / UTM zone 42N (metres). The Haversine
        column is a separate geodesic reference for the returned pair.
      </p>

      {!response && <div className="mt-4"><EmptyState message="Run the comparison to see results." /></div>}

      {response && (
        <div className="mt-4 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="metric-card">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Minimum distance</p>
              <p className="mt-1 font-mono text-lg font-semibold text-amber-300">
                {formatDistance(response.results[0]?.distance_m)}
              </p>
            </div>
            <div className="metric-card">
              <p className="text-[10px] uppercase tracking-wider text-slate-500">Outputs agree</p>
              <p className="mt-1 text-lg font-semibold">
                {response.agree === null ? (
                  <span className="text-slate-500">n/a</span>
                ) : response.agree ? (
                  <span className="flex items-center gap-1.5 text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" /> Yes
                  </span>
                ) : (
                  <span className="text-rose-400">No</span>
                )}
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Algorithm</th>
                  <th>Pair</th>
                  <th>UTM m</th>
                  <th>Haversine m</th>
                  <th>Dist. evals</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {response.results.map((result) => (
                  <tr key={result.algorithm}>
                    <td className="font-medium text-slate-200">
                      {result.algorithm === "brute_force" ? "Brute force" : "Divide & conquer"}
                    </td>
                    <td className="font-mono text-[11px]">
                      {result.pair_names.join(" ↔ ")}
                    </td>
                    <td className="font-mono">{formatNumber(result.distance_m, 2)}</td>
                    <td className="font-mono">{formatNumber(result.haversine_m, 2)}</td>
                    <td className="font-mono">{formatInteger(result.distance_evaluations)}</td>
                    <td className="font-mono text-brand-300">{formatNumber(result.runtime_ms, 3)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {response.agree && (
            <p className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-[11px] text-emerald-300">
              <GitCompareArrows className="h-3.5 w-3.5" />
              Both algorithms returned the same minimum distance on this dataset.
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}
