import os
import secrets

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.api.health_routes import router as health_router
from app.api.chatbot_routes import router as chatbot_router
from app.api.recommendation_routes import router as recommendation_router
from app.schemas.versions import CONTRACT_VERSION

API_KEY_ENV = "SMARTMARKET_API_KEY"

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    expected = os.getenv(API_KEY_ENV, "").strip()

    # ponytail: sin variable de entorno la API queda abierta a propósito (dev local)
    if not expected:
        return
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="API key inválida o ausente.")


_protected = bool(os.getenv(API_KEY_ENV, "").strip())

app = FastAPI(
    title="SmartMarket SV Expert Service",
    version=CONTRACT_VERSION,
    description="API independiente para el Sistema Experto de SmartMarket SV.",
    docs_url=None if _protected else "/docs",
    redoc_url=None if _protected else "/redoc",
    openapi_url=None if _protected else "/openapi.json",
)

app.include_router(health_router)
app.include_router(recommendation_router, dependencies=[Security(require_api_key)])
app.include_router(chatbot_router, dependencies=[Security(require_api_key)])
