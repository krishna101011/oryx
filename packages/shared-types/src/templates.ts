import type { ContentFormat } from './drafts';

export type ContentTone =
  | "formal"
  | "analytical"
  | "conversational"
  | "authoritative"
  | "concise";

export interface ContentTemplate {
  id: string;
  workspaceId: string;
  name: string;
  format: ContentFormat;
  tone: ContentTone;
  maxWords: number | null;
  minWords: number | null;
  structureHint: string | null;
  isDefault: boolean;
}

export interface CreateTemplateRequest {
  name: string;
  format: ContentFormat;
  tone?: ContentTone;
  maxWords?: number | null;
  minWords?: number | null;
  structureHint?: string | null;
}

export interface UpdateTemplateRequest {
  name?: string;
  tone?: ContentTone;
  maxWords?: number | null;
  minWords?: number | null;
  structureHint?: string | null;
}
