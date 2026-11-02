"""Lectura de la consistencia de reglas sin alterar el motor."""

from fastapi import APIRouter

from app.expert_system.rule_auditor import audit_rules
from app.schemas.rule_audit import RuleAuditResponse

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


@router.get(
    "/rule-audit",
    response_model=RuleAuditResponse,
    summary="Audita duplicados, sombras y solapamientos de las reglas",
)
def get_rule_audit() -> RuleAuditResponse:
    return audit_rules()
