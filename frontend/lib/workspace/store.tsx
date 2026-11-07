"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { detectImage, uploadImage, type Assessment } from "@/lib/api";

import { seedState } from "./seed";
import type {
  Analysis,
  Capture,
  ChatMessage,
  ChatThread,
  Farm,
  Health,
  Inspection,
  Language,
  Plant,
  PlantPart,
  ReviewStatus,
  Role,
  Severity,
  User,
  WorkspaceState,
} from "./types";

const STORAGE_KEY = "ps03.workspace.v1";

function newId(prefix: string): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10);
  return `${prefix}-${random}`;
}

function now(): string {
  return new Date().toISOString();
}

interface NewFarmInput {
  name: string;
  village: string;
  district: string;
  areaAcres: number;
  crop: string;
  variety: string;
  lat: number;
  lng: number;
  soil: string;
  irrigation: string;
}

interface NewCaptureInput {
  farmId: string;
  subjectId: string;
  subjectLabel: string;
  mediaType: "image" | "video";
  plantPart: PlantPart;
  notes: string;
  gps: { lat: number; lng: number };
  imageTone: number;
  imageUrl?: string;
}

interface NewInspectionInput {
  farmId: string;
  title: string;
  type: Inspection["type"];
  crop: string;
  target: string;
  scheduledFor: string;
  assignee: string;
  notes: string;
  farmerReport?: string | null;
}

interface ReviewInput {
  verdict: Exclude<ReviewStatus, "not_requested" | "pending">;
  correctedLabel?: string;
  note: string;
  recommendations: string[];
}

interface WorkspaceContextValue {
  state: WorkspaceState;
  role: Role;
  setRole: (role: Role) => void;
  signIn: (role: Role) => void;
  updateProfile: (patch: Partial<Pick<User, "name" | "phone" | "email" | "village" | "district">>) => void;
  setLanguage: (language: Language) => void;
  addFarm: (input: NewFarmInput) => Farm;
  addPlot: (farmId: string, name: string, areaAcres: number) => void;
  addCropGroup: (
    farmId: string,
    plotId: string,
    sectionId: string | null,
    crop: string,
    variety: string,
    areaAcres: number,
  ) => void;
  addPlant: (farmId: string, plotId: string, cropGroupId: string, label: string) => void;
  updatePlant: (plantId: string, patch: Partial<Plant>) => void;
  addCapture: (input: NewCaptureInput) => Capture;
  syncCaptures: () => void;
  createAnalysis: (captureId: string) => Promise<Analysis | null>;
  requestVerification: (analysisId: string) => void;
  resolveReview: (analysisId: string, input: ReviewInput) => void;
  newThread: (title: string) => string;
  sendChat: (threadId: string, text: string, imageTone?: number) => void;
  scheduleInspection: (input: NewInspectionInput) => void;
  updateInspection: (inspectionId: string, patch: Partial<Inspection>) => void;
  markNotificationRead: (notificationId: string) => void;
  markAllNotificationsRead: () => void;
  resetDemo: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function replaceById<T extends { id: string }>(items: T[], id: string, patch: Partial<T>): T[] {
  return items.map((item) => (item.id === id ? { ...item, ...patch } : item));
}

function has(text: string, ...needles: string[]): boolean {
  const lower = text.toLowerCase();
  return needles.some((needle) => lower.includes(needle));
}

function assistantReply(text: string, state: WorkspaceState): ChatMessage {
  const farm = state.farms[0];
  const pending = state.analyses.filter((item) => item.reviewStatus === "pending").length;
  const lower = text.toLowerCase();
  let reply: string;

  if (has(lower, "why", "cause", "appear")) {
    reply =
      "Several local factors can explain this pattern: recent warm nights and humid canopy conditions favour pest and disease build-up, while dense growth hides early damage. Check whether the affected block has had rain, overhead irrigation or new growth in the last week. This is context from your farm records, not a confirmed cause.";
  } else if (has(lower, "biological", "natural enemy", "predator")) {
    reply =
      "Biological options centre on conserving natural enemies such as predatory mites, lady beetles and pirate bugs, plus monitoring with sticky or pheromone traps. Any product name, dose or interval must come from your approved local advisory or extension officer. I can prepare a scouting summary with your recent observations for that conversation.";
  } else if (has(lower, "chemical", "spray", "pesticide", "fungicide")) {
    reply =
      "I cannot recommend chemical products, doses or intervals. That decision needs an approved local advisory and, for uncertain cases, expert verification. The safer next step is to record the affected area, inspect a sample of plants and request expert review. I can attach your latest photo and notes to the request.";
  } else if (has(lower, "prevent", "avoid", "stop")) {
    reply =
      "Prevention starts with field hygiene: remove and bag severely affected material, keep tools separate between blocks, avoid evening overhead irrigation, and scout new growth twice a week. Compare the same plants after five to seven days so you can see whether the situation is improving or spreading.";
  } else if (has(lower, "control", "manage", "treatment", "next")) {
    reply =
      "A safe sequence is: confirm what part of the plant is affected, inspect ten plants across the block, compare with the approved advisory, and escalate uncertain or fast-spreading cases to an expert. If you add a photo, I can attach it to an assistive photo assessment.";
  } else if (has(lower, "crop", "tomato", "chilli", "mango", "maize", "brinjal", "cowpea")) {
    reply =
      "For crop-specific management, the key is to match the symptom to the crop stage. In your records, the highest-priority block is Tomato Block A1 with possible pinworm damage, followed by Tomato Block V1 with possible late blight. Both need field inspection, not an automatic spray decision.";
  } else if (pending > 0) {
    reply = `Thanks. I can see ${pending} observation${pending === 1 ? "" : "s"} awaiting expert verification. If you are asking about a recent photo, open AI analysis and request verification so an extension worker can confirm or correct the automated comparison.`;
  } else {
    reply =
      "I can help you interpret a photo, compare an observation with your farm records, and prepare questions for an extension worker. I will not confirm a diagnosis or recommend a product dose. Tell me the crop, the plant part and what you see.";
  }

  if (farm && !has(lower, "hello", "hi")) {
    reply += ` Context used: ${farm.name}, ${state.plots.filter((plot) => plot.farmId === farm.id).length} plots on record.`;
  }

  return {
    id: newId("msg"),
    role: "assistant",
    text: reply,
    at: now(),
  };
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WorkspaceState>(seedState);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as WorkspaceState;
        if (parsed && parsed.currentUser && parsed.farms) {
          // One-time hydration from localStorage after mount. A lazy initializer
          // would mismatch the server-rendered seed state.
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setState(parsed);
        }
      }
    } catch {
      // A corrupt local cache must not block the demo; fall back to seed.
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Storage can be full or blocked; the in-memory state still works.
    }
  }, [state, hydrated]);

  const setRole = useCallback((role: Role) => {
    setState((current) => {
      const user = current.users.find((item) => item.role === role);
      return user ? { ...current, currentUser: user } : current;
    });
  }, []);

  const signIn = useCallback((role: Role) => {
    setState((current) => {
      const user = current.users.find((item) => item.role === role);
      return user ? { ...current, currentUser: user } : current;
    });
  }, []);

  const updateProfile = useCallback<WorkspaceContextValue["updateProfile"]>((patch) => {
    setState((current) => {
      const updated = { ...current.currentUser, ...patch };
      updated.initials = updated.name
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? "")
        .join("");
      return {
        ...current,
        currentUser: updated,
        users: current.users.map((user) => (user.id === updated.id ? updated : user)),
      };
    });
  }, []);

  const setLanguage = useCallback((language: Language) => {
    setState((current) => ({
      ...current,
      currentUser: { ...current.currentUser, language },
    }));
  }, []);

  const addFarm = useCallback<WorkspaceContextValue["addFarm"]>((input) => {
    const farmId = newId("farm");
    const plotId = newId("plot");
    const sectionId = newId("sec");
    const cropGroupId = newId("cg");
    const farm: Farm = {
      id: farmId,
      name: input.name,
      ownerId: "usr-farmer-1",
      village: input.village,
      district: input.district,
      state: "Tamil Nadu",
      lat: input.lat,
      lng: input.lng,
      areaAcres: input.areaAcres,
      boundary: [
        { x: 6, y: 6 },
        { x: 92, y: 4 },
        { x: 95, y: 94 },
        { x: 4, y: 92 },
      ],
      createdAt: now(),
      soil: input.soil,
      irrigation: input.irrigation,
    };
    setState((current) => ({
      ...current,
      farms: [farm, ...current.farms],
      plots: [
        {
          id: plotId,
          farmId,
          name: "Main Plot",
          areaAcres: input.areaAcres,
          health: "healthy",
          box: { x: 10, y: 12, w: 76, h: 72 },
          sections: [
            { id: sectionId, name: "Section 1", areaAcres: input.areaAcres, cropGroupId },
          ],
        },
        ...current.plots,
      ],
      cropGroups: [
        {
          id: cropGroupId,
          farmId,
          plotId,
          sectionId,
          name: `${input.crop} Block 1`,
          crop: input.crop,
          variety: input.variety,
          stage: "Vegetative",
          plantedOn: new Date().toISOString().slice(0, 10),
          areaAcres: input.areaAcres,
          health: "healthy",
        },
        ...current.cropGroups,
      ],
      notifications: [
        {
          id: newId("notif"),
          title: "Farm added",
          body: `${input.name} is ready. Add plots and plants to start scouting.`,
          kind: "system",
          at: now(),
          read: false,
          href: `/farms/${farmId}`,
        },
        ...current.notifications,
      ],
    }));
    return farm;
  }, []);

  const addPlot = useCallback<WorkspaceContextValue["addPlot"]>((farmId, name, areaAcres) => {
    setState((current) => {
      const index = current.plots.filter((plot) => plot.farmId === farmId).length;
      const boxes = [
        { x: 8, y: 10, w: 38, h: 34 },
        { x: 54, y: 10, w: 38, h: 34 },
        { x: 8, y: 54, w: 38, h: 34 },
        { x: 54, y: 54, w: 38, h: 34 },
      ];
      const box = boxes[index % boxes.length] ?? boxes[0]!;
      return {
        ...current,
        plots: [
          ...current.plots,
          {
            id: newId("plot"),
            farmId,
            name,
            areaAcres,
            health: "healthy",
            box,
            sections: [
              { id: newId("sec"), name: "Section 1", areaAcres, cropGroupId: null },
            ],
          },
        ],
      };
    });
  }, []);

  const addCropGroup = useCallback<WorkspaceContextValue["addCropGroup"]>(
    (farmId, plotId, sectionId, crop, variety, areaAcres) => {
      const id = newId("cg");
      setState((current) => ({
        ...current,
        cropGroups: [
          ...current.cropGroups,
          {
            id,
            farmId,
            plotId,
            sectionId,
            name: `${crop} Block ${current.cropGroups.length + 1}`,
            crop,
            variety,
            stage: "Vegetative",
            plantedOn: new Date().toISOString().slice(0, 10),
            areaAcres,
            health: "healthy",
          },
        ],
        plots: current.plots.map((plot) =>
          plot.id === plotId
            ? {
                ...plot,
                sections: plot.sections.map((section) =>
                  section.id === sectionId ? { ...section, cropGroupId: id } : section,
                ),
              }
            : plot,
        ),
      }));
    },
    [],
  );

  const addPlant = useCallback<WorkspaceContextValue["addPlant"]>(
    (farmId, plotId, cropGroupId, label) => {
      setState((current) => {
        const number = current.plants.filter((plant) => plant.cropGroupId === cropGroupId).length + 1;
        const crop = current.cropGroups.find((group) => group.id === cropGroupId)?.crop ?? "PLT";
        const code = `${crop.slice(0, 3).toUpperCase()}-${String(number).padStart(3, "0")}`;
        return {
          ...current,
          plants: [
            ...current.plants,
            {
              id: newId("plant"),
              farmId,
              plotId,
              cropGroupId,
              code,
              label: label || `${crop} plant ${number}`,
              health: "healthy",
              plantedOn: new Date().toISOString().slice(0, 10),
              lastScouted: new Date().toISOString().slice(0, 10),
              notes: "",
              mapPosition: {
                x: 10 + ((number * 13) % 80),
                y: 14 + ((number * 17) % 70),
              },
            },
          ],
        };
      });
    },
    [],
  );

  const updatePlant = useCallback<WorkspaceContextValue["updatePlant"]>((plantId, patch) => {
    setState((current) => ({ ...current, plants: replaceById(current.plants, plantId, patch) }));
  }, []);

  const addCapture = useCallback<WorkspaceContextValue["addCapture"]>((input) => {
    const farm = state.farms.find((item) => item.id === input.farmId);
    const capture: Capture = {
      id: newId("cap"),
      farmId: input.farmId,
      farmName: farm?.name ?? "Farm",
      subjectId: input.subjectId,
      subjectLabel: input.subjectLabel,
      mediaType: input.mediaType,
      plantPart: input.plantPart,
      notes: input.notes,
      gps: input.gps,
      capturedAt: now(),
      syncState: "queued",
      imageTone: input.imageTone,
      analysisId: null,
      imageUrl: input.imageUrl,
    };
    setState((current) => ({
      ...current,
      captures: [capture, ...current.captures],
      notifications: [
        {
          id: newId("notif"),
          title: "Capture saved offline",
          body: `${input.subjectLabel} (${input.mediaType}) is queued for sync.`,
          kind: "system",
          at: now(),
          read: false,
          href: "/scan",
        },
        ...current.notifications,
      ],
    }));
    return capture;
  }, [state.farms]);

  const syncCaptures = useCallback(() => {
    setState((current) => ({
      ...current,
      captures: current.captures.map((capture) =>
        capture.syncState === "synced" ? capture : { ...capture, syncState: "synced" },
      ),
    }));
  }, []);

  const createAnalysis = useCallback<WorkspaceContextValue["createAnalysis"]>(async (captureId) => {
    const capture = state.captures.find((item) => item.id === captureId);
    if (!capture) {
      return null;
    }
    const farm = state.farms.find((item) => item.id === capture.farmId);
    const group = state.cropGroups.find((item) => item.id === capture.subjectId);
    const crop = group?.crop ?? "Tomato";
    const video = capture.mediaType === "video";

    // Run the real pretrained detector when the capture has image bytes. The
    // result is always demo-labelled by the API; an abstention is not a healthy
    // verdict and must never fall back to an invented template diagnosis.
    const attempted = !video && Boolean(capture.imageUrl);
    let detection: Assessment | null = null;
    if (attempted && capture.imageUrl) {
      try {
        const blob = await fetch(capture.imageUrl).then((response) => response.blob());
        const file = new File([blob], "capture.jpg", {
          type: blob.type || "image/jpeg",
        });
        const uploaded = await uploadImage(file);
        detection = await detectImage(uploaded.upload_id, "plant");
      } catch {
        detection = null;
      }
    }
    const primary = detection?.state === "assessed" ? detection.candidates[0] : undefined;
    const modelAlternatives =
      detection?.state === "assessed"
        ? detection.candidates.slice(1).map((candidate) => ({
            label: candidate.display_name ?? candidate.label,
            confidence: Math.round(candidate.score * 100),
          }))
        : [];

    const templates: Record<
      string,
      Pick<Analysis, "pest" | "disease" | "category" | "symptoms" | "causes" | "alternatives" | "nextSteps" | "severity">
    > = {
      Tomato: {
        pest: "South American tomato pinworm",
        disease: null,
        category: "pest",
        symptoms: ["Irregular leaf mines", "Dark frass near growing tips", "Pinhole fruit damage"],
        causes: ["Warm nights", "Dense canopy", "No pheromone traps"],
        alternatives: [
          { label: "Tomato leaf miner", confidence: 18 },
          { label: "Early blight leaf damage", confidence: 9 },
        ],
        nextSteps: [
          "Inspect 10 plants across the block",
          "Photograph the same plant again in 5 days",
          "Request expert verification before any treatment decision",
        ],
        severity: "high",
      },
      Chilli: {
        pest: "Thrips",
        disease: null,
        category: "pest",
        symptoms: ["Curled new leaves", "Silvery leaf underside", "Stunted tip"],
        causes: ["Dry spell", "Weed hosts along the bund"],
        alternatives: [{ label: "Mite damage", confidence: 21 }],
        nextSteps: ["Use sticky traps", "Check 20 growing tips", "Request expert review if spreading"],
        severity: "low",
      },
      Mango: {
        pest: "Mango leaf hopper",
        disease: null,
        category: "pest",
        symptoms: ["Adults on new shoots", "Honeydew and sooty mould", "Curling tender leaves"],
        causes: ["New flush", "Orchard floor weeds"],
        alternatives: [{ label: "Mango mealybug", confidence: 14 }],
        nextSteps: ["Prune infested shoots", "Conserve predators", "Repeat the assessment in 7 days"],
        severity: "moderate",
      },
      Maize: {
        pest: "Fall armyworm",
        disease: null,
        category: "pest",
        symptoms: ["Ragged whorl feeding", "Moist frass in the whorl"],
        causes: ["Warm weather", "Continuous maize planting"],
        alternatives: [{ label: "Stem borer", confidence: 16 }],
        nextSteps: ["Scout 20 whorls", "Check neighbouring plots", "Request expert verification"],
        severity: "high",
      },
    };
    const fallback = templates.Tomato!;
    const template = templates[crop] ?? fallback;
    const analysis: Analysis = {
      id: newId("ana"),
      farmId: capture.farmId,
      farmName: farm?.name ?? capture.farmName,
      subjectType: group ? "crop_group" : "plant",
      subjectId: capture.subjectId,
      subjectLabel: capture.subjectLabel,
      mediaType: capture.mediaType,
      plantPart: capture.plantPart,
      createdAt: now(),
      modelVersion: attempted
        ? (detection?.model_version ?? "pretrained-yolo-0.1")
        : video
          ? "video-0.2.0"
          : "photo-0.3.1",
      pest: null,
      disease: attempted
        ? (primary?.display_name ?? primary?.label ?? null)
        : video
          ? "Possible nutrient deficiency"
          : template.disease,
      category: attempted ? "uncertain" : video ? "nutrient" : template.category,
      symptoms: attempted
        ? []
        : video
          ? ["Variable leaf colour across frames", "No clear fungal lesion in sampled frames"]
          : template.symptoms,
      affectedParts: attempted
        ? [capture.plantPart]
        : video
          ? ["leaf", "whole_plant"]
          : [capture.plantPart, "leaf"],
      severity: attempted ? "none" : video ? "low" : (template.severity as Severity),
      confidenceBand: attempted ? "not_calibrated" : video ? "low" : "medium",
      confidenceScore: attempted
        ? primary
          ? Math.round(primary.score * 100)
          : 0
        : video
          ? 52
          : 69,
      calibrated: false,
      causes: attempted ? [] : video
        ? ["Insufficient close-up frames", "Possible nutrient or water stress"]
        : template.causes,
      alternatives: attempted
        ? modelAlternatives
        : video
          ? [{ label: "Waterlogging stress", confidence: 22 }]
          : template.alternatives,
      nextSteps: attempted
        ? primary
          ? [
              "Retake the same plant in 5 days",
              "Request expert verification before any treatment decision",
            ]
          : [
              "The model found no confident match. Retake in good light or request expert review.",
            ]
        : video
          ? [
              "Capture 10-second close-ups of affected leaves",
              "Take a soil sample if the patch is uniform",
              "Request expert review before adding nutrients",
            ]
          : template.nextSteps,
      reviewStatus: "not_requested",
      isDemo: true,
      imageTone: capture.imageTone,
      notes: capture.notes,
      imageUrl: capture.imageUrl,
    };
    setState((current) => ({
      ...current,
      analyses: [analysis, ...current.analyses],
      captures: current.captures.map((item) =>
        item.id === captureId ? { ...item, analysisId: analysis.id } : item,
      ),
      notifications: [
        {
          id: newId("notif"),
          title: "Photo assessment ready",
          body: analysis.pest ?? analysis.disease
            ? `${analysis.subjectLabel}: possible ${analysis.pest ?? analysis.disease}. This is assistive, not a diagnosis.`
            : `${analysis.subjectLabel}: no confident match. This is assistive, not a diagnosis.`,
          kind: "review",
          at: now(),
          read: false,
          href: "/analysis",
        },
        ...current.notifications,
      ],
    }));
    return analysis;
  }, [state.captures, state.cropGroups, state.farms]);

  const requestVerification = useCallback<WorkspaceContextValue["requestVerification"]>((analysisId) => {
    setState((current) => ({
      ...current,
      analyses: current.analyses.map((analysis) =>
        analysis.id === analysisId ? { ...analysis, reviewStatus: "pending" } : analysis,
      ),
      notifications: [
        {
          id: newId("notif"),
          title: "Verification requested",
          body: "An extension worker will review the photo assessment.",
          kind: "review",
          at: now(),
          read: false,
          href: "/expert",
        },
        ...current.notifications,
      ],
    }));
  }, []);

  const resolveReview = useCallback<WorkspaceContextValue["resolveReview"]>((analysisId, input) => {
    setState((current) => {
      const target = current.analyses.find((analysis) => analysis.id === analysisId);
      return {
        ...current,
        analyses: current.analyses.map((analysis) => {
          if (analysis.id !== analysisId) {
            return analysis;
          }
          const corrected = input.verdict === "corrected" && input.correctedLabel;
          return {
            ...analysis,
            reviewStatus: input.verdict,
            reviewer: current.currentUser.name,
            reviewerNote: input.note,
            expertRecommendation: input.recommendations,
            pest: corrected ? null : analysis.pest,
            disease: corrected ? input.correctedLabel ?? analysis.disease : analysis.disease,
            category: corrected ? "disease" : analysis.category,
          };
        }),
        notifications: [
          {
            id: newId("notif"),
            title: "Expert review recorded",
            body: `${target?.subjectLabel ?? "Assessment"} marked ${input.verdict}.`,
            kind: "review",
            at: now(),
            read: false,
            href: "/analysis",
          },
          ...current.notifications,
        ],
      };
    });
  }, []);

  const newThread = useCallback<WorkspaceContextValue["newThread"]>((title) => {
    const thread: ChatThread = {
      id: newId("thread"),
      title,
      farmId: state.farms[0]?.id ?? null,
      updatedAt: now(),
      messages: [],
    };
    setState((current) => ({ ...current, threads: [thread, ...current.threads] }));
    return thread.id;
  }, [state.farms]);

  const sendChat = useCallback<WorkspaceContextValue["sendChat"]>((threadId, text, imageTone) => {
    setState((current) => {
      const thread = current.threads.find((item) => item.id === threadId);
      if (!thread) {
        return current;
      }
      const userMessage: ChatMessage = {
        id: newId("msg"),
        role: "user",
        text,
        imageTone,
        at: now(),
      };
      const reply = assistantReply(text, current);
      return {
        ...current,
        threads: current.threads.map((item) =>
          item.id === threadId
            ? {
                ...item,
                updatedAt: reply.at,
                messages: [...item.messages, userMessage, reply],
              }
            : item,
        ),
      };
    });
  }, []);

  const scheduleInspection = useCallback<WorkspaceContextValue["scheduleInspection"]>((input) => {
    const farm = state.farms.find((item) => item.id === input.farmId);
    setState((current) => ({
      ...current,
      inspections: [
        {
          id: newId("insp"),
          farmId: input.farmId,
          farmName: farm?.name ?? "Farm",
          title: input.title,
          type: input.type,
          crop: input.crop,
          target: input.target,
          scheduledFor: input.scheduledFor,
          assignee: input.assignee,
          status: "scheduled",
          notes: input.notes,
          beforeTone: null,
          afterTone: null,
          treatment: null,
          effectiveness: null,
          recovery: null,
          failedTreatment: false,
          farmerReport: input.farmerReport ?? null,
        },
        ...current.inspections,
      ],
      notifications: [
        {
          id: newId("notif"),
          title: "Inspection scheduled",
          body: `${input.title} on ${new Date(input.scheduledFor).toLocaleDateString()}.`,
          kind: "reminder",
          at: now(),
          read: false,
          href: "/monitoring",
        },
        ...current.notifications,
      ],
    }));
  }, [state.farms]);

  const updateInspection = useCallback<WorkspaceContextValue["updateInspection"]>(
    (inspectionId, patch) => {
      setState((current) => ({
        ...current,
        inspections: replaceById(current.inspections, inspectionId, patch),
      }));
    },
    [],
  );

  const markNotificationRead = useCallback<WorkspaceContextValue["markNotificationRead"]>((id) => {
    setState((current) => ({
      ...current,
      notifications: replaceById(current.notifications, id, { read: true }),
    }));
  }, []);

  const markAllNotificationsRead = useCallback(() => {
    setState((current) => ({
      ...current,
      notifications: current.notifications.map((item) => ({ ...item, read: true })),
    }));
  }, []);

  const resetDemo = useCallback(() => {
    setState(seedState);
  }, []);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      state,
      role: state.currentUser.role,
      setRole,
      signIn,
      updateProfile,
      setLanguage,
      addFarm,
      addPlot,
      addCropGroup,
      addPlant,
      updatePlant,
      addCapture,
      syncCaptures,
      createAnalysis,
      requestVerification,
      resolveReview,
      newThread,
      sendChat,
      scheduleInspection,
      updateInspection,
      markNotificationRead,
      markAllNotificationsRead,
      resetDemo,
    }),
    [
      state,
      setRole,
      signIn,
      updateProfile,
      setLanguage,
      addFarm,
      addPlot,
      addCropGroup,
      addPlant,
      updatePlant,
      addCapture,
      syncCaptures,
      createAnalysis,
      requestVerification,
      resolveReview,
      newThread,
      sendChat,
      scheduleInspection,
      updateInspection,
      markNotificationRead,
      markAllNotificationsRead,
      resetDemo,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used inside WorkspaceProvider");
  }
  return context;
}

export function healthLabel(health: Health): string {
  switch (health) {
    case "healthy":
      return "Healthy";
    case "watch":
      return "Watch";
    case "diseased":
      return "Disease signs";
    case "pest":
      return "Pest signs";
    case "recovering":
      return "Recovering";
  }
}

export function healthTone(health: Health): string {
  switch (health) {
    case "healthy":
      return "ok";
    case "watch":
      return "warn";
    case "diseased":
      return "bad";
    case "pest":
      return "alert";
    case "recovering":
      return "info";
  }
}

export function severityTone(severity: Severity): string {
  switch (severity) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "moderate":
      return "moderate";
    case "low":
      return "low";
    case "none":
      return "ok";
  }
}

export function cropGroupHealth(state: WorkspaceState, groupId: string): Health {
  const plants = state.plants.filter((plant) => plant.cropGroupId === groupId);
  if (plants.some((plant) => plant.health === "pest")) return "pest";
  if (plants.some((plant) => plant.health === "diseased")) return "diseased";
  if (plants.some((plant) => plant.health === "recovering")) return "recovering";
  if (plants.some((plant) => plant.health === "watch")) return "watch";
  return state.cropGroups.find((group) => group.id === groupId)?.health ?? "healthy";
}
