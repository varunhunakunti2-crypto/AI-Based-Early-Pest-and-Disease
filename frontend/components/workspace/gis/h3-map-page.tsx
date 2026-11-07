"use client";

/**
 * H3 GIS Map Page - Interactive hexagonal agricultural intelligence map.
 *
 * Integrates Leaflet/OpenStreetMap with H3 hexagonal cell overlays,
 * hotspot intelligence, weather risk, and task distribution.
 */

import { useEffect, useState, useCallback, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  H3HexagonLayer,
  type H3HexagonLayerProps,
} from "@/components/workspace/gis/H3HexagonLayer";
import {
  classificationColor,
  classificationLabel,
  allClassifications,
} from "@/lib/gis/h3-colors";
import { haversineDistanceKm } from "@/lib/gis/h3-geojson";
import {
  Badge,
  Button,
  Icon,
  PageHeader,
  StatCard,
  Tabs,
  EmptyState,
} from "@/components/workspace/ui";

// Default center: Bangalore, India
const DEFAULT_CENTER = [12.9716, 77.5946];
const DEFAULT_ZOOM = 10;

// H3 resolutions available for the map
const RESOLUTIONS = [
  { value: 6, label: "Region (Res 6)" },
  { value: 7, label: "District/Village (Res 7)" },
  { value: 8, label: "Farm Cluster (Res 8)" },
  { value: 9, label: "Field (Res 9)" },
  { value: 10, label: "Fine (Res 10)" },
];

interface HexagonData {
  cellId: string;
  resolution: number;
  centerLat: number;
  centerLng: number;
  boundary: number[][];
  classification?: string;
  score?: number;
  diseaseHotspot?: {
    targetCode: string;
    classification: string;
    score: number;
    uniqueAffectedFarms: number;
  };
  pestHotspot?: {
    targetCode: string;
    classification: string;
    score: number;
    uniqueAffectedFarms: number;
  };
  riskScore?: number;
  riskLabel?: string;
  weatherRisk?: number;
}

interface SelectedCellInfo {
  cellId: string;
  centerLat: number;
  centerLng: number;
  classification: string;
  score: number;
  areaKm2: number;
  diseaseReports: number;
  pestReports: number;
  uniqueFarms: number;
  verifiedFarms: number;
  weatherRisk: number;
  riskScore: number;
}

/** Keeps the Leaflet view in sync when the parent selects a new cell. */
function MapViewSync({
  center,
  zoom,
}: {
  center: [number, number];
  zoom: number;
}) {
  const map = useMap();

  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center, zoom]);

  return null;
}

export default function H3MapPage() {
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const [center, setCenter] = useState<[number, number]>([
    DEFAULT_CENTER[0] as number,
    DEFAULT_CENTER[1] as number,
  ]);
  const [resolution, setResolution] = useState(9);
  const [hexagons, setHexagons] = useState<HexagonData[]>([]);
  const [selectedCell, setSelectedCell] = useState<SelectedCellInfo | null>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [layerVisibility, setLayerVisibility] = useState({
    hexagons: true,
    hotspots: true,
    weatherRisk: true,
    tasks: true,
    farmBoundaries: false,
  });
  const [filters, setFilters] = useState({
    disease: "" as string,
    pest: "" as string,
    crop: "" as string,
    severity: "" as string,
    minClassification: "low" as string,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mock data generation - in production this comes from API
  const mockHexagons = useMemo((): HexagonData[] => {
    const cells: HexagonData[] = [];
    const classifications: ("low" | "moderate" | "high" | "critical")[] = [
      "low",
      "moderate",
      "high",
      "critical",
    ];

    // Generate a grid of hexagons around the center
    for (let i = -3; i <= 3; i++) {
      for (let j = -3; j <= 3; j++) {
        const lat = DEFAULT_CENTER[0]! + i * 0.02;
        const lng = DEFAULT_CENTER[1]! + j * 0.02;
        const cellId = String(
          Math.floor(Math.random() * 1e18)
        );
        const classification =
          classifications[Math.floor(Math.random() * classifications.length)];
        const score = Math.round(Math.random() * 100) / 100;

        cells.push({
          cellId,
          resolution,
          centerLat: lat,
          centerLng: lng,
          boundary: generateHexBoundary(lat, lng, 0.01),
          classification,
          score,
          diseaseHotspot:
            classification !== "low"
              ? {
                  targetCode: "rice_blast",
                  classification: classification as string,
                  score,
                  uniqueAffectedFarms: Math.floor(Math.random() * 5) + 1,
                }
              : undefined,
          pestHotspot:
            classification === "high" || classification === "critical"
              ? {
                  targetCode: "fall_armyworm",
                  classification,
                  score,
                  uniqueAffectedFarms: Math.floor(Math.random() * 3) + 1,
                }
              : undefined,
          riskScore: score,
          riskLabel: classification,
          weatherRisk: Math.round(Math.random() * 100) / 100,
        });
      }
    }
    return cells;
  }, [resolution]);

  // Generate a hexagon boundary around a center point
  function generateHexBoundary(
    lat: number,
    lng: number,
    radius: number,
  ): number[][] {
    const boundary: number[][] = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i;
      const vLat = lat + radius * Math.cos(angle);
      const vLng = lng + radius * Math.sin(angle);
      boundary.push([vLat, vLng]);
    }
    return boundary;
  }

  // Filter hexagons based on current filters
  const filteredHexagons = useMemo(() => {
    return hexagons.filter((h) => {
      if (filters.disease && h.diseaseHotspot?.targetCode !== filters.disease)
        return false;
      if (filters.pest && h.pestHotspot?.targetCode !== filters.pest)
        return false;
      if (filters.severity && h.classification !== filters.severity)
        return false;

      const classificationOrder: Record<string, number> = {
        low: 0,
        moderate: 1,
        high: 2,
        critical: 3,
      };
      const minOrder = classificationOrder[filters.minClassification] ?? 0;
      const cellOrder =
        classificationOrder[h.classification ?? "low"] ?? 0;
      if (cellOrder < minOrder) return false;

      return true;
    });
  }, [hexagons, filters]);

  // Handle cell click
  const handleCellClick = useCallback((cellId: string) => {
    const cell = hexagons.find((h) => h.cellId === cellId);
    if (!cell) return;

    setSelectedCell({
      cellId: cell.cellId,
      centerLat: cell.centerLat,
      centerLng: cell.centerLng,
      classification: cell.classification ?? "low",
      score: cell.score ?? 0,
      areaKm2: 0.75, // Approximate for resolution 9
      diseaseReports: cell.diseaseHotspot
        ? cell.diseaseHotspot.uniqueAffectedFarms
        : 0,
      pestReports: cell.pestHotspot
        ? cell.pestHotspot.uniqueAffectedFarms
        : 0,
      uniqueFarms: Math.max(
        cell.diseaseHotspot?.uniqueAffectedFarms ?? 0,
        cell.pestHotspot?.uniqueAffectedFarms ?? 0,
      ),
      verifiedFarms: Math.floor(
        (Math.max(
          cell.diseaseHotspot?.uniqueAffectedFarms ?? 0,
          cell.pestHotspot?.uniqueAffectedFarms ?? 0,
        ) * 0.7),
      ),
      weatherRisk: cell.weatherRisk ?? 0,
      riskScore: cell.riskScore ?? 0,
    });
    setCenter([cell.centerLat, cell.centerLng]);
    setZoom(13);
  }, [hexagons]);

  // Handle layer toggle
  const handleToggleLayer = (layer: keyof typeof layerVisibility) => {
    setLayerVisibility((prev) => ({ ...prev, [layer]: !prev[layer] }));
  };

  // Load data from API
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // In production, fetch from API endpoints:
      // GET /api/v1/regional-overview/hexagons
      // GET /api/v1/hotspots/nearby
      // For now, mock data is used
      setHexagons(mockHexagons);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load map data",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (isLoading && hexagons.length === 0) {
    return (
      <div className="ws-page">
        <PageHeader eyebrow="GIS Map" title="Loading..." />
        <div className="ws-panel ws-stack">
          <div style={{ textAlign: "center", padding: "40px" }}>
            <Icon name="sync" size={32} />
            <p style={{ marginTop: "12px", color: "#666" }}>
              Loading hexagonal map...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ws-page">
        <PageHeader eyebrow="GIS Map" title="Map Error" />
        <div className="ws-panel ws-stack">
          <div style={{ textAlign: "center", padding: "40px" }}>
            <span style={{ color: "#b42318" }}><Icon name="alert" size={32} /></span>
            <p style={{ marginTop: "12px" }}>{error}</p>
            <Button onClick={loadData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ws-page">
      <PageHeader
        eyebrow="Hexagonal GIS Intelligence"
        title="Agricultural Surveillance Map"
        lede="H3 hexagonal grid with disease & pest hotspots, weather risk, and task distribution"
        actions={
          <div style={{ display: "flex", gap: "8px" }}>
            <Button size="sm" onClick={loadData}>
              <Icon name="refresh" /> Refresh
            </Button>
            <Button size="sm" variant="outline">
              <Icon name="fullscreen" /> Fullscreen
            </Button>
          </div>
        }
      />

      <div className="ws-map-container">
        <MapContainer
          center={center}
          zoom={zoom}
          style={{ height: "100%", width: "100%" }}
          zoomControl={true}
          attributionControl={true}
        >
          <MapViewSync center={center} zoom={zoom} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {layerVisibility.hexagons ? (
            <H3HexagonLayer
              hexagons={filteredHexagons.map((h) => ({
                cellId: h.cellId,
                resolution: h.resolution,
                centerLat: h.centerLat,
                centerLng: h.centerLng,
                boundary: h.boundary,
                classification: h.classification ?? "low",
                score: h.score ?? 0,
              }))}
              selectedCellId={selectedCell?.cellId ?? undefined}
              onCellClick={handleCellClick}
            />
          ) : null}

          {/* Center marker for selected cell */}
          {selectedCell ? (
            <Marker position={[selectedCell.centerLat, selectedCell.centerLng] as [number, number]}>
              <Popup>
                <div style={{ minWidth: "220px" }}>
                  <div style={{ fontWeight: "bold", fontSize: "14px", marginBottom: "8px" }}>
                    H3 Cell: {selectedCell.cellId}
                  </div>
                  <div style={{ marginBottom: "6px" }}>
                    <span style={{ color: "#666", fontSize: "12px" }}>
                      Classification:
                    </span>{" "}
                    <span
                      style={{
                        color:
                          classificationColor(
                            selectedCell.classification,
                            selectedCell.score,
                          ),
                          fontWeight: "bold",
                        }}
                      >
                        {classificationLabel(selectedCell.classification)}
                      </span>
                    </div>
                    <div style={{ marginBottom: "6px" }}>
                      <span style={{ color: "#666", fontSize: "12px" }}>
                        Risk Score:
                      </span>{" "}
                      {selectedCell.riskScore.toFixed(2)}
                    </div>
                    <div style={{ marginBottom: "6px" }}>
                      <span style={{ color: "#666", fontSize: "12px" }}>
                        Weather Risk:
                      </span>{" "}
                      {selectedCell.weatherRisk.toFixed(2)}
                    </div>
                    <div style={{ marginBottom: "6px" }}>
                      <span style={{ color: "#666", fontSize: "12px" }}>
                        Affected Farms:
                      </span>{" "}
                      {selectedCell.uniqueFarms}
                    </div>
                    <div style={{ marginTop: "10px" }}>
                      <Button
                        size="sm"
                        onClick={() => {
                          setActiveTab("detail");
                        }}
                      >
                        View Details
                      </Button>
                    </div>
                  </div>
                </Popup>
              </Marker>
            ) : null}
        </MapContainer>
      </div>

      {/* Hexagon Intelligence Panel */}
      {selectedCell && (
        <div className="ws-panel ws-intelligence-panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ margin: 0, fontSize: "16px" }}>Hexagon Intelligence</h3>
            <Button size="sm" onClick={() => setSelectedCell(null)}>
              Close
            </Button>
          </div>

          <Tabs
            label="Hexagon Intelligence Tabs"
            value={activeTab}
            onChange={setActiveTab}
            tabs={[
              { value: "overview", label: "Overview", count: 0 },
              { value: "disease", label: "Disease", count: selectedCell.diseaseReports },
              { value: "pest", label: "Pest", count: selectedCell.pestReports },
              { value: "weather", label: "Weather", count: 0 },
              { value: "tasks", label: "Tasks", count: 0 },
              { value: "recovery", label: "Recovery", count: 0 },
            ]}
          />

          <div className="ws-panel-body" style={{ marginTop: "16px" }}>
            {activeTab === "overview" && (
              <div className="ws-stat-grid">
                <StatCard
                  label="Classification"
                  value={classificationLabel(selectedCell.classification)}
                  tone={selectedCell.classification as any}
                />
                <StatCard
                  label="Risk Score"
                  value={selectedCell.riskScore.toFixed(2)}
                  detail="0.0 - 1.0 scale"
                />
                <StatCard
                  label="Weather Risk"
                  value={selectedCell.weatherRisk.toFixed(2)}
                  detail="Weather suitability"
                />
                <StatCard
                  label="Affected Farms"
                  value={selectedCell.uniqueFarms}
                  detail="Unique farms"
                />
              </div>
            )}

            {activeTab === "disease" && selectedCell.diseaseReports > 0 && (
              <div className="ws-stack">
                <p>Disease reports in this hexagon.</p>
                <EmptyState
                  icon="alert-triangle"
                  title="Disease Intelligence"
                  body="Disease intelligence coming in next phase."
                />
              </div>
            )}

            {activeTab === "pest" && selectedCell.pestReports > 0 && (
              <div className="ws-stack">
                <p>Pest reports in this hexagon.</p>
                <EmptyState
                  icon="bug"
                  title="Pest Intelligence"
                  body="Pest intelligence coming in next phase."
                />
              </div>
            )}

            {activeTab === "weather" && (
              <div className="ws-stack">
                <p>Weather-supported risk indicators.</p>
                <EmptyState
                  icon="cloud"
                  title="Weather Risk"
                  body="Weather risk integration coming in next phase."
                />
              </div>
            )}

            {activeTab === "tasks" && (
              <div className="ws-stack">
                <p>Inspection tasks for this hexagon.</p>
                <EmptyState
                  icon="clipboard"
                  title="Task Distribution"
                  body="Task distribution coming in next phase."
                />
              </div>
            )}

            {activeTab === "recovery" && (
              <div className="ws-stack">
                <p>Recovery monitoring for this hexagon.</p>
                <EmptyState
                  icon="leaf"
                  title="Recovery Monitoring"
                  body="Recovery monitoring coming in next phase."
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Map controls sidebar */}
      <div className="ws-map-sidebar">
        <div className="ws-panel">
          <div style={{ fontWeight: "bold", marginBottom: "12px", fontSize: "14px" }}>
            Map Layers
          </div>
          {Object.entries(layerVisibility).map(([key, visible]) => (
            <div
              key={key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "8px",
                fontSize: "13px",
                cursor: "pointer",
              }}
              onClick={() => handleToggleLayer(key as keyof typeof layerVisibility)}
            >
              <input
                type="checkbox"
                checked={visible}
                readOnly
                onChange={(e) => handleToggleLayer(e.target.checked as any)}
              />
              {key.charAt(0).toUpperCase() + key.slice(1)}
            </div>
          ))}
        </div>

        <div className="ws-panel" style={{ marginTop: "12px" }}>
          <div style={{ fontWeight: "bold", marginBottom: "12px", fontSize: "14px" }}>
            H3 Resolution
          </div>
          {RESOLUTIONS.map((r) => (
            <Button
              size="sm"
              variant={resolution === r.value ? ("solid" as const) : ("outline" as const)}
              onClick={() => setResolution(r.value)}
              style={{ width: "100%", textAlign: "left" }}
            >
              {r.label}
            </Button>
          ))}
        </div>

        <div className="ws-panel" style={{ marginTop: "12px" }}>
          <div style={{ fontWeight: "bold", marginBottom: "12px", fontSize: "14px" }}>
            Classifications
          </div>
          {allClassifications().map((c) => (
            <div
              key={c.value}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "6px",
                fontSize: "12px",
              }}
            >
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  backgroundColor: c.color,
                  borderRadius: "2px",
                }}
              />
              <span>{c.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
