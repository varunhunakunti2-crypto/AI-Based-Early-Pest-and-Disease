"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  Badge,
  Field,
  Icon,
  PageHeader,
  PhotoTile,
  Segmented,
  StatCard,
} from "@/components/workspace/ui";
import { formatDateTime, partLabel } from "@/lib/format";
import { useWorkspace } from "@/lib/workspace/store";
import type { PlantPart, SyncState } from "@/lib/workspace/types";

const PARTS: PlantPart[] = ["leaf", "stem", "root", "fruit", "flower", "whole_plant"];

function syncBadge(syncState: SyncState) {
  if (syncState === "synced") return <Badge tone="ok">Synced</Badge>;
  if (syncState === "queued") return <Badge tone="warn">Queued</Badge>;
  if (syncState === "syncing") return <Badge tone="info">Syncing</Badge>;
  return <Badge tone="bad">Failed</Badge>;
}

export default function ScanPage() {
  const router = useRouter();
  const { state, addCapture, syncCaptures, createAnalysis } = useWorkspace();
  const [mediaType, setMediaType] = useState<"image" | "video">("image");
  const [farmId, setFarmId] = useState(state.farms[0]?.id ?? "");
  const [selectedSubjectId, setSubjectId] = useState<string | null>(null);
  const [part, setPart] = useState<PlantPart>("leaf");
  const [notes, setNotes] = useState("");
  const [gps, setGps] = useState<{ lat: number; lng: number } | null>(null);
  const [gpsStatus, setGpsStatus] = useState("");
  const [staged, setStaged] = useState<{ name: string; tone: number; size: string; url?: string }[]>([]);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [online, setOnline] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [analysingId, setAnalysingId] = useState<string | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const videoStreamRef = useRef<HTMLVideoElement>(null);
  const streamTrackRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLInputElement>(null);

  const farm = state.farms.find((item) => item.id === farmId);
  const farmGroups = useMemo(() => state.cropGroups.filter((group) => group.farmId === farmId), [state.cropGroups, farmId]);
  const subjectId =
    selectedSubjectId && farmGroups.some((group) => group.id === selectedSubjectId)
      ? selectedSubjectId
      : (farmGroups[0]?.id ?? "");
  const subject = state.cropGroups.find((group) => group.id === subjectId);
  const subjectPlants = state.plants.filter((plant) => plant.cropGroupId === subjectId);
  const queued = state.captures.filter((capture) => capture.syncState !== "synced").length;

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  async function startCamera() {
    setCameraError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Camera API not supported or insecure context (requires localhost or HTTPS).");
      }
      
      let stream: MediaStream | null = null;
      try {
        // Try back/environment camera first
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
      } catch {
        // If environment camera fails, fallback to any available camera (webcam)
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        });
      }

      if (!stream) {
        throw new Error("No video stream returned.");
      }

      streamTrackRef.current = stream;
      setCameraActive(true);
      setTimeout(() => {
        if (videoStreamRef.current) {
          videoStreamRef.current.srcObject = stream;
          videoStreamRef.current.play().catch(() => {});
        }
      }, 100);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unable to access camera.";
      setCameraError(msg);
      // Do not automatically trigger file picker if user denied permission,
      // show helpful guidance button instead so they can choose.
    }
  }

  function stopCamera() {
    if (streamTrackRef.current) {
      streamTrackRef.current.getTracks().forEach((track) => track.stop());
      streamTrackRef.current = null;
    }
    setCameraActive(false);
  }

  function captureFromCamera() {
    if (!videoStreamRef.current) return;
    const video = videoStreamRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    stopCamera();

    const newCaptureItem = {
      name: `camera-capture-${Date.now().toString().slice(-4)}.jpg`,
      size: `${Math.round((dataUrl.length * 0.75) / 1024)} KB`,
      tone: Math.floor(Math.random() * 8),
      url: dataUrl,
    };
    setStaged((current) => [...current, newCaptureItem].slice(0, 6));
    setSavedId(null);
  }

  useEffect(() => {
    return () => {
      if (streamTrackRef.current) {
        streamTrackRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  function addFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const next = Array.from(files).map((file, index) => {
      const url = URL.createObjectURL(file);
      return {
        name: file.name,
        size: `${(file.size / 1024).toFixed(0)} KB`,
        tone: (file.name.length + index) % 8,
        url,
      };
    });
    setStaged((current) => (mediaType === "video" ? next.slice(0, 1) : [...current, ...next].slice(0, 6)));
    setSavedId(null);
  }

  function captureLocation() {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setGps({ lat: farm?.lat ?? 12.7409, lng: farm?.lng ?? 77.8253 });
      setGpsStatus("GPS unavailable. Farm coordinates used.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGps({ lat: Number(position.coords.latitude.toFixed(5)), lng: Number(position.coords.longitude.toFixed(5)) });
        setGpsStatus("GPS saved with permission.");
      },
      () => {
        setGps({ lat: farm?.lat ?? 12.7409, lng: farm?.lng ?? 77.8253 });
        setGpsStatus("Permission denied. Farm coordinates used; you can retry.");
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }

  function save() {
    if (!farm || staged.length === 0) return;
    const capture = addCapture({
      farmId,
      subjectId,
      subjectLabel: subject?.name ?? "Unassigned observation",
      mediaType,
      plantPart: part,
      notes,
      gps: gps ?? { lat: farm.lat, lng: farm.lng },
      imageTone: staged[0]?.tone ?? 3,
      imageUrl: staged[0]?.url,
    });
    setSavedId(capture.id);
    setStaged([]);
    setNotes("");
    if (online) {
      // In this demo "online" means the queue drains immediately after saving.
      window.setTimeout(() => syncCaptures(), 600);
    }
  }

  async function analyse(captureId: string) {
    setAnalysingId(captureId);
    try {
      const analysis = await createAnalysis(captureId);
      if (analysis) {
        router.push(`/analysis?focus=${analysis.id}`);
      }
    } finally {
      setAnalysingId(null);
    }
  }

  return (
    <div className="ws-page">
      <PageHeader
        eyebrow="Camera & farm scanning"
        title="Capture what you see"
        lede="Photograph a leaf, stem, root, fruit, flower or the whole plant. Add notes and GPS, then save offline if the signal is weak."
        actions={
          <div className="ws-online-pill">
            <span className={online ? "ws-live-dot" : "ws-offline-dot"} />
            {online ? "Online" : "Offline"}
          </div>
        }
      />

      {!online ? (
        <div className="ws-banner ws-banner-warn">
          <Icon name="alert" size={18} />
          <div>
            <strong>You are offline</strong>
            <p>Captures are saved on this device and will sync when a connection returns. Nothing will be lost.</p>
          </div>
        </div>
      ) : null}

      <div className="ws-stat-grid">
        <StatCard label="Captures on device" value={state.captures.length} detail={`${queued} waiting to sync`} icon="camera" tone={queued > 0 ? "warn" : "ok"} />
        <StatCard label="Synced" value={state.captures.filter((item) => item.syncState === "synced").length} detail="Ready for analysis" icon="sync" tone="ok" />
        <StatCard label="Observations" value={state.analyses.length} detail="Across all farms" icon="analysis" />
        <StatCard label="Plant parts covered" value={new Set(state.captures.map((item) => item.plantPart)).size} detail="Leaf, stem, fruit and more" icon="leaf" />
      </div>

      <div className="ws-scan-grid">
        <section className="ws-panel">
          <div className="ws-panel-head">
            <div><p className="ws-eyebrow">New observation</p><h2>Capture a plant</h2></div>
            <Segmented
              label="Capture type"
              value={mediaType}
              onChange={(value) => {
                setMediaType(value);
                setStaged([]);
              }}
              options={[
                { value: "image", label: "Photo" },
                { value: "video", label: "Video" },
              ]}
            />
          </div>

          <div className="ws-capture-stage">
            {cameraActive ? (
              <div className="ws-camera-viewfinder" style={{ display: "grid", gap: "10px", textAlign: "center" }}>
                <div style={{ position: "relative", width: "100%", maxWidth: "480px", margin: "0 auto", borderRadius: "12px", overflow: "hidden", background: "#000" }}>
                  <video
                    ref={videoStreamRef}
                    autoPlay
                    playsInline
                    muted
                    style={{ width: "100%", height: "auto", display: "block" }}
                  />
                  <div style={{ position: "absolute", inset: "20px", border: "2px dashed rgba(255,255,255,0.7)", borderRadius: "8px", pointerEvents: "none" }} />
                </div>
                <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
                  <button type="button" className="ws-button ws-button-primary" onClick={captureFromCamera}>
                    <Icon name="camera" size={17} /> Take snapshot
                  </button>
                  <button type="button" className="ws-button ws-button-secondary" onClick={stopCamera}>
                    <Icon name="close" size={16} /> Cancel
                  </button>
                </div>
              </div>
            ) : staged.length > 0 ? (
              <div className="ws-capture-preview">
                <PhotoTile
                  tone={staged[0]?.tone ?? 2}
                  mediaType={mediaType}
                  label="Captured preview"
                  size="lg"
                  src={staged[0]?.url}
                />
                <div>
                  <strong>{staged.length} {mediaType === "video" ? "video" : "photo"}{staged.length === 1 ? "" : "s"} ready</strong>
                  <p className="ws-small ws-muted">{staged.map((item) => item.name).join(", ")}</p>
                  <div className="ws-chip-row">
                    <span className="ws-chip">{partLabel(part)}</span>
                    <span className="ws-chip">{gps ? "GPS attached" : "No GPS yet"}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="ws-capture-empty">
                <span className="ws-capture-icon"><Icon name={mediaType === "video" ? "video" : "camera"} size={30} /></span>
                <strong>{mediaType === "video" ? "Record or upload a plant video" : "Take a photo of the affected part"}</strong>
                <p className="ws-small ws-muted">
                  Hold steady in daylight, about 30 cm from the plant. Avoid shadows and background clutter.
                </p>
                {cameraError ? (
                  <div style={{ background: "#fff2f0", border: "1px solid #ffccc7", borderRadius: "8px", padding: "8px 12px", marginTop: "8px", maxWidth: "420px" }}>
                    <p className="ws-small" style={{ color: "#cf1322", fontWeight: 600, margin: 0 }}>
                      Camera permission blocked by browser
                    </p>
                    <p className="ws-small" style={{ color: "#595959", margin: "4px 0 6px" }}>
                      Click the camera/lock icon in your browser address bar (left of localhost:3000) and change <strong>Camera</strong> to <strong>Allow</strong>, then reload or click below.
                    </p>
                    <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
                      <button type="button" className="ws-button ws-button-primary" style={{ padding: "4px 10px", fontSize: "0.8rem" }} onClick={startCamera}>
                        Retry camera
                      </button>
                      <button type="button" className="ws-button ws-button-secondary" style={{ padding: "4px 10px", fontSize: "0.8rem" }} onClick={() => fileRef.current?.click()}>
                        Choose image file
                      </button>
                    </div>
                  </div>
                ) : null}
              </div>
            )}

            {!cameraActive ? (
              <div className="ws-capture-buttons">
                <button
                  type="button"
                  className="ws-button ws-button-primary"
                  onClick={() => {
                    if (mediaType === "video") {
                      videoRef.current?.click();
                    } else {
                      startCamera();
                    }
                  }}
                >
                  <Icon name="camera" size={17} /> {mediaType === "video" ? "Record video" : "Open camera"}
                </button>
                <button type="button" className="ws-button ws-button-secondary" onClick={() => fileRef.current?.click()}>
                  <Icon name="upload" size={16} /> {mediaType === "video" ? "Upload video" : "Upload from gallery"}
                </button>
                <button type="button" className="ws-button ws-button-ghost" onClick={() => fileRef.current?.click()}>
                  <Icon name="plus" size={16} /> Multiple images
                </button>
                <input
                  ref={fileRef}
                  type="file"
                  accept={mediaType === "video" ? "video/*" : "image/*"}
                  capture={mediaType === "image" ? "environment" : undefined}
                  multiple={mediaType === "image"}
                  className="ws-hidden-input"
                  onChange={(event) => addFiles(event.target.files)}
                />
                <input
                  ref={videoRef}
                  type="file"
                  accept="video/*"
                  capture="environment"
                  className="ws-hidden-input"
                  onChange={(event) => {
                    setMediaType("video");
                    addFiles(event.target.files);
                  }}
                />
              </div>
            ) : null}
          </div>

          <div className="ws-form">
            <div className="ws-form-grid">
              <Field label="Farm">
                <select
                  value={farmId}
                  onChange={(event) => {
                    setFarmId(event.target.value);
                    setGps(null);
                  }}
                >
                  {state.farms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </Field>
              <Field label="Attach to crop group or plant">
                <select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
                  {farmGroups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
                  {subjectPlants.map((plant) => <option key={plant.id} value={plant.id}>{plant.code} · {plant.label}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Plant part" hint="Choose the part in the centre of the frame.">
              <div className="ws-part-picker">
                {PARTS.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={part === option ? "ws-part ws-part-active" : "ws-part"}
                    onClick={() => setPart(option)}
                  >
                    {partLabel(option)}
                  </button>
                ))}
              </div>
            </Field>
            <Field label="Observation notes">
              <textarea
                rows={3}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="What do you see? Any recent rain, spraying or new growth?"
              />
            </Field>
            <div className="ws-gps-box">
              <div>
                <strong>GPS coordinates</strong>
                <p className="ws-small ws-muted">
                  {gps ? `${gps.lat}, ${gps.lng}` : "Not captured. Farm coordinates are used as a fallback."}
                </p>
                {gpsStatus ? <p className="ws-small">{gpsStatus}</p> : null}
              </div>
              <button type="button" className="ws-button ws-button-secondary" onClick={captureLocation}>
                <Icon name="location" size={16} /> Add GPS
              </button>
            </div>
            <div className="ws-form-actions">
              <span className="ws-small ws-muted">
                {online ? "Will sync automatically after saving." : "Saved offline; sync when connected."}
              </span>
              <button
                type="button"
                className="ws-button ws-button-primary ws-button-large"
                disabled={staged.length === 0}
                onClick={save}
              >
                <Icon name="shield" size={17} /> Save observation
              </button>
            </div>
            {savedId ? (
              <div className="ws-success-note">
                <Icon name="check" size={17} />
                <div>
                  <strong>Observation saved{online ? " and queued for sync" : " offline"}</strong>
                  <span className="ws-small">You can analyse it now or wait for expert review.</span>
                </div>
                <button
                  type="button"
                  className="ws-button ws-button-primary"
                  disabled={analysingId === savedId}
                  onClick={() => analyse(savedId)}
                >
                  <Icon name="analysis" size={16} /> {analysingId === savedId ? "Analysing…" : "Analyse"}
                </button>
              </div>
            ) : null}
          </div>
        </section>

        <aside className="ws-stack">
          <section className="ws-panel">
            <div className="ws-panel-head">
              <div><p className="ws-eyebrow">Offline queue</p><h2>{queued} waiting</h2></div>
              <button
                type="button"
                className="ws-button ws-button-secondary"
                disabled={queued === 0 || syncing}
                onClick={() => {
                  setSyncing(true);
                  window.setTimeout(() => {
                    syncCaptures();
                    setSyncing(false);
                  }, 800);
                }}
              >
                <Icon name="sync" size={15} /> {syncing ? "Syncing…" : "Sync now"}
              </button>
            </div>
            <ul className="ws-queue-list">
              {state.captures.slice(0, 5).map((capture) => (
                <li key={capture.id}>
                  <PhotoTile tone={capture.imageTone} mediaType={capture.mediaType} label={capture.subjectLabel} size="sm" />
                  <div>
                    <strong>{capture.subjectLabel}</strong>
                    <span className="ws-small ws-muted">{partLabel(capture.plantPart)} · {formatDateTime(capture.capturedAt)}</span>
                  </div>
                  <div className="ws-queue-actions">
                    {syncBadge(capture.syncState)}
                    {capture.analysisId ? (
                      <Link href={`/analysis?focus=${capture.analysisId}`} className="ws-link">Result</Link>
                    ) : (
                      <button
                        type="button"
                        className="ws-link-button"
                        disabled={analysingId === capture.id}
                        onClick={() => analyse(capture.id)}
                      >
                        {analysingId === capture.id ? "Analysing…" : "Analyse"}
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            {state.captures.length === 0 ? <p className="ws-empty-inline">No captures yet.</p> : null}
          </section>

          <section className="ws-panel">
            <div className="ws-panel-head"><h2>Capture checklist</h2><Badge tone="info">Guidance</Badge></div>
            <ul className="ws-checklist">
              <li><Icon name="sun" size={15} /> Day­light, no harsh shadow</li>
              <li><Icon name="camera" size={15} /> Fill the frame with the affected part</li>
              <li><Icon name="leaf" size={15} /> Add a whole-plant photo for context</li>
              <li><Icon name="location" size={15} /> Save GPS only with permission</li>
              <li><Icon name="shield" size={15} /> Keep blurred photos — do not delete evidence</li>
            </ul>
            <div className="ws-notice">
              Image quality is checked before an assessment. A blurry photo returns “no assessment yet”
              with retake guidance, not a guessed diagnosis.
            </div>
          </section>

          <section className="ws-panel">
            <div className="ws-panel-head"><h2>Recent activity</h2><Link href="/analysis" className="ws-link">All</Link></div>
            <ul className="ws-activity-list">
              {state.analyses.slice(0, 4).map((analysis) => (
                <li key={analysis.id}>
                  <span className="ws-activity-dot ws-tone-warn" />
                  <div>
                    <strong>{analysis.subjectLabel}</strong>
                    <span className="ws-small ws-muted">{analysis.pest ?? analysis.disease}</span>
                  </div>
                  <Link href={`/analysis?focus=${analysis.id}`} className="ws-link">Open</Link>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
