import { adminRequest } from "./httpClient";
import type { KnowledgeSource, KnowledgeSourceStatus, PaginatedResult } from "@/types/admin";

export const KNOWLEDGE_API_ENDPOINTS = {
  upload: "/api/v1/admin/knowledge/upload",
  createFromUrl: "/api/v1/admin/knowledge/url",
  listSources: "/api/v1/admin/knowledge/sources",
  sourceById: (id: string) => `/api/v1/admin/knowledge/sources/${encodeURIComponent(id)}`,
  sourceStatus: (id: string) => `/api/v1/admin/knowledge/sources/${encodeURIComponent(id)}/status`,
  sourceReprocess: (id: string) => `/api/v1/admin/knowledge/sources/${encodeURIComponent(id)}/reprocess`,
  sourceLabel: (id: string) => `/api/v1/admin/knowledge/sources/${encodeURIComponent(id)}/label`,
  bulkDelete: "/api/v1/admin/knowledge/sources/bulk-delete",
  bulkReprocess: "/api/v1/admin/knowledge/sources/bulk-reprocess"
} as const;

export interface GetKnowledgeSourcesParams {
  page?: number;
  pageSize?: number;
  domain?: string;
  label?: string;
  search?: string;
  status?: string;
  type?: string;
}

export interface CreateKnowledgeSourceFromUrlPayload {
  url: string;
  domain: string;
  label: string;
  tags: string[];
}

interface KnowledgeSourceDto {
  id: string;
  name: string;
  type: KnowledgeSource["type"];
  domain: string;
  label: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  status: KnowledgeSource["status"];
  total_chunks: number;
  embedded_chunks: number;
  indexing_completed: boolean;
  error_message?: string;
}

interface IngestionStepStatusDto {
  step: string;
  status: string;
  message?: string;
  progress?: number;
  started_at?: string;
  completed_at?: string;
}

interface KnowledgeSourceStatusDto {
  source_id: string;
  status: string;
  steps: IngestionStepStatusDto[];
  total_chunks: number;
  embedded_chunks: number;
  indexing_completed: boolean;
  last_updated_at: string;
}

interface PaginatedKnowledgeSourceDto {
  items: KnowledgeSourceDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

function toKnowledgeSource(dto: KnowledgeSourceDto): KnowledgeSource {
  return {
    id: dto.id,
    name: dto.name,
    type: dto.type,
    domain: dto.domain,
    label: dto.label,
    tags: dto.tags ?? [],
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    status: dto.status,
    totalChunks: dto.total_chunks ?? 0,
    embeddedChunks: dto.embedded_chunks ?? 0,
    indexingCompleted: Boolean(dto.indexing_completed),
    errorMessage: dto.error_message
  };
}

function toKnowledgeSourceStatus(dto: KnowledgeSourceStatusDto): KnowledgeSourceStatus {
  return {
    sourceId: dto.source_id,
    status: dto.status as KnowledgeSourceStatus["status"],
    steps: (dto.steps ?? []).map((step) => ({
      step: step.step as KnowledgeSourceStatus["steps"][number]["step"],
      status: step.status as KnowledgeSourceStatus["steps"][number]["status"],
      message: step.message,
      progress: step.progress,
      startedAt: step.started_at,
      completedAt: step.completed_at
    })),
    totalChunks: dto.total_chunks ?? 0,
    embeddedChunks: dto.embedded_chunks ?? 0,
    indexingCompleted: Boolean(dto.indexing_completed),
    lastUpdatedAt: dto.last_updated_at
  };
}

export async function uploadKnowledgeSource(formData: FormData): Promise<KnowledgeSource> {
  const data = await adminRequest<KnowledgeSourceDto, FormData>({
    method: "POST",
    url: KNOWLEDGE_API_ENDPOINTS.upload,
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
  return toKnowledgeSource(data);
}

export async function createKnowledgeSourceFromUrl(
  payload: CreateKnowledgeSourceFromUrlPayload
): Promise<KnowledgeSource> {
  const data = await adminRequest<KnowledgeSourceDto, CreateKnowledgeSourceFromUrlPayload>({
    method: "POST",
    url: KNOWLEDGE_API_ENDPOINTS.createFromUrl,
    data: payload
  });
  return toKnowledgeSource(data);
}

export async function getKnowledgeSources(
  params: GetKnowledgeSourcesParams = {}
): Promise<PaginatedResult<KnowledgeSource>> {
  const queryParams = {
    page: params.page,
    page_size: params.pageSize,
    domain: params.domain,
    label: params.label,
    search: params.search,
    status: params.status,
    type: params.type
  };

  const data = await adminRequest<PaginatedKnowledgeSourceDto>({
    method: "GET",
    url: KNOWLEDGE_API_ENDPOINTS.listSources,
    params: queryParams
  });
  return {
    items: (data.items ?? []).map(toKnowledgeSource),
    total: data.total ?? 0,
    page: data.page ?? 1,
    pageSize: data.page_size ?? params.pageSize ?? 20,
    totalPages: data.total_pages ?? 0
  };
}

export async function deleteKnowledgeSource(id: string): Promise<void> {
  await adminRequest<void>({
    method: "DELETE",
    url: KNOWLEDGE_API_ENDPOINTS.sourceById(id)
  });
}

export async function getKnowledgeSourceStatus(id: string): Promise<KnowledgeSourceStatus> {
  const data = await adminRequest<KnowledgeSourceStatusDto>({
    method: "GET",
    url: KNOWLEDGE_API_ENDPOINTS.sourceStatus(id)
  });
  return toKnowledgeSourceStatus(data);
}

export async function reprocessKnowledgeSource(id: string): Promise<KnowledgeSourceStatus> {
  const data = await adminRequest<KnowledgeSourceStatusDto>({
    method: "POST",
    url: KNOWLEDGE_API_ENDPOINTS.sourceReprocess(id),
    data: {}
  });
  return toKnowledgeSourceStatus(data);
}

export async function getKnowledgeSource(id: string): Promise<KnowledgeSource> {
  const data = await adminRequest<KnowledgeSourceDto>({
    method: "GET",
    url: KNOWLEDGE_API_ENDPOINTS.sourceById(id)
  });
  return toKnowledgeSource(data);
}

export async function updateKnowledgeSourceLabel(id: string, label: string): Promise<KnowledgeSource> {
  const data = await adminRequest<KnowledgeSourceDto, { label: string }>({
    method: "PATCH",
    url: KNOWLEDGE_API_ENDPOINTS.sourceLabel(id),
    data: { label }
  });
  return toKnowledgeSource(data);
}

export interface BulkSourceActionResponse {
  requested: number;
  processed: number;
  failed_source_ids: string[];
}

export async function bulkDeleteKnowledgeSources(sourceIds: string[]): Promise<BulkSourceActionResponse> {
  return adminRequest<BulkSourceActionResponse, { source_ids: string[] }>({
    method: "POST",
    url: KNOWLEDGE_API_ENDPOINTS.bulkDelete,
    data: { source_ids: sourceIds }
  });
}

export async function bulkReprocessKnowledgeSources(sourceIds: string[]): Promise<BulkSourceActionResponse> {
  return adminRequest<BulkSourceActionResponse, { source_ids: string[] }>({
    method: "POST",
    url: KNOWLEDGE_API_ENDPOINTS.bulkReprocess,
    data: { source_ids: sourceIds }
  });
}
