"use client";

import { useRef, useState } from "react";
import { Database, MapPin, RotateCcw, Sparkles, Trash2, Upload } from "lucide-react";
import { apiPost, apiPostFile } from "@/lib/api";
import type { DatasetOut, GeoPoint } from "@/lib/types";
import { Panel, Spinner } from "./ui";

interface DatasetPanelProps {
  points: GeoPoint[];
  depotIndex: number;
  onChange: (points: GeoPoint[]) => void;
  onSetDepot: (index: number) => void;
  onError: (message: string | null) => void;
}

export default function DatasetPanel({
  points,
  depotIndex,
  onChange,
  onSetDepot,
  onError,
}: DatasetPanelProps) {
  const [count, setCount] = useState("40");
  const [seed, setSeed] = useState("42");
  const [clustered, setClustered] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(action: string, task: () => Promise<void>) {
    setBusy(action);
    onError(null);
    try {
      await task();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Dataset request failed");
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function generate() {
    void run("generate", async () => {
      const safeCount = Math.min(10_000, Math.max(2, Number.parseInt(count, 10) || 40));
      const dataset = await apiPost<DatasetOut>("/api/datasets/synthetic", {
        count: safeCount,
        seed: Number.parseInt(seed, 10) || 42,
        clustered,
        name: `Karachi synthetic (${safeCount})`,
      });
      onChange(dataset.points);
      onSetDepot(0);
    });
  }

  function importCsv(file: File | undefined) {
    if (!file) return;
    void run("import", async () => {
      const dataset = await apiPostFile<DatasetOut>("/api/datasets/import", file);
      onChange(dataset.points);
      onSetDepot(0);
    });
  }

  return (
    <Panel
      title="Dataset controls"
      subtitle="Build a synthetic Karachi dataset, import CSV, or manage map points."
      icon={<Database className="h-4 w-4 text-brand-400" />}
    >
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="point-count">
            Points
          </label>
          <input
            id="point-count"
            className="input font-mono"
            value={count}
            inputMode="numeric"
            onChange={(event) => setCount(event.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="seed">
            Random seed
          </label>
          <input
            id="seed"
            className="input font-mono"
            value={seed}
            inputMode="numeric"
            onChange={(event) => setSeed(event.target.value)}
          />
        </div>
      </div>

      <label className="mt-3 flex cursor-pointer items-center gap-2 text-xs text-slate-400">
        <input
          type="checkbox"
          checked={clustered}
          onChange={(event) => setClustered(event.target.checked)}
          className="h-4 w-4 accent-sky-500"
        />
        Cluster around Karachi neighbourhoods
      </label>

      <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
        <button className="btn btn-primary" onClick={generate} disabled={busy !== null}>
          {busy === "generate" ? <Spinner label="Generating" /> : <><Sparkles className="h-4 w-4" /> Generate</>}
        </button>
        <button className="btn" onClick={() => fileRef.current?.click()} disabled={busy !== null}>
          {busy === "import" ? <Spinner label="Importing" /> : <><Upload className="h-4 w-4" /> Import CSV</>}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(event) => importCsv(event.target.files?.[0])}
        />
        <button
          className="btn btn-danger"
          onClick={() => {
            onChange([]);
            onSetDepot(0);
          }}
          disabled={points.length === 0 || busy !== null}
        >
          <Trash2 className="h-4 w-4" /> Clear all
        </button>
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between">
          <p className="label mb-0">Locations ({points.length})</p>
          <span className="text-[10px] text-slate-600">CSV: lat,lng,name</span>
        </div>
        <div className="max-h-52 space-y-1.5 overflow-y-auto pr-1">
          {points.length === 0 && (
            <p className="rounded-lg border border-dashed border-white/10 px-3 py-5 text-center text-xs text-slate-600">
              No locations yet
            </p>
          )}
          {points.map((point, index) => (
            <div
              key={point.id}
              className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 text-xs ${
                index === depotIndex
                  ? "border-emerald-500/40 bg-emerald-500/10"
                  : "border-white/5 bg-white/[0.02]"
              }`}
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/10 font-mono text-[10px] text-slate-300">
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-slate-200">{point.name}</p>
                <p className="font-mono text-[10px] text-slate-500">
                  {point.lat.toFixed(5)}, {point.lng.toFixed(5)}
                </p>
              </div>
              {index === depotIndex ? (
                <span className="text-[10px] font-semibold uppercase text-emerald-400">Depot</span>
              ) : (
                <button
                  className="rounded p-1 text-slate-500 hover:bg-white/10 hover:text-emerald-300"
                  title="Set as depot"
                  onClick={() => onSetDepot(index)}
                >
                  <MapPin className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                className="rounded p-1 text-slate-500 hover:bg-white/10 hover:text-rose-300"
                title="Remove location"
                onClick={() => {
                  const next = points.filter((_, itemIndex) => itemIndex !== index);
                  onChange(next);
                  if (depotIndex >= next.length) onSetDepot(0);
                  else if (index < depotIndex) onSetDepot(depotIndex - 1);
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
        <button
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-white/10 py-2 text-[11px] text-slate-500 transition hover:border-brand-400/40 hover:text-brand-300"
          onClick={() => {
            onChange([
              { id: "demo-dha", name: "DHA", lat: 24.7905, lng: 67.0308 },
              { id: "demo-clifton", name: "Clifton", lat: 24.8205, lng: 67.0055 },
              { id: "demo-saddar", name: "Saddar", lat: 24.8605, lng: 67.0125 },
              { id: "demo-pechs", name: "PECHS", lat: 24.8512, lng: 67.0622 },
              { id: "demo-gulshan", name: "Gulshan-e-Iqbal", lat: 24.8842, lng: 67.0938 },
              { id: "demo-nn", name: "North Nazimabad", lat: 24.9312, lng: 67.0318 },
            ]);
            onSetDepot(0);
          }}
        >
          <RotateCcw className="h-3.5 w-3.5" /> Restore Karachi demo set
        </button>
      </div>
    </Panel>
  );
}
