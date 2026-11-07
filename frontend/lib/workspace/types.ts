export type Role = "farmer" | "expert" | "agent" | "admin";

export type Health = "healthy" | "watch" | "diseased" | "pest" | "recovering";

export type Severity = "none" | "low" | "moderate" | "high" | "critical";

export type SyncState = "synced" | "queued" | "syncing" | "failed";

export type ReviewStatus =
  | "not_requested"
  | "pending"
  | "verified"
  | "corrected"
  | "rejected";

export type PlantPart =
  | "leaf"
  | "stem"
  | "root"
  | "fruit"
  | "flower"
  | "whole_plant";

export type RiskBand =
  | "low"
  | "moderate"
  | "high"
  | "urgent"
  | "insufficient";

export interface User {
  id: string;
  name: string;
  role: Role;
  phone: string;
  email: string;
  language: Language;
  village: string;
  district: string;
  organisation: string;
  initials: string;
}

export type Language = "en" | "hi" | "kn";

export interface MapPoint {
  x: number;
  y: number;
}

export interface Farm {
  id: string;
  name: string;
  ownerId: string;
  village: string;
  district: string;
  state: string;
  lat: number;
  lng: number;
  areaAcres: number;
  boundary: MapPoint[];
  createdAt: string;
  soil: string;
  irrigation: string;
}

export interface Section {
  id: string;
  name: string;
  areaAcres: number;
  cropGroupId: string | null;
  subSections?: string[];
}

export interface Plot {
  id: string;
  farmId: string;
  name: string;
  areaAcres: number;
  health: Health;
  sections: Section[];
  box: { x: number; y: number; w: number; h: number };
}

export interface CropGroup {
  id: string;
  farmId: string;
  plotId: string;
  sectionId: string | null;
  name: string;
  crop: string;
  variety: string;
  stage: string;
  plantedOn: string;
  areaAcres: number;
  health: Health;
}

export interface Plant {
  id: string;
  farmId: string;
  plotId: string;
  cropGroupId: string;
  code: string;
  label: string;
  health: Health;
  plantedOn: string;
  lastScouted: string;
  notes: string;
  mapPosition: MapPoint;
}

export interface DiagnosisAlternative {
  label: string;
  confidence: number;
}

export interface Analysis {
  id: string;
  farmId: string;
  farmName: string;
  subjectType: "plant" | "crop_group" | "farm";
  subjectId: string;
  subjectLabel: string;
  mediaType: "image" | "video";
  plantPart: PlantPart;
  createdAt: string;
  modelVersion: string;
  pest: string | null;
  disease: string | null;
  category: "pest" | "disease" | "nutrient" | "healthy" | "uncertain";
  symptoms: string[];
  affectedParts: PlantPart[];
  severity: Severity;
  confidenceBand: "low" | "medium" | "high" | "not_calibrated";
  confidenceScore: number;
  calibrated: boolean;
  causes: string[];
  alternatives: DiagnosisAlternative[];
  nextSteps: string[];
  reviewStatus: ReviewStatus;
  reviewer?: string;
  reviewerNote?: string;
  expertRecommendation?: string[];
  isDemo: boolean;
  imageTone: number;
  notes: string;
  imageUrl?: string;
}

export interface Capture {
  id: string;
  farmId: string;
  farmName: string;
  subjectId: string;
  subjectLabel: string;
  mediaType: "image" | "video";
  plantPart: PlantPart;
  notes: string;
  gps: { lat: number; lng: number };
  capturedAt: string;
  syncState: SyncState;
  imageTone: number;
  analysisId: string | null;
  imageUrl?: string;
}

export interface Inspection {
  id: string;
  farmId: string;
  farmName: string;
  title: string;
  type: "inspection" | "scouting" | "follow_up" | "treatment_check";
  crop: string;
  target: string;
  scheduledFor: string;
  assignee: string;
  status: "scheduled" | "in_progress" | "completed" | "overdue";
  notes: string;
  beforeTone: number | null;
  afterTone: number | null;
  treatment: string | null;
  effectiveness: number | null;
  recovery: number | null;
  failedTreatment: boolean;
  farmerReport: string | null;
}

export interface HotspotCase {
  id: string;
  pest: string;
  crop: string;
  district: string;
  village: string;
  x: number;
  y: number;
  reportedAt: string;
  severity: Severity;
  verified: boolean;
  cases: number;
}

export interface RiskRegion {
  id: string;
  district: string;
  crop: string;
  pest: string;
  band: RiskBand;
  x: number;
  y: number;
  coverage: "good" | "partial" | "low";
  reports: number;
  verified: number;
  updatedAt: string;
  horizon: string;
}

export interface Notification {
  id: string;
  title: string;
  body: string;
  kind: "alert" | "reminder" | "review" | "system";
  at: string;
  read: boolean;
  href: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  imageTone?: number;
  analysisId?: string;
  at: string;
}

export interface ChatThread {
  id: string;
  title: string;
  farmId: string | null;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface WorkspaceState {
  currentUser: User;
  users: User[];
  farms: Farm[];
  plots: Plot[];
  cropGroups: CropGroup[];
  plants: Plant[];
  analyses: Analysis[];
  captures: Capture[];
  inspections: Inspection[];
  cases: HotspotCase[];
  riskRegions: RiskRegion[];
  notifications: Notification[];
  threads: ChatThread[];
}
