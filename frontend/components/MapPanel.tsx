"use client";

import dynamic from "next/dynamic";
import { MapPinned, MousePointerClick } from "lucide-react";
import type { GeoPoint } from "@/lib/types";
import { Panel } from "./ui";

const MapCanvas = dynamic(() => import("./MapCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-xs text-slate-500">
      Loading map…
    </div>
  ),
});

interface MapPanelProps {
  points: GeoPoint[];
  depotIndex: number;
  closestIds: string[];
  route: number[][] | null;
  routeDashed: boolean;
  onAddPoint: (lat: number, lng: number) => void;
}

export default function MapPanel(props: MapPanelProps) {
  return (
    <Panel
      title="Geographic workspace"
      subtitle="Click the map to add a location. Markers are numbered in insertion order."
      icon={<MapPinned className="h-4 w-4 text-brand-400" />}
      action={
        <div className="hidden flex-wrap items-center gap-1.5 sm:flex">
          <span className="chip">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Depot
          </span>
          <span className="chip">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> Closest pair
          </span>
          <span className="chip">
            <span className="h-2 w-2 rounded-full bg-sky-400" /> Route
          </span>
        </div>
      }
    >
      <div className="relative h-[420px] overflow-hidden rounded-xl border border-white/10 bg-ink-950 lg:h-[560px]">
        <MapCanvas {...props} />
      </div>
      <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-500">
        <MousePointerClick className="h-3.5 w-3.5" />
        {props.points.length === 0
          ? "No locations yet — generate a dataset or click the map."
          : `${props.points.length} locations loaded · depot is marker ${props.depotIndex + 1}`}
      </div>
    </Panel>
  );
}
