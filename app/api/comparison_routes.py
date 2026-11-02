"""Ruta opcional; /api/v1/recommend permanece sin modificaciones."""

from fastapi import APIRouter

from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import compare_alternatives

router = APIRouter(prefix="/api/v1", tags=["comparison"])


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compara de 2 a 10 alternativas con inferencia explicable",
    description=(
        "Evalúa cada alternativa con las ocho reglas actuales y las ordena "
        "según su conclusión experta e índice auxiliar. "
        "Este endpoint no cambia el contrato de /recommend."
    ),
)
def create_comparison(request: ComparisonRequest) -> ComparisonResponse:
    return compare_alternatives(request)
