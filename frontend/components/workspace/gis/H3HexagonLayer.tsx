"use client";

/**
 * H3HexagonLayer - Leaflet layer for rendering H3 hexagonal cells on a map.
 *
 * Displays H3 cells as colored polygons with hotspot classification colors.
 * Supports click interactions, resolution switching, and layer toggling.
 */

import { useCallback } from "react";
import { Polygon, Popup } from "react-leaflet";
import { classificationColor } from "@/lib/gis/h3-colors";
import type { LeafletMouseEvent } from "leaflet";

export interface H3HexagonProps {
  /** H3 cell ID (decimal string) */
  cellId: string;
  /** Resolution level */
  resolution: number;
  /** Center latitude */
  centerLat: number;
  /** Center longitude */
  centerLng: number;
  /** Boundary coordinates [[lat, lng], ...] */
  boundary: number[][];
  /** Hotspot classification: low | moderate | high | critical */
  classification?: string;
  /** Hotspot score (0-1) */
  score?: number;
  /** Whether the cell is selected */
  selected?: boolean;
  /** Click handler */
  onClick?: (cellId: string, event: LeafletMouseEvent) => void;
  /** Hover handler */
  onHover?: (cellId: string) => void;
}

export function H3Hexagon({
  cellId,
  resolution,
  centerLat,
  centerLng,
  boundary,
  classification = "low",
  score = 0,
  selected = false,
  onClick,
  onHover,
}: H3HexagonProps) {
  const color = classificationColor(classification, score);
  const fillOpacity = selected ? 0.6 : 0.4;
  const weight = selected ? 3 : 1;

  // Convert boundary from [lat, lng] to Leaflet [lat, lng]
  const positions = boundary.map(([lat, lng]) => [lat, lng] as [number, number]);

  return (
    <Polygon
      positions={positions as unknown as import("leaflet").LatLngExpression[]}
      color={color}
      weight={weight}
      fillColor={color}
      fillOpacity={fillOpacity}
      dashArray={selected ? "6, 6" : undefined}
      eventHandlers={{
        click: (e: LeafletMouseEvent) => onClick?.(cellId, e),
        mouseover: () => onHover?.(cellId),
        mouseout: () => onHover?.(""),
      }}
    >
      {selected ? (
        <Popup position={[centerLat, centerLng]}>
          <div style={{ minWidth: "200px", fontSize: "12px" }}>
            <div style={{ fontWeight: "bold", marginBottom: "6px" }}>
              H3 Cell: {cellId}
            </div>
            <div style={{ marginBottom: "4px" }}>
              <span style={{ color: "#666" }}>Resolution:</span> {resolution}
            </div>
            <div style={{ marginBottom: "4px" }}>
              <span style={{ color: "#666" }}>Classification:</span>
              <strong style={{ color: color }}>{classification}</strong>
            </div>
            <div style={{ marginBottom: "4px" }}>
              <span style={{ color: "#666" }}>Score:</span> {score.toFixed(2)}
            </div>
            <div style={{ marginBottom: "4px" }}>
              <span style={{ color: "#666" }}>Area:</span> {(areaKm2(resolution)).toFixed(2)} km²
            </div>
            <div style={{ marginTop: "8px", fontSize: "11px", color: "#888" }}>
              Click to view cell details
            </div>
          </div>
        </Popup>
      ) : undefined}
    </Polygon>
  );
}

/**
 * Approximate hexagon area in km² for a given resolution.
 */
function areaKm2(resolution: number): number {
  const areas: Record<number, number> = {
    0: 4349493,
    1: 621356,
    2: 88765,
    3: 12680,
    4: 1811,
    5: 258.8,
    6: 36.97,
    7: 5.281,
    8: 0.7545,
    9: 0.1078,
    10: 0.0154,
  };
  return areas[resolution] ?? 0.0154;
}

/**
 * H3HexagonLayer - Renders multiple H3 hexagons as a Leaflet layer group.
 */
export interface H3HexagonLayerProps {
  hexagons: Array<{
    cellId: string;
    resolution: number;
    centerLat: number;
    centerLng: number;
    boundary: number[][];
    classification?: string;
    score?: number;
  }>;
  selectedCellId?: string;
  onCellClick?: (cellId: string) => void;
  onCellHover?: (cellId: string) => void;
}

export function H3HexagonLayer({
  hexagons,
  selectedCellId,
  onCellClick,
  onCellHover,
}: H3HexagonLayerProps) {
  return (
    <>
      {hexagons.map((h) => (
        <H3Hexagon
          key={h.cellId}
          cellId={h.cellId}
          resolution={h.resolution}
          centerLat={h.centerLat}
          centerLng={h.centerLng}
          boundary={h.boundary}
          classification={h.classification ?? "low"}
          score={h.score ?? 0}
          selected={selectedCellId === h.cellId}
          onClick={(cellId) => onCellClick?.(cellId)}
          onHover={(cellId) => onCellHover?.(cellId)}
        />
      ))}
    </>
  );
}
