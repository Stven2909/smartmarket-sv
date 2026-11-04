"""Consulta segura de la base de conocimiento para la demostración."""

from fastapi import APIRouter, HTTPException, Response

from app.expert_system.classifiers import THRESHOLDS, THRESHOLDS_VERSION
from app.expert_system.convenience_config import (
    CONVENIENCE_CONFIG_VERSION,
    DEFAULT_CONVENIENCE_CONFIG,
)
from app.expert_system.rule_loader import RuleLoaderError, load_rules
from app.expert_system.rules_fingerprint import current_rules_fingerprint
from app.schemas.knowledge import KnowledgeResponse
from app.schemas.versions import RULES_VERSION

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


@router.get(
    "/knowledge",
    response_model=KnowledgeResponse,
    summary="Expone reglas, umbrales y pesos actuales en modo lectura",
)
def get_knowledge(response: Response) -> KnowledgeResponse:
    try:
        rules = load_rules()
        response.headers["X-Expert-Rules-SHA256"] = current_rules_fingerprint()
    except RuleLoaderError as exc:
        raise HTTPException(
            status_code=503,
            detail="La base de reglas del sistema experto no está disponible.",
        ) from exc
    return KnowledgeResponse(
        rules=rules,
        thresholds=THRESHOLDS,
        weights=DEFAULT_CONVENIENCE_CONFIG.weights(),
        rules_version=RULES_VERSION,
        thresholds_version=THRESHOLDS_VERSION,
        convenience_version=CONVENIENCE_CONFIG_VERSION,
    )
