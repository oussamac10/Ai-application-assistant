import { z } from "zod";

export const BoundingBoxSchema = z.object({
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
});

export type BoundingBox = z.infer<typeof BoundingBoxSchema>;

export const DetectedFieldOptionSchema = z.object({
  value: z.string(),
  position: z.number(),
});

export const FIELD_TYPES = [
  "text",
  "multiline_text",
  "date",
  "email",
  "phone",
  "address",
  "number",
  "currency",
  "checkbox",
  "radio",
  "select",
  "multiple_choice",
  "signature",
  "unknown",
] as const;

export const DetectedFieldSchema = z.object({
  fieldId: z.string(),
  pageNumber: z.number(),
  label: z.string(),
  normalizedName: z.string(),
  fieldType: z.string(),
  required: z.boolean().nullable().optional(),
  multiple: z.boolean(),
  confidence: z.number(),
  source: z.string(),
  labelBoundingBox: BoundingBoxSchema.nullable().optional(),
  inputBoundingBox: BoundingBoxSchema.nullable().optional(),
  options: z.array(DetectedFieldOptionSchema).default([]),
  existingValue: z.string().nullable().optional(),
  reviewStatus: z.string(),
});

export type DetectedField = z.infer<typeof DetectedFieldSchema>;

export const FieldDetectionResultResponseSchema = z.object({
  documentId: z.string(),
  status: z.string(),
  provider: z.string().nullable().optional(),
  sourceType: z.string().nullable().optional(),
  fieldCount: z.number().nullable().optional(),
  averageConfidence: z.number().nullable().optional(),
  fields: z.array(DetectedFieldSchema).default([]),
  errorCode: z.string().nullable().optional(),
  expiresAt: z.string(),
});

export type FieldDetectionResultResponse = z.infer<typeof FieldDetectionResultResponseSchema>;

export const SessionCreateResponseSchema = z.object({
  sessionId: z.string(),
  ownershipToken: z.string(),
  status: z.string(),
});

export type SessionCreateResponse = z.infer<typeof SessionCreateResponseSchema>;

// Phase 13 — plain-language-safe response for the automatic
// upload-to-questions orchestration endpoint. Deliberately has no
// confidence/provider/field-key fields: the normal-user flow never reads
// them, only debug/admin tooling (FieldDetectionResultResponse above) does.
export const UncertaintyInfoSchema = z.object({
  hasUncertainFields: z.boolean(),
  uncertainFieldCount: z.number(),
});

export type UncertaintyInfo = z.infer<typeof UncertaintyInfoSchema>;

export const PrepareQuestionsResponseSchema = z.object({
  documentId: z.string(),
  status: z.enum(["ready", "needs_clarification", "failed"]),
  sessionId: z.string().nullable().optional(),
  ownershipToken: z.string().nullable().optional(),
  reusedExistingSession: z.boolean().default(false),
  uncertainty: UncertaintyInfoSchema.nullable().optional(),
  // Populated only when status === "failed" — a stable machine-readable
  // code (never a raw exception message) and which processing step failed.
  errorCode: z.string().nullable().optional(),
  stage: z.string().nullable().optional(),
});

export type PrepareQuestionsResponse = z.infer<typeof PrepareQuestionsResponseSchema>;

// LOW_CONFIDENCE_THRESHOLD mirrors backend/app/field_detection/constants.py
export const LOW_CONFIDENCE_THRESHOLD = 0.4;
