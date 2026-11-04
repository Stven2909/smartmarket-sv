import os
import secrets

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.api.chatbot_routes import router as chatbot_router
from app.api.comparison_routes import router as comparison_router
from app.api.diagnosis_routes import router as diagnosis_router
from app.api.evidence_report_routes import router as evidence_report_router
from app.api.health_routes import router as health_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.recommendation_routes import router as recommendation_router
from app.api.rule_audit_routes import router as rule_audit_router
from app.api.rule_regression_routes import router as rule_regression_router
from app.api.sensitivity_routes import router as sensitivity_router
from app.schemas.versions import CONTRACT_VERSION
from app.security.request_size import RequestBodySizeLimitMiddleware

API_KEY_ENV = "SMARTMARKET_API_KEY"
STREAMLIT_API_KEY_ENV = "SMARTMARKET_API_KEY_STREAMLIT"
PREVIOUS_API_KEY_ENV = "SMARTMARKET_API_KEY_PREVIOUS"
ENVIRONMENT_ENV = "SMARTMARKET_ENV"


def is_production() -> bool:
    """Any explicitly deployed environment must require a service key.

    Missing environment is kept open only for backward-compatible local demos.
    An unexpected value (including a typo of production) must not fail open.
    """
    # Render sets RENDER=true automatically. Never allow local/dev settings
    # to disable service authentication on a real deployed host.
    if os.getenv("RENDER", "").strip().lower() in {"true", "1"}:
        return True
    environment = os.getenv(ENVIRONMENT_ENV, "").strip().lower()
    return environment not in {"", "local", "dev", "development", "test", "testing"}

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Accept only the configured service secret (or a temporary rotation key).

    This authenticates Laravel-to-Python calls, not the end user's Laravel session.
    """
    expected = os.getenv(API_KEY_ENV, "").strip()
    streamlit = os.getenv(STREAMLIT_API_KEY_ENV, "").strip()
    previous = os.getenv(PREVIOUS_API_KEY_ENV, "").strip()

    # Never let a leftover rotation secret act as the primary configuration.
    if not expected:
        if is_production() or previous or streamlit:
            raise HTTPException(
                status_code=503,
                detail="El servicio experto no está disponible.",
            )
        return

    supplied = api_key or ""
    # Validate every configured client secret without short-circuiting on
    # the first match. Secrets never leave the backend HTTP response.
    valid_current = secrets.compare_digest(supplied, expected)
    valid_streamlit = secrets.compare_digest(supplied, streamlit) if streamlit else False
    valid_previous = secrets.compare_digest(supplied, previous) if previous else False
    if not (valid_current | valid_streamlit | valid_previous):
        raise HTTPException(status_code=401, detail="API key inválida o ausente.")


_protected = (
    is_production()
    or bool(os.getenv(API_KEY_ENV, "").strip())
    or bool(os.getenv(STREAMLIT_API_KEY_ENV, "").strip())
    or bool(os.getenv(PREVIOUS_API_KEY_ENV, "").strip())
)

app = FastAPI(
    title="SmartMarket SV Expert Service",
    version=CONTRACT_VERSION,
    description="API independiente para el Sistema Experto de SmartMarket SV.",
    docs_url=None if _protected else "/docs",
    redoc_url=None if _protected else "/redoc",
    openapi_url=None if _protected else "/openapi.json",
)

@app.middleware("http")
async def add_api_security_headers(request, call_next):
    """Prevent intermediaries or browsers from caching personal expert results."""
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        existing_vary = response.headers.get("Vary", "")
        fields = [item.strip() for item in existing_vary.split(",") if item.strip()]
        if "x-api-key" not in {field.lower() for field in fields}:
            fields.append("X-API-Key")
        response.headers["Vary"] = ", ".join(fields)
    return response


app.add_middleware(RequestBodySizeLimitMiddleware)

app.include_router(health_router)
app.include_router(recommendation_router, dependencies=[Security(require_api_key)])
app.include_router(chatbot_router, dependencies=[Security(require_api_key)])
app.include_router(comparison_router, dependencies=[Security(require_api_key)])
app.include_router(diagnosis_router, dependencies=[Security(require_api_key)])
app.include_router(evidence_report_router, dependencies=[Security(require_api_key)])
app.include_router(knowledge_router, dependencies=[Security(require_api_key)])
app.include_router(rule_audit_router, dependencies=[Security(require_api_key)])
app.include_router(rule_regression_router, dependencies=[Security(require_api_key)])
app.include_router(sensitivity_router, dependencies=[Security(require_api_key)])
