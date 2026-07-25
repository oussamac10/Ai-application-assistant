import { z } from "zod";

export const DocumentAnalysisSummarySchema = z.object({
  pageCount: z.number(),
  documentType: z.string(),
  hasNativeText: z.boolean(),
  hasAcroForm: z.boolean(),
  hasEmbeddedImages: z.boolean(),
  isProbablyScanned: z.boolean(),
  matchedTemplate: z
    .object({
      templateKey: z.string(),
      formKey: z.string(),
      formVersion: z.number(),
    })
    .nullable(),
  nextStep: z.string(),
});

export type DocumentAnalysisSummary = z.infer<typeof DocumentAnalysisSummarySchema>;

export const DocumentUploadResponseSchema = z.object({
  documentId: z.string(),
  ownershipToken: z.string().nullable().optional(),
  status: z.string(),
  analysis: DocumentAnalysisSummarySchema.nullable().optional(),
  expiresAt: z.string(),
});

export type DocumentUploadResponse = z.infer<typeof DocumentUploadResponseSchema>;

export const DocumentRetrieveResponseSchema = z.object({
  documentId: z.string(),
  status: z.string(),
  analysis: DocumentAnalysisSummarySchema.nullable().optional(),
  expiresAt: z.string(),
});

export type DocumentRetrieveResponse = z.infer<typeof DocumentRetrieveResponseSchema>;

export const SessionCreateResponseSchema = z.object({
  sessionId: z.string(),
  ownershipToken: z.string(),
  status: z.string(),
});

export type SessionCreateResponse = z.infer<typeof SessionCreateResponseSchema>;
