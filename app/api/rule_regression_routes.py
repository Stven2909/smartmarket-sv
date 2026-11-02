"""Prueba comparativa de snapshots de reglas sin despliegue ni escritura."""

from fastapi import APIRouter

from app.schemas.rule_regression import RuleRegressionRequest, RuleRegressionResponse
from app.services.rule_regression_service import compare_rule_versions

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


@router.post(
    "/rule-regression",
    response_model=RuleRegressionResponse,
    summary="Compara dos bases de reglas con exactamente los mismos escenarios",
)
def run_rule_regression(request: RuleRegressionRequest) -> RuleRegressionResponse:
    return compare_rule_versions(request)
