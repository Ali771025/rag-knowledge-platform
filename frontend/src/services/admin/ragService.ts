import { adminRequest } from "./httpClient";
import type { RAGConfig, RAGTestRequest, RAGTestResult } from "@/types/admin";

export const RAG_API_ENDPOINTS = {
  config: "/api/v1/admin/rag/config",
  test: "/api/v1/admin/rag/test"
} as const;

interface RAGConfigDto {
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  similarity_threshold: number;
  reranker_enabled: boolean;
  hybrid_search_enabled: boolean;
  graph_enhanced_retrieval_enabled: boolean;
  embedding_model: string;
  reranker_model: string;
  vector_collection_name: string;
  default_labels: string[];
  updated_at?: string;
}

interface RAGRetrievedChunkDto {
  chunk_id: string;
  source_id: string;
  source_title?: string;
  label?: string;
  content: string;
  score?: number;
  rerank_score?: number;
  metadata?: Record<string, string | number | boolean | null | undefined>;
}

interface RAGCitationDto {
  source_id: string;
  source_title?: string;
  label?: string;
  chunk_id?: string;
  locator?: string;
  score?: number;
  snippet: string;
}

interface RAGDiagnosticsDto {
  timings_ms?: Record<string, number>;
  flags?: Record<string, boolean>;
  retrieval_summary?: Record<string, unknown>;
  warnings?: string[];
}

interface RAGTestResultDto {
  query: string;
  config_used: RAGConfigDto;
  retrieved_chunks: RAGRetrievedChunkDto[];
  reranked_chunks?: RAGRetrievedChunkDto[];
  final_answer: string;
  citations: RAGCitationDto[];
  diagnostics: RAGDiagnosticsDto;
  latency_ms?: number;
}

function toConfig(dto: RAGConfigDto): RAGConfig {
  return {
    chunkSize: dto.chunk_size,
    chunkOverlap: dto.chunk_overlap,
    topK: dto.top_k,
    similarityThreshold: dto.similarity_threshold,
    rerankerEnabled: dto.reranker_enabled,
    hybridSearchEnabled: dto.hybrid_search_enabled,
    graphEnhancedRetrievalEnabled: dto.graph_enhanced_retrieval_enabled,
    embeddingModel: dto.embedding_model as RAGConfig["embeddingModel"],
    rerankerModel: dto.reranker_model,
    vectorCollectionName: dto.vector_collection_name,
    defaultLabels: dto.default_labels ?? [],
    updatedAt: dto.updated_at
  };
}

function fromConfig(config: RAGConfig): RAGConfigDto {
  return {
    chunk_size: config.chunkSize,
    chunk_overlap: config.chunkOverlap,
    top_k: config.topK,
    similarity_threshold: config.similarityThreshold,
    reranker_enabled: config.rerankerEnabled,
    hybrid_search_enabled: config.hybridSearchEnabled,
    graph_enhanced_retrieval_enabled: config.graphEnhancedRetrievalEnabled,
    embedding_model: config.embeddingModel,
    reranker_model: config.rerankerModel,
    vector_collection_name: config.vectorCollectionName,
    default_labels: config.defaultLabels,
    updated_at: config.updatedAt
  };
}

function toTestResult(dto: RAGTestResultDto): RAGTestResult {
  const mapChunk = (chunk: RAGRetrievedChunkDto) => ({
    id: chunk.chunk_id,
    sourceId: chunk.source_id,
    sourceTitle: chunk.source_title,
    label: chunk.label ?? "",
    score: chunk.score ?? 0,
    rerankedScore: chunk.rerank_score,
    content: chunk.content,
    metadata: chunk.metadata ?? {}
  });

  return {
    query: dto.query,
    configUsed: toConfig(dto.config_used),
    retrievedChunks: (dto.retrieved_chunks ?? []).map(mapChunk),
    rerankedChunks: dto.reranked_chunks?.map(mapChunk),
    finalAnswer: dto.final_answer,
    citations: (dto.citations ?? []).map((item) => ({
      sourceId: item.source_id,
      sourceTitle: item.source_title,
      label: item.label ?? "",
      chunkId: item.chunk_id ?? "",
      locator: item.locator,
      score: item.score,
      snippet: item.snippet
    })),
    diagnostics: {
      timingsMs: dto.diagnostics?.timings_ms ?? {},
      flags: dto.diagnostics?.flags ?? {},
      retrievalSummary: dto.diagnostics?.retrieval_summary ?? {},
      warnings: dto.diagnostics?.warnings ?? []
    },
    latencyMs: dto.latency_ms
  };
}

export async function getRAGConfig(): Promise<RAGConfig> {
  const data = await adminRequest<RAGConfigDto>({
    method: "GET",
    url: RAG_API_ENDPOINTS.config
  });
  return toConfig(data);
}

export async function updateRAGConfig(config: RAGConfig): Promise<RAGConfig> {
  const data = await adminRequest<RAGConfigDto, RAGConfigDto>({
    method: "PUT",
    url: RAG_API_ENDPOINTS.config,
    data: fromConfig(config)
  });
  return toConfig(data);
}

export async function testRAG(request: RAGTestRequest): Promise<RAGTestResult> {
  const payload = {
    query: request.query,
    domain: request.domain,
    labels: request.labels,
    source_ids: request.sourceIds,
    top_k: request.topK,
    similarity_threshold: request.similarityThreshold,
    reranker_enabled: request.rerankerEnabled,
    hybrid_search_enabled: request.hybridSearchEnabled,
    graph_enhanced_retrieval_enabled: request.graphEnhancedRetrievalEnabled,
    include_graph_context: request.includeGraphContext
  };

  const data = await adminRequest<RAGTestResultDto, typeof payload>({
    method: "POST",
    url: RAG_API_ENDPOINTS.test,
    data: payload
  });
  return toTestResult(data);
}
