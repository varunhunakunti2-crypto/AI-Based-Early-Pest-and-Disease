# Progress tracker

**Single place to see where the project is, what is decided, and what comes next.**
Update this file in the same change as any scope, schema, API or decision change.

**Last updated:** 2026-11-07
**Current phase:** Phase 0 / Phase 1 — Discovery & Data Platform (architecture decided in ADR-009/010/011; Phase 1 data layer, weather/boundary/historical ingestion, and zero-imputation forecast gates implemented in `database/` with 38 unit tests passing; backend identity, persisted chat, content-safety gate and optional vision adapter present under recorded Gate-1 exception; 392 backend tests passing). Phase 3 has a **reproducible synthetic-only ML scaffold** (`ml/`, 29 tests) proving manifest → grouped split → train → evaluate → promotion plumbing; it ships no trained image model, real dataset or operating point, so **Gate 3 remains open**. Gate 4 has a deterministic demo-rules harness and synthetic input-sensitivity/reproducibility tests, but no approved operating point, real weather provider or field evaluation, so **Gate 4 remains open**.

---

## 1. Status legend

| Symbol | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done and verified |
| `[!]` | Blocked |
| `[-]` | Deferred / out of v1 |
| `[?]` | Decision required |

---

## 2. Phase plan and gates

Each phase must produce something a real user would use on its own. A phase does not
start until its gate is met. The detailed work, deliverables, owners and boundaries for
every phase are in `./phase-plan.md`; this section is the live status view.

### Phase 0 — Discovery `[~]`

- [x] Blueprint summarised and distilled into operating docs.
- [x] Full 55-chapter blueprint and Appendices A–H mapped to repository files (`../README.md`).
- [x] Realism audit applied; v1 scope narrowed.
- [x] Architecture baseline and feature specs drafted.
- [x] **Architecture** reconciled to PostgreSQL/PostGIS + Cloudinary + Next.js/Flutter
      (`adr/0009-data-platform.md`, `adr/0010-v1-roles.md`, `adr/0011-open-crop-catalogue.md`).
- [x] **D1** Crop + targets policy decided: open catalogue + validated-target allowlist
      (ADR-011). The first concrete allowlist is split out as **D1a** (recorded in `phase-0/d1a-allowlist-decision.md`).
- [x] **D2** Nowcast (last 10 days) decided; 7-day outlook deferred.
- [x] **D3** Verifier role decided (extension-first, `can_confirm` permission; capacity
      and SLA documented in `phase-0/d3b-verifier-capacity-sla.md`; partner sign-off pending as a pilot prerequisite).
- [x] **D4** Owning/paying institution policy decided (`phase-0/d4-owning-institution.md`; partner counterparty pending as a pilot prerequisite).
- [x] **D5** Primary outcome metric pre-registered (`phase-0/d5-primary-metric.md`).
- [x] **D6** Advisory policy decided: non-chemical only (R5 unchanged).
- [~] **D7–D12** Scientific-integrity interim rules recorded in `phase-0-decisions.md` §7.
- [x] **D13** v1 languages decided: English + Kannada.
- [x] **D14** Output semantics decided: confidence band + abstention; severity is an
      expert-review field.
- [x] **D15** Notification channels decided: in-app mandatory; email for staff; SMS optional;
      WhatsApp/push/IVR deferred.
- [x] Crop calendar and epidemic window documented for the pilot area (`phase-0/crop-calendar.md`, `phase-0/target-reference-sheet.md`, `phase-0/pilot-sites.csv`).

**Gate 0:** D1–D6, D7, D8 and D13 are answered and recorded in §4, each with a recorded
date and owner; D14 and D15 are also decided. D9–D12 are deliberate pre-Gate-2/pre-Gate-4
decisions and are not part of the checklist's Gate 0 scope. Gate 0 closes when the
checklist's Gate 0 items are met (architecture, docs consistency, clean clone) — they are,
so **Gate 0 is closed**. Partner signatures (D3 SLA, D4 counterparty) and D1a/D1b remain
pilot prerequisites. Working record: the decision log below, `phase-0-decisions.md` and `phase-0/`.

### Phase 1 — Data foundation `[~]`

- [~] Partner MoUs and data-permission records (registers created in `database/governance/`; signatures pending).
- [~] Image collection protocol and consent wording (drafted in `database/collection/` and `database/governance/03-consent-wording-and-capture.md`).
- [~] Labelling handbook (taxonomy, uncertainty classes, severity, provenance drafted in `database/labelling/`).
- [~] Plant-clinic archive access assessed (protocols drafted in `database/archive/`).
- [x] Weather provider client / ingestion data model with source timestamp, units, physical bounds, freshness check, spatial matching methods, and leaf-wetness proxy derivation (`database/ingestion/weather_ingest.py`).
- [x] Versioned boundary geometry loader (EPSG:4326 GeoJSON MultiPolygon validation, coordinate range check, WKT conversion, boundary version propagation in `database/ingestion/boundary_loader.py`).
- [x] Historical occurrence ingestion with verification tier, `report_date >= event_date` check, source link provenance, deterministic SHA-256 dedupe key, and dedupe history logging (`database/ingestion/historical_ingest.py`, table `historical_occurrences`).
- [x] Zero silent imputation forecast gate: explicit `insufficient_data` refusal with `probability = NULL` for missing/stale weather (>24h SLA) or boundary mismatch (`database/ingestion/forecast_gate.py`, DB function `check_weather_sufficiency` in `01-schema.sql`).
- [x] Database schema implemented and migrated (`05-data-layer.md` — 14 slices, 40 tables, append-only triggers on 13 tables, PostGIS spatial boundary, Alembic migrations, demo seed in `database/`; 38 unit tests passing across `test_schema_and_seed.py`, `test_storage_rules.py`, `test_weather_and_boundaries.py`).
- [~] Data dictionary v1; quality checks for each ingestion batch (v1 drafted in `database/data-dictionary/`).
- [x] Quarantine path for suspicious records (`database/governance/06-quarantine-policy.md`).

**Gate 1:** documented permissions for every dataset; reproducible ingestion; label
handbook approved by a pathologist.

### Phase 2 — Platform MVP `[~]`

- [x] **§5.1 Engineering foundation** — backend/web/mobile scaffolds, CI,
      Alembic baseline, local compose, dev/staging env templates, structured
      logging, OpenAPI/error contract and `../TEST-MATRIX.md`. Mobile
      `flutter analyze` and `flutter test` pass locally (Flutter 3.47.9); a debug APK
      built and an emulator capture/offline smoke passed (real-device camera and iOS
      unverified). Gate 1 is **not met**; foundation-only work proceeds
      under an explicit user instruction recorded 2026-11-06 and adds no schema
      or feature behaviour.
- [~] Auth, roles, consent (`03-auth-and-roles.md`): Backend identity service, phone OTP,
      staff MFA, JWT tokens, RBAC, scoped permissions (`can_confirm`, `can_approve_advisory`),
      consent versioning, privacy requests/self-export/soft delete, audited admin views/exports in `backend/app/api/v1/auth.py`, `me.py`, `admin.py`.
- [~] Mobile context + capture + quality feedback + offline queue (`02-...`):
      camera/gallery capture with preview, 10 MB/JPEG-PNG-WebP checks, upload-first
      contract, persisted outbox (`ps03.chat.outbox.v1`), `queued`/`failed` bubbles with
      Retry/Delete, and flush on manual action, a 15 s page timer and app resume.
      `flutter analyze` clean; `flutter test` 14 passed. Crop context, quality-feedback
      copy beyond the server card, platform runners, APK and device/airplane-mode runs
      remain open.
- [~] Observation API with idempotency and signed uploads: `POST /v1/observations`,
      `POST /v1/observations/{id}/images`, `POST /v1/observations/{id}/images/{id}/confirm` in `backend/app/api/v1/observations.py`.
- [~] Web frontend shell + mobile app shell consuming the same `/v1` API (`frontend/` and `mobile/`).
- [~] Conversational capture: `conversations` module + chat on web and mobile
      (`08-conversational-capture.md`). **Backend + web + mobile capture slice implemented**
      (Alembic `0002_chat_persistence`): conversation list/thread, structured assessment
      card, image composer (web) and camera/gallery capture (mobile), upload-first
      messages, idempotent turns, review requests, and a durable mobile outbox with
      `queued`/`failed` states. Mobile is unit-verified only.
- [x] Chat reply contract (`assessment`, `abstained`, `unsupported_crop`, `queued`, `failed`,
      `review_requested`) and chemical-content validator (`backend/app/modules/assessments/explanation.py`, `backend/app/modules/advisories/validator.py`).
- [~] Expert review queue and decision flow (`04-expert-review.md`): Triage queue, claim,
      decision, notes in `backend/app/api/v1/review.py` and `modules/review/service.py`.
- [~] Audit trail for reviews, roles, exports and chat events (`backend/app/modules/audit/service.py`, `database/schema/01-schema.sql`).
- [~] Admin config for crops, targets, geographies (`backend/app/api/v1/forecast.py`, `backend/app/db/seed.py`).
- [ ] End-to-end test: report → upload → review, including airplane mode.
- [~] End-to-end test: chat image → structured reply on web and mobile, retry idempotent.
      Web + API path verified (14 backend tests and a live upload → demo assessment →
      review smoke). Mobile upload/send/retry/offline-queue semantics are unit-verified
      (`mobile/test/*`, 14 tests); a device or airplane-mode run and browser automation
      remain open.

**Gate 2:** a report can be captured offline, synced once, reviewed, and audited, on a
low-end device; chat image → assessment works on web and mobile. No predictive model
required; any demo reply is labelled.

### Phase 3 — Image AI `[~]`

- [~] Reproducible ML **scaffold** only (`ml/`): dataset-manifest contract (licence,
  provenance, checksum, permissions), synthetic label map, grouped/stratified splits
  with leakage checks, deterministic baseline, evaluation through the backend Gate 3
  harness, fail-closed promotion and model card. Verified with 23 tests on a
  clearly-labelled synthetic fixture; no real dataset, image extractor, trained image
  model, calibration artefact or operating point exists, and synthetic output can
  never be approved for serving. **Gate 3 stays open.**
- [~] **Pretrained third-party detectors wired into the app, demo-only.** Two
  Hugging Face YOLO wrappers (`agroai_pest_detection` YOLO11s/IP102, 102 classes;
  `plant_diseasedetection` YOLOv11x, 116 classes) run in the isolated FastAPI service
  `ml/serve` (`/health`, `/v1/models`, `/v1/detect`). The backend calls it through
  `PretrainedAssessmentEngine` (`APP_CHAT_ENGINE=pretrained` / `yolo*`) and the scan
  screen reaches it via `POST /v1/uploads` → `POST /v1/detections`. Every response sets
  `is_demo: true`, carries a demo warning, and tags raw model labels
  `unverified_model_label`; candidate names are shown as "unverified model label". No
  mapping to the D1a allowlist and no calibration exist, and `ultralytics` is
  **AGPL-3.0**, so the runtime is kept out of the backend process and CI. Pest/plant
  weights are cached from Hugging Face, never committed. **Not production-ready:**
  AGPL deployment terms, D1a taxonomy mapping and calibration/operating point remain open.
- [ ] Quality gate model (blur, exposure, resolution, no-plant).
- [ ] Field-image baseline; public data used for pretraining only.
- [ ] Group-held-out field test set frozen before model selection.
- [ ] Calibration on a dedicated split (temperature scaling) and the D8 abstention decision function (`τ_c`, margin, entropy, OOD) chosen on validation.
- [ ] Evaluation report: macro F1, per-class recall, ECE/Brier, abstention rate, OOD on held-out classes, subgroups; D8 floors pre-registered before the test set is opened.
- [ ] ONNX export, registry entry, versioned serving.
- [ ] Result card with top-3, confidence band, quality flags, escalation.

**Gate 3:** the D8 floors are **met**, not merely reported, at the shipped abstention
threshold on the frozen field-only test set, with sample counts and confidence intervals;
abstention behaviour is reported on hard negatives. A performance number that does not
clear the pre-registered floor fails the gate.

### Phase 4 — Forecasting `[~]`

- [x] Event definition and spatial unit documented (`06-forecast-and-risk-map.md`; D7 accepted 2026-11-06).
- [~] Versioned, expert-approved rules baseline (e.g. blight risk index) — *deterministic demo rules in `backend/app/modules/forecast/rules.py`; no expert-approved index or operating point*.
- [x] Weather ingestion with source timestamps and freshness checks (`database/ingestion/weather_ingest.py`; the backend snapshot path reads `WeatherSnapshot`).
- [x] Feature snapshot persisted per forecast run (`FeatureSnapshot` stores weather, coverage, rule score and rule contributions).
- [x] No-score behaviour for stale/low-coverage inputs (`insufficient_data`, `probability = NULL`, typed `reason_code`; tested).
- [~] Risk bands with operational meanings and approved actions — *bands implemented; thresholds are unapproved demo configuration and no operational action mapping is approved*.
- [~] Separate map layers + coverage panel — *five separate `/v1/map/layers/*` endpoints and the `/outlook` reader exist; boundary geometry is not served and no merged risk layer is built*.
- [ ] Temporal holdout evaluation; calibration report — *no field data, sentinel panel, D8 forecast floors or approved operating point*.
- [x] Alert trigger, dedupe, cooldown, delivery status (`backend/app/modules/alerts/`; Gate 5 delivery channels remain open).

**Gate 4:** the D7 event definition, label eligibility rule, sentinel-panel membership and
visit schedule are fixed and frozen before the test season; the D8 forecast floors are
pre-registered and **met** on sentinel-panel negatives; the D9 coverage, freshness and
suppression values are recorded and approved; the forecast is reproducible from a stored
snapshot; the no-score path is verified against those values; the map never merges reports and
predictions.

**Status (2026-11-06):** D7 is recorded and the backend can reproduce a scored band from a
stored feature snapshot on synthetic fixtures (`backend/tests/test_forecast_rules.py`,
`backend/tests/test_forecast_service.py`). **Still open:** a real weather provider and
scheduled ingestion runner, D8 forecast floors, approved D9 values, D1b pilot zone/boundary
version, and an expert-approved operating point. No field performance, calibration or
outbreak claim is made. Gate 4 is **not met**.

### Phase 5 — Pilot `[ ]`

- [ ] Site selection and control/matched design documented.
- [ ] Silent phase running (predictions not shown).
- [ ] Comparison with field observations; false alerts and missed events logged.
- [ ] Limited alert phase with approved templates and escalation owners.
- [ ] Usability and comprehension rounds with farmers and extension workers.
- [ ] Lead-time measurement against baseline.
- [ ] Weekly review cadence and issue log.

**Gate 5:** silent-phase evidence reviewed against the D5 pre-registered metric; alert
response workflow staffed; every logged safety issue either closed or explicitly accepted in
writing by the D6 owner ("unresolved" means neither, and blocks). Pilot timed to the
epidemic season.

### Phase 6 — Rollout `[ ]`

- [ ] Operational runbooks, on-call ownership, incident response.
- [ ] Backups and restore tested; RTO documented.
- [ ] Monitoring dashboards for data, model, product metrics.
- [ ] Training for extension staff and admins.
- [ ] Controlled expansion criteria written and approved.
- [ ] Launch-readiness checklist (blueprint Appendix H) signed off.

**Gate 6:** all launch gates met. If not, feature stays silent/non-operational.

---

## 3. Workstream status

| Workstream | Status | Next action |
|---|---|---|
| Documentation | `[x]` | Keep in sync with decisions |
| Blueprint coverage | `[x]` | Chapter map maintained in `../README.md` |
| Decisions | `[~]` | D1–D6 resolved; close D9–D12 before Gates 2/4 |
| Data acquisition | `[ ]` | Identify archive partners; draft MoU |
| Labelling | `[ ]` | Draft handbook after D1a |
| Data platform | `[x]` | Reference schema (40 tables), Alembic migrations, storage rules, backup design, demo seed, weather/boundary/historical ingestion, and zero-imputation forecast gate verified in `database/` (38 unit tests pass); `backend/` remains schema authority |
| Backend | `[~]` | Health, problem-details errors, JSON logging, Alembic baseline + `0002_chat_persistence`, compose; persisted demo chat (uploads, demo quality gate, demo/OpenAI-compatible engine, content-safety gate, review requests); §5.2 identity slice in memory; 375 unit tests passing |
| Mobile | `[~]` | Flutter client with photo capture, upload-first chat, assessment card and a persisted offline outbox; `flutter analyze` clean and `flutter test` 14 passed. Platform runners committed, debug APK built, emulator capture/offline smoke passed; real-device camera and iOS unverified. Single mobile stack per ADR-013 |
| Web | `[~]` | Next.js app in `frontend/` with chat, outlook, review, weather and workspace pages (`map`, `scan`, `analysis`, `assistant`, `farms`, `settings`); typecheck, lint and build pass |
| Chat | `[~]` | Spec 08 + persisted demo chat backend and web surface (upload → quality gate → demo/OpenAI-compatible engine → content-safety gate → review) and the mobile capture + offline-queue client (unit-verified). Real assessment waits on Phase 3, D8 and a live key |
| Image ML | `[ ]` | Baseline on public data for pipeline only |
| Forecast | `[~]` | Deterministic demo rules (`backend/app/modules/forecast/rules.py`) wired through the persisted forecast service; synthetic input-sensitivity and snapshot-reproducibility tests; rules, domain models, weather ingestion, boundary loader, historical occurrences and forecast gates in `database/ingestion/`; no approved operating point, real provider or scheduled runner |
| MLOps | `[~]` | `model_registry` schema, triggers, checksum verification, and demo entries implemented in `database/` |
| Security/privacy | `[~]` | Object storage rules (TTL ≤ 10m) & RBAC matrix implemented; DPIA drafted |
| Pilot ops | `[ ]` | Site list and verification capacity after D3 |

---

## 4. Decisions (blocking)

Record: decision, options, consequence, owner, date. Do not delete history.

Every decision carries **one named accountable owner** and a **`Needs by` date tied to a
phase gate**. A decision with neither cannot be counted as answered, and Gate 0 cannot
close while any remain open. Where a decision needs a number that the repository is not
entitled to invent (R6), the decision must still define *who sets the number, from what
measurement, before which gate* — the rule for setting the value is itself the decision.

### D1 — Crop + targets + zone `[x]`

**Decision (2026-11-06): open, crop-agnostic horticulture catalogue with a validated
crop × target allowlist.** Any horticulture crop may be submitted; a photo assessment or
area outlook is returned only for a `crop × target` pair on the release allowlist.
Everything else returns an explicit abstention (`unsupported_crop`, `unsupported_target`)
rather than mapping to the nearest supported class (R2). This carries the user's direction
to cover horticulture crops without making validation claims the project cannot support.

**Still open as D1a:** the first concrete allowlist (crop × target entries plus
healthy/abiotic/unknown classes) must be fixed before Gate 3.

**Still open as D1b:** the single pilot agro-climatic zone (state/district/block) and its
boundary version must be named before Gate 4.

**Scope note:** "pesticides" is read as pest and disease *targets*, not pesticide product
advice. D6 and R5 keep all chemical prescriptions out of the product.

**Owner:** Product lead + agronomist. **Recorded:** 2026-11-06.

| Option considered | Consequence |
|---|---|
| Open catalogue + validated allowlist (chosen) | Crop-agnostic schema; claims limited to validated entries; abstains elsewhere |
| Potato late blight only | Validated weather model exists (BLITECAST/SimCast); credible day one, but narrow |
| Tomato blight complex | More targets and public data; weaker forecast baseline for non-blight targets |
| Rice blast / BLB / brown spot | Large farmer base, harder image data, blast weather models exist |

### D2 — Nowcast or 7-day outlook `[x]`

**Accepted 2026-11-06: nowcast over the last 10 days.** A 7-day outlook is deferred until
at least one season of verified outcomes exists. **Owner:** Agronomist + ML lead.
**Recorded:** 2026-11-06.

### D3 — Verifier, capacity, SLA `[x]`

**Accepted 2026-11-06: extension-worker-first verification with pathologist escalation.**
A published SLA and workload cap are required; their numeric values and the partner
commitment are set before the pilot (Gate 5), not invented here. Extension workers triage
and escalate; only pathologists verify escalated cases. **Owner:** Programme lead + partner.
**Recorded:** 2026-11-06.

### D4 — Owning/paying institution `[x]`

**Accepted 2026-11-06: grant/NGO-funded pilot, with operations handed to a cooperative
or crop insurer.** Input-company funding of the advisory layer stays rejected on trust
grounds. The named institution and written data-ownership/exit agreement are still required
before the pilot; the ownership model itself is settled. **Owner:** Product lead.
**Recorded:** 2026-11-06.

### D5 — Primary outcome metric `[x]`

**Accepted 2026-11-06: median lead time from the first farmer report to verified expert
confirmation**, compared with the existing advisory baseline and pre-registered before the
pilot. Secondary metrics: prioritisation accuracy and false-alert burden.
**Owner:** Product lead + evaluator. **Recorded:** 2026-11-06.

### D6 — Legal position on advisory content `[x]`

**Accepted 2026-11-06: non-chemical guidance only, with escalation to a human.** Legal
review is required before the pilot. This confirms R5: no pesticide, herbicide, fungicide
or dosage content, and no chemical-use instructions in any advisory or chat response.
**Owner:** Programme lead + legal. **Recorded:** 2026-11-06; legal sign-off gates Gate 5.

### D7 — Forecast event, negative class and label eligibility `[x]`

**Accepted 2026-11-06.** Sentinel-panel absence sampling; `probable` is eligible with an
evidence tier.

**Negative class.** A fixed sentinel panel of monitored field points is defined per supported
area before the season and visited on a pre-registered schedule by extension workers or
partners. At each visit the visitor records observed presence or absence of the supported
target using the same diagnostic criteria as case verification. A visit yields a **verified
negative** only if all of these hold: the visit falls inside the label window; the point is on
the supported crop in the supported area; the visit was scheduled in advance, not triggered
by a report; and the D9 coverage gate passed for that area and window. `no visit`, `no
report`, `unresolved` and `needs_visit` are never negatives.

**Event.** First evidence-eligible case of the target in the spatial unit within the event
window. The event date is the earliest observed/onset date recorded. The exact outcome (first
case, incidence threshold or escalation) still follows D1/D5, but the eligibility rule is
fixed: a case enters features only if `verified_at <= cutoff` and its event date is
`<= cutoff`. `confirmed` and `probable` are eligible; `probable` carries its evidence tier as
a lower-confidence flag. `unverified`, `needs_visit`, `duplicate`, `unresolved` and `rejected`
are never eligible.

**Training versus evaluation.** Features may be trained on presence-only data, but that is a
positive-unlabelled design: PR-AUC, precision/recall, Brier and ECE are reported **only** on
the sentinel panel, which supplies real negatives. If the panel is below the D8 minimum
sample for a stratum, the metric is reported as underpowered and is not used for a gate. No
metric is ever computed by treating an unvisited area as negative.

**Blinding.** The primary review records the label before seeing model candidates or the
forecast at report time; both are revealed only after the decision is stored. A double-read
subset is labelled independently and inter-rater agreement is reported; its size and threshold
are set under D8.

**Label maturity.** A season is not frozen as test data until its label window has closed and
the review backlog for that window is cleared. Right-censored recent cases are excluded from
the frozen set, never labelled negative.

**Consequence — capacity:** the panel and its visit schedule are a D3 commitment. Without
them the forecast track has no negative class and must fall back to presence-only, in which
case discrimination and calibration are not reported at all.

**Owner:** ML lead + agronomist + pathologist + field ops. **Recorded:** 2026-11-06;
frozen before Gate 4.
**Blocks:** `06-forecast-and-risk-map.md` §2/§9/§11, `04-expert-review.md` §3/§6,
`05-data-layer.md` §4.4, `phase-plan.md` §7.1.

### D8 — Abstention rule and numeric acceptance floors `[x]`

**Accepted 2026-11-06: the decision function, the operating posture, the calibration and OOD
requirements, the override policy and the floor-setting process. The floor *values* are not
invented here — they are measured and pre-registered before the frozen test set is opened, as
described below.**

#### Decision function — image assessment

Applied only after the server quality gate passes:

1. Calibrated class probabilities (or the raw decision score when calibration is not
   approved for display).
2. Top-1/top-2 margin and normalised entropy.
3. An explicit out-of-distribution score computed on embeddings or energy, with its threshold
   fitted on held-out classes.

Abstain with a machine reason code if **any** of these holds: the top candidate's calibrated
probability is below its class threshold `τ_c`; the margin is below `m`; entropy is above
`h`; the OOD score is above `ood_max`; the crop is unsupported; the quality gate fails (a
separate upstream state). Return up to three candidates only when none hold.

`τ_c`, `m`, `h` and `ood_max` are stored per prediction with the model version. Per-class
`τ_c` is required; a single global threshold is not sufficient for classes of unequal
prevalence.

#### Operating posture

**Safety-first.** Per-class recall floors take precedence over coverage. Among operating
points that satisfy the recall and OOD constraints, choose the one that maximises the share
of images assessed. Never trade a recall floor for coverage. A model that abstains on
everything fails Gate 3 — the coverage floor exists precisely to prevent that.

#### Calibration

Probabilities used by the decision function are calibrated with **temperature scaling** on a
dedicated calibration split, separate from the validation split used for model selection and
from the frozen test set. Isotonic calibration is permitted only where the sample size
supports it. ECE is a diagnostic, not a fitting method. Report reliability diagram, Brier
score and ECE on the frozen test set.

If the data cannot support a separate calibration split, calibration is **not approved**:
the UI shows qualitative bands only, no percentage, and no probability-derived claim. The
model may still abstain on its raw score.

#### Out-of-distribution

A supervised `unknown` class is not open-set detection: it only recognises unknowns present
in training. D8 therefore requires a separate OOD score evaluated on **held-out classes** —
unknown-vs-known AUROC and false-accept rate at the shipped threshold. Both are gate
metrics, not diagnostics.

#### Numeric floors — measured, never invented

Two floor sets, each pre-registered in this section, timestamped and committed **before** the
frozen test set is opened:

**Image floors**
- Minimum per-class recall at the shipped threshold.
- Maximum overall and per-class abstention rate.
- Minimum share of quality-passing images assessed.
- Maximum ECE (only if calibration is approved).
- Maximum OOD false-accept rate on held-out classes.
- Minimum top-3 containment for supported classes.

**Forecast floors**
- Minimum share of area-days carrying a scored band (not `insufficient_data`).
- Maximum `insufficient_data` rate.
- Minimum lift over the climatology / naive baseline on the D7 evaluation.
- Maximum Brier and calibration error on sentinel-panel negatives.
- Results broken down by coverage stratum.

Procedure:
1. Freeze dataset, split and model versions.
2. On validation/calibration data only, measure risk–coverage curves per class and subgroup
   and the baseline lift.
3. The evaluator and product lead write the floors and the chosen operating point into this
   section, with a timestamp and commit, under D7's anti-leakage rules.
4. Open the frozen test set once and report at the shipped threshold.
5. Any floor that is not met means the model is **not approved** and Gate 3 (or Gate 4 for
   forecast) fails. Thresholds may not be retuned after the test set is opened; a retrain
   requires a new pre-registration.

Floors set after seeing test results are void.

#### Override policy

- There is **no user-facing control that changes a model output**. An abstained prediction
  stays abstained in the record.
- A reviewer may still verify a report manually through the normal review flow. That decision
  is separate, audited, and never rewrites the prediction row or counts as an assessed image
  in coverage.
- `confirmed` remains pathologist-only. Extension workers may escalate; agronomists and
  admins cannot verify.
- Every manual decision records actor, role, timestamp, reason and the model state it
  replaced, and appears in the audit log.
- Manual labels are not fed back as ground truth for model evaluation without D7's labelling
  protocol and evidence tier; doing so would import confirmation bias into the test set.

**Owner:** ML lead + product lead + evaluator. **Recorded:** 2026-11-06.
**Floor values:** not yet recorded — Gate 3 and Gate 4 cannot close until the relevant set is
pre-registered and met.
**Blocks:** Gate 3, Gate 4, `ml-models.md` §6, `01-design-system.md` confidence bands,
`02-reporting-and-capture.md` FR-02-25, `05-data-layer.md` `image_predictions`.

### D9 — Coverage, freshness and suppression values `[?]`

Coverage formula with numerator, denominator and window (active reporters per area per
window, report completeness, weather freshness, representativeness — **not** reporter count
alone, which is gameable); the minimum value that permits a scored band and an alert; the
weather freshness threshold; the aggregation unit and coordinate precision; and the small-
count suppression threshold applied consistently to map, API and exports.
**Owner:** Data engineer + product lead + legal. **Needs by:** Gate 4.

### D10 — Retention, deletion and derived-data policy `[?]`

Per-entity deletion matrix including `image_predictions`, `feature_snapshots`, the frozen
test set, backups and trained weights; whether model weights are derived personal data;
tombstone erasure applied on restore; on-device TTL, encryption at rest and wipe-on-logout
for unsent images; and the named data controller (see also `03-auth-and-roles.md` §13 Q3).
**Owner:** Programme lead + legal + engineering lead. **Needs by:** Gate 2 (capture starts
there, so the policy must precede it).

### D11 — Identity model for on-behalf capture and offline sessions `[?]`

Separate `reporter_id` (actor) from `subject_user_id` (farmer) with on-behalf authorisation;
object-level access rules; idempotency scope; and the offline session policy — maximum
offline period, whether capture continues after the 15-minute access token expires, and how
role revocation and logout-all reach a device that is offline for ≥ 7 days (required by
`02-reporting-and-capture.md` §8).
**Owner:** Backend lead + product lead. **Needs by:** Gate 2.

### D12 — Client-side quality pre-check mechanism `[?]`

FR-02-07 requires an on-device pre-check, while `architecture-context.md` §2 rejects
on-device inference and `02-reporting-and-capture.md` §11 lists it as out of scope.
Decide: deterministic heuristics (blur/exposure/resolution) with plant-presence as
guidance only, or a small on-device model (which needs an ADR reversing the architecture
stance). Record framework, size, thresholds, latency and battery budget, and state what an
offline user sees between capture and sync.
**Owner:** Mobile lead + ML lead. **Needs by:** Gate 2.
**Interim rule until decided:** the client pre-check is advisory only. It must never block
saving or submitting a report (R8), and the server quality gate remains authoritative for
assessment (FR-02-12).

### D13 — `agronomist` as a fifth role `[x]`

**Accepted 2026-11-06.** `agronomist` is a fifth RBAC role, not an attribute on
`pathologist` and not an external approver who never logs in.

**Why:** advisory approval was impossible to perform as specified — the role matrix had no
agronomist column, yet `07-advisory-and-alerts.md` required a named agronomist as author and
a second qualified approver, and `06-forecast-and-risk-map.md` required agronomist threshold
approval. `update.md:38` also makes expert capacity the binding constraint, so a design that
needed two pathologists (one to author, one to approve) was unstaffable.

**What `agronomist` can do:** author and approve advisory content; approve risk bands and
threshold changes as second approver; read area queue, case evidence and map layers
read-only.

**What it cannot do:** set verification status, correct labels, create or upload
observations, manage users, export, or read the audit log. Author ≠ approver is enforced per
record (`author_id != approver_id`), so one account holding both roles still cannot
self-approve.

**Consequence — capacity:** the programme must staff at least **two** qualified accounts
(any mix of `agronomist` and `pathologist`) before any advisory can be published. With one,
publication is blocked. This is tracked under D3 and R-03, not resolved by relaxing the rule.

**Owner:** Product lead + programme lead. **Recorded:** 2026-11-06.
**Implemented in:** `03-auth-and-roles.md` §1–§4, §10; `PRD.md` §4.2; `04-expert-review.md`
§2; `05-data-layer.md` §4.1; `07-advisory-and-alerts.md` §2–§3; `phase-plan.md` §5.2.

---

## 5. ADR log

| ID | Decision | Status | Date |
|---|---|---|---|
| ADR-001 | Modular monolith over microservices | Accepted | 2026-11-06 |
| ADR-002 | FastAPI + SQLAlchemy/Alembic as single schema authority (no Prisma) | Accepted | 2026-11-06 |
| ADR-003 | Web portals are API-only clients | Accepted | 2026-11-06 |
| ADR-004 | Rules-based forecast before ML | Accepted | 2026-11-06 |
| ADR-005 | ONNX Runtime CPU inference for pilot | Proposed | 2026-11-06 |
| ADR-006 | Flutter capture + SMS/WhatsApp delivery | Proposed | 2026-11-06 |
| ADR-007 | Full-stack delivery: one API, web app and mobile app are all in scope | Accepted | 2026-11-06 |
| ADR-008 | Chat is a `conversations` wrapper over photo assessment, not a new model or generative diagnosis | Accepted | 2026-11-06 |
| ADR-009 | PostgreSQL/PostGIS + Cloudinary as the v1 data platform | Accepted | 2026-11-06 |
| ADR-010 | v1 roles: farmer, extension_worker, admin, pathologist, agronomist; `can_confirm` for confirmation | Accepted | 2026-11-06 |
| ADR-011 | Open crop catalogue with a validated-target allowlist | Accepted | 2026-11-06 |
| ADR-012 | Next.js web app lives in `frontend/` (source documents say `web/`) | Accepted | 2026-11-06 |
| [ADR-013](adr/0013-mobile-stack.md) | Flutter is the single mobile client; the Expo prototype is not adopted | Accepted | 2026-11-06 |

---

## 6. Risk register

| ID | Risk | L | I | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R-01 | No verified historical data in year one | H | H | Rules baseline; nowcast; state limits | ML lead | Open |
| R-02 | Public-data model fails in field | H | H | Field test set; domain adaptation; quality gate | ML lead | Open |
| R-03 | Verification backlog empties the verified layer | H | H | Extension-first triage; SLA; workload caps | Programme | Open |
| R-04 | "No reports" read as "no disease" | M | H | Coverage as feature + UI; suppression rules | Product | Open |
| R-05 | Advisory liability | L | H | Non-chemical only; approval workflow; legal review | Programme | Open |
| R-06 | Privacy breach (location/identity) | L | H | Approximate location; RBAC; audit; DPIA | Eng lead | Open |
| R-07 | Pilot misses epidemic season | M | H | Calendar-driven planning | Programme | Open |
| R-08 | Partner withdrawal mid-pilot | M | H | Dual partnerships; data ownership agreement | Product | Open |
| R-09 | False-alert fatigue | M | M | Calibration; cooldown; feedback loop | Product | Open |
| R-10 | Scope creep (multi-crop, universal diagnosis) | H | H | Expansion rule; Gate 0 decisions | Product | Open |
| R-11 | Look-alike symptoms mislabelled as disease | H | M | Abiotic class; label handbook; expert review | Agronomist | Open |
| R-12 | Low-coverage area read as low risk | H | H | Coverage gate blocks scored bands; UI coverage panel | Product | Open |
| R-13 | Biosecurity: public map used to infer farm vulnerability | L | H | Aggregation, suppression, access control | Eng lead | Open |
| R-14 | Adversarial input (borrowed/gamed images) | M | M | Provenance metadata; duplicate detection; spot checks | Field ops | Open |
| R-15 | Expert burnout from unpaid review labour | M | H | Workload caps; compensation; triage | Programme | Open |
| R-16 | Weather provider outage, gap or licence change | M | H | Freshness checks; `insufficient_data` path; provider terms recorded | Data engineer | Open |
| R-17 | Chat reply read as a diagnosis | H | H | Structured templates; "assistive, not diagnosis" copy; abstention; review escalation | Product | Open |
| R-18 | Chat emits chemical advice or free-form medical text | L | H | Server-side validator before storage; template tests; no generative diagnosis path in v1 | Eng lead | Open |
| R-19 | Chat scope creep into a general LLM assistant | M | M | Explicit out-of-scope; wrapper-only architecture; no free-form model | Product | Open |

L = likelihood, I = impact, both H/M/L.

---

## 7. Changelog

| Date | Change |
|---|---|
| 2026-11-06 | Created `docs-context/` and `feature-specs/` from `summary.md`, `totalcontent.md`, `update.md`. v1 scope narrowed per realism audit. Six decisions recorded as open. |
| 2026-11-06 | Aligned the full documentation set to the supplied 55-chapter blueprint. Added `data-foundation.md`, `ml-models.md`, `operations-and-pilot.md`, `roadmap-and-resources.md`, `appendices.md`, and the chapter map in `README.md`. Expanded overview, architecture, UI, code standards, workflow rules and feature specs. No scope decision changed; D1–D6 remain open. |
| 2026-11-06 | Added `phase-plan.md`: a detailed per-phase work breakdown (workstreams, deliverables, exit gates, owners, dependencies and explicit exclusions for Phases 0–6). Linked it from the README, `AGENTS.md`, `project-overview.md` and `roadmap-and-resources.md`. No gate, scope or decision changed. |
| 2026-11-06 | Added `final/PRD.md` and `final/TRD.md`: consolidated product and technical requirements distilled from the operating docs, feature specs and phase plan. No gate, scope or decision changed. |
| 2026-11-06 | Loophole audit applied. Added decisions D7–D12 (forecast event/negative class, abstention rule + numeric floors, coverage/freshness/suppression values, retention/deletion, on-behalf identity + offline sessions, client pre-check mechanism). Gate 0 now needs a calendar target and named owners; Gates 3–5 now require floors to be **met**, not merely reported, and require D7/D9 values. Fixed internal contradictions: `ui-context.md` status tokens and calibration copy, `01-design-system.md` status token list, `TRD.md` raw-score example, `02-reporting-and-capture.md` on-device scope, `code-standards.md` ADR gating, `AGENTS.md` scope wording. Findings: `../audit/loopholes-2026-11-06.md`. |
| 2026-11-06 | Made full-stack delivery explicit (backend API + Next.js web app + Flutter mobile app) and added `feature-specs/08-conversational-capture.md`: chat on web and mobile where a user sends an image and receives a structured, validator-checked assessment reply. Updated PRD, TRD, architecture, UI, phase plan, AGENTS and READMEs. Added ADR-007/008 and R-17–R-19. |
| 2026-11-06 | **Phase 0 architecture reconciliation.** Accepted ADR-009 (PostgreSQL/PostGIS + Cloudinary), ADR-010 (roles + `can_confirm`), ADR-011 (open crop catalogue + validated-target allowlist), ADR-012 (`frontend/` naming). Answered D1, D2, D6, D13 (English + Kannada) and D14 (confidence band + abstention). Added D15 (in-app/email/SMS channels). Added `phase-0-decisions.md`. Gate 0 remains open on D1a, D3b, D4, D5 and D7–D12. |
| 2026-11-06 | Added Phase 1 reference artifacts in `database/`: complete schema slices (39 tables) against `05-data-layer.md`, Alembic migrations, object storage / presigned rules, backup and recovery design, demo-seed policy (`is_demo = true`, R5 non-chemical compliance), and schema/storage tests passing. |
| 2026-11-06 | Reconciled `../../IMPLEMENTATION-CHECKLIST.md` against the repository: updated work log for Phase 1 data platform, backend foundations, API router scaffolds, and test evidence. |
| 2026-11-06 | **D13 accepted:** `agronomist` added as a fifth role (advisory author/approver, risk-band approval, read-only area; cannot verify cases). Updated the RBAC matrix, MFA list and acceptance criteria in `03-auth-and-roles.md`; role lists in `PRD.md`, `phase-plan.md` and `05-data-layer.md`; review-role table in `04-expert-review.md`; advisory author/approver rules in `07-advisory-and-alerts.md`. Publication now requires two qualified accounts (D3 capacity). |
| 2026-11-06 | **D7 accepted:** forecast negatives come from a pre-registered sentinel panel, not from missing reports; `probable` is eligible with an evidence tier; as-of cutoffs, label-maturity embargo and blinded primary review are mandatory. Updated forecast task/evaluation/edge cases, review flow and requirements, sentinel tables, label-eligibility invariants in TRD/architecture/workflow rules, and Phase 4 plan. Discrimination/calibration are reported only on sentinel negatives; panel below the D8 minimum is marked underpowered. |
| 2026-11-06 | **D8 accepted:** safety-first abstention function (per-class `τ_c`, margin, entropy, explicit OOD, quality/crop gates), temperature scaling on a dedicated calibration split, OOD evaluated on held-out classes, and no user-facing override of a model output. Image and forecast floors are pre-registered before the frozen test set is opened; floors set after opening are void. Updated `ml-models.md`, `phase-plan.md` §6.4–6.5 and Gate 3, design-system confidence/abstain states, reporting requirements and acceptance, `image_predictions` schema/constraints (`decision_thresholds`, `ood_score`, `calibration_version`), TRD invariants and forecast evaluation/acceptance. Floor values remain unrecorded pending measurement. |
| 2026-11-06 | Reconciled the partner-added `database/` Phase-1 artifacts with D7/D8/D10/D13: forecast negatives come only from sentinel visits (image healthy/hard negatives are not forecast negatives); added the D8 prediction-decision table and D7 sentinel site/visit fields; verification rows now name the pathologist, not the agronomist; retention/controller references now point to D10. |
| 2026-11-06 | Phase 2 §5.1 engineering foundation: FastAPI app factory with RFC 7807 problem details, request-id middleware and JSON logs; SQLAlchemy session + Alembic `0001_baseline`; Next.js web client in `frontend/` (typecheck, lint and build pass); Flutter shell in `mobile/` (committed, unverified — no SDK); compose with PostGIS, API and web images; env templates for dev/staging; CI for backend, web, mobile, compose and image builds; `TEST-MATRIX.md`. No feature work; Gate 1 remains unmet. Added ADR-009. |
| 2026-11-06 | Web chat surface (Phase 2 §5.7, demo backend): `/chat` conversation list and `/chat/[conversationId]` thread; structured assessment card with assessed/abstained/unsupported/failed states; metadata-only image picker and drag-and-drop; idempotent retry and conversation delete; honest not-available routes for `/outlook` and `/review`. Added `design/tokens.json` and an application shell with mirrored CSS variables. Typecheck, lint, production build and live smoke pass. Upload/media, real inference, auth scoping and the mobile surface remain open; no gate is claimed. |
| 2026-11-06 | Desktop web shell: persistent section sidebar (Overview, Photo assessment, Area outlook, Review queue) with active-state marker and skip link; desktop dashboard with platform status and separate-output cards; collapses to a horizontal nav below 1024px and single-column grids below 640px; locked `/review` boundary page with no fabricated cases; `/outlook` now reads the five independent `/v1/map/layers/*` endpoints and shows each layer's own state (`map_not_configured` is explicit, never a merged risk value). Typecheck, lint, production build and live route smoke pass. |
| 2026-11-06 | Reconciled `../../IMPLEMENTATION-CHECKLIST.md` against the repository: added a work log for the §5.1 foundation, §5.7 web chat surface, `database/` governance artifacts and test evidence; ticked only evidence-backed items (architecture choices, doc reconciliation, rebuilt venv, JSON logging/request IDs/problem details, frontend build/lint/typecheck, production docs restriction). `.gitignore` stays unticked because `dist/` is missing; all auth, readiness, domain-schema, media, model, forecast, alert, map, admin, audit and i18n items remain open. Verdict remains **NOT COMPLIANT**; Gate 0 and Gate 1 are unmet. |
| 2026-11-06 | **D1–D6 decided.** D1: open horticulture catalogue with a validated crop × target allowlist; the first allowlist (D1a) stays open before Gate 3 and the pilot zone/boundary version (D1b) before Gate 4. D2: nowcast (last 10 days). D3: extension-first verification with pathologist escalation. D4: grant/NGO pilot → cooperative/insurer operations. D5: median lead time from first report to verified confirmation. D6: non-chemical guidance only, with legal review before Gate 5. "Pesticides" is read as pest/disease targets; R5 still forbids chemical prescriptions. |
| 2026-11-06 | Verified the Flutter client locally after installing Flutter 3.47.9 (stable, Dart 3.13.7): `flutter pub get` resolved 30 packages, `flutter analyze` reported no issues, `flutter test` passed the single widget test. Updated `TEST-MATRIX.md` FND-11 to Verified (analyze + test), the mobile README, `AGENTS.md` §5, PRD/TRD status lines and `IMPLEMENTATION-CHECKLIST.md` W-11. Still open: `android/`/`ios/` runners, an APK build, a device/emulator smoke and a recorded CI run. No gate is claimed. |
| 2026-11-06 | Phase 2 §5.2 identity backend slice: phone OTP for farmers, provisioned staff accounts, five-role deny-by-default dependencies, password+TOTP login, rotating refresh tokens with family revocation, versioned consent capture, privacy requests/self-export/soft deletion, credential-only retention job, and audited role changes, admin record views and exports. 64 new tests; full backend suite 294 passed. Deliberately **not** done: durable SQLAlchemy/Alembic persistence, authentication of the existing demo chat/assessment/advisory/map routes, real SMS/email providers, password reset, Argon2id (stdlib `scrypt` used instead), and D10/D11-dependent retention/on-behalf/offline behaviour. Gate 1 remains unmet and no gate is claimed. |
| 2026-11-06 | Reconciled the chat ORM with the merged domain ORM: `app/db/base.py` now provides the shared `UTCDateTime`/`utc_now`/`new_id` helpers; `app/db/models.py` re-exports the chat models (`Conversation`, `Message`, `MessageEvent`, `ImageUpload`, `ChatReviewRequest`) and keeps the observation-review `ReviewRequest` on `review_requests`; the chat review table is `chat_review_requests` (Alembic `0002_chat_persistence`); `alembic/env.py` loads `app.db.models`. Verified: both ORM modules import together, `Base.metadata.create_all` creates 48 tables on SQLite, `alembic history`/offline SQL are unchanged in chain, full suite 294 passed, and the live upload → assessment → review smoke passed on a fresh database. |
| 2026-11-06 | Persisted chat slice (Phase 2 §5.7): Alembic `0002_chat_persistence` (`conversations`, `messages`, `message_events`, `image_uploads`, `chat_review_requests`); `POST/GET /v1/uploads` with a JPEG/PNG/WebP allow-list, 10 MB ceiling, real decode, SHA-256 and a versioned demo quality gate; pluggable `AssessmentEngine` seam with a deterministic, labelled `DemoAssessmentEngine` (`demo-chat-0.1`) and fail-closed unknown configuration; idempotent turns; `POST …/messages/{id}/review`; web composer now uploads first and references `upload_id`, renders the stored preview, quality flags and review status. 14 new chat tests; full suite 294 passed. Live smoke (uvicorn + SQLite + `next start`) passed upload → assessed demo reply → persisted review → preview byte-match → 415 rejection. PostgreSQL/Alembic apply was not run (Docker daemon unavailable); real inference is still blocked on the API key and governance. |
| 2026-11-06 | Reconciled a force-pushed `main`: a collaborator's line (`697944d`, diverged at `611aa48`) added a parallel backend, Phase-0 docs and ADRs. Merged it while keeping this line's tested backend for overlapping paths (`app/api`, `app/core`, `app/db`, conversations, identity). The collaborator's new Phase-0 documents, ADRs, `backend/backend/*` vertical slice and non-conflicting files are retained; its superseded `app/*` implementations remain in history but are not wired. Removed the committed `backend/var/ps03.db` artifact. Backend suite re-run after the merge: 294 passed. |
| 2026-11-06 | Added the chat content-safety gate (CHAT-10, R5/R18): the deterministic, fail-closed `chat-safety-0.1` validator checks the reply text, assessment reason and candidate display names before storage. A blocked reply is stored as `failed` with `reason_code`/`error_code` `unsafe_content_blocked`, no candidates and `request_review`; a `validator_rejected` message event records the validator version and rule categories without the unsafe text. 19 validator unit tests and 3 API safety-gate tests; full backend suite 316 passed. A live API smoke on a fresh SQLite database re-ran upload → assessed `demo-chat-0.1` reply → persisted review → idempotent replay → preview byte-match → `415` rejection with the validator in the path. |
| 2026-11-06 | Added the optional OpenAI-compatible vision engine behind the `AssessmentEngine` seam (`APP_CHAT_ENGINE=openai_compatible`): the adapter posts a downscaled JPEG plus `APP_CHAT_LABELS` to `{APP_CHAT_BASE_URL}/chat/completions`, accepts JSON-only candidates, drops unknown labels and renders reply text from fixed templates. Missing key/model/labels, timeouts, HTTP failures and malformed output are explicit `failed` states; a model abstention is `abstained`/`model_abstained`. `is_demo` stays true until `APP_CHAT_LABELS_APPROVED=true`, so no D1/D2 taxonomy is invented in code. `httpx` moved to runtime dependencies; compose passes the chat variables and mounts a media volume. 19 engine tests and 1 API wiring test; full suite 336 passed. Verified with a mock transport and a live uvicorn run against a local OpenAI-compatible HTTP stub: upload → `assessed`, `is_demo=false`, `model_version=stub-vision-1`, one approved candidate, template text, persisted review and 2 messages. No real vendor call was made. |
| 2026-11-06 | **Phase 1 Weather, Boundaries, Historical Occurrences & Forecast Gate Ingestion:** Implemented `database/ingestion/weather_ingest.py` (variables, physical bounds, freshness, spatial matching method, leaf-wetness proxy), `boundary_loader.py` (EPSG:4326 GeoJSON MultiPolygon validation, coordinate range check, WKT conversion, boundary version propagation), `historical_ingest.py` (verification tier, `report_date >= event_date` check, source link provenance, deterministic SHA-256 dedupe key, dedupe history logging), and `forecast_gate.py` (strict pre-flight gating with explicit `insufficient_data` refusal, `probability = NULL`, zero silent imputation). Updated `01-schema.sql` (added table `historical_occurrences` [#40], `ck_weather_spatial_method`, `ck_hist_dates`, `ck_hist_tier`, `ck_forecasts_no_imputation`, and `check_weather_sufficiency` plpgsql function) and `02-demo-seed.sql`. All 38 unit tests pass in `database/tests/`. |
| 2026-11-06 | Merged `origin/main` (`c5ba4f7`) into the local Gate 0 line, resolving docs and lockfile conflicts. Upstream already contained the integrated assessments, mapping, alerts, auth, identity and observations work; local D1–D6 decisions, the consolidated ADR, and the Gate 0 closure were retained. Backend suite and lockfile to be regenerated and re-verified as part of the merge commit. |
| 2026-11-06 | **Mobile capture + offline queue (CHAT-02/CHAT-04, spec 08 §10):** the Flutter client now takes a photo or picks one from the gallery, previews/removes it, enforces the 10 MB and JPEG/PNG/WebP contract, uploads with `POST /v1/uploads`, and sends a message that references `image.upload_id` with `Idempotency-Key`. A turn is written to a persisted outbox (`ps03.chat.outbox.v1`) before the first call; `queued`/`failed` bubbles expose Retry/Delete, flush runs on manual action, a 15 s page timer and app resume, and the upload id and conversation id are persisted so retries reuse the same `client_message_id`. A missing local image becomes a visible failed turn, never a fabricated reply. `image_picker` 1.2.4, `shared_preferences` 2.5.6 and `http_parser` 4.1.2 added; `flutter analyze` clean and `flutter test` **14 passed** (Flutter 3.47.9 / Dart 3.13.7). Platform runners, an APK build, a device/airplane-mode smoke and the presigned-upload path (CHAT-NF-03) remain open; no gate is claimed. |
| 2026-11-06 | **Gate 4 forecast rules harness (partial):** extracted the inline demo scoring from `backend/app/modules/forecast/service.py` into pure `backend/app/modules/forecast/rules.py`; missing variables are skipped rather than imputed and the temperature window requires both bounds. `FeatureSnapshot.features` now records the rule result and contributions so a forecast can be re-derived. Added 21 synthetic-fixture tests in `backend/tests/test_forecast_rules.py` and `test_forecast_service.py`: dry vs wet weather changes score/band, a verified report changes the score with weather held constant, identical inputs reproduce the stored result, and missing/stale weather, low coverage, missing calendar and boundary mismatch return `insufficient_data` with `probability = NULL`. Backend suite **374 passed**. Still open: real weather provider, scheduler/runner, D8 floors, approved D9 values, D1b, and an expert-approved operating point; Gate 4 is **not met**. |
| 2026-11-06 | **Mobile stack decided (ADR-013):** Flutter `mobile/` is the single mobile client; the merged Expo prototype at `frontend/mobile/` was removed (recoverable at `ebcc5df`) because it had no network layer, offline queue, tests or device evidence, while Flutter speaks `/v1` and passes 14 tests with a built APK. `frontend/tsconfig.json` and `eslint.config.mjs` now exclude `mobile`; web typecheck and build pass. Reconciled the React Native statements in `architecture-context.md`, `ui-context.md`, `code-standards.md`, `phase-plan.md`, `project-overview.md`, `components/README.md`, `feature-specs/01-design-system.md`, `feature-specs/08-conversational-capture.md`, `README.md`, `summary.md` and `totalcontent.md` to Flutter, and corrected the ADR-006 index entry. The merged workspace pages were then fixed to derive selection state instead of setting it in effects, so web typecheck, lint and build pass. ML lint and format were made clean and `weights/*.pt`, `*.pth` and `*.onnx` are now git-ignored. No gate is claimed. |
| 2026-11-07 | **Pretrained YOLO detectors wired into the app (demo-only).** Added the isolated inference service `ml/serve` (FastAPI: `GET /health`, `GET /v1/models`, `POST /v1/detect`) so `ultralytics` (**AGPL-3.0**) stays out of the backend process and backend CI; weights are downloaded from Hugging Face and never committed. Added the demo-labelled CLI `ml/run_pretrained.py`, the HTTP client engine `backend/app/modules/conversations/pretrained_engine.py` (selected by `APP_CHAT_ENGINE=pretrained`/`yolo*`), and `POST /v1/detections` (`upload_id`, optional `model=pest|plant`). Every payload sets `is_demo: true`, carries a demo warning, and marks class names `unverified_model_label`; empty detections are an abstention, not a healthy verdict. The web `/scan` flow now uploads the captured photo and calls the real detector instead of a client-side template. Verified live on CPU: pest abstained on the test image; plant returned `corn smut (unverified model label)` 0.2911 through `/v1/uploads` → `/v1/detections`. Backend **392 passed**, ML **29 passed**, web typecheck/lint/build pass. Still open: AGPL deployment terms, D1a taxonomy mapping and calibration/operating point; Gate 3 remains open. |

---

## 8. Next five actions

1. Finish Gate 1 on the tested line: durable SQLAlchemy/Alembic identity and consent, authenticated demo feature routes, domain schema/media/readiness; keep the suite green.
2. Fix the **D1a** initial crop × target allowlist before Gate 3 and the **D1b** pilot zone/boundary version before Gate 4.
3. Secure the D3 SLA and D4 partner-counterparty signatures, then draft the data acquisition plan, labelling handbook and pilot protocol against the decided scope.
4. Retention/privacy follow-through: D10/D11 values for retention and on-behalf identity before Gate 7.
5. Verify the mobile scaffold (generate `android/`/`ios/` runners, build a debug APK, device smoke) and build both container images before claiming them.

---

## 9. Team and ownership

From blueprint Chapter 49. Roles are named here; individuals are assigned at Gate 0.

| Role | Owns | Accountable for |
|---|---|---|
| Product lead | Scope, research, milestones, stakeholder communication | Acceptance and decisions D1–D6 |
| Agronomist / pathologist | Taxonomy, labels, risk rules, advisory approval | Data and advisory correctness |
| Data engineer | Ingestion, quality, geospatial processing, lineage | Data foundation gates |
| ML engineer | Image and forecast modelling, evaluation, calibration, monitoring | Model gates and honesty |
| Application engineers | Mobile, backend, portal, APIs, offline sync | Platform MVP gate |
| QA and field researcher | Test strategy, usability, field pilot, issue reporting | Pilot evidence quality |
| Field operations lead | Partner coordination, verification capacity, training | Review SLA and coverage |

**Implementation points**

- One accountable owner per deliverable.
- Regular field feedback sessions throughout development.
- Staffing shape is 7–9 people for v1; the first operational hire after engineering is a
  field operations lead.

---

## 10. Budget and resources

From blueprint Chapter 51. No figure is committed until the work breakdown and the owning
institution (D4) are settled.

| Category | Cost driver |
|---|---|
| People | Engineering, data, ML, agronomy, field collection, QA, support |
| Data acquisition | Field visits, enumerators, expert labelling, lab confirmation, licences |
| Infrastructure | CPU inference, training GPU, database, storage, maps, monitoring, backups |
| Operations | Connectivity, devices, training, translation, support, maintenance |
| Risk reserve | Seasonal delay, provider change, extra collection |

Guidance: people and field data dominate; infrastructure is usually under 10% at pilot
scale. Prepare low, expected and high scenarios and track recurring cost separately from
one-time development. See `roadmap-and-resources.md` §2.

---

## 11. Success metrics (pre-registration)

From blueprint Chapter 53. Baselines and targets are set with domain experts **after** the
baseline is measured; no target numbers are committed here.

| Level | Metrics |
|---|---|
| Technical | Image macro F1, per-class recall, calibration, abstention rate; forecast PR-AUC, Brier, calibration on sentinel-panel negatives only (underpowered below the D8 minimum); latency |
| Operational | Report-to-review time, backlog, verified case rate, delivery, sync success |
| User | Task completion, comprehension, repeat use, alert usefulness, opt-out |
| Agricultural | Lead time, visit prioritisation, credible outcome indicators |
| Equity | Performance and adoption by geography, device and segment |

**Primary metric (D5):** median lead time from first farmer report to verified expert
confirmation, versus the existing advisory baseline. Pre-register before the pilot.

---

## 12. Documentation coverage

The supplied blueprint (`../totalcontent.md`) is 55 chapters plus Appendices A–H. Coverage:

| Range | Document |
|---|---|
| Ch 1–10 | `project-overview.md` |
| Ch 11–12 | `../feature-specs/02`–`08`, `code-standards.md` |
| Ch 13–14, 43, 47, 48 | `architecture-context.md` |
| Ch 15–17 | `ui-context.md` |
| Ch 18–24 | `data-foundation.md` |
| Ch 25–26 | `../feature-specs/05-data-layer.md` |
| Ch 27–38 | `ml-models.md` |
| Ch 39 | `../feature-specs/06-forecast-and-risk-map.md` |
| Ch 40–44 | `../feature-specs/07-advisory-and-alerts.md`, `../feature-specs/02-reporting-and-capture.md`, `../feature-specs/03-auth-and-roles.md`, `ml-models.md` |
| Ch 45–49, 53–55 | `operations-and-pilot.md` |
| Ch 50–52 | `roadmap-and-resources.md` |
| Appendices A–H | `appendices.md` |

The chapter-to-file map is maintained in `../README.md`. Coverage is documentation, not
scope approval.
