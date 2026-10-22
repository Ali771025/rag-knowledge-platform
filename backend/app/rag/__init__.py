"""RAG package boundary.

Owns retrieval-augmented generation orchestration only.
Must not absorb ingestion, knowledge-graph construction, API transport,
or conversation persistence responsibilities.
"""

from app.rag.pipeline import RAGPipeline
from app.rag.answer_generator import AnswerGenerationInput, AnswerGenerator, GeneratedAnswer
from app.rag.citation_builder import CitationBuildInput, CitationBuilder
from app.rag.context_assembler import ContextAssembleInput, ContextAssembler
from app.rag.grounding_checker import GroundingCheckInput, GroundingChecker
from app.rag.prompt_builder import PromptBuildInput, PromptBuildResult, PromptBuilder
from app.rag.query_analyzer import QueryAnalysis, QueryAnalyzer, QueryType, RetrievalHints
from app.rag.rag_orchestrator import RAGOrchestrator, RAGOrchestratorInput, RAGOrchestratorResult, RAGPolicyConfig
from app.rag.reranker import RerankInput, RerankResult, Reranker
from app.rag.retrieval_planner import RetrievalPlanner
from app.rag.retrievers.graph_retriever import GraphQueryInput, GraphRetrievalResult, GraphRetriever, GraphRetrieverError
from app.rag.retrievers.hybrid_retriever import HybridRetrievalInput, HybridRetriever, HybridRetrieverError
from app.rag.retrievers.keyword_retriever import KeywordQueryInput, KeywordRetriever, KeywordRetrieverError
from app.rag.retrievers.vector_retriever import VectorQueryInput, VectorRetriever, VectorRetrieverError

__all__ = [
    "RAGPipeline",
    "AnswerGenerationInput",
    "AnswerGenerator",
    "GeneratedAnswer",
    "CitationBuildInput",
    "CitationBuilder",
    "ContextAssembleInput",
    "ContextAssembler",
    "GroundingCheckInput",
    "GroundingChecker",
    "PromptBuildInput",
    "PromptBuildResult",
    "PromptBuilder",
    "QueryAnalysis",
    "QueryAnalyzer",
    "QueryType",
    "RAGOrchestrator",
    "RAGOrchestratorInput",
    "RAGOrchestratorResult",
    "RAGPolicyConfig",
    "RerankInput",
    "RerankResult",
    "Reranker",
    "RetrievalHints",
    "RetrievalPlanner",
    "GraphQueryInput",
    "GraphRetrievalResult",
    "GraphRetriever",
    "GraphRetrieverError",
    "HybridRetrievalInput",
    "HybridRetriever",
    "HybridRetrieverError",
    "KeywordQueryInput",
    "KeywordRetriever",
    "KeywordRetrieverError",
    "VectorQueryInput",
    "VectorRetriever",
    "VectorRetrieverError",
]
