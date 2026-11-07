"use client";

/**
 * Task Management Dashboard - Phase 8
 *
 * Uber-style intelligent task distribution interface for farmers,
 * field agents, and agricultural experts.
 *
 * Supports:
 * - Viewing available nearby tasks (voluntary acceptance)
 * - Viewing my assigned tasks
 * - Accept/decline/start/submit/complete task actions
 * - Eligible user lookup for task assignment
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
  StatCard,
  Tabs,
} from "@/components/workspace/ui";
import { formatDateTime, relativeTime } from "@/lib/format";
import {
  acceptTask,
  completeTask,
  createInspectionTask,
  declineTask,
  getEligibleUsers,
  listAvailableTasks,
  listMyTasks,
  listTaskResults,
  startTask,
  submitTask,
  type AvailableTask,
  type EligibleUser,
  type InspectionTaskSummary,
  type TaskCreateInput,
} from "@/lib/api";
import { readSession } from "@/lib/auth";

type TaskTab = "available" | "my-tasks" | "create" | "results";

const PRIORITY_TONE: Record<string, "ok" | "warn" | "bad" | "alert"> = {
  low: "ok",
  moderate: "warn",
  high: "bad",
  urgent: "alert",
};

const STATUS_TONE: Record<string, "ok" | "warn" | "bad" | "neutral"> = {
  CREATED: "neutral",
  AVAILABLE: "warn",
  ASSIGNED: "warn",
  ACCEPTED: "warn",
  IN_PROGRESS: "bad",
  SUBMITTED: "warn",
  UNDER_REVIEW: "warn",
  VERIFIED: "ok",
  COMPLETED: "ok",
};

export default function TasksPage() {
  const session = readSession();
  const token = session?.accessToken ?? "";

  const [tab, setTab] = useState<TaskTab>("available");
  const [availableTasks, setAvailableTasks] = useState<AvailableTask[]>([]);
  const [myTasks, setMyTasks] = useState<InspectionTaskSummary[]>([]);
  const [eligibleUsers, setEligibleUsers] = useState<EligibleUser[]>([]);
  const [taskResults, setTaskResults] = useState<any[]>([]);
  const [selectedTask, setSelectedTask] = useState<AvailableTask | null>(null);
  const [selectedMyTask, setSelectedMyTask] = useState<InspectionTaskSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<TaskCreateInput>({
    h3_cell_id: "",
    crop_code: "",
    target_code: "",
    task_type: "routine_scouting",
    priority: "moderate",
    required_expertise: [],
  });

  // Load available tasks
  const loadAvailableTasks = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const tasks = await listAvailableTasks(token, 50);
      setAvailableTasks(tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load available tasks");
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Load my tasks
  const loadMyTasks = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const tasks = await listMyTasks(token, undefined, 50);
      setMyTasks(tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load my tasks");
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Load eligible users for task creation
  const loadEligibleUsers = useCallback(async (cellId: string, taskType: string, cropCode: string, targetCode: string) => {
    if (!token) return;
    try {
      const result = await getEligibleUsers(token, {
        h3_cell_id: cellId,
        task_type: taskType,
        crop_code: cropCode,
        target_code: targetCode,
      });
      setEligibleUsers(result.eligible_users);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load eligible users");
    }
  }, [token]);

  // Load task results
  const loadTaskResults = useCallback(async (taskId: string) => {
    if (!token) return;
    try {
      const result = await listTaskResults(taskId, token);
      setTaskResults(result.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load task results");
    }
  }, [token]);

  useEffect(() => {
    loadAvailableTasks();
    loadMyTasks();
  }, [loadAvailableTasks, loadMyTasks]);

  const handleAccept = useCallback(async (task: AvailableTask) => {
    if (!token) return;
    setLoading(true);
    try {
      const updated = await acceptTask(task.task_id, token);
      setAvailableTasks(availableTasks.filter((t) => t.task_id !== task.task_id));
      setMyTasks([updated, ...myTasks]);
      setSelectedTask(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to accept task");
    } finally {
      setLoading(false);
    }
  }, [token, availableTasks, myTasks]);

  const handleDecline = useCallback(async (task: InspectionTaskSummary) => {
    if (!token) return;
    setLoading(true);
    try {
      await declineTask(task.task_id, token);
      setAvailableTasks(availableTasks.filter((t) => t.task_id !== task.task_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to decline task");
    } finally {
      setLoading(false);
    }
  }, [token, availableTasks]);

  const handleStart = useCallback(async (task: InspectionTaskSummary) => {
    if (!token) return;
    setLoading(true);
    try {
      const updated = await startTask(task.task_id, token);
      setMyTasks(myTasks.map((t) => (t.task_id === task.task_id ? updated : t)));
      setSelectedMyTask(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start task");
    } finally {
      setLoading(false);
    }
  }, [token, myTasks]);

  const handleSubmit = useCallback(async (task: InspectionTaskSummary) => {
    if (!token) return;
    setLoading(true);
    try {
      const updated = await submitTask(task.task_id, token);
      setMyTasks(myTasks.map((t) => (t.task_id === task.task_id ? updated : t)));
      setSelectedMyTask(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit task");
    } finally {
      setLoading(false);
    }
  }, [token, myTasks]);

  const handleComplete = useCallback(async (task: InspectionTaskSummary, verified = true) => {
    if (!token) return;
    setLoading(true);
    try {
      const updated = await completeTask(task.task_id, token, verified);
      setMyTasks(myTasks.map((t) => (t.task_id === task.task_id ? updated : t)));
      setSelectedMyTask(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete task");
    } finally {
      setLoading(false);
    }
  }, [token, myTasks]);

  const handleCreate = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const created = await createInspectionTask(createForm, token);
      setMyTasks([created, ...myTasks]);
      setCreateOpen(false);
      setCreateForm({
        h3_cell_id: "",
        crop_code: "",
        target_code: "",
        task_type: "routine_scouting",
        priority: "moderate",
        required_expertise: [],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setLoading(false);
    }
  }, [token, createForm, myTasks]);

  const availableCount = availableTasks.length;
  const myActiveCount = myTasks.filter(
    (t) =>
      t.status !== "COMPLETED" &&
      t.status !== "REJECTED" &&
      t.status !== "CANCELLED" &&
      t.status !== "EXPIRED",
  ).length;
  const completedCount = myTasks.filter((t) => t.status === "COMPLETED").length;

  return (
    <div className="ws-page">
      <PageHeader
        eyebrow="Task Distribution"
        title="Inspection Tasks"
        lede="Uber-style intelligent task distribution. Accept nearby tasks, manage your assignments, and submit field results."
        actions={
          <div className="ws-chip-row">
            <Badge tone={availableCount > 0 ? "warn" : "neutral"}>
              {availableCount} available
            </Badge>
            <Badge tone={myActiveCount > 0 ? "bad" : "ok"}>
              {myActiveCount} active
            </Badge>
          </div>
        }
      />

      {error && (
        <div className="ws-panel ws-stack" style={{ padding: "16px" }}>
          <div style={{ color: "#b42318", fontSize: "13px", marginBottom: "8px" }}>
            <Icon name="alert" size={14} /> {error}
          </div>
          <Button size="sm" onClick={() => {
            loadAvailableTasks();
            loadMyTasks();
            setError(null);
          }}>
            Retry
          </Button>
        </div>
      )}

      <Tabs
        label="Task views"
        value={tab}
        onChange={setTab}
        tabs={[
          { value: "available", label: "Available Nearby", count: availableCount },
          { value: "my-tasks", label: "My Tasks", count: myTasks.length },
          { value: "create", label: "Create Task", count: 0 },
          { value: "results", label: "Task Results", count: taskResults.length },
        ]}
      />

      {tab === "available" && (
        <section className="ws-panel">
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Voluntary acceptance</p>
              <h2>Available Nearby Tasks</h2>
            </div>
            {availableCount === 0 && <Badge tone="neutral">No tasks nearby</Badge>}
          </div>
          {loading && <div style={{ textAlign: "center", padding: "24px" }}>Loading tasks...</div>}
          {availableTasks.length === 0 && !loading && (
            <EmptyState
              icon="map"
              title="No available tasks"
              body="There are no inspection tasks nearby that match your expertise and availability. Check back later or contact your coordinator."
            />
          )}
          {availableTasks.map((task) => (
            <div
              key={task.task_id}
              className="ws-task-card"
              style={{
                border: "1px solid var(--ws-line)",
                borderRadius: "12px",
                padding: "16px",
                marginBottom: "12px",
                background: "var(--ws-card)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "8px" }}>
                <div>
                  <strong style={{ fontSize: "14px" }}>{task.target_code}</strong>
                  <span className="ws-small ws-muted ws-block">{task.crop_code}</span>
                </div>
                <Badge tone={PRIORITY_TONE[task.priority] ?? "neutral"}>
                  {task.priority}
                </Badge>
              </div>
              <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Icon name="location" size={12} />
                  Cell: {task.h3_cell_id}
                </span>
              </div>
              <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Icon name="calendar" size={12} />
                  Deadline: {task.deadline ? formatDateTime(task.deadline) : "—"}
                </span>
              </div>
              <div style={{ marginBottom: "8px" }}>
                <span className="ws-chip">{task.task_type.replace("_", " ")}</span>
                <span className="ws-chip">{task.assignment_type}</span>
              </div>
              <div className="ws-chip-row" style={{ marginTop: "8px" }}>
                <Button
                  size="sm"
                  variant="solid"
                  onClick={() => handleAccept(task)}
                  disabled={loading}
                >
                  <Icon name="check" size={14} /> Accept
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDecline(task)}
                  disabled={loading}
                >
                  Decline
                </Button>
              </div>
            </div>
          ))}
        </section>
      )}

      {tab === "my-tasks" && (
        <section className="ws-panel">
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Your assignments</p>
              <h2>My Tasks</h2>
            </div>
          </div>
          {myTasks.length === 0 && !loading && (
            <EmptyState
              icon="clipboard"
              title="No assigned tasks"
              body="You don't have any inspection tasks assigned. Browse available tasks to accept one nearby."
            />
          )}
          {myTasks.map((task) => (
            <div
              key={task.task_id}
              className="ws-task-card"
              style={{
                border: "1px solid var(--ws-line)",
                borderRadius: "12px",
                padding: "16px",
                marginBottom: "12px",
                background: "var(--ws-card)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "8px" }}>
                <div>
                  <strong style={{ fontSize: "14px" }}>{task.target_code}</strong>
                  <span className="ws-small ws-muted ws-block">{task.crop_code}</span>
                </div>
                <Badge tone={STATUS_TONE[task.status] ?? "neutral"}>
                  {task.status}
                </Badge>
              </div>
              <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Icon name="location" size={12} />
                  Cell: {task.h3_cell_id}
                </span>
              </div>
              <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Icon name="calendar" size={12} />
                  Deadline: {task.deadline ? formatDateTime(task.deadline) : "—"}
                </span>
              </div>
              <div style={{ marginBottom: "8px" }}>
                <span className="ws-chip">{task.task_type.replace("_", " ")}</span>
                <span className="ws-chip">{task.assignment_type}</span>
              </div>
              <div className="ws-chip-row" style={{ marginTop: "8px" }}>
                {task.status === "AVAILABLE" && (
                  <>
                    <Button
                      size="sm"
                      variant="solid"
                      onClick={() => {
                        setSelectedMyTask(task);
                        loadEligibleUsers(task.h3_cell_id, task.task_type, task.crop_code, task.target_code);
                      }}
                      disabled={loading}
                    >
                      Accept
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDecline(task)}
                      disabled={loading}
                    >
                      Decline
                    </Button>
                  </>
                )}
                {task.status === "ACCEPTED" && (
                  <Button
                    size="sm"
                    variant="solid"
                    onClick={() => handleStart(task)}
                    disabled={loading}
                  >
                    <Icon name="refresh" size={14} /> Start
                  </Button>
                )}
                {task.status === "IN_PROGRESS" && (
                  <Button
                    size="sm"
                    variant="solid"
                    onClick={() => handleSubmit(task)}
                    disabled={loading}
                  >
                    <Icon name="check" size={14} /> Submit
                  </Button>
                )}
                {(task.status === "SUBMITTED" || task.status === "UNDER_REVIEW") && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleComplete(task, true)}
                    disabled={loading}
                  >
                    Complete
                  </Button>
                )}
              </div>
              {eligibleUsers.length > 0 && (
                <div
                  style={{
                    marginTop: "12px",
                    padding: "10px",
                    background: "#eef1eb",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                >
                  <strong>Eligible nearby users:</strong>
                  {eligibleUsers.map((u) => (
                    <span
                      key={u.user_id}
                      className="ws-chip"
                      style={{ marginRight: "6px", marginBottom: "4px", display: "inline-block" }}
                    >
                      {u.user_id} · {u.distance_km ?? "?"}km
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {tab === "create" && (
        <section className="ws-panel ws-stack" style={{ maxWidth: "600px" }}>
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Create inspection task</p>
              <h2>New Task</h2>
            </div>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); handleCreate(); }} className="ws-form ws-stack">
            <Field label="H3 Cell ID">
              <input
                value={createForm.h3_cell_id}
                onChange={(e) => setCreateForm({ ...createForm, h3_cell_id: e.target.value })}
                placeholder="e.g. 580964351931676600"
                required
              />
            </Field>
            <Field label="Crop Code">
              <input
                value={createForm.crop_code}
                onChange={(e) => setCreateForm({ ...createForm, crop_code: e.target.value })}
                placeholder="e.g. rice"
                required
              />
            </Field>
            <Field label="Target Code">
              <input
                value={createForm.target_code}
                onChange={(e) => setCreateForm({ ...createForm, target_code: e.target.value })}
                placeholder="e.g. rice_blast"
                required
              />
            </Field>
            <Field label="Task Type">
              <select
                value={createForm.task_type}
                onChange={(e) =>
                  setCreateForm({ ...createForm, task_type: e.target.value as TaskCreateInput["task_type"] })
                }
              >
                <option value="routine_scouting">Routine Scouting</option>
                <option value="hotspot_verification">Hotspot Verification</option>
                <option value="recovery_inspection">Recovery Inspection</option>
                <option value="expert_review">Expert Review</option>
              </select>
            </Field>
            <Field label="Priority">
              <select
                value={createForm.priority}
                onChange={(e) =>
                  setCreateForm({ ...createForm, priority: e.target.value as TaskCreateInput["priority"] })
                }
              >
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </Field>
            <Field label="Required Expertise (comma-separated)">
              <input
                value={createForm.required_expertise?.join(",") ?? ""}
                onChange={(e) =>
                  setCreateForm({
                    ...createForm,
                    required_expertise: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="e.g. rice_blast, field_scouting"
              />
            </Field>
            <div className="ws-chip-row" style={{ marginTop: "12px" }}>
              <Button type="submit" size="sm" variant="solid" disabled={loading}>
                Create Task
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </Button>
            </div>
          </form>
        </section>
      )}

      {tab === "results" && (
        <section className="ws-panel">
          <div className="ws-panel-head">
            <div>
              <p className="ws-eyebrow">Inspection results</p>
              <h2>Task Results</h2>
            </div>
          </div>
          {taskResults.length === 0 && (
            <EmptyState
              icon="check"
              title="No results yet"
              body="Select a task from My Tasks to view its inspection results."
            />
          )}
          {taskResults.map((result) => (
            <div
              key={result.result_id}
              className="ws-task-card"
              style={{
                border: "1px solid var(--ws-line)",
                borderRadius: "12px",
                padding: "16px",
                marginBottom: "12px",
                background: "var(--ws-card)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "8px" }}>
                <div>
                  <strong style={{ fontSize: "14px" }}>{result.target_code}</strong>
                  <span className="ws-small ws-muted ws-block">{result.crop_code}</span>
                </div>
                <Badge tone={result.found_issue ? "bad" : "ok"}>
                  {result.found_issue ? "Issue Found" : "No Issue"}
                </Badge>
              </div>
              <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Icon name="location" size={12} />
                  Cell: {result.h3_cell_id}
                </span>
              </div>
              {result.severity && (
                <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                  Severity: <strong>{result.severity}</strong>
                </div>
              )}
              {result.ai_confidence != null && (
                <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                  AI Confidence: {(result.ai_confidence * 100).toFixed(1)}%
                </div>
              )}
              {result.symptoms_observed && (
                <div className="ws-small ws-muted" style={{ marginBottom: "8px" }}>
                  Symptoms: {result.symptoms_observed}
                </div>
              )}
              <div style={{ marginBottom: "8px" }}>
                <span className="ws-chip">{result.photos_taken} photos</span>
                <span className="ws-chip">{result.videos_taken} videos</span>
              </div>
              <div className="ws-small ws-muted">
                Inspected by {result.inspected_by} on {formatDateTime(result.inspection_date)}
              </div>
            </div>
          ))}
        </section>
      )}

      {selectedMyTask && (
        <Modal
          open={!!selectedMyTask}
          onClose={() => setSelectedMyTask(null)}
          title={`Task: ${selectedMyTask.target_code}`}
          footer={
            <>
              <Button size="sm" variant="ghost" onClick={() => setSelectedMyTask(null)}>
                Close
              </Button>
              {selectedMyTask.status === "SUBMITTED" || selectedMyTask.status === "UNDER_REVIEW" ? (
                <Button
                  size="sm"
                  variant="solid"
                  onClick={() => handleComplete(selectedMyTask, true)}
                  disabled={loading}
                >
                  Complete
                </Button>
              ) : null}
            </>
          }
        >
          <div className="ws-form ws-stack">
            <Field label="Target"><span>{selectedMyTask.target_code}</span></Field>
            <Field label="Crop"><span>{selectedMyTask.crop_code}</span></Field>
            <Field label="Type"><span>{selectedMyTask.task_type.replace("_", " ")}</span></Field>
            <Field label="Priority"><span>{selectedMyTask.priority}</span></Field>
            <Field label="Status"><span>{selectedMyTask.status}</span></Field>
            <Field label="Deadline"><span>{selectedMyTask.deadline ?? "—"}</span></Field>
            <Field label="Suspected Issue"><span>{selectedMyTask.suspected_issue ?? "—"}</span></Field>
            <Field label="H3 Cell"><span>{selectedMyTask.h3_cell_id}</span></Field>
            {eligibleUsers.length > 0 && (
              <div style={{ marginTop: "12px" }}>
                <strong style={{ display: "block", marginBottom: "6px", fontSize: "12px" }}>
                  Eligible nearby users for reassignment:
                </strong>
                {eligibleUsers.map((u) => (
                  <span
                    key={u.user_id}
                    className="ws-chip"
                    style={{ marginRight: "6px", marginBottom: "4px", display: "inline-block" }}
                  >
                    {u.user_id} · {u.distance_km ?? "?"}km
                  </span>
                ))}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
