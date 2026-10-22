from fastapi import APIRouter

from app.api.admin.analytics import router as admin_analytics_router
from app.api.admin.cache import router as admin_cache_router
from app.api.admin.cost import router as admin_cost_router
from app.api.admin.llm import router as admin_llm_router
from app.api.admin.token_budget import router as token_budget_router
from app.api.admin.token_optimization import router as token_optimization_router
from app.api.admin.token_usage import router as token_usage_router
from app.api.health import router as observability_health_router
from app.api.metrics import router as metrics_router
from app.api.tasks import router as tasks_router
from app.api.worker_health import router as worker_health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.endpoints.persona_conversion import router as persona_conversion_router
from app.api.v1.endpoints.analytics_internal import router as analytics_internal_router
from app.api.v1.endpoints.admin_ingestion import router as admin_ingestion_router
from app.api.v1.endpoints.admin_knowledge import router as admin_knowledge_router
from app.api.v1.endpoints.admin_knowledge_graph import router as admin_knowledge_graph_router
from app.api.v1.endpoints.admin_rag import router as admin_rag_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.audio import router as audio_router
from app.api.v1.endpoints.dashboard import router as dashboard_router
from app.api.v1.endpoints.knowledge_graph import router as knowledge_graph_router
from app.api.v1.endpoints.referral import router as referral_router
from app.api.v1.endpoints.session import router as session_router
from app.api.v1.endpoints.user import router as user_router
from app.api.v1.user_onboarding import router as user_onboarding_router
from app.rag.api.routes import router as rag_router
from app.qora.api.public_conversations import router as qora_agent_router

api_router = APIRouter()
api_router.include_router(observability_health_router)
api_router.include_router(metrics_router)
api_router.include_router(tasks_router)
api_router.include_router(worker_health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(session_router, prefix="/session", tags=["session"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(audio_router)
api_router.include_router(dashboard_router)
api_router.include_router(user_onboarding_router)
api_router.include_router(persona_conversion_router)
api_router.include_router(analytics_internal_router)
api_router.include_router(user_router, prefix="/users", tags=["users"])
api_router.include_router(referral_router)
api_router.include_router(rag_router, prefix="/rag", tags=["rag"])
api_router.include_router(admin_analytics_router)
api_router.include_router(admin_cache_router)
api_router.include_router(admin_cost_router)
api_router.include_router(admin_llm_router)
api_router.include_router(token_usage_router)
api_router.include_router(token_budget_router)
api_router.include_router(token_optimization_router)
api_router.include_router(admin_ingestion_router)
api_router.include_router(admin_knowledge_router)
api_router.include_router(admin_knowledge_graph_router)
api_router.include_router(admin_rag_router)
api_router.include_router(knowledge_graph_router)
api_router.include_router(documents_router)
api_router.include_router(qora_agent_router)
