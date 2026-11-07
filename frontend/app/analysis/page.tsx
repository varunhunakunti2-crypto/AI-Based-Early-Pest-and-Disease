"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { AnalysisReport } from "@/components/workspace/analysis-report";
import {
  Badge,
  EmptyState,
  Icon,
  Modal,
  PageHeader,
  PhotoTile,
  ProgressBar,
  SeverityPill,
  StatCard,
  Tabs,
} from "@/components/workspace/ui";
import { formatDateTime, relativeTime } from "@/lib/format";
import { useWorkspace } from "@/lib/workspace/store";
import type { Analysis } from "@/lib/workspace/types";

type Filter = "all" | "pending" | "verified" | "high";

export default function AnalysisPage() {
  return (
    <Suspense fallback={null}>
      <AnalysisWorkspace />
    </Suspense>
  );
}

function AnalysisWorkspace() {
  const searchParams = useSearchParams();
  const { state, createAnalysis } = useWorkspace();
  const [filter, setFilter] = useState<Filter>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);

  const focus = searchParams.get("focus");
  const focusedId =
    focus && state.analyses.some((analysis) => analysis.id === focus) ? focus : null;
  const activeId = selectedId ?? focusedId ?? state.analyses[0]?.id ?? null;

  const filtered = useMemo(
    () =>
      state.analyses.filter((analysis) => {
        if (filter === "pending") return analysis.reviewStatus === "pending";
        if (filter === "verified") return analysis.reviewStatus === "verified" || analysis.reviewStatus === "corrected";
        if (filter === "high") return analysis.severity === "high" || analysis.severity === "critical";
        return true;
      }),
    [state.analyses, filter],
  );

  const active = state.analyses.find((analysis) => analysis.id === activeId) ?? filtered[0] ?? state.analyses[0];
  const pending = state.analyses.filter((analysis) => analysis.reviewStatus === "pending");
  const unsyncedAnalyses = state.captures.filter((capture) => !capture.analysisId);

  function select(analysis: Analysis) {
    setSelectedId(analysis.id);
    window.history.replaceState(null, "", `/analysis?focus=${analysis.id}`);
  }

  const previous = active
    ? state.analyses.find(
        (analysis) =>
          analysis.subjectId === active.subjectId && analysis.createdAt < active.createdAt,
      ) ?? state.analyses.find((analysis) => analysis.subjectId === active.subjectId && analysis.id !== active.id)
    : undefined;

  return (
    <div className="ws-page">
      <PageHeader
        eyebrow="AI analysis"
        title="Explainable photo & video triage"
        lede="See the detected pest or disease, visible symptoms, affected parts, severity, confidence band, possible causes, alternatives and one safe next step."
        actions={
          <Link href="/scan" className="ws-button ws-button-primary">
            <Icon name="camera" size={17} /> New capture
          </Link>
        }
      />

      <div className="ws-stat-grid">
        <StatCard label="Assessments" value={state.analyses.length} detail="Images and videos" icon="analysis" tone="brand" />
        <StatCard label="Awaiting verification" value={pending.length} detail="Expert review requested" icon="expert" tone="warn" />
        <StatCard label="High or critical" value={state.analyses.filter((item) => item.severity === "high" || item.severity === "critical").length} detail="Field follow-up prioritised" icon="alert" tone="bad" />
        <StatCard label="Expert verified" value={state.analyses.filter((item) => item.reviewStatus === "verified" || item.reviewStatus === "corrected").length} detail="Human-confirmed records" icon="shield" tone="ok" />
      </div>

      {unsyncedAnalyses.length > 0 ? (
        <div className="ws-banner ws-banner-info">
          <Icon name="scan" size={18} />
          <div>
            <strong>{unsyncedAnalyses.length} capture{unsyncedAnalyses.length === 1 ? "" : "s"} not analysed yet</strong>
            <p>Run an assistive assessment on a saved photo or video. The result is labelled as demo content.</p>
          </div>
          <div className="ws-banner-actions">
            {unsyncedAnalyses.slice(0, 2).map((capture) => (
              <button
                key={capture.id}
                type="button"
                className="ws-button ws-button-secondary"
                onClick={async () => {
                  const analysis = await createAnalysis(capture.id);
                  if (analysis) {
                    setSelectedId(analysis.id);
                    setCompareOpen(false);
                  }
                }}
              >
                Analyse {capture.subjectLabel}
              </button>
            ))}
            <Link href="/scan" className="ws-link">Open scan & capture</Link>
          </div>
        </div>
      ) : null}

      <Tabs
        label="Analysis filters"
        value={filter}
        onChange={setFilter}
        tabs={[
          { value: "all", label: "All", count: state.analyses.length },
          { value: "pending", label: "Needs review", count: pending.length },
          { value: "verified", label: "Verified", count: state.analyses.filter((item) => item.reviewStatus === "verified" || item.reviewStatus === "corrected").length },
          { value: "high", label: "High severity", count: state.analyses.filter((item) => item.severity === "high" || item.severity === "critical").length },
        ]}
      />

      <div className="ws-analysis-layout">
        <aside className="ws-panel ws-analysis-list">
          <div className="ws-panel-head">
            <h2>Assessments</h2>
            <Badge tone="neutral">{filtered.length}</Badge>
          </div>
          <ul className="ws-analysis-items">
            {filtered.map((analysis) => (
              <li key={analysis.id}>
                <button
                  type="button"
                  className={analysis.id === active?.id ? "ws-analysis-item ws-analysis-item-active" : "ws-analysis-item"}
                  onClick={() => select(analysis)}
                >
                  <PhotoTile tone={analysis.imageTone} mediaType={analysis.mediaType} label={analysis.subjectLabel} size="sm" />
                  <span className="ws-analysis-item-body">
                    <span className="ws-analysis-item-top">
                      <strong>{analysis.pest ?? analysis.disease ?? "No specific match"}</strong>
                      <SeverityPill severity={analysis.severity} />
                    </span>
                    <span className="ws-small ws-muted">{analysis.subjectLabel} · {relativeTime(analysis.createdAt)}</span>
                    <span className="ws-chip-row">
                      <span className="ws-chip">{analysis.confidenceBand} confidence</span>
                      {analysis.reviewStatus !== "not_requested" ? <span className="ws-chip">{analysis.reviewStatus.replace("_", " ")}</span> : null}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {filtered.length === 0 ? <p className="ws-empty-inline">No assessments match this filter.</p> : null}
        </aside>

        <div className="ws-stack">
          {active ? (
            <>
              <AnalysisReport
                analysis={active}
                onCompare={previous ? () => setCompareOpen(true) : undefined}
              />

              <section className="ws-panel">
                <div className="ws-panel-head">
                  <div><p className="ws-eyebrow">Observation context</p><h2>Why this result is cautious</h2></div>
                  <Badge tone="info">Safety boundary</Badge>
                </div>
                <div className="ws-context-grid">
                  <div>
                    <span>Image quality</span>
                    <strong>Good · sharp, daylight</strong>
                    <ProgressBar value={82} label="Quality gate score" tone="ok" />
                  </div>
                  <div>
                    <span>Calibration state</span>
                    <strong>Not yet calibrated</strong>
                    <p className="ws-small ws-muted">Bands are shown instead of numeric probability until calibration is approved.</p>
                  </div>
                  <div>
                    <span>Human review</span>
                    <strong>{active.reviewStatus === "pending" ? "Queued with an expert" : active.reviewStatus === "not_requested" ? "Not requested" : "Completed"}</strong>
                    <p className="ws-small ws-muted">A person has {active.reviewer ? `reviewed this case (${active.reviewer})` : "not reviewed this case"}.</p>
                  </div>
                </div>
                <div className="ws-notice">
                  This card never changes the stored prediction. Retaking a photo creates a new
                  assessment; requesting review opens a separate human workflow.
                </div>
              </section>

              {previous ? (
                <section className="ws-panel">
                  <div className="ws-panel-head">
                    <div><p className="ws-eyebrow">Previous vs current</p><h2>Observation comparison</h2></div>
                    <button type="button" className="ws-button ws-button-secondary" onClick={() => setCompareOpen(true)}>
                      <Icon name="monitoring" size={15} /> Open comparison
                    </button>
                  </div>
                  <div className="ws-compare-strip">
                    <div>
                      <PhotoTile tone={previous.imageTone} mediaType={previous.mediaType} label="Previous capture" />
                      <span className="ws-small ws-muted">Previous · {formatDateTime(previous.createdAt)}</span>
                    </div>
                    <Icon name="arrow" size={20} />
                    <div>
                      <PhotoTile tone={active.imageTone} mediaType={active.mediaType} label="Current capture" />
                      <span className="ws-small ws-muted">Current · {formatDateTime(active.createdAt)}</span>
                    </div>
                    <div className="ws-compare-summary">
                      <Badge tone={active.severity === previous.severity ? "warn" : "info"}>
                        {active.severity === previous.severity ? "Similar severity" : "Severity changed"}
                      </Badge>
                      <p className="ws-small">Compare the same plant and plant part. Lighting and distance can change how a symptom looks.</p>
                    </div>
                  </div>
                </section>
              ) : null}
            </>
          ) : (
            <EmptyState
              title="No assessments yet"
              body="Capture a photo from Scan & capture, then run an assistive assessment."
              action={<Link href="/scan" className="ws-button ws-button-primary">Scan a plant</Link>}
            />
          )}
        </div>
      </div>

      <Modal open={compareOpen} onClose={() => setCompareOpen(false)} title="Compare observations">
        {active && previous ? (
          <div className="ws-compare-modal">
            <div className="ws-compare-col">
              <p className="ws-eyebrow">Previous</p>
              <PhotoTile tone={previous.imageTone} mediaType={previous.mediaType} label="Previous observation" size="lg" />
              <dl className="ws-detail-list">
                <div><dt>Date</dt><dd>{formatDateTime(previous.createdAt)}</dd></div>
                <div><dt>Match</dt><dd>{previous.pest ?? previous.disease ?? "None"}</dd></div>
                <div><dt>Severity</dt><dd>{previous.severity}</dd></div>
                <div><dt>Confidence</dt><dd>{previous.confidenceBand}</dd></div>
              </dl>
            </div>
            <div className="ws-compare-col">
              <p className="ws-eyebrow">Current</p>
              <PhotoTile tone={active.imageTone} mediaType={active.mediaType} label="Current observation" size="lg" />
              <dl className="ws-detail-list">
                <div><dt>Date</dt><dd>{formatDateTime(active.createdAt)}</dd></div>
                <div><dt>Match</dt><dd>{active.pest ?? active.disease ?? "None"}</dd></div>
                <div><dt>Severity</dt><dd>{active.severity}</dd></div>
                <div><dt>Confidence</dt><dd>{active.confidenceBand}</dd></div>
              </dl>
            </div>
            <p className="ws-disclaimer">
              Visual comparison is not proof of treatment effectiveness. Confirm change with a
              field inspection and expert review when the case is high impact.
            </p>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
