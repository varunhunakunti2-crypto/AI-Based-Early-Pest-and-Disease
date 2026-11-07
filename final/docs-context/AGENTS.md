# AGENTS.md — working agreement

**Project:** PS-03 — AI-Based Early Pest and Disease Outbreak Prediction Network
**Purpose of this file:** the entry point for any human or AI agent contributing to this
repository. It states what the system is, what must never be violated, and how work is
planned, built, tested and documented.

**Status:** documentation plus engineering scaffolds (Phase 2 §5.1), the persisted
demo chat slice (§5.7: image upload, demo quality gate, deterministic demo engine,
optional OpenAI-compatible vision adapter, review requests; Alembic
`0002_chat_persistence`), the demo-labelled video-reading machinery (spec 09:
bounded decode, frame sampling, `demo-motion-0.1` detector, `bytetrack-lite-0.1`
tracker, per-frame assessments, non-diagnostic summary; Alembic
`0003_video_persistence`), and the §5.2 identity backend slice (in memory: OTP,
staff MFA, five roles, consent, privacy, audit). The default photo path is still the
labelled demo engine; the two pretrained YOLO detectors in `ml/` are wired as an
opt-in, **demo-only** path (isolated `ml/serve` service + `APP_CHAT_ENGINE=pretrained`
+ `POST /v1/detections`) so `ultralytics` (AGPL-3.0) stays out of the backend; raw
model labels are shown as unverified and no D1a mapping or calibration exists. Demo
paths are labelled, the provider adapter is mock- and local-stub tested (no vendor
call), the shipped video detector is a demo heuristic, and identity state is lost on
restart. A **synthetic-only ML scaffold** exists in `ml/` (manifest contract, grouped
splits, deterministic baseline, backend-harness evaluation, fail-closed promotion,
model card; 29 tests including the inference service) but it ships no approved trained
image model, real dataset, calibration artefact or operating point. A
**synthetic-fixture forecast rules harness** exists in
`backend/app/modules/forecast/rules.py` with 21 tests proving input sensitivity,
snapshot reproducibility and no-score refusal; it uses demo points/thresholds and
has no real weather provider, approved operating point or field evaluation. The
mobile client adds photo capture and a persisted offline queue; `flutter analyze`
is clean and 14 tests pass, the `android/` and `ios/` runners are committed, a debug
APK builds, and an emulator smoke covered gallery capture → upload → assessment →
airplane-mode queueing → reconnect flush. Real-device camera and iOS remain
unverified. **Last updated:** 2026-11-07

---

## 1. What we are building

An explainable, offline-tolerant decision-support platform with two separate outputs:

| Output | Question it answers | Unit |
|---|---|---|
| **Photo assessment** | What might be visible on *this* plant? | One image + crop context |
| **Area outlook** | How likely is *this threat* in *this area* over *this window*? | Crop × target × geography × horizon |

Neither output is a laboratory confirmation and neither is a confirmed outbreak.
The platform is deliberately narrow in v1: one crop, one agro-climatic zone, a small
target list, a rules-based weather risk model, assistive image triage, extension-worker
verification, and SMS/WhatsApp delivery. These are the intended shape, not settled scope —
crop, targets, zone, horizon and channel are fixed by decisions D1, D2 and D4 in
`progress-tracker.md` §4. See `project-overview.md`.

---

## 2. Read order

1. `AGENTS.md` (this file) — rules and workflow.
2. `project-overview.md` — scope, users, success criteria.
3. `architecture-context.md` — components, boundaries, data flow, invariants.
4. `ui-context.md` — wording, visual rules, screen inventory.
5. `code-standards.md` — language, API, testing and ML conventions.
6. `progress-tracker.md` — current phase, decisions, open questions.
7. `phase-plan.md` — the detailed work breakdown for the current and next phase.
8. The relevant file in `../feature-specs/` before touching that feature.
9. Domain depth, when the task touches data, models, pilot or planning:
   - `data-foundation.md` — chapters 18–24 (data strategy, images, labels, splits,
     weather, historical records).
   - `ml-models.md` — chapters 27–38 (image and forecast modelling, reliability, combining
     outputs).
   - `operations-and-pilot.md` — chapters 45–49 and 53–55 (testing, pilot, deployment,
     monitoring, team, success metrics, demo scenario).
   - `roadmap-and-resources.md` — chapters 50–52 (roadmap, budget, risk register).
   - `phase-plan.md` — the detailed work, deliverables and exit gates for every phase.
   - `appendices.md` — appendices A–H (templates, checklists, glossary, launch gates).
10. `../README.md` — the chapter-to-file map.
11. `../summary.md`, `../totalcontent.md`, `../update.md` — original blueprint and
    realism audit. Reference only; they are not implementation instructions.

If documents conflict, apply this precedence:

```
explicit user instruction
  > this file (AGENTS.md)
  > feature-specs/ (the specific feature)
  > architecture-context.md / ui-context.md / code-standards.md
  > progress-tracker.md decisions
  > summary.md / totalcontent.md / update.md
```

For v1 scope conflicts, the realism constraints in `update.md` win over the maximal
blueprint. Record the resolution in the decision log in `progress-tracker.md`.

---

## 3. Non-negotiable rules

These are product-safety and scientific-integrity rules, not style preferences.

### R1 — Never conflate the two outputs
Photo assessment and area outlook are separate cards, separate data, separate model
versions, separate timestamps. No screen, API response, map layer or database view may
merge them into one "risk" number.

### R2 — Abstain rather than force a result
If image quality is poor, the crop is unsupported, or inputs are outside the model's
validated domain, return an explicit no-assessment state with a reason. Never map an
unknown input onto the nearest supported class.

### R3 — No report is not evidence of absence
Surveillance intensity and data coverage are first-class features and first-class UI.
Low coverage must be shown as low coverage, not as low risk. Never treat "zero reports"
as a confirmed negative label.

### R4 — Human verification is mandatory
Model output is never auto-promoted to a verified case. Only an authorised reviewer can
set verification status, and every change is audited. Unverified photo assessments never
enter forecast features as confirmed cases.

### R5 — No chemical advice, ever
The advisory layer contains only expert-approved, versioned, non-chemical guidance
(scouting, monitoring, sanitation, crop management, escalation). Do not generate,
paraphrase or "improve" pesticide names, doses, mixtures, intervals, pre-harvest
intervals or legal-use instructions. This is a liability boundary, not a content gap.

### R6 — No fabricated data or metrics
Never invent model performance numbers, dataset sizes, field results, partner names,
thresholds or "example" forecasts that could be mistaken for real output. Demo and
synthetic data must carry a visible `demo`/`synthetic` label in data, API and UI.

### R7 — Every prediction is traceable
Persist, for every displayed output: model version, input source timestamps, generation
timestamp, issue/expiry time where applicable, calibration status, and the feature or
image snapshot it was computed from. Prediction rows are append-only.

### R8 — Offline-first is core
Field capture must work without connectivity. Client-generated identifiers plus
idempotency keys prevent duplicates. Cached forecasts are visibly marked stale after
expiry. Do not design a flow that requires a live server round-trip to save a report.

### R9 — Privacy by default
Approximate location by default. No exact farm coordinates to unauthorised roles. No
personally identifiable farmer data in dashboards or exports. Suppress small counts.
Consent is captured in plain language and is auditable.

### R10 — Spec before code, docs after code
No feature work without an accepted spec in `feature-specs/`. Any change to scope,
schema, API contract, model behaviour or risk semantics updates the spec and
`progress-tracker.md` in the same change.

---

## 4. Target repository layout

```
/
├── AGENTS.md                     # pointer to docs-context/AGENTS.md
├── components/                   # shared web UI components (not created yet)
├── docs-context/                 # this folder: operating context for agents
├── feature-specs/                # feature-level specifications
├── backend/                      # FastAPI modular monolith (scaffold)
├── mobile/                       # Flutter capture app (capture + offline queue; analyze/test verified)
├── frontend/                     # Next.js web app (scaffold; source docs say web/)
├── ml/                           # synthetic-only training/eval scaffold (no model)
├── database/                     # database workspace; schema authority is backend Alembic
└── deploy/                       # compose, environment templates, runbooks (scaffold)
```

`frontend/` is the web app: the folder predates this scaffold and the naming
reconciliation is ADR-009 in `progress-tracker.md`. `database/` holds reference
artifacts, governance registers, Alembic migrations plan, storage rules, and backup
design — SQLAlchemy models and Alembic migrations in `backend/` are the
single schema authority (ADR-002). Do not add a second ORM or manual DDL.

Nothing beyond the Phase 2 §5.1 foundation, the persisted demo chat slice
(§5.7), the in-memory §5.2 identity backend slice, the demo-labelled video-reading machinery (spec 09),
the mobile capture + offline-queue slice (spec 08 §10),
the synthetic-only `ml/` scaffold, and the Phase 1 weather/boundaries/historical ingestion components exists in these folders.
Do not create scaffolding that implies a decision has been made unless the decision is recorded in `progress-tracker.md`.

---

## 5. Commands

Verified on 2026-11-06 (Windows 11; Python 3.14.5 in the venv, runtime target
3.12; Node 24.14.0; Docker client 29.8.0; Flutter 3.47.9 / Dart 3.13.7). POSIX
paths are in each agent's `README.md`.

| Task | Command | Last result |
|---|---|---|
| Backend tests | `cd backend && .venv\Scripts\python -m pytest` | 392 passed |
| Backend lint | `cd backend && .venv\Scripts\python -m ruff check app tests` | clean |
| Backend format check | `cd backend && .venv\Scripts\python -m ruff format --check app tests` | clean (141 files formatted) |
| Migration history | `cd backend && .venv\Scripts\python -m alembic history` | `0001_baseline`, `0002_chat_persistence`, `0003_video_persistence` |
| Review migration SQL offline | `cd backend && .venv\Scripts\python -m alembic upgrade head --sql` | SQL emitted |
| Backend dev server | `cd backend && .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000` | `/health` returned 200 |
| Web install | `cd frontend && npm ci` | 346 packages |
| Web typecheck | `cd frontend && npm run typecheck` | pass |
| Web lint | `cd frontend && npm run lint` | pass |
| Web build | `cd frontend && npm run build` | pass; 17 routes |
| Web chat smoke | `uvicorn` + `next start`, then upload a photo, send it, request review, open the thread and delete | pass; upload → `demo-chat-0.1` assessment → persisted review → preview byte-match → 415 rejection; list, thread, demo badge, delete and empty state observed |
| ML scaffold tests | `cd ml && ..\backend\.venv\Scripts\python -m pytest` | 29 passed (synthetic fixture + fake-detector service; no torch) |
| ML scaffold lint | `cd ml && ..\backend\.venv\Scripts\python -m ruff check .` | pass |
| ML scaffold format check | `cd ml && ..\backend\.venv\Scripts\python -m ruff format --check .` | pass |
| ML scaffold run | `cd ml && ..\backend\.venv\Scripts\python -m pest_ml.pipeline` | pass; artefacts under `ml/artifacts` (git-ignored), status `evaluated` only |
| Compose parse | `docker compose --env-file deploy/.env.example -f deploy/docker-compose.yml -f deploy/docker-compose.dev.yml config --quiet` | pass |
| Mobile analyze + test | `cd mobile && flutter pub get && flutter analyze && flutter test` | pass — dependencies resolved; analyze clean; **14 tests passed** (Flutter 3.47.9 / Dart 3.13.7) |
| Container builds | `docker build -t ps03-api:ci backend` and `docker build -t ps03-web:ci frontend` | **NOT RUN — daemon unavailable**; CI builds |

`alembic upgrade head` against a live database has not been run (no local
PostGIS). The offline SQL path is verified; applying it is not.

Never document a command you have not run in this repository. The container-build
row is marked NOT RUN on purpose and must be converted to evidence before the
containers are called working. Mobile analyze/test are verified, including the
capture/offline contract tests; the debug APK and an emulator airplane-mode run are
verified, while real-device camera capture, iOS and background execution remain
unverified.

---

## 6. Definition of done

A change is done only when all of the following hold:

- [ ] It implements an accepted requirement ID from a feature spec.
- [ ] The failure path is implemented, not just the happy path (unsupported crop,
      blurry image, stale weather, offline, duplicate retry, unauthorised role).
- [ ] Tests cover the new behaviour and at least one negative case.
- [ ] No R1–R10 rule is weakened; if one is touched, the spec says why.
- [ ] API changes are reflected in the OpenAPI schema and in the spec.
- [ ] Schema changes ship with a forward migration and a rollback note.
- [ ] New user-facing strings follow `ui-context.md` wording rules and are externalised
      for translation.
- [ ] Telemetry/audit events are emitted where the spec requires them.
- [ ] `progress-tracker.md` status is updated.

---

## 7. How to work (agent workflow)

1. **Locate the work.** Identify the feature spec and requirement IDs involved. If none
   exist, stop and propose a spec addition instead of writing code.
2. **Check the decision log.** If the work depends on an unresolved decision (crop,
   target, geography, forecast horizon, verification SLA, advisory legality), ask.
   Do not silently pick a default that changes scope.
3. **Plan in small slices.** State the files to touch and the test that proves the
   slice. Prefer one vertical slice over broad scaffolding.
4. **Implement the smallest correct change.** Match surrounding patterns; do not
   refactor unrelated code in the same change.
5. **Test.** Run the relevant suite. Report exact commands and results. If you cannot
   run something, say so explicitly.
6. **Update docs.** Spec + tracker + API schema as applicable.
7. **Summarise.** What changed, what is verified, what is still open, what you did not
   do. No claims beyond evidence.

### When to stop and ask

- Choosing or changing crop, target class list, geography or forecast horizon.
- Adding a dependency, external provider or paid service.
- Any change to verification states, role permissions or audit behaviour.
- Any advisory wording, or anything that could read as treatment advice.
- Any use of real farmer data, images or locations.
- Any schema change that is not additive.

---

## 8. Hard stops

Refuse and escalate (do not implement) if asked to:

- generate pesticide, herbicide, fungicide or dosage recommendations;
- present a model score as a diagnosis, laboratory result or confirmed outbreak;
- remove or hide abstention / coverage / staleness indicators;
- auto-verify cases or bypass expert review;
- train or evaluate on data without documented permission;
- put real personal or farm-identifying data into demo content, tests or fixtures;
- weaken authentication, authorisation or audit logging to make a demo easier.

---

## 9. Documentation map

| File | Answers |
|---|---|
| `project-overview.md` | Why the project exists, who it serves, what v1 includes |
| `architecture-context.md` | How the system is put together and where logic belongs |
| `code-standards.md` | How code, tests, APIs, migrations and ML experiments are written |
| `ui-context.md` | How it looks, reads and behaves for users |
| `progress-tracker.md` | Where we are, what is decided, what is next |
| `phase-plan.md` | What work each phase contains, what it produces and when it may exit |
| `ai-workflow-rules.md` | Detailed agent operating procedure and handoff format |
| `../TEST-MATRIX.md` | Requirement ID → scenario → expected result → evidence for the current scaffold |
| `data-foundation.md` | How data is collected, labelled, cleaned, split and governed |
| `ml-models.md` | How the image and forecast models are formulated, trained, evaluated and combined |
| `operations-and-pilot.md` | How the system is tested, piloted, deployed, monitored and staffed |
| `roadmap-and-resources.md` | Phase roadmap, budget/resource logic and the risk register rationale |
| `appendices.md` | Approved templates, checklists, glossary and launch gates |
| `../feature-specs/01..09` | What each feature must do, with acceptance criteria |
| `../README.md` | Which file covers which blueprint chapter |

---

## 10. Vocabulary (use these terms exactly)

| Term | Meaning |
|---|---|
| **Photo assessment** | Image-based triage of visible symptoms. Never "diagnosis". |
| **Video reading** | Per-frame photo assessments plus a non-diagnostic summary of a short clip. Never a video-level diagnosis, severity, yield loss or area outlook. |
| **Area outlook** | Forecast risk for crop × target × geography × horizon. Never "outbreak alert". |
| **Abstention / no assessment** | Model declined to answer because evidence is insufficient. |
| **Coverage** | Completeness, freshness and representativeness of inputs for an area. |
| **Verification** | Human decision on a report: confirmed, probable, rejected, duplicate, needs visit, unresolved. |
| **Target** | A supported pest/disease condition on the supported crop list. |
| **Supported** | Explicitly in the approved crop/target/geography list for the current release. |
| **Stale** | Past its validity window; must be visually distinct from fresh data. |

---

## 11. Blueprint coverage

`../totalcontent.md` is the supplied 55-chapter report and implementation blueprint. It is
the source of what the product must eventually do; this repository is the operational
distillation of it. `../README.md` maps every chapter and appendix to the file that covers
it, so no part of the blueprint is lost and no part is silently treated as committed scope.

Two rules follow from that split:

- The blueprint is **maximal**; `../update.md` narrows v1. Where they differ on v1 scope,
  `../update.md` wins and the difference is recorded in `progress-tracker.md`.
- A chapter being covered by a document does **not** mean its capability is approved for
  v1. Coverage is documentation; approval is a decision in `progress-tracker.md` §4.

Chapters 1–17 and 25–26 and 39–44 are covered by `project-overview.md`,
`architecture-context.md`, `ui-context.md` and feature specs 01–07. Chapters 18–24, 27–38,
45–55 and Appendices A–H are covered by the domain documents listed in §9.
