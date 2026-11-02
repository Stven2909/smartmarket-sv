"""Diagnóstico opcional de oportunidades de reglas para una alternativa."""

from fastapi import APIRouter

from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse
from app.services.diagnosis_service import diagnose

router = APIRouter(prefix="/api/v1", tags=["diagnosis"])


@router.post(
    "/diagnosis",
    response_model=DiagnosisResponse,
    summary="Explica condiciones favorables pendientes y riesgos críticos",
)
def create_diagnosis(request: DiagnosisRequest) -> DiagnosisResponse:
    return diagnose(request)
