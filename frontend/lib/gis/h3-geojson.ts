/**
 * H3 GeoJSON utilities for frontend.
 *
 * Converts H3 cell boundary data to GeoJSON format for Leaflet rendering.
 * These functions mirror the backend H3 utilities but operate on the frontend.
 */

/**
 * Convert H3 cell boundary coordinates to GeoJSON Polygon geometry.
 * Input boundary is [[lat, lng], ...] and output is GeoJSON [[lng, lat], ...]
 */
export function h3BoundaryToGeoJSON(
  cellId: string,
  boundary: number[][],
  resolution: number,
): GeoJSON.Polygon {
  // Convert [lat, lng] to GeoJSON [lng, lat]
  const coordinates = boundary.map(([lat, lng]) => [lng, lat] as [number, number]);
  // Close the ring
  if (coordinates.length > 0) {
    const first = coordinates[0];
    if (first) {
      coordinates.push([first[0], first[1]]);
    }
  }

  return {
    type: "Polygon",
    coordinates: [coordinates],
  } as GeoJSON.Polygon;
}

/**
 * Convert a list of H3 cells to a GeoJSON FeatureCollection.
 */
export function cellsToGeoJSON(
  cells: Array<{
    cellId: string;
    resolution: number;
    centerLat: number;
    centerLng: number;
    boundary: number[][];
    classification?: string;
    score?: number;
  }>,
): GeoJSON.FeatureCollection<GeoJSON.Polygon> {
  return {
    type: "FeatureCollection",
    features: cells.map((cell) => ({
      type: "Feature",
      properties: {
        cellId: cell.cellId,
        resolution: cell.resolution,
        classification: cell.classification ?? "low",
        score: cell.score ?? 0,
        centerLat: cell.centerLat,
        centerLng: cell.centerLng,
      },
      geometry: h3BoundaryToGeoJSON(
        cell.cellId,
        cell.boundary,
        cell.resolution,
      ),
    })),
  } as GeoJSON.FeatureCollection<GeoJSON.Polygon>;
}

/**
 * Approximate H3 cell center from boundary coordinates.
 */
export function boundaryCenter(boundary: number[][]): [number, number] {
  if (boundary.length === 0) return [0, 0];
  let sumLat = 0;
  let sumLng = 0;
  for (const point of boundary) {
    const lat = point[0];
    const lng = point[1];
    if (lat !== undefined && lng !== undefined) {
      sumLat += lat;
      sumLng += lng;
    }
  }
  return [sumLat / boundary.length, sumLng / boundary.length];
}

/**
 * Calculate approximate distance between two points in kilometres (Haversine).
 */
export function haversineDistanceKm(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const R = 6371; // Earth radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}
