export enum KnowledgeSourceType {
  FILE = "file",
  URL = "url",
  TEXT = "text",
  API = "api"
}

export enum IngestionStatus {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed"
}

export enum IngestionStep {
  UPLOADED = "uploaded",
  PARSING = "parsing",
  CHUNKING = "chunking",
  EMBEDDING = "embedding",
  INDEXING = "indexing",
  COMPLETED = "completed",
  FAILED = "failed"
}

export enum EmbeddingModel {
  TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large",
  BGE_M3 = "bge-m3"
}

export enum EntityType {
  PERSON = "person",
  ORGANIZATION = "organization",
  LOCATION = "location",
  TECHNOLOGY = "technology",
  PRODUCT = "product",
  CONCEPT = "concept",
  EVENT = "event",
  DOCUMENT = "document",
  OTHER = "other"
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface IngestionStepStatus {
  step: IngestionStep;
  status: IngestionStatus;
  message?: string;
  progress?: number;
  startedAt?: string;
  completedAt?: string;
}

export interface KnowledgeSource {
  id: string;
  name: string;
  type: KnowledgeSourceType;
  domain: string;
  label: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  status: IngestionStatus;
  totalChunks: number;
  embeddedChunks: number;
  indexingCompleted: boolean;
  errorMessage?: string;
}

export interface KnowledgeSourceStatus {
  sourceId: string;
  status: IngestionStatus;
  steps: IngestionStepStatus[];
  totalChunks: number;
  embeddedChunks: number;
  indexingCompleted: boolean;
  lastUpdatedAt: string;
}

export interface RAGConfig {
  chunkSize: number;
  chunkOverlap: number;
  topK: number;
  similarityThreshold: number;
  rerankerEnabled: boolean;
  hybridSearchEnabled: boolean;
  graphEnhancedRetrievalEnabled: boolean;
  embeddingModel: EmbeddingModel;
  rerankerModel: string;
  vectorCollectionName: string;
  defaultLabels: string[];
  updatedAt?: string;
}

export interface RAGRetrievedChunkMetadata {
  page_number?: number;
  section_title?: string;
  document_type?: string;
  url?: string;
  [key: string]: string | number | boolean | null | undefined;
}

export interface RAGRetrievedChunk {
  id: string;
  sourceId: string;
  sourceTitle?: string;
  label: string;
  domain?: string;
  score: number;
  rerankedScore?: number;
  content: string;
  metadata: RAGRetrievedChunkMetadata;
}

export interface RAGTestRequest {
  query: string;
  domain?: string;
  labels?: string[];
  sourceIds?: string[];
  topK?: number;
  similarityThreshold?: number;
  rerankerEnabled?: boolean;
  hybridSearchEnabled?: boolean;
  graphEnhancedRetrievalEnabled?: boolean;
  includeGraphContext?: boolean;
}

export interface RAGCitation {
  sourceId: string;
  label: string;
  sourceTitle?: string;
  chunkId: string;
  locator?: string;
  score?: number;
  snippet?: string;
}

export interface RAGDiagnostics {
  timingsMs: Record<string, number>;
  flags: Record<string, boolean>;
  retrievalSummary: Record<string, unknown>;
  warnings: string[];
}

export interface RAGTestResult {
  query: string;
  configUsed: RAGConfig;
  retrievedChunks: RAGRetrievedChunk[];
  rerankedChunks?: RAGRetrievedChunk[];
  finalAnswer: string;
  citations: RAGCitation[];
  diagnostics: RAGDiagnostics;
  latencyMs?: number;
}

export interface EntityMetadata {
  id: string;
  name: string;
  type: EntityType;
  domain?: string;
  label?: string;
  description?: string;
  aliases?: string[];
  confidence?: number;
  sourceIds?: string[];
  metadata?: Record<string, unknown>;
  createdAt?: string;
  updatedAt?: string;
}

export interface KnowledgeGraphRelationship {
  id: string;
  sourceEntityId: string;
  targetEntityId: string;
  relationshipType: string;
  label?: string;
  confidence?: number;
  metadata?: Record<string, unknown>;
}

export interface KnowledgeGraphNode {
  id: string;
  label: string;
  type: EntityType;
  domain?: string;
  sourceLabel?: string;
  metadata?: Record<string, unknown>;
}

export interface KnowledgeGraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight?: number;
  sourceLabel?: string;
  metadata?: Record<string, unknown>;
}
