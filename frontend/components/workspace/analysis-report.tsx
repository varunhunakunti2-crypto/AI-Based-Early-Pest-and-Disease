"use client";

import { useState } from "react";

import { formatDateTime, partLabel } from "@/lib/format";
import { useWorkspace } from "@/lib/workspace/store";
import type { Analysis } from "@/lib/workspace/types";

import { Badge, Icon, PhotoTile, SeverityPill } from "./ui";

function confidenceLabel(band: Analysis["confidenceBand"]): string {
  switch (band) {
    case "high":
      return "High confidence band";
    case "medium":
      return "Medium confidence band";
    case "low":
      return "Low confidence band";
    case "not_calibrated":
      return "Not yet calibrated";
  }
}

function confidenceTone(band: Analysis["confidenceBand"]): "ok" | "warn" | "bad" | "neutral" {
  if (band === "high") return "ok";
  if (band === "medium") return "warn";
  if (band === "low") return "bad";
  return "neutral";
}

function reviewBadge(analysis: Analysis) {
  switch (analysis.reviewStatus) {
    case "pending":
      return <Badge tone="purple">Pending expert review</Badge>;
    case "verified":
      return <Badge tone="ok">Expert verified</Badge>;
    case "corrected":
      return <Badge tone="info">Corrected by expert</Badge>;
    case "rejected":
      return <Badge tone="bad">Rejected by expert</Badge>;
    default:
      return <Badge tone="neutral">Not reviewed</Badge>;
  }
}

export function AnalysisReport({
  analysis,
  compact = false,
  onCompare,
}: {
  analysis: Analysis;
  compact?: boolean;
  onCompare?: () => void;
}) {
  const { requestVerification } = useWorkspace();
  const [requested, setRequested] = useState(false);
  const subject = analysis.pest ?? analysis.disease ?? "No specific match";
  const isHealthy = analysis.category === "healthy";

  return (
    <article className={compact ? "ws-report ws-report-compact" : "ws-report"}>
      <div className="ws-report-media">
        <PhotoTile
          tone={analysis.imageTone}
          mediaType={analysis.mediaType}
          label={`${analysis.subjectLabel} capture`}
          size="lg"
          src={analysis.imageUrl}
        />
        <div className="ws-report-media-meta">
          <span className="ws-chip">{analysis.mediaType === "video" ? "Video" : "Photo"}</span>
          <span className="ws-chip">{partLabel(analysis.plantPart)}</span>
          <span className="ws-chip ws-chip-demo">Demo</span>
        </div>
      </div>

      <div className="ws-report-body">
        <div className="ws-report-head">
          <div>
            <p className="ws-eyebrow">Assistive photo assessment</p>
            <h2>{isHealthy ? "No visible symptoms detected" : `Possible symptom match: ${subject}`}</h2>
            <p className="ws-small ws-muted">
              {analysis.subjectLabel} · {analysis.farmName} · {formatDateTime(analysis.createdAt)}
            </p>
          </div>
          <div className="ws-report-badges">
            <SeverityPill severity={analysis.severity} />
            {reviewBadge(analysis)}
          </div>
        </div>

        <div className="ws-report-summary">
          <div>
            <span>Confidence</span>
            <strong>{confidenceLabel(analysis.confidenceBand)}</strong>
            <small>{analysis.calibrated ? "Calibrated probabilities approved" : "Not yet calibrated · shown as a band, not a percentage"}</small>
          </div>
          <div>
            <span>Model</span>
            <strong>{analysis.modelVersion}</strong>
            <small>Generated from {analysis.mediaType === "video" ? "video frames" : "one image"} plus crop context</small>
          </div>
          <div>
            <span>Category</span>
            <strong className="ws-capitalize">{analysis.category}</strong>
            <small>Not a laboratory confirmation</small>
          </div>
        </div>

        <div className="ws-report-columns">
          <section>
            <h3>Visible symptoms</h3>
            <ul className="ws-list">
              {analysis.symptoms.map((symptom) => (
                <li key={symptom}>{symptom}</li>
              ))}
            </ul>
          </section>
          <section>
            <h3>Affected plant parts</h3>
            <div className="ws-chip-row">
              {analysis.affectedParts.length > 0
                ? analysis.affectedParts.map((part) => <span key={part} className="ws-chip">{partLabel(part)}</span>)
                : <span className="ws-chip ws-chip-muted">None observed</span>}
            </div>
            <h3 className="ws-mt">Possible causes</h3>
            <ul className="ws-list">
              {analysis.causes.map((cause) => (
                <li key={cause}>{cause}</li>
              ))}
            </ul>
          </section>
        </div>

        <section>
          <h3>Alternative possible diagnoses</h3>
          {analysis.alternatives.length > 0 ? (
            <div className="ws-alternatives">
              {analysis.alternatives.map((alternative) => (
                <div key={alternative.label} className="ws-alternative">
                  <div>
                    <strong>{alternative.label}</strong>
                    <span>{alternative.confidence}% relative evidence</span>
                  </div>
                  <div className="ws-alt-bar" aria-hidden="true">
                    <span style={{ width: `${alternative.confidence}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="ws-small ws-muted">No other class cleared the comparison threshold.</p>
          )}
        </section>

        <section className="ws-next-steps">
          <h3>Recommended next steps</h3>
          <ol>
            {analysis.nextSteps.map((step) => (
              <li key={step}>
                <Icon name="check" size={16} />
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </section>

        {analysis.reviewer ? (
          <div className="ws-review-note">
            <div className="ws-review-note-head">
              <Icon name="expert" size={18} />
              <div>
                <strong>Expert review · {analysis.reviewer}</strong>
                <small>{analysis.reviewStatus === "corrected" ? "Diagnosis corrected" : "Verification recorded"}</small>
              </div>
            </div>
            <p>{analysis.reviewerNote}</p>
            {analysis.expertRecommendation && analysis.expertRecommendation.length > 0 ? (
              <ul className="ws-list">
                {analysis.expertRecommendation.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        {analysis.notes ? <p className="ws-report-notes"><strong>Field notes:</strong> {analysis.notes}</p> : null}

        <div className="ws-report-actions">
          {analysis.reviewStatus === "not_requested" ? (
            <button
              type="button"
              className="ws-button ws-button-primary"
              disabled={requested}
              onClick={() => {
                requestVerification(analysis.id);
                setRequested(true);
              }}
            >
              <Icon name="expert" size={16} />
              {requested ? "Verification requested" : "Request expert verification"}
            </button>
          ) : (
            <span className="ws-reviewed-chip">
              <Icon name="shield" size={15} />
              Human review: {analysis.reviewStatus.replace("_", " ")}
            </span>
          )}
          {onCompare ? (
            <button type="button" className="ws-button ws-button-secondary" onClick={onCompare}>
              <Icon name="monitoring" size={16} /> Compare with previous
            </button>
          ) : null}
        </div>

        <p className="ws-disclaimer">
          This is an automated visual comparison, not a diagnosis. Insect damage, nutrient
          deficiency and disease can look alike. If symptoms are spreading, request an expert visit.
        </p>
      </div>
    </article>
  );
}

export { confidenceTone };
