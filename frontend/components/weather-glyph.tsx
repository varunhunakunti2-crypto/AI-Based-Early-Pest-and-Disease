import type { WeatherGlyphName } from "@/lib/weather";

/**
 * Shared weather glyph. Kept free of client hooks so server components (the
 * dashboard) and the interactive weather page can both render it.
 */
export function WeatherGlyph({ name }: { name: WeatherGlyphName }) {
  const common = {
    width: 48,
    height: 48,
    viewBox: "0 0 48 48",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
  };

  switch (name) {
    case "clear":
      return (
        <svg {...common}>
          <circle cx="24" cy="24" r="8" />
          <path d="M24 6v5M24 37v5M6 24h5M37 24h5M11.3 11.3l3.5 3.5M33.2 33.2l3.5 3.5M36.7 11.3l-3.5 3.5M14.8 33.2l-3.5 3.5" />
        </svg>
      );
    case "partly":
      return (
        <svg {...common}>
          <circle cx="18" cy="18" r="6" />
          <path d="M18 6v3M6 18h3M9.5 9.5l2.1 2.1M26.5 9.5l-2.1 2.1" />
          <path d="M34 39a6 6 0 0 0-1-11.9A8.5 8.5 0 0 0 16.4 29 6 6 0 0 0 17 39Z" />
        </svg>
      );
    case "cloud":
      return (
        <svg {...common}>
          <path d="M34 37a7 7 0 0 0-1.2-13.9A9.5 9.5 0 0 0 14.3 26 7 7 0 0 0 15 37Z" />
        </svg>
      );
    case "fog":
      return (
        <svg {...common}>
          <path d="M33 28a6.5 6.5 0 0 0-1.1-12.9A9 9 0 0 0 15 19a6.5 6.5 0 0 0 .6 12.9" />
          <path d="M10 34h28M14 40h22" />
        </svg>
      );
    case "drizzle":
      return (
        <svg {...common}>
          <path d="M33 26a6.5 6.5 0 0 0-1.1-12.9A9 9 0 0 0 15 17a6.5 6.5 0 0 0 .6 12.9" />
          <path d="M17 33v3M24 33v3M31 33v3" />
        </svg>
      );
    case "rain":
      return (
        <svg {...common}>
          <path d="M33 24a6.5 6.5 0 0 0-1.1-12.9A9 9 0 0 0 15 15a6.5 6.5 0 0 0 .6 12.9" />
          <path d="M16 30l-2 6M24 30l-2 6M32 30l-2 6" />
        </svg>
      );
    case "snow":
      return (
        <svg {...common}>
          <path d="M33 24a6.5 6.5 0 0 0-1.1-12.9A9 9 0 0 0 15 15a6.5 6.5 0 0 0 .6 12.9" />
          <path d="M16 32v6M13 35h6M24 32v6M21 35h6M32 32v6M29 35h6" />
        </svg>
      );
    case "thunder":
      return (
        <svg {...common}>
          <path d="M33 22a6.5 6.5 0 0 0-1.1-12.9A9 9 0 0 0 15 13a6.5 6.5 0 0 0 .6 12.9" />
          <path d="M26 28l-7 10h6l-2 6 8-11h-6l3-5Z" />
        </svg>
      );
  }
}
