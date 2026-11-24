"use client";

import L from "leaflet";
import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { GeoPoint } from "@/lib/types";

interface MapCanvasProps {
  points: GeoPoint[];
  depotIndex: number;
  closestIds: string[];
  route: number[][] | null;
  routeDashed: boolean;
  onAddPoint: (lat: number, lng: number) => void;
}

function ClickHandler({ onAddPoint }: { onAddPoint: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(event) {
      onAddPoint(event.latlng.lat, event.latlng.lng);
    },
  });
  return null;
}

function FitBounds({ points }: { points: GeoPoint[] }) {
  const map = useMap();

  useEffect(() => {
    if (!points.length) return;
    if (points.length === 1) {
      map.setView([points[0].lat, points[0].lng], 13);
      return;
    }
    const bounds = L.latLngBounds(points.map((point) => [point.lat, point.lng]));
    map.fitBounds(bounds, { padding: [48, 48], maxZoom: 15 });
  }, [map, points]);

  return null;
}

export default function MapCanvas({
  points,
  depotIndex,
  closestIds,
  route,
  routeDashed,
  onAddPoint,
}: MapCanvasProps) {
  const icons = useMemo(
    () =>
      points.map((point, index) => {
        const classes = [
          "gr-pin",
          index === depotIndex ? "is-depot" : "",
          closestIds.includes(point.id) ? "is-closest" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return L.divIcon({
          className: "gr-pin-wrapper",
          html: `<div class="${classes}">${index + 1}</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 26],
          tooltipAnchor: [0, -20],
        });
      }),
    [points, depotIndex, closestIds],
  );

  const routePositions = useMemo(
    () => route?.map(([lng, lat]) => [lat, lng] as [number, number]) ?? [],
    [route],
  );

  return (
    <MapContainer
      center={[24.86, 67.0]}
      zoom={12}
      scrollWheelZoom
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onAddPoint={onAddPoint} />
      <FitBounds points={points} />
      {routePositions.length > 1 && (
        <Polyline
          positions={routePositions}
          pathOptions={{
            color: "#38bdf8",
            weight: 4,
            opacity: 0.9,
            dashArray: routeDashed ? "7 8" : undefined,
          }}
        />
      )}
      {points.map((point, index) => (
        <Marker key={point.id} position={[point.lat, point.lng]} icon={icons[index]}>
          <Tooltip direction="top">
            <span className="font-semibold">{point.name}</span>
            <br />
            <span className="font-mono text-[10px]">
              {point.lat.toFixed(5)}, {point.lng.toFixed(5)}
            </span>
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
