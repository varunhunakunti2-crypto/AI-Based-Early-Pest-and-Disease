"use client";

/**
 * Inspection Result Submission - Phase 8
 *
 * Field agents and farmers submit inspection results with photo/video
 * evidence, symptom descriptions, and severity assessments.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  Field,
  Icon,
  Modal,
  PageHeader,
  PhotoTile,
  ProgressBar,
  StatCard,
} from "@/components/workspace/ui";
import { formatDateTime } from "@/lib/format";
import {
  submitInspectionResult,
  getInspectionResult,
  listTaskResults,
  type InspectionResultSubmit,
} from "@/lib/api";
import { readSession } from "@/lib/auth";

export default function InspectionsPage() {
  const session = readSession();
  const token = session?.accessToken ?? "";

  const [taskId, setTaskId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<InspectionResultSubmit | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);

    const formData = new FormData(e.currentTarget as HTMLFormElement);
    const payload: InspectionResultSubmit = {
      task_id: taskId,
      h3_cell_id: formData.get("h3_cell_id") as string,
      crop_code: formData.get("crop_code") as string,
      target_code: formData.get("target_code") as string,
      found_issue: formData.get("found_issue") === "true",
      severity: (formData.get("severity") as string) || undefined,
      ai_confidence: formData.get("ai_confidence")
        ? parseFloat(formData.get("ai_confidence") as string)
        : undefined,
      symptoms_observed: (formData.get("symptoms_observed") as string) || undefined,
      photos_taken: parseInt(formData.get("photos_taken") as string) || 0,
      videos_taken: parseInt(formData.get("videos_taken") as string) || 0,
      farmer_notified: formData.get("farmer_notified") === "true",
    };

    try {
      const created = await submitInspectionResult(payload, token);
      setSubmitted(payload);
      setResult(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit inspection result");
    } finally {
      setSubmitting(false);
    }
  }, [token, taskId]);

  const loadResult = useCallback(async (id: string) => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await getInspectionResult(id, token);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load result");
    } finally {
      setLoading(false);
    }
  }, [token]);

  const handleTaskIdChange = useCallback(async (id: string) => {
    setTaskId(id);
    if (id) {
      await loadResult(id);
    } else {
      setResult(null);
    }
  }, [loadResult]);

  return (
    <div className="ws-page">
      <PageHeader
        eyebrow="Field Inspection"
        title="Submit Inspection Result"
        lede="Record field inspection findings with photo/video evidence, symptom descriptions and severity."
      />

      {error && (
        <div className="ws-panel ws-stack" style={{ padding: "16px" }}>
          <div style={{ color: "#b42318", fontSize: "13px", marginBottom: "8px" }}>
            <Icon name="alert" size={14} /> {error}
          </div>
        </div>
      )}

      <div className="ws-two-col ws-two-col-wide">
        {/* Left: Submission form */}
        <section className="ws-panel ws-stack">
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Field report</p>
              <h2>Submit Result</h2>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="ws-form ws-stack">
            <Field label="Task ID">
              <input
                value={taskId}
                onChange={(e) => handleTaskIdChange(e.target.value)}
                placeholder="Enter task ID"
                required
              />
              <p className="ws-small ws-muted">
                The task must be in ACCEPTED or IN_PROGRESS status and assigned to you.
              </p>
            </Field>

            {result && (
              <div style={{ padding: "12px", background: "#eef1eb", borderRadius: "8px", marginBottom: "16px" }}>
                <strong style={{ display: "block", marginBottom: "6px", fontSize: "12px" }}>
                  Task details:
                </strong>
                <div className="ws-small ws-muted">
                  <span>Target: {result.target_code}</span>
                  <span>Crop: {result.crop_code}</span>
                  <span>Status: {result.status}</span>
                  <span>Cell: {result.h3_cell_id}</span>
                </div>
              </div>
            )}

            <Field label="H3 Cell ID">
              <input
                name="h3_cell_id"
                placeholder="e.g. 580964351931676600"
                required
              />
            </Field>
            <Field label="Crop Code">
              <input
                name="crop_code"
                placeholder="e.g. rice"
                required
              />
            </Field>
            <Field label="Target Code">
              <input
                name="target_code"
                placeholder="e.g. rice_blast"
                required
              />
            </Field>
            <Field label="Found Issue?">
              <div className="ws-segmented" role="group">
                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", flex: 1 }}>
                  <input
                    type="radio"
                    name="found_issue"
                    value="true"
                    defaultChecked={submitted?.found_issue}
                    onChange={() => {}}
                  />
                  Yes
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", flex: 1 }}>
                  <input
                    type="radio"
                    name="found_issue"
                    value="false"
                    defaultChecked={!submitted?.found_issue}
                    onChange={() => {}}
                  />
                  No
                </label>
              </div>
            </Field>
            <Field label="Severity">
              <select name="severity">
                <option value="">None</option>
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </Field>
            <Field label="AI Confidence (0-1)">
              <input
                name="ai_confidence"
                type="number"
                step="0.01"
                min="0"
                max="1"
                placeholder="0.85"
              />
            </Field>
            <Field label="Symptoms Observed">
              <textarea
                name="symptoms_observed"
                rows={3}
                placeholder="Describe observed symptoms..."
              />
            </Field>
            <Field label="Photos Taken">
              <input name="photos_taken" type="number" min="0" value="0" />
            </Field>
            <Field label="Videos Taken">
              <input name="videos_taken" type="number" min="0" value="0" />
            </Field>
            <Field label="Farmer Notified?">
              <div className="ws-segmented" role="group">
                <button type="button" className="ws-segmented-btn">Yes</button>
                <button type="button" className="ws-segmented-btn">No</button>
              </div>
              <input type="hidden" name="farmer_notified" value="false" />
            </Field>

            <div style={{ marginTop: "16px" }}>
              <Button type="submit" variant="solid" size="sm" disabled={submitting}>
                {submitting ? "Submitting..." : "Submit Inspection Result"}
              </Button>
            </div>
          </form>
        </section>

        {/* Right: Result preview */}
        {(submitted || result) && (
          <section className="ws-panel ws-stack">
            <div className="ws-panel-head">
              <div>
                <p className="ws-eyebrow">Submission preview</p>
                <h2>Inspection Result</h2>
              </div>
            </div>

            <StatCard label="Found Issue" value={submitted?.found_issue ?? result?.found_issue ? "Yes" : "No"} detail={submitted?.found_issue ?? result?.found_issue ? "Issue detected in field" : "No issue detected"} tone={submitted?.found_issue ?? result?.found_issue ? "bad" : "ok"} />
            {submitted?.severity && (
              <StatCard label="Severity" value={submitted.severity} detail="Field assessment" tone="warn" />
            )}
            <StatCard label="Photos" value={submitted?.photos_taken ?? result?.photos_taken} detail="Field evidence" />
            <StatCard label="Videos" value={submitted?.videos_taken ?? result?.videos_taken} detail="Field evidence" />

            {submitted?.symptoms_observed && (
              <div style={{ marginTop: "12px", padding: "12px", background: "#f4f6f1", borderRadius: "8px" }}>
                <strong style={{ display: "block", marginBottom: "6px", fontSize: "12px" }}>Symptoms:</strong>
                <p style={{ margin: 0, fontSize: "13px" }}>{submitted.symptoms_observed}</p>
              </div>
            )}

            <div style={{ marginTop: "12px" }}>
              <Button size="sm" variant="outline" onClick={() => setSubmitted(null)}>
                Submit Another
              </Button>
            </div>
          </section>
        )}
      </div>

      {result && (
        <section className="ws-panel ws-stack" style={{ marginTop: "24px" }}>
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Stored result</p>
              <h2>Verification</h2>
            </div>
          </div>
          <div className="ws-small ws-muted">
            <span>Result ID: {result.result_id}</span>
            <span>Inspected by: {result.inspected_by}</span>
            <span>Date: {formatDateTime(result.inspection_date)}</span>
            <span>Farmer notified: {result.farmer_notified ? "Yes" : "No"}</span>
          </div>
          <div style={{ marginTop: "12px" }}>
            <Button size="sm" variant="outline" onClick={() => setResult(null)}>
              Dismiss
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
