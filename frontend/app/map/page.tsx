"use client";

/**
 * Leaflet reads `window` when its module is evaluated, so the interactive map
 * must not run during prerendering. Load it in the browser only.
 */

import dynamic from "next/dynamic";

const H3MapPage = dynamic(
  () => import("@/components/workspace/gis/h3-map-page"),
  {
    ssr: false,
    loading: () => (
      <div className="ws-page">
        <div className="ws-panel ws-stack">
          <div style={{ textAlign: "center", padding: "40px" }}>
            Loading map…
          </div>
        </div>
      </div>
    ),
  },
);

export default function MapPage() {
  return <H3MapPage />;
}
