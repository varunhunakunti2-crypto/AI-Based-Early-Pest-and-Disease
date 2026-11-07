# PS-03 web client (Next.js + TypeScript)

API-only client for the PS-03 modular monolith. It consumes the versioned
`/v1` API and never connects to the database
(`final/docs-context/architecture-context.md`, ADR-003).

> Folder note: the source documents call this app `web/`; the implementation
> lives in `frontend/` because that folder already existed in the repository.
> See ADR-009 in `final/docs-context/progress-tracker.md`.

## Commands

```bash
npm install
npm run dev        # http://localhost:3000
npm run typecheck  # tsc --noEmit
npm run lint       # eslint .
npm run build      # production build
npm run start      # serve the production build
```

Set `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`) for browser
requests; see `.env.example`. Server components read `API_BASE_URL` first
(compose sets it to `http://api:8000`) so they use the container network while
the browser uses the public origin.

## Routes

| Route | What it does | Evidence |
| --- | --- | --- |
| `/` | Reports API reachability, shows live weather context (current conditions, short forecast, source and fetch time) and explains the two separate outputs. Weather is context only and never becomes a risk score. | live smoke, build |
| `/chat` | Conversation list: create, open and delete; empty and API-unreachable states. | live smoke, build |
| `/chat/[conversationId]` | Thread with image upload, structured assessment replies, review requests, idempotent retry, demo badge and delete. | live smoke (upload → assessment → review), build |
| `/weather` | Open-Meteo current conditions and a seven-day forecast for one location, with place search and browser geolocation. Missing values stay “—”; source and fetch time are shown. Context only, never a risk score. | live smoke, build |
| `/outlook` | Independent map-layer states (verified, unverified, modelled risk, coverage, boundaries) fetched from `/v1/map/layers/*`; explicit “not configured” state, never a merged risk value. | live smoke, build |
| `/review` | Honest “locked” state for the expert review portal; no fabricated cases. | live smoke, build |
| `/admin` | Admin dashboard for the identity slice: staff sign-in + MFA, profile, account list/counts, provision staff, audited record view, role/status changes, retention and aggregate exports. Tokens stay in the tab's `sessionStorage`; unauthenticated, non-admin and expired states are explicit. | live smoke, build |

The desktop shell is a persistent left sidebar (Overview, Photo assessment, Area
outlook, Review queue, Admin) with an active-section marker, a skip link and a top bar.
Below 1024px the sidebar collapses into a horizontal scrollable nav. Layout
reflows to a single column and the dashboard grids stack at 640px.

The web chat is the Phase 2 §5.7 surface, not a new model. It renders the
server's structured `AssessmentCard` fields; it never parses prose into a
diagnosis and never invents a result. The composer uploads the photo to
`POST /v1/uploads` first and the message references the returned `upload_id`.
The server validates and stores the image, runs a demo quality gate and returns
a labelled demo assessment. No real image model is connected; the demo engine
(`demo-chat-0.1`) and all synthetic labels are visibly marked.

## Design system

`design/tokens.json` is the semantic token source
(`final/feature-specs/01-design-system.md`). `app/globals.css` mirrors those
values as CSS variables until a generator exists; update both in one change.
Risk and status namespaces stay separate.

## Scope

Implemented:

- conversation list, thread, create and delete;
- honest placeholder routes for area outlook and expert review (no fabricated data);
- image composer with file picker, drag-and-drop, local preview and 10 MB guard;
- real upload to `/v1/uploads`, server-side validation and stored preview rendering;
- structured assessment card with assessed / abstained / unsupported / failed
  states, quality flags, confidence band, calibration status, model version and
  generation time;
- request expert review from an assessment and see its persisted status;
- demo labelling, offline notice, failed-send retry with the same
  `client_message_id`, and empty/error states;
- admin sign-in (staff login + TOTP MFA) with one-time refresh and logout;
- admin account list and role/status counts derived from the server list;
- staff provisioning (one-time MFA secret), audited record view with a
  required reason, role and status changes (staff-only, last-admin guards),
  credential retention and aggregate-only exports with required purposes.

Not implemented in this phase:

- presigned-URL/object-storage uploads (local multipart storage only) and signed preview URLs;
- real image inference (replies are labelled demo);
- chat context fields (crop, stage, area) — the crop list is blocked on D1;
- the reviewer queue, advisories and area outlook;
- per-user ownership for chat (the chat backend still uses a single demo owner);
- httpOnly-cookie sessions (admin tokens live in `sessionStorage`; see
  `lib/auth.ts`);
- localisation catalogs (copy is currently English-only in components).

## Verified locally

| Check | Result |
| --- | --- |
| `npm run typecheck` | pass |
| `npm run lint` | pass |
| `npm run build` | pass; routes `/`, `/_not-found`, `/admin`, `/chat`, `/chat/[conversationId]`, `/outlook`, `/review` |
| Live smoke | `/`, `/chat`, `/outlook`, `/review`, `/admin` returned 200; `/chat/conv_missing` returned 404; the sidebar nav (including Admin) and platform status rendered. Upload → message → review returned a persisted `demo-chat-0.1` assessment and review status; the preview bytes matched the upload; the thread rendered the stored image, quality flags and review status; delete returned the empty state. `/outlook` rendered all five layer cards as “Not configured” with the new map router and “0 of 5 layers serving data”; no value was merged into a risk number. `/admin` rendered the staff sign-in form while unauthenticated; the supporting API flows (login → MFA → profile/list, provision, audited view with reason, role/status guards, retention, aggregates, refresh rotation, 401/403 negative paths) were verified directly against the live backend |

The production build and live smoke used the local FastAPI dev server with a
file-backed SQLite database (the production schema is Alembic
`0002_chat_persistence`; PostgreSQL apply is not yet verified). The upload,
demo quality gate, demo assessment and review paths were exercised; no real
model inference was.
