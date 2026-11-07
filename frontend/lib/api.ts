/**
 * Typed client for the PS-03 `/v1` API.
 *
 * Rules:
 * - the web app is an API-only client and never touches the database;
 * - errors are the problem-details envelope from final/TRD.md §7.2;
 * - demo/synthetic content is always labelled by the API, never inferred here.
 */

export type AssessmentState = "assessed" | "abstained" | "unsupported_crop" | "failed";

export interface Assessment {
  state: AssessmentState;
  reason_code: string | null;
  reason_text: string | null;
  quality_flag: string | null;
  quality_flags: string[];
  candidates: { label: string; display_name: string | null; score: number }[];
  confidence_band: string | null;
  calibrated: boolean;
  model_version: string;
  generated_at: string;
  is_demo: boolean;
  observation_id: string | null;
  error_code: string | null;
  retryable: boolean;
}

export interface UploadedImage {
  upload_id: string;
  filename: string;
  content_type: string;
  content_hash: string;
  width: number;
  height: number;
  quality_result: string;
  quality_flags: string[];
  preview_url: string;
}

export interface UploadDescriptor extends UploadedImage {
  size_bytes: number;
  quality_gate_version: string;
  created_at: string;
  is_demo: boolean;
}

export interface ReviewRequest {
  review_request_id: string;
  conversation_id: string;
  message_id: string;
  status: string;
  reason: string | null;
  submitted_at: string;
}

export interface Message {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  kind: string;
  text: string | null;
  client_message_id: string | null;
  observation_id: string | null;
  image: UploadedImage | null;
  assessment: Assessment | null;
  review_request: ReviewRequest | null;
  next_steps: string[];
  created_at: string;
  is_demo: boolean;
}

export interface Conversation {
  conversation_id: string;
  owner_id: string;
  title: string;
  created_at: string;
  last_message_at: string;
}

export interface SendResult {
  user_message: Message;
  assistant_message: Message;
}

/**
 * A reference to an image already uploaded through `POST /v1/uploads`.
 * Raw bytes never travel in the JSON message body.
 */
export interface ImageReference {
  uploadId: string;
  filename?: string;
  contentType?: string;
  contentHash?: string;
}

export interface SendMessageInput {
  clientMessageId: string;
  text?: string;
  image?: ImageReference;
}

export interface Health {
  status: string;
  service: string;
  version: string;
  environment: string;
  time: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string | null;
  request_id: string | null;
  retryable: boolean;
  fields: { field: string; message: string }[];
}

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails | null;

  constructor(status: number, problem: ProblemDetails | null) {
    super(problem?.title ?? `API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

export function apiBaseUrl(): string {
  // Server components must reach the API over the container network, while the
  // browser needs the public origin. API_BASE_URL is server-only.
  return (
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  );
}

/**
 * The browser-visible API origin. Unlike `apiBaseUrl()`, this never reads the
 * server-only `API_BASE_URL`, so an `<img>` rendered on the server and hydrated
 * in the browser resolves to the same host.
 */
export function publicApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

/** Turn a relative API path such as `/v1/uploads/up_x` into a browser URL. */
export function publicAssetUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const base = publicApiBaseUrl().replace(/\/$/, "");
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "X-Request-ID": crypto.randomUUID(),
      ...init.headers,
    },
  });

  if (!response.ok) {
    let problem: ProblemDetails | null = null;
    try {
      problem = (await response.json()) as ProblemDetails;
    } catch {
      problem = null;
    }
    throw new ApiError(response.status, problem);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/v1/conversations");
}

export function createConversation(title = "Photo assessment"): Promise<Conversation> {
  return request<Conversation>("/v1/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function getConversation(conversationId: string): Promise<Conversation> {
  return request<Conversation>(`/v1/conversations/${conversationId}`);
}

export function deleteConversation(conversationId: string): Promise<void> {
  return request<void>(`/v1/conversations/${conversationId}`, { method: "DELETE" });
}

export function listMessages(conversationId: string): Promise<Message[]> {
  return request<Message[]>(`/v1/conversations/${conversationId}/messages`);
}

export function sendMessage(
  conversationId: string,
  input: SendMessageInput,
): Promise<SendResult> {
  return request<SendResult>(`/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": input.clientMessageId,
    },
    body: JSON.stringify({
      client_message_id: input.clientMessageId,
      text: input.text ?? null,
      image: input.image
        ? {
            upload_id: input.image.uploadId,
            filename: input.image.filename ?? null,
            content_type: input.image.contentType ?? null,
            content_hash: input.image.contentHash ?? null,
          }
        : null,
    }),
  });
}

/**
 * Upload raw image bytes. The backend validates the declared type, the real
 * decode, the size ceiling and the demo quality gate before storing anything.
 * The returned `upload_id` is what the chat message references.
 */
export async function uploadImage(file: File): Promise<UploadDescriptor> {
  const form = new FormData();
  form.append("file", file, file.name);
  return request<UploadDescriptor>("/v1/uploads", {
    method: "POST",
    // Do not set Content-Type: the browser adds the multipart boundary.
    body: form,
  });
}

/**
 * Run the pretrained YOLO detector on an already-uploaded image.
 *
 * Demo-only: the backend always returns `is_demo: true`, and candidate names
 * carry an "unverified model label" marker until the taxonomy is approved. An
 * `abstained` state is not a healthy verdict.
 */
export function detectImage(
  uploadId: string,
  model: "pest" | "plant" = "plant",
): Promise<Assessment> {
  return request<Assessment>("/v1/detections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id: uploadId, model }),
  });
}

/**
 * Ask a human expert to review an assistant assessment. This is an audited,
 * separate request and never changes the stored prediction.
 */
export function requestReview(
  conversationId: string,
  messageId: string,
  reason?: string,
): Promise<ReviewRequest> {
  return request<ReviewRequest>(
    `/v1/conversations/${conversationId}/messages/${messageId}/review`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: reason ?? null }),
    },
  );
}

export function retryMessage(
  conversationId: string,
  messageId: string,
): Promise<Message> {
  return request<Message>(
    `/v1/conversations/${conversationId}/messages/${messageId}/retry`,
    { method: "POST" },
  );
}

/**
 * GIS layers are separate by design (spec 06 §7–§8). There is deliberately no
 * merged "risk" endpoint and the web client must never combine these values.
 */
export type MapLayerName =
  | "verified_reports"
  | "unverified_reports"
  | "modelled_risk"
  | "coverage"
  | "boundaries";

export interface MapLayer {
  type: "FeatureCollection";
  layer: MapLayerName;
  boundary_version: string;
  generated_at: string;
  aggregation_level: string;
  features: unknown[];
  empty: boolean;
  empty_message: string | null;
  small_count_suppression_applied: boolean;
}

export function getMapLayer(layer: MapLayerName): Promise<MapLayer> {
  return request<MapLayer>(`/v1/map/layers/${layer}`);
}

/* ------------------------------------------------------------------ */
/* Identity + admin (identity slice, in-memory)                        */
/*                                                                     */
/* The backend protects these routes with a bearer token. The browser   */
/* stores the current access/refresh pair in sessionStorage via         */
/* ``@/lib/auth`` and passes the access token explicitly. There is no    */
/* httpOnly cookie or CSRF handling in this scaffold — see Admin page   */
/* for the production warning.                                          */
/* ------------------------------------------------------------------ */

export type Role = "farmer" | "extension_worker" | "pathologist" | "agronomist" | "admin";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  refresh_expires_in: number;
  user_id: string;
  role: Role;
}

export interface LoginResponse {
  mfa_required: boolean;
  challenge_token: string | null;
  challenge_expires_in: number | null;
  tokens: TokenPair | null;
}

export interface UserSummary {
  user_id: string;
  kind: "farmer" | "staff";
  roles: Role[];
  status: "active" | "disabled" | "deleted";
  email: string | null;
  phone_masked: string | null;
  mfa_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfile extends UserSummary {
  phone: string | null;
  last_login_at: string | null;
}

export interface AdminUserDetail extends UserSummary {
  last_login_at: string | null;
  consent_complete: boolean | null;
  active_consents: string[];
}

export interface StaffProvisioned {
  user: UserSummary;
  mfa_secret: string | null;
  otpauth_uri: string | null;
  note: string;
}

export interface RetentionResult {
  expired_otp_challenges: number;
  expired_refresh_tokens: number;
  expired_mfa_challenges: number;
  note: string;
}

export interface AdminExportSummary {
  schema_version: "1.0";
  exported_at: string;
  purpose: string;
  row_limit: number;
  total_users: number;
  counts_by_role: Record<string, number>;
  counts_by_status: Record<string, number>;
  note: string;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

/** Staff login. Admins and MFA roles return `mfa_required` first. */
export function loginStaff(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

/** Complete the MFA step with a 6-digit TOTP code. */
export function verifyMfa(challenge: string, totp: string): Promise<TokenPair> {
  return request<TokenPair>("/v1/auth/mfa/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge, totp }),
  });
}

/**
 * Rotate the refresh token. The backend revokes the whole family on reuse,
 * so the caller must store the returned pair immediately.
 */
export function refreshTokens(refreshToken: string): Promise<TokenPair> {
  return request<TokenPair>("/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

/** End the current session. The caller must clear stored tokens. */
export function logoutSession(token: string): Promise<void> {
  return request<void>("/v1/auth/logout", {
    method: "POST",
    headers: authHeaders(token),
  });
}

/** The caller's own profile; proves whose token this is. */
export function getProfile(token: string): Promise<UserProfile> {
  return request<UserProfile>("/v1/me", { headers: authHeaders(token) });
}

/** All users. Admin role only; 401 without a token, 403 for non-admins. */
export function listAdminUsers(token: string): Promise<UserSummary[]> {
  return request<UserSummary[]>("/v1/admin/users", { headers: authHeaders(token) });
}

/** Provision a staff account. The MFA secret is shown once. */
export function provisionStaff(
  token: string,
  input: {
    email: string;
    password: string;
    roles: Role[];
    require_mfa: boolean;
    reason: string;
  },
): Promise<StaffProvisioned> {
  return request<StaffProvisioned>("/v1/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify(input),
  });
}

/**
 * One user detail. The `reason` (≥8 chars) is required and the backend
 * writes `admin.record_viewed` before returning the record.
 */
export function getAdminUser(
  token: string,
  userId: string,
  reason: string,
): Promise<AdminUserDetail> {
  const query = new URLSearchParams({ reason });
  return request<AdminUserDetail>(`/v1/admin/users/${userId}?${query}`, {
    headers: authHeaders(token),
  });
}

/** Replace staff roles. Staff-only, audited; cannot change own roles. */
export function updateAdminRoles(
  token: string,
  userId: string,
  roles: Role[],
  reason: string,
): Promise<UserSummary> {
  return request<UserSummary>(`/v1/admin/users/${userId}/roles`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ roles, reason }),
  });
}

/** Enable/disable a staff account. Cannot change own status. */
export function updateAdminStatus(
  token: string,
  userId: string,
  status: "active" | "disabled",
  reason: string,
): Promise<UserSummary> {
  return request<UserSummary>(`/v1/admin/users/${userId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ status, reason }),
  });
}

/** Purge expired OTP/refresh/MFA challenges. Reason ≥8 chars. */
export function runRetention(token: string, reason: string): Promise<RetentionResult> {
  return request<RetentionResult>("/v1/admin/maintenance/retention", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ reason }),
  });
}

/**
 * Aggregate identity counts (no names/emails/phones). `purpose` ≥8 chars.
 */
export function exportAggregates(
  token: string,
  purpose: string,
  rowLimit = 1000,
): Promise<AdminExportSummary> {
  return request<AdminExportSummary>("/v1/admin/exports", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ purpose, row_limit: rowLimit }),
  });
}
