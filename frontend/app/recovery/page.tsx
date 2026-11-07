"use client";

/**
 * Recovery Monitoring - Phase 8
 *
 * Track farm recovery after treatment/intervention with follow-up
 * inspection dates and recovery progress.
 */

import { useCallback, useMemo, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  Field,
  Icon,
  Modal,
  PageHeader,
  ProgressBar,
  StatCard,
} from "@/components/workspace/ui";
import { formatDateTime } from "@/lib/format";
import {
  createRecoveryRecord,
  listFarmRecoveryRecords,
  type RecoveryRecordCreate,
} from "@/lib/api";
import { readSession } from "@/lib/auth";

export default function RecoveryPage() {
  const session = readSession();
  const token = session?.accessToken ?? "";

  const [farmId, setFarmId] = useState("");
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<RecoveryRecordCreate>({
    farm_id: "",
    h3_cell_id: "",
    crop_code: "",
    target_code: "",
    previous_severity: "high",
    current_severity: "moderate",
    recovery_percentage: 50,
    recovery_status: "partial_recovery",
    follow_up_date: "",
    notes: "",
  });

  const loadRecords = useCallback(async (id: string) => {
    if (!token) return;
    setLoading(true);
    try {
      const result = await listFarmRecoveryRecords(id, token);
      setRecords(result.records);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load recovery records");
    } finally {
      setLoading(false);
    }
  }, [token]);

  const handleCreate = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      await createRecoveryRecord(createForm, token);
      setCreateOpen(false);
      setCreateForm({
        farm_id: "",
        h3_cell_id: "",
        crop_code: "",
        target_code: "",
        previous_severity: "high",
        current_severity: "moderate",
        recovery_percentage: 50,
        recovery_status: "partial_recovery",
        follow_up_date: "",
        notes: "",
      });
      if (createForm.farm_id) {
        await loadRecords(createForm.farm_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create recovery record");
    } finally {
      setLoading(false);
    }
  }, [token, createForm, loadRecords]);

  const handleFarmChange = useCallback(async (id: string) => {
    setFarmId(id);
    if (id) {
      await loadRecords(id);
    } else {
      setRecords([]);
    }
  }, [loadRecords]);

  const recoveryProgress = useMemo(() => {
    if (records.length === 0) return 0;
    const latest = records.reduce(
      (prev: any, curr: any) =>
        new Date(curr.created_at) > new Date(prev.created_at) ? curr : prev,
    );
    return latest.recovery_percentage;
  }, [records]);

  const latestRecord = useMemo(() => {
    if (records.length === 0) return null;
    return records.reduce(
      (prev: any, curr: any) =>
        new Date(curr.created_at) > new Date(prev.created_at) ? curr : prev,
    );
  }, [records]);

  return (
    <div className="ws-page">
      <PageHeader
        eyebrow="Recovery Monitoring"
        title="Farm Recovery Tracking"
        lede="Track recovery progress after treatment with follow-up inspection dates and severity changes."
      />

      {error && (
        <div className="ws-panel ws-stack" style={{ padding: "16px" }}>
          <div style={{ color: "#b42318", fontSize: "13px", marginBottom: "8px" }}>
            <Icon name="alert" size={14} /> {error}
          </div>
        </div>
      )}

      <div className="ws-two-col ws-two-col-wide">
        <section className="ws-panel ws-stack">
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Farm recovery</p>
              <h2>Select Farm</h2>
            </div>
          </div>

          <form onSubmit={(e) => e.preventDefault()} className="ws-form ws-stack">
            <Field label="Farm ID">
              <input
                value={farmId}
                onChange={(e) => handleFarmChange(e.target.value)}
                placeholder="Enter farm ID"
              />
            </Field>
            <div style={{ marginTop: "12px" }}>
              <Button size="sm" variant="solid" onClick={() => handleFarmChange(farmId)}>
                Load Records
              </Button>
            </div>
          </form>

          {loading && <div style={{ textAlign: "center", padding: "24px" }}>Loading...</div>}

          {records.length === 0 && !loading && farmId && (
            <EmptyState
              icon="leaf"
              title="No recovery records"
              body="No recovery monitoring records found for this farm. Create one to start tracking."
            />
          )}

          {records.length > 0 && latestRecord && (
            <div style={{ marginTop: "16px" }}>
              <strong>Latest Record:</strong>
              <div className="ws-small ws-muted" style={{ marginTop: "6px" }}>
                Severity: {latestRecord.previous_severity} → {latestRecord.current_severity}<br />
                Recovery: {latestRecord.recovery_percentage}%<br />
                Status: {latestRecord.recovery_status}<br />
                Follow-up: {latestRecord.follow_up_date || "—"}
              </div>
            </div>
          )}
        </section>

        <section className="ws-panel ws-stack">
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Recovery progress</p>
              <h2>Tracking</h2>
            </div>
          </div>

          {latestRecord && (
            <div>
              <StatCard label="Recovery %" value={Math.round(recoveryProgress)} detail="Current recovery" tone="brand" />
              <StatCard label="Previous Severity" value={latestRecord.previous_severity} tone="warn" />
              <StatCard label="Current Severity" value={latestRecord.current_severity} tone={latestRecord.current_severity === "none" || latestRecord.current_severity === "low" ? "ok" : "bad"} />
              <StatCard label="Status" value={latestRecord.recovery_status.replace("_", " ")} tone="brand" />

              <div style={{ marginTop: "16px" }}>
                <ProgressBar
                  value={recoveryProgress}
                  label="Recovery Progress"
                  tone={recoveryProgress >= 75 ? "ok" : recoveryProgress >= 50 ? "warn" : "bad"}
                />
              </div>

              {latestRecord.follow_up_date && (
                <div style={{ marginTop: "12px", padding: "12px", background: "#eef1eb", borderRadius: "8px" }}>
                  <strong style={{ display: "block", marginBottom: "6px", fontSize: "12px" }}>
                    Follow-up Inspection
                  </strong>
                  <p style={{ margin: 0, fontSize: "13px" }}>{formatDateTime(latestRecord.follow_up_date)}</p>
                </div>
              )}

              {latestRecord.notes && (
                <div style={{ marginTop: "12px", padding: "12px", background: "#f4f6f1", borderRadius: "8px" }}>
                  <strong style={{ display: "block", marginBottom: "6px", fontSize: "12px" }}>Notes:</strong>
                  <p style={{ margin: 0, fontSize: "13px" }}>{latestRecord.notes}</p>
                </div>
              )}
            </div>
          )}

          {!latestRecord && farmId && (
            <EmptyState icon="leaf" title="No recovery data" body="Create a recovery record to start tracking this farm's progress." />
          )}

          <div style={{ marginTop: "16px" }}>
            <Button size="sm" variant="solid" onClick={() => setCreateOpen(true)}>
              + Create Recovery Record
            </Button>
          </div>
        </section>
      </div>

      {createOpen && (
        <Modal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          title="Create Recovery Record"
          footer={
            <>
              <Button size="sm" variant="ghost" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" variant="solid" onClick={handleCreate} disabled={loading}>
                Create
              </Button>
            </>
          }
        >
          <form onSubmit={(e) => { e.preventDefault(); handleCreate(); }} className="ws-form ws-stack">
            <Field label="Farm ID">
              <input
                value={createForm.farm_id}
                onChange={(e) => setCreateForm({ ...createForm, farm_id: e.target.value })}
                required
              />
            </Field>
            <Field label="H3 Cell ID">
              <input
                value={createForm.h3_cell_id}
                onChange={(e) => setCreateForm({ ...createForm, h3_cell_id: e.target.value })}
                required
              />
            </Field>
            <Field label="Crop Code">
              <input
                value={createForm.crop_code}
                onChange={(e) => setCreateForm({ ...createForm, crop_code: e.target.value })}
                required
              />
            </Field>
            <Field label="Target Code">
              <input
                value={createForm.target_code}
                onChange={(e) => setCreateForm({ ...createForm, target_code: e.target.value })}
                required
              />
            </Field>
            <Field label="Previous Severity">
              <select
                value={createForm.previous_severity}
                onChange={(e) => setCreateForm({ ...createForm, previous_severity: e.target.value }) as any}
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="moderate">Moderate</option>
                <option value="low">Low</option>
                <option value="none">None</option>
              </select>
            </Field>
            <Field label="Current Severity">
              <select
                value={createForm.current_severity}
                onChange={(e) => setCreateForm({ ...createForm, current_severity: e.target.value }) as any}
              >
                <option value="none">None</option>
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </Field>
            <Field label="Recovery Percentage">
              <input
                type="number"
                min="0"
                max="100"
                value={createForm.recovery_percentage}
                onChange={(e) => setCreateForm({ ...createForm, recovery_percentage: parseFloat(e.target.value) || 0 })}
                required
              />
            </Field>
            <Field label="Recovery Status">
              <select
                value={createForm.recovery_status}
                onChange={(e) => setCreateForm({ ...createForm, recovery_status: e.target.value }) as any}
              >
                <option value="worsening">Worsening</option>
                <option value="stable">Stable</option>
                <option value="partial_recovery">Partial Recovery</option>
                <option value="full_recovery">Full Recovery</option>
              </select>
            </Field>
            <Field label="Follow-up Date">
              <input type="date" value={createForm.follow_up_date} onChange={(e) => setCreateForm({ ...createForm, follow_up_date: e.target.value })} />
            </Field>
            <Field label="Notes">
              <textarea rows={3} value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />
            </Field>

            <div style={{ marginTop: "16px" }}>
              <Button type="submit" variant="solid" size="sm" disabled={loading}>
                {loading ? "Creating..." : "Create Record"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
