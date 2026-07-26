import { z } from "zod";

export const BoundingBoxSchema = z.object({
  x: z.number(),
  y: z.number(),
  width: z.number(),
  height: z.number(),
});

export type BoundingBox = z.infer<typeof BoundingBoxSchema>;

export const OcrWordSchema = z.object({
  text: z.string(),
  confidence: z.number(),
  boundingBox: BoundingBoxSchema,
});

export const OcrLineSchema = z.object({
  text: z.string(),
  confidence: z.number(),
  boundingBox: BoundingBoxSchema,
  words: z.array(OcrWordSchema),
});

export const OcrPageSchema = z.object({
  pageNumber: z.number(),
  width: z.number(),
  height: z.number(),
  text: z.string(),
  averageConfidence: z.number(),
  lines: z.array(OcrLineSchema),
});

export type OcrPage = z.infer<typeof OcrPageSchema>;

export const OcrResultResponseSchema = z.object({
  documentId: z.string(),
  status: z.string(),
  provider: z.string().nullable().optional(),
  language: z.string(),
  pageCount: z.number().nullable().optional(),
  pages: z.array(OcrPageSchema),
  errorCode: z.string().nullable().optional(),
  expiresAt: z.string(),
});

export type OcrResultResponse = z.infer<typeof OcrResultResponseSchema>;
