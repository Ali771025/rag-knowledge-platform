"""Retriever adapter placeholders.

Owns retrieval adapter implementations against contracts.
Must not implement ranking or generation behavior here.
"""

from app.rag.retrievers.graph_retriever import GraphQueryInput, GraphRetrievalResult, GraphRetriever, GraphRetrieverError
from app.rag.retrievers.hybrid_retriever import HybridRetrievalInput, HybridRetriever, HybridRetrieverError
from app.rag.retrievers.keyword_retriever import KeywordQueryInput, KeywordRetriever, KeywordRetrieverError
from app.rag.retrievers.vector_retriever import VectorQueryInput, VectorRetriever, VectorRetrieverError

__all__ = [
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
