"""add token monitoring core tables

Revision ID: a9b8c7d6e5f4
Revises: 3c4d5e6f7a8b
Create Date: 2026-05-31 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a9b8c7d6e5f4"
down_revision: Union[str, None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


token_provider_enum = postgresql.ENUM("openai", "anthropic", "deepseek", name="token_provider_enum", create_type=False)
recommendation_category_enum = postgresql.ENUM(
    "cost",
    "performance",
    "reliability",
    "caching",
    name="recommendation_category_enum",
    create_type=False,
)
recommendation_severity_enum = postgresql.ENUM(
    "info",
    "warning",
    "critical",
    name="recommendation_severity_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'token_provider_enum') THEN
                    CREATE TYPE token_provider_enum AS ENUM ('openai', 'anthropic', 'deepseek');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recommendation_category_enum') THEN
                    CREATE TYPE recommendation_category_enum AS ENUM ('cost', 'performance', 'reliability', 'caching');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'recommendation_severity_enum') THEN
                    CREATE TYPE recommendation_severity_enum AS ENUM ('info', 'warning', 'critical');
                END IF;
            END
            $$;
            """
        )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            token_provider_enum if dialect_name == "postgresql" else sa.String(length=32),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("key_alias", sa.String(length=32), nullable=True),
        sa.Column("key_fingerprint", sa.String(length=24), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_fingerprint", name="uq_api_keys_key_fingerprint"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index(op.f("ix_api_keys_provider"), "api_keys", ["provider"], unique=False)
    op.create_index(op.f("ix_api_keys_is_active"), "api_keys", ["is_active"], unique=False)
    op.create_index(op.f("ix_api_keys_created_at"), "api_keys", ["created_at"], unique=False)

    op.create_table(
        "token_usage_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column(
            "provider",
            token_provider_enum if dialect_name == "postgresql" else sa.String(length=32),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cache_hit", sa.Boolean(), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_usage_logs_created_at", "token_usage_logs", ["created_at"], unique=False)
    op.create_index("ix_token_usage_logs_api_key_id", "token_usage_logs", ["api_key_id"], unique=False)
    op.create_index("ix_token_usage_logs_provider", "token_usage_logs", ["provider"], unique=False)
    op.create_index("ix_token_usage_logs_model_name", "token_usage_logs", ["model_name"], unique=False)
    op.create_index(op.f("ix_token_usage_logs_request_id"), "token_usage_logs", ["request_id"], unique=False)
    op.create_index("ix_token_usage_logs_latency_ms", "token_usage_logs", ["latency_ms"], unique=False)
    op.create_index("ix_token_usage_logs_cache_hit", "token_usage_logs", ["cache_hit"], unique=False)
    op.create_index(op.f("ix_token_usage_logs_endpoint"), "token_usage_logs", ["endpoint"], unique=False)
    op.create_index(op.f("ix_token_usage_logs_session_id"), "token_usage_logs", ["session_id"], unique=False)

    op.create_table(
        "daily_aggregates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("total_requests", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key_id", "date", name="uq_daily_aggregates_api_key_date"),
    )
    op.create_index("ix_daily_aggregates_date", "daily_aggregates", ["date"], unique=False)
    op.create_index("ix_daily_aggregates_api_key_id", "daily_aggregates", ["api_key_id"], unique=False)

    op.create_table(
        "optimization_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=True),
        sa.Column(
            "category",
            recommendation_category_enum if dialect_name == "postgresql" else sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "severity",
            recommendation_severity_enum if dialect_name == "postgresql" else sa.String(length=32),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_recommendations_generated_at", "optimization_recommendations", ["generated_at"], unique=False)
    op.create_index("ix_optimization_recommendations_is_dismissed", "optimization_recommendations", ["is_dismissed"], unique=False)
    op.create_index(op.f("ix_optimization_recommendations_api_key_id"), "optimization_recommendations", ["api_key_id"], unique=False)

    op.create_table(
        "budget_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("threshold_usd", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("current_spend_usd", sa.Numeric(precision=18, scale=9), nullable=False),
        sa.Column("period", sa.String(length=16), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_alerts_api_key_id", "budget_alerts", ["api_key_id"], unique=False)

    if dialect_name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                BEGIN
                    PERFORM create_hypertable('token_usage_logs', 'created_at', if_not_exists => TRUE);
                EXCEPTION
                    WHEN undefined_function OR feature_not_supported OR invalid_schema_name OR insufficient_privilege THEN
                        NULL;
                END;
            END
            $$;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_index("ix_budget_alerts_api_key_id", table_name="budget_alerts")
    op.drop_table("budget_alerts")

    op.drop_index(op.f("ix_optimization_recommendations_api_key_id"), table_name="optimization_recommendations")
    op.drop_index("ix_optimization_recommendations_is_dismissed", table_name="optimization_recommendations")
    op.drop_index("ix_optimization_recommendations_generated_at", table_name="optimization_recommendations")
    op.drop_table("optimization_recommendations")

    op.drop_index("ix_daily_aggregates_api_key_id", table_name="daily_aggregates")
    op.drop_index("ix_daily_aggregates_date", table_name="daily_aggregates")
    op.drop_table("daily_aggregates")

    op.drop_index(op.f("ix_token_usage_logs_session_id"), table_name="token_usage_logs")
    op.drop_index(op.f("ix_token_usage_logs_endpoint"), table_name="token_usage_logs")
    op.drop_index("ix_token_usage_logs_cache_hit", table_name="token_usage_logs")
    op.drop_index("ix_token_usage_logs_latency_ms", table_name="token_usage_logs")
    op.drop_index(op.f("ix_token_usage_logs_request_id"), table_name="token_usage_logs")
    op.drop_index("ix_token_usage_logs_model_name", table_name="token_usage_logs")
    op.drop_index("ix_token_usage_logs_provider", table_name="token_usage_logs")
    op.drop_index("ix_token_usage_logs_api_key_id", table_name="token_usage_logs")
    op.drop_index("ix_token_usage_logs_created_at", table_name="token_usage_logs")
    op.drop_table("token_usage_logs")

    op.drop_index(op.f("ix_api_keys_created_at"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_is_active"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_provider"), table_name="api_keys")
    op.drop_table("api_keys")

    if dialect_name == "postgresql":
        recommendation_severity_enum.drop(bind, checkfirst=True)
        recommendation_category_enum.drop(bind, checkfirst=True)
        token_provider_enum.drop(bind, checkfirst=True)
