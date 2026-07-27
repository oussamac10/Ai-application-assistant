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

// LOW_CONFIDENCE_THRESHOLD mirrors backend/app/field_detection/constants.py
export const LOW_CONFIDENCE_THRESHOLD = 0.4;
