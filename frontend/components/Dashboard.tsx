"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  BookOpen,
  MapPinned,
  Navigation2,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type {
  ClosestPairResponse,
  GeoPoint,
  HealthPayload,
  RouteOptimizeResponse,
} from "@/lib/types";
import BenchmarkPanel from "./BenchmarkPanel";
import ClosestPairPanel from "./ClosestPairPanel";
import DatasetPanel from "./DatasetPanel";
import DocsPanel from "./DocsPanel";
import MapPanel from "./MapPanel";
import RoutePanel from "./RoutePanel";
import { ErrorBanner } from "./ui";

type Tab = "playground" | "benchmarks" | "docs";

const DEMO_POINTS: GeoPoint[] = [
  { id: "demo-dha", name: "DHA", lat: 24.7905, lng: 67.0308 },
  { id: "demo-clifton", name: "Clifton", lat: 24.8205, lng: 67.0055 },
  { id: "demo-saddar", name: "Saddar", lat: 24.8605, lng: 67.0125 },
  { id: "demo-pechs", name: "PECHS", lat: 24.8512, lng: 67.0622 },
  { id: "demo-gulshan", name: "Gulshan-e-Iqbal", lat: 24.8842, lng: 67.0938 },
  { id: "demo-nn", name: "North Nazimabad", lat: 24.9312, lng: 67.0318 },
];

const TABS: { value: Tab; label: string; icon: React.ReactNode }[] = [
  { value: "playground", label: "Playground", icon: <MapPinned className="h-4 w-4" /> },
  { value: "benchmarks", label: "Benchmarks", icon: <BarChart3 className="h-4 w-4" /> },
  { value: "docs", label: "Algorithm notes", icon: <BookOpen className="h-4 w-4" /> },
];

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("playground");
  const [points, setPoints] = useState<GeoPoint[]>(DEMO_POINTS);
  const [depotIndex, setDepotIndex] = useState(0);
  const [closestIds, setClosestIds] = useState<string[]>([]);
  const [routeGeometry, setRouteGeometry] = useState<number[][] | null>(null);
  const [routeDashed, setRouteDashed] = useState(true);
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [datasetVersion, setDatasetVersion] = useState(0);

  useEffect(() => {
    let active = true;
    apiGet<HealthPayload>("/api/health")
      .then((payload) => {
        if (active) setHealth(payload);
      })
      .catch((caught) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Cannot reach the GeoRoute backend.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  function updatePoints(next: GeoPoint[]) {
    setPoints(next);
    setDepotIndex((current) => Math.min(current, Math.max(0, next.length - 1)));
    setClosestIds([]);
    setRouteGeometry(null);
    setDatasetVersion((current) => current + 1);
  }

  function addPoint(lat: number, lng: number) {
    const index = points.length;
    const point: GeoPoint = {
      id: `manual-${Date.now()}-${index}`,
      name: `Location ${index + 1}`,
      lat: Number(lat.toFixed(7)),
      lng: Number(lng.toFixed(7)),
    };
    updatePoints([...points, point]);
  }

  function selectDepot(index: number) {
    setDepotIndex(index);
    setRouteGeometry(null);
  }

  function handleClosestResult(result: ClosestPairResponse) {
    setClosestIds(result.results[0]?.pair_ids ?? []);
  }

  function handleRouteResult(result: RouteOptimizeResponse) {
    setRouteGeometry(result.geometry);
    setRouteDashed(!result.geometry_source?.startsWith("OSRM"));
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/[0.06] bg-ink-950/40 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-brand-400/30 bg-brand-500/15 text-brand-300">
              <Navigation2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-white">
                GeoRoute
              </h1>
              <p className="text-[11px] text-slate-500">
                Route optimization &amp; algorithm benchmarking
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="chip">
              <Activity className="h-3.5 w-3.5 text-emerald-400" />
              {health ? `Engine: ${health.engine.mode}` : "Backend unreachable"}
            </span>
            <span className="chip hidden sm:inline-flex">
              CS2009 · FAST-NU · November 2026
            </span>
          </div>
        </div>

        <nav className="mx-auto flex max-w-[1600px] gap-1 overflow-x-auto px-4 pb-3 sm:px-6 lg:px-8">
          {TABS.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setTab(item.value)}
              className={`tab flex items-center gap-2 ${tab === item.value ? "tab-active" : ""}`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        {tab === "playground" && (
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(380px,0.9fr)]">
            <MapPanel
              points={points}
              depotIndex={depotIndex}
              closestIds={closestIds}
              route={routeGeometry}
              routeDashed={routeDashed}
              onAddPoint={addPoint}
            />
            <div className="space-y-6">
              <DatasetPanel
                key={`dataset-${datasetVersion}`}
                points={points}
                depotIndex={depotIndex}
                onChange={updatePoints}
                onSetDepot={selectDepot}
                onError={setError}
              />
              <ClosestPairPanel
                key={`closest-${datasetVersion}`}
                points={points}
                onResult={handleClosestResult}
                onError={setError}
              />
              <RoutePanel
                key={`route-${datasetVersion}`}
                points={points}
                depotIndex={depotIndex}
                limits={health?.limits}
                onResult={handleRouteResult}
                onError={setError}
              />
            </div>
          </div>
        )}

        {tab === "benchmarks" && <BenchmarkPanel limits={health?.limits} />}
        {tab === "docs" && <DocsPanel />}
      </main>

      <footer className="mx-auto max-w-[1600px] px-4 pb-8 pt-2 text-[10px] text-slate-600 sm:px-6 lg:px-8">
        GeoRoute · C++17 engine · FastAPI · Next.js · Leaflet · OSRM · OpenStreetMap contributors
      </footer>
    </div>
  );
}
