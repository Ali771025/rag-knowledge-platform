import { adminRequest } from "./httpClient";
import type {
  EntityMetadata,
  KnowledgeGraphEdge,
  KnowledgeGraphNode,
  KnowledgeGraphRelationship,
  PaginatedResult
} from "@/types/admin";

export const KNOWLEDGE_GRAPH_API_ENDPOINTS = {
  entities: "/api/v1/admin/knowledge-graph/entities",
  relationships: "/api/v1/admin/knowledge-graph/relationships",
  graph: "/api/v1/admin/knowledge-graph/visualize"
} as const;

export interface GetEntitiesParams {
  page?: number;
  pageSize?: number;
  label?: string;
  type?: string;
  search?: string;
}

export interface GetRelationshipsParams {
  page?: number;
  pageSize?: number;
  label?: string;
  type?: string;
  relationshipType?: string;
  search?: string;
}

export interface GetGraphParams {
  label?: string;
  type?: string;
  search?: string;
  relationshipType?: string;
  centerEntityId?: string;
  depth?: number;
  limit?: number;
}

export interface KnowledgeGraphResponse {
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
  metadata?: Record<string, unknown>;
  graphBackendAvailable?: boolean;
  graphBackendStatus?: string;
  graphBackendReason?: string;
}

interface PaginatedDto<TItem> {
  items: TItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface EntityDto {
  id: string;
  name: string;
  type: string;
  label?: string;
  domain?: string;
  description?: string;
  aliases?: string[];
  confidence?: number;
  source_ids?: string[];
  metadata_json?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

interface RelationshipDto {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  label?: string;
  confidence?: number;
  metadata_json?: Record<string, unknown>;
}

interface GraphNodeDto {
  id: string;
  label: string;
  type: string;
  domain?: string;
  source_label?: string;
  metadata_json?: Record<string, unknown>;
}

interface GraphEdgeDto {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight?: number;
  source_label?: string;
  metadata_json?: Record<string, unknown>;
}

interface GraphDto {
  nodes: GraphNodeDto[];
  edges: GraphEdgeDto[];
  metadata_json?: Record<string, unknown>;
}

function toEntity(item: EntityDto): EntityMetadata {
  return {
    id: item.id,
    name: item.name,
    type: (item.type?.toLowerCase() ?? "other") as EntityMetadata["type"],
    domain: item.domain,
    label: item.label,
    description: item.description,
    aliases: item.aliases ?? [],
    confidence: item.confidence,
    sourceIds: item.source_ids ?? [],
    metadata: item.metadata_json ?? {},
    createdAt: item.created_at,
    updatedAt: item.updated_at
  };
}

function toRelationship(item: RelationshipDto): KnowledgeGraphRelationship {
  return {
    id: item.id,
    sourceEntityId: item.source_entity_id,
    targetEntityId: item.target_entity_id,
    relationshipType: item.relationship_type,
    label: item.label,
    confidence: item.confidence,
    metadata: item.metadata_json ?? {}
  };
}

function toGraphNode(item: GraphNodeDto): KnowledgeGraphNode {
  return {
    id: item.id,
    label: item.label,
    type: (item.type?.toLowerCase() ?? "other") as KnowledgeGraphNode["type"],
    domain: item.domain,
    sourceLabel: item.source_label,
    metadata: item.metadata_json ?? {}
  };
}

function toGraphEdge(item: GraphEdgeDto): KnowledgeGraphEdge {
  return {
    id: item.id,
    source: item.source,
    target: item.target,
    relation: item.relation,
    weight: item.weight,
    sourceLabel: item.source_label,
    metadata: item.metadata_json ?? {}
  };
}

function toPaginated<TInput, TOutput>(payload: PaginatedDto<TInput>, mapper: (item: TInput) => TOutput): PaginatedResult<TOutput> {
  return {
    items: (payload.items ?? []).map(mapper),
    total: payload.total,
    page: payload.page,
    pageSize: payload.page_size,
    totalPages: payload.total_pages
  };
}

export async function getEntities(params: GetEntitiesParams = {}): Promise<PaginatedResult<EntityMetadata>> {
  const data = await adminRequest<PaginatedDto<EntityDto>>({
    method: "GET",
    url: KNOWLEDGE_GRAPH_API_ENDPOINTS.entities,
    params: {
      page: params.page,
      page_size: params.pageSize,
      label: params.label,
      type: params.type,
      search: params.search
    }
  });
  return toPaginated(data, toEntity);
}

export async function getEntityById(id: string): Promise<EntityMetadata> {
  const data = await adminRequest<EntityDto>({
    method: "GET",
    url: `${KNOWLEDGE_GRAPH_API_ENDPOINTS.entities}/${id}`
  });
  return toEntity(data);
}

export async function getRelationships(
  params: GetRelationshipsParams = {}
): Promise<PaginatedResult<KnowledgeGraphRelationship>> {
  const data = await adminRequest<PaginatedDto<RelationshipDto>>({
    method: "GET",
    url: KNOWLEDGE_GRAPH_API_ENDPOINTS.relationships,
    params: {
      page: params.page,
      page_size: params.pageSize,
      label: params.label,
      type: params.type,
      relationship_type: params.relationshipType,
      search: params.search
    }
  });
  return toPaginated(data, toRelationship);
}

export async function getGraph(params: GetGraphParams = {}): Promise<KnowledgeGraphResponse> {
  const data = await adminRequest<GraphDto>({
    method: "GET",
    url: KNOWLEDGE_GRAPH_API_ENDPOINTS.graph,
    params: {
      label: params.label,
      type: params.type,
      search: params.search,
      relationship_type: params.relationshipType,
      center_entity_id: params.centerEntityId,
      depth: params.depth,
      limit: params.limit
    }
  });

  return {
    nodes: (data.nodes ?? []).map(toGraphNode),
    edges: (data.edges ?? []).map(toGraphEdge),
    metadata: data.metadata_json ?? {},
    graphBackendAvailable:
      typeof data.metadata_json?.graph_backend_available === "boolean"
        ? data.metadata_json.graph_backend_available
        : undefined,
    graphBackendStatus:
      typeof data.metadata_json?.graph_backend_status === "string"
        ? data.metadata_json.graph_backend_status
        : undefined,
    graphBackendReason:
      typeof data.metadata_json?.graph_backend_reason === "string"
        ? data.metadata_json.graph_backend_reason
        : undefined
  };
}
