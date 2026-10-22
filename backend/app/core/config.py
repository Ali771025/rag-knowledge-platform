from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "RAGAi Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["https://example.invalid", "http://localhost:3000"],
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )

    database_url: str = Field(
        default="sqlite:///./app.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    redis_key_prefix: str = "ragai:session"
    redis_session_ttl: int = 3600
    rate_limit: int = Field(default=100, validation_alias=AliasChoices("RATE_LIMIT", "rate_limit"))
    rate_limit_fail_open: bool = Field(
        default=True,
        validation_alias=AliasChoices("RATE_LIMIT_FAIL_OPEN", "rate_limit_fail_open"),
    )
    admin_knowledge_upload_max_bytes: int = Field(
        default=25 * 1024 * 1024,
        validation_alias=AliasChoices("ADMIN_KNOWLEDGE_UPLOAD_MAX_BYTES", "admin_knowledge_upload_max_bytes"),
    )
    admin_knowledge_ingestion_submit_retries: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "ADMIN_KNOWLEDGE_INGESTION_SUBMIT_RETRIES",
            "admin_knowledge_ingestion_submit_retries",
        ),
    )
    neo4j_uri: str = Field(
        default="",
        validation_alias=AliasChoices("NEO4J_URI", "neo4j_uri"),
    )
    neo4j_user: str = Field(
        default="",
        validation_alias=AliasChoices("NEO4J_USER", "NEO4J_USERNAME", "neo4j_user", "neo4j_username"),
    )
    neo4j_password: str = Field(
        default="",
        validation_alias=AliasChoices("NEO4J_PASSWORD", "neo4j_password"),
    )
    neo4j_database: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("NEO4J_DATABASE", "neo4j_database"),
    )

    jwt_secret_key: str = Field(
        default="change-me-in-production",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "jwt_secret_key"),
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(
        default=30,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "access_token_expire_minutes"),
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRE_DAYS", "refresh_token_expire_days"),
    )
    telegram_auth_secret: str = Field(
        default="",
        validation_alias=AliasChoices("TELEGRAM_AUTH_SECRET", "telegram_auth_secret"),
    )

    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    llm_provider: str = Field(
        default="openai",
        validation_alias=AliasChoices("LLM_PROVIDER", "llm_provider"),
    )
    openai_generation_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_GENERATION_MODEL", "openai_generation_model"),
    )
    openai_generation_timeout_sec: float = Field(
        default=8.0,
        validation_alias=AliasChoices("OPENAI_GENERATION_TIMEOUT_SEC", "openai_generation_timeout_sec"),
    )
    openai_generation_max_retries: int = Field(
        default=0,
        validation_alias=AliasChoices("OPENAI_GENERATION_MAX_RETRIES", "openai_generation_max_retries"),
    )
    openai_embedding_timeout_sec: float = Field(
        default=6.0,
        validation_alias=AliasChoices("OPENAI_EMBEDDING_TIMEOUT_SEC", "openai_embedding_timeout_sec"),
    )
    openai_embedding_max_retries: int = Field(
        default=0,
        validation_alias=AliasChoices("OPENAI_EMBEDDING_MAX_RETRIES", "openai_embedding_max_retries"),
    )
    embedding_cache_size: int = Field(
        default=256,
        validation_alias=AliasChoices("EMBEDDING_CACHE_SIZE", "embedding_cache_size"),
    )
    anthropic_generation_model: str = Field(
        default="claude-3-5-haiku-latest",
        validation_alias=AliasChoices("ANTHROPIC_GENERATION_MODEL", "anthropic_generation_model"),
    )
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    openai_request_timeout_sec: float = Field(
        default=20.0,
        validation_alias=AliasChoices("OPENAI_REQUEST_TIMEOUT_SEC", "openai_request_timeout_sec"),
    )
    openai_max_retries: int = Field(
        default=1,
        validation_alias=AliasChoices("OPENAI_MAX_RETRIES", "openai_max_retries"),
    )
    claude_request_timeout_sec: float = Field(
        default=8.0,
        validation_alias=AliasChoices("CLAUDE_REQUEST_TIMEOUT_SEC", "claude_request_timeout_sec"),
    )
    claude_max_retries: int = Field(
        default=0,
        validation_alias=AliasChoices("CLAUDE_MAX_RETRIES", "claude_max_retries"),
    )
    ingestion_metadata_llm_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("INGESTION_METADATA_LLM_ENABLED", "ingestion_metadata_llm_enabled"),
    )
    knowledge_graph_entity_llm_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("KNOWLEDGE_GRAPH_ENTITY_LLM_ENABLED", "knowledge_graph_entity_llm_enabled"),
    )
    knowledge_graph_relation_llm_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("KNOWLEDGE_GRAPH_RELATION_LLM_ENABLED", "knowledge_graph_relation_llm_enabled"),
    )
    default_model: str = "claude-3-5-haiku-latest"
    max_tokens: int = 512
    temperature: float = 0.2

    feature_cache_orchestration_enabled: bool = False
    feature_model_routing_enabled: bool = False
    feature_unified_llm_client_enabled: bool = False
    feature_fallback_enabled: bool = False
    feature_cost_tracking_enabled: bool = False
    feature_budget_guard_enabled: bool = False
    feature_shadow_routing_enabled: bool = False
    feature_observability_adapters_enabled: bool = True
    rag_min_grounding_ratio: float = 0.6
    rag_fallback_on_no_evidence: bool = True
    rag_fallback_on_weak_grounding: bool = True
    rag_warning_on_weak_grounding: bool = False
    rag_allow_graph_degrade: bool = True
    rag_allow_vector_degrade: bool = True
    rag_token_budget: int = 1800
    rag_min_relevance_score: float = 0.15
    rag_min_retrieved_items: int = 1
    rag_relax_filters_on_zero_results: bool = True
    rag_enforce_citation_presence: bool = False
    rag_retry_on_ungrounded_once: bool = False
    rag_refusal_message: str = "I could not find this information in the available documents."

    kafka_enabled: bool = False
    kafka_strict_mode: bool = False
    kafka_bootstrap_servers: str = ""
    kafka_topic_prefix: str = ""
    kafka_linger_ms: int = 5
    kafka_retries: int = 3
    kafka_send_timeout_sec: float = 10.0
    kafka_flush_timeout_sec: float = 10.0

    model_config = SettingsConfigDict(
        env_file=(str(_BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [entry.strip() for entry in value.split(",") if entry.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
