"""Análisis de sensibilidad opcional sobre una alternativa de compra."""

from fastapi import APIRouter

from app.schemas.sensitivity import SensitivityRequest, SensitivityResponse
from app.services.sensitivity_service import analyze_sensitivity

router = APIRouter(prefix="/api/v1", tags=["sensitivity"])


@router.post(
    "/sensitivity",
    response_model=SensitivityResponse,
    summary="Analiza la estabilidad de una recomendación ante cambios hipotéticos",
)
def create_sensitivity(request: SensitivityRequest) -> SensitivityResponse:
    return analyze_sensitivity(request)
