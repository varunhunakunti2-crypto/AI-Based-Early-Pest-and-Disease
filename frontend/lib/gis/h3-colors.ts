/**
 * H3 hotspot classification colors for the frontend.
 *
 * Mirrors the design system colors from globals.css and theme.ts.
 * Classification colors:
 * - low: green (#2f6f4e)
 * - moderate: amber (#9a6700)
 * - high: orange (#c2410c)
 * - critical: red (#b42318)
 * - insufficient: neutral (#5f6b7a)
 */

/**
 * Return the fill color for a given hotspot classification and score.
 */
export function classificationColor(
  classification: string,
  score: number = 0,
): string {
  const baseColors: Record<string, string> = {
    low: "#2f6f4e",
    moderate: "#9a6700",
    high: "#c2410c",
    critical: "#b42318",
    insufficient: "#5f6b7a",
  };

  const base = (baseColors[classification] ?? baseColors.insufficient) as string;

  // If score is provided, adjust opacity/brightness based on score intensity
  // Higher score = more intense color
  if (score !== undefined && score > 0 && classification !== "insufficient") {
    // Blend toward white for lower scores, toward full color for higher scores
    const intensity = Math.min(Math.max(score, 0), 1);
    // Lighten the color based on inverse intensity
    const r = parseInt(base.slice(1, 3), 16);
    const g = parseInt(base.slice(3, 5), 16);
    const b = parseInt(base.slice(5, 7), 16);
    const lightenedR = Math.round(r + (255 - r) * (1 - intensity) * 0.4);
    const lightenedG = Math.round(g + (255 - g) * (1 - intensity) * 0.4);
    const lightenedB = Math.round(b + (255 - b) * (1 - intensity) * 0.4);
    return `#${lightenedR.toString(16).padStart(2, "0")}${lightenedG.toString(16).padStart(2, "0")}${lightenedB.toString(16).padStart(2, "0")}`;
  }

  return base;
}

/**
 * Return the border color for a classification (always full intensity).
 */
export function classificationBorderColor(classification: string): string {
  const borderColors: Record<string, string> = {
    low: "#2f6f4e",
    moderate: "#9a6700",
    high: "#c2410c",
    critical: "#b42318",
    insufficient: "#5f6b7a",
  };
  return (borderColors[classification] ?? borderColors.insufficient) as string;
}

/**
 * Return human-readable label for a classification.
 */
export function classificationLabel(classification: string): string {
  const labels: Record<string, string> = {
    low: "Low Risk",
    moderate: "Moderate Risk",
    high: "High Risk",
    critical: "Critical Risk",
    insufficient: "Insufficient Data",
  };
  return (labels[classification] ?? "Unknown") as string;
}

/**
 * Return all available classifications with their metadata.
 */
export function allClassifications(): Array<{
  value: string;
  label: string;
  color: string;
}> {
  return [
    { value: "low", label: "Low Risk", color: "#2f6f4e" },
    { value: "moderate", label: "Moderate Risk", color: "#9a6700" },
    { value: "high", label: "High Risk", color: "#c2410c" },
    { value: "critical", label: "Critical Risk", color: "#b42318" },
    { value: "insufficient", label: "Insufficient Data", color: "#5f6b7a" },
  ];
}
