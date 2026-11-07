"use client";

import { useEffect, useId, type ReactNode } from "react";

import { healthLabel, healthTone, severityTone } from "@/lib/workspace/store";
import type { Health, RiskBand, Severity } from "@/lib/workspace/types";
import { riskLabel, severityLabel } from "@/lib/format";

export type IconName =
  | "dashboard"
  | "farm"
  | "scan"
  | "analysis"
  | "assistant"
  | "map"
  | "hotspot"
  | "monitoring"
  | "expert"
  | "bell"
  | "help"
  | "user"
  | "settings"
  | "plus"
  | "sync"
  | "leaf"
  | "check"
  | "alert"
  | "arrow"
  | "close"
  | "search"
  | "globe"
  | "logout"
  | "camera"
  | "video"
  | "upload"
  | "location"
  | "calendar"
  | "filter"
  | "edit"
  | "plant"
  | "water"
  | "sun"
  | "shield"
  | "menu";

const paths: Record<IconName, ReactNode> = {
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1.6" />
      <rect x="14" y="3" width="7" height="7" rx="1.6" />
      <rect x="3" y="14" width="7" height="7" rx="1.6" />
      <rect x="14" y="14" width="7" height="7" rx="1.6" />
    </>
  ),
  farm: (
    <>
      <path d="M3 20h18" />
      <path d="M5 20V9l7-5 7 5v11" />
      <path d="M9 20v-6h6v6" />
    </>
  ),
  scan: (
    <>
      <path d="M4 8V5a1 1 0 0 1 1-1h3M20 8V5a1 1 0 0 0-1-1h-3M4 16v3a1 1 0 0 0 1 1h3M20 16v3a1 1 0 0 1-1 1h-3" />
      <path d="M8 12h8M12 8v8" />
    </>
  ),
  analysis: (
    <>
      <path d="M4 19V5M4 19h16" />
      <path d="m7 15 3-4 3 2 4-6" />
      <circle cx="17" cy="7" r="1.3" />
    </>
  ),
  assistant: (
    <>
      <path d="M21 12a8 8 0 1 1-3.2-6.4" />
      <path d="M8 10h.01M12 10h.01M16 10h.01" />
      <path d="M8 14c1.2 1.3 2.5 2 4 2s2.8-.7 4-2" />
    </>
  ),
  map: (
    <>
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z" />
      <path d="M9 4v14M15 6v14" />
    </>
  ),
  hotspot: (
    <>
      <circle cx="12" cy="12" r="3" />
      <circle cx="12" cy="12" r="7" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
    </>
  ),
  monitoring: (
    <>
      <path d="M8 3v3M16 3v3" />
      <rect x="4" y="5" width="16" height="16" rx="2" />
      <path d="M4 10h16" />
      <path d="m9 16 2 2 4-4" />
    </>
  ),
  expert: (
    <>
      <path d="M9 4h6l1 2h3a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h3l1-2Z" />
      <path d="m8.5 13 2.2 2.2L16 10" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </>
  ),
  help: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.6 9a2.5 2.5 0 1 1 3.4 2.3c-.7.3-1 1-1 1.7v.5" />
      <path d="M12 17h.01" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3H9a1.7 1.7 0 0 0 1-1.6V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9V9a1.7 1.7 0 0 0 1.6 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  sync: (
    <>
      <path d="M21 12a9 9 0 0 1-15.5 6.3L3 16" />
      <path d="M3 12a9 9 0 0 1 15.5-6.3L21 8" />
      <path d="M21 3v5h-5M3 21v-5h5" />
    </>
  ),
  leaf: (
    <>
      <path d="M20 4c-8 0-14 4-14 11a5 5 0 0 0 5 5c7 0 9-8 9-16Z" />
      <path d="M4 21c2-6 6-9 12-11" />
    </>
  ),
  check: <path d="m5 12 4.5 4.5L19 7" />,
  alert: (
    <>
      <path d="M12 3 2 21h20L12 3Z" />
      <path d="M12 9v5M12 17h.01" />
    </>
  ),
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c3 3.5 3 14 0 18M12 3c-3 3.5-3 14 0 18" />
    </>
  ),
  logout: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5M21 12H9" />
    </>
  ),
  camera: (
    <>
      <path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z" />
      <circle cx="12" cy="13" r="3.2" />
    </>
  ),
  video: (
    <>
      <rect x="3" y="6" width="13" height="12" rx="2" />
      <path d="m16 10 5-3v10l-5-3" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V4M7 9l5-5 5 5" />
      <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </>
  ),
  location: (
    <>
      <path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.6" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18" />
    </>
  ),
  filter: <path d="M4 5h16l-6 8v6l-4 2v-8L4 5Z" />,
  edit: (
    <>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z" />
    </>
  ),
  plant: (
    <>
      <path d="M12 22V9" />
      <path d="M12 13c-5 0-8-3-8-8 5 0 8 3 8 8Z" />
      <path d="M12 11c0-4 3-6 7-6 0 4-3 6-7 6Z" />
    </>
  ),
  water: (
    <>
      <path d="M12 2s7 8 7 12a7 7 0 1 1-14 0c0-4 7-12 7-12Z" />
      <path d="M9 14a3 3 0 0 0 3 3" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
};

export function Icon({
  name,
  size = 18,
  className,
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      {paths[name]}
    </svg>
  );
}

export function PageHeader({
  eyebrow,
  title,
  lede,
  actions,
}: {
  eyebrow: string;
  title: string;
  lede?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="ws-page-header">
      <div>
        <p className="ws-eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {lede ? <p className="ws-lede">{lede}</p> : null}
      </div>
      {actions ? <div className="ws-page-actions">{actions}</div> : null}
    </header>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?:
    | "neutral"
    | "ok"
    | "warn"
    | "bad"
    | "alert"
    | "info"
    | "purple"
    | "brand"
    | "low"
    | "moderate"
    | "high"
    | "critical"
    | "urgent";
}) {
  return <span className={`ws-badge ws-badge-${tone}`}>{children}</span>;
}

export function HealthPill({ health }: { health: Health }) {
  return <Badge tone={healthTone(health) as "ok" | "warn" | "bad" | "alert" | "info"}>{healthLabel(health)}</Badge>;
}

export function SeverityPill({ severity }: { severity: Severity }) {
  return <Badge tone={severityTone(severity) as "ok" | "low" | "moderate" | "high" | "critical"}>{severityLabel(severity)}</Badge>;
}

export function RiskPill({ band }: { band: RiskBand }) {
  const tone = band === "insufficient" ? "neutral" : band;
  return <Badge tone={tone as "low" | "moderate" | "high" | "urgent" | "neutral"}>{riskLabel(band)}</Badge>;
}

export function StatCard({
  label,
  value,
  detail,
  icon,
  tone = "default",
}: {
  label: string;
  value: string | number;
  detail?: string;
  icon?: IconName;
  tone?: "default" | "ok" | "warn" | "bad" | "brand";
}) {
  return (
    <div className={`ws-stat ws-stat-${tone}`}>
      <div className="ws-stat-top">
        <p>{label}</p>
        {icon ? (
          <span className="ws-stat-icon">
            <Icon name={icon} size={17} />
          </span>
        ) : null}
      </div>
      <strong>{value}</strong>
      {detail ? <span className="ws-stat-detail">{detail}</span> : null}
    </div>
  );
}

export function ProgressBar({
  value,
  label,
  tone = "brand",
}: {
  value: number;
  label?: string;
  tone?: "brand" | "ok" | "warn" | "bad";
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="ws-progress">
      {label ? (
        <div className="ws-progress-label">
          <span>{label}</span>
          <span>{clamped}%</span>
        </div>
      ) : null}
      <div
        className="ws-progress-track"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? "Progress"}
      >
        <span className={`ws-progress-fill ws-fill-${tone}`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

export function Sparkline({
  values,
  tone = "brand",
  label,
}: {
  values: number[];
  tone?: "brand" | "bad" | "warn";
  label: string;
}) {
  const max = Math.max(...values, 1);
  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 100;
      const y = 30 - (value / max) * 26;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg className={`ws-spark ws-spark-${tone}`} viewBox="0 0 100 32" role="img" aria-label={label}>
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export function PhotoTile({
  tone,
  label,
  mediaType = "image",
  size = "md",
  src,
}: {
  tone: number;
  label: string;
  mediaType?: "image" | "video";
  size?: "sm" | "md" | "lg";
  src?: string;
}) {
  if (src) {
    return (
      <div className={`ws-photo ws-photo-${size} ws-photo-custom`} role="img" aria-label={label} style={{ overflow: "hidden", position: "relative" }}>
        {mediaType === "video" ? (
          <video src={src} style={{ width: "100%", height: "100%", objectFit: "cover" }} controls playsInline />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- blob/data URL from capture.
          <img src={src} alt={label} style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
        )}
      </div>
    );
  }

  return (
    <div className={`ws-photo ws-photo-${size} ws-tone-${Math.abs(tone) % 8}`} role="img" aria-label={label}>
      <svg viewBox="0 0 120 90" aria-hidden="true">
        <path d="M12 82c8-30 22-46 46-52 12-3 24-7 34-16-2 16-8 30-18 40-14 14-30 20-50 22Z" />
        <path d="M58 80c2-22 12-38 32-48" />
        <path d="M42 74c8-2 14-7 18-14" />
      </svg>
      {mediaType === "video" ? (
        <span className="ws-photo-play">
          <Icon name="video" size={16} />
          Video
        </span>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  icon = "leaf",
  action,
}: {
  title: string;
  body: string;
  icon?: IconName;
  action?: ReactNode;
}) {
  return (
    <div className="ws-empty">
      <span className="ws-empty-icon">
        <Icon name={icon} size={24} />
      </span>
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  );
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
}: {
  tabs: { value: T; label: string; count?: number }[];
  value: T;
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div className="ws-tabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          role="tab"
          aria-selected={value === tab.value}
          className={value === tab.value ? "ws-tab ws-tab-active" : "ws-tab"}
          onClick={() => onChange(tab.value)}
        >
          {tab.label}
          {typeof tab.count === "number" ? <span className="ws-tab-count">{tab.count}</span> : null}
        </button>
      ))}
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="ws-modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div
        className="ws-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="ws-modal-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="ws-icon-button" onClick={onClose} aria-label="Close dialog">
            <Icon name="close" size={18} />
          </button>
        </div>
        <div className="ws-modal-body">{children}</div>
        {footer ? <div className="ws-modal-foot">{footer}</div> : null}
      </div>
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="ws-field">
      <span>{label}</span>
      {children}
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
  label: string;
}) {
  return (
    <div className="ws-segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={value === option.value ? "ws-segmented-active" : ""}
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
