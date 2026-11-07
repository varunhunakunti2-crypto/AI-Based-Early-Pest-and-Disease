# Repository agent instructions

The authoritative working agreement for this repository is
[docs-context/AGENTS.md](docs-context/AGENTS.md). Read it before making any change.

Short version:

- **Two outputs, never conflated:** photo assessment (one image) and area outlook
  (crop × target × geography × horizon).
- **Abstain instead of guessing.** "No assessment" is a valid, expected result.
- **No report is not proof of absence.** Data coverage and surveillance intensity
  must be visible wherever risk is shown.
- **No chemical prescriptions.** Advisory content is expert-approved, versioned and
  non-chemical; severe or uncertain cases escalate to a human.
- **No fabricated metrics, datasets or predictions.** Demo data must be labelled as
  demo data everywhere it appears.
- **Spec before code.** Update `docs-context/progress-tracker.md` when scope,
  decisions or status change.

Repository status as of 2026-11-06: documentation plus Phase 2 engineering scaffolds
(FastAPI, Next.js web client, Flutter shell, compose and CI), the **persisted demo
chat slice** (image upload + quality gate + deterministic demo engine + optional
mock- and local-stub-tested OpenAI-compatible vision adapter + review requests, Alembic
`0002_chat_persistence`), the **demo-labelled video-reading machinery** (bounded clip
decode, deterministic sampling, `demo-motion-0.1` detector, `bytetrack-lite-0.1`
tracker, per-frame assessments, non-diagnostic summary, Alembic
`0003_video_persistence`), and the **§5.2 identity backend slice** (phone OTP, staff
MFA, five roles, consent, privacy, audit — in memory). The default photo path is the
labelled demo engine; two pretrained YOLO detectors are wired as an opt-in **demo-only**
path through the isolated `ml/serve` service and `POST /v1/detections`, keeping
`ultralytics` (AGPL-3.0) out of the backend, and show raw labels as unverified with no
D1a mapping or calibration. The shipped video detector is a heuristic rather than a pest
detector, and identity state is not durable; the web app builds and its chat flow passed
a live upload → assessment → review smoke test, while the mobile client adds photo capture
and a persisted offline queue, with `flutter analyze` clean and 14 tests passing
(platform runners committed, debug APK built and an emulator smoke passed; real-device
camera and iOS unverified). A synthetic-only
ML scaffold in `ml/` proves the manifest → grouped split → train → evaluate →
promotion plumbing (29 tests) but ships no approved trained image model, real dataset or
operating point. A deterministic forecast rules harness in
`backend/app/modules/forecast/rules.py` is covered by 21 synthetic-fixture tests
(input sensitivity, snapshot reproducibility, no-score refusal), but it uses demo
points/thresholds and has no real weather provider, approved operating point or
field evaluation. Gate 1, Gate 3 and Gate 4 are not met.

The full 55-chapter blueprint and Appendices A–H are mapped to repository files in
[README.md](README.md). Coverage is documentation, not scope approval: v1 scope is set by
[update.md](update.md) and recorded in `docs-context/progress-tracker.md` §2 and §4.
