from fastapi import APIRouter, HTTPException, Response

from app.expert_system.rule_loader import RuleLoaderError, load_rules
from app.expert_system.rules_fingerprint import current_rules_fingerprint

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Verifica la disponibilidad del servicio",
    responses={
        200: {
            "description": "Servicio disponible.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "service": "smartmarket-expert-service",
                    }
                }
            },
        }
    },
)
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "smartmarket-expert-service"}


@router.get(
    "/ready",
    summary="Comprueba que la base de reglas esté lista para inferencia",
    responses={503: {"description": "Base de conocimiento no disponible."}},
)
def readiness_check(response: Response) -> dict[str, str]:
    try:
        if not load_rules():
            raise RuleLoaderError("La base de conocimiento no tiene reglas.")
        response.headers["X-Expert-Rules-SHA256"] = current_rules_fingerprint()
    except RuleLoaderError as exc:
        raise HTTPException(
            status_code=503,
            detail="La base de reglas del sistema experto no está disponible.",
        ) from exc
    return {"status": "ready", "service": "smartmarket-expert-service"}
