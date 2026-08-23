from fastapi import APIRouter, HTTPException

from app.expert_system.inference_engine import InferenceError
from app.schemas.recommendation import (
    RECOMMENDATION_CRITICAL_RESPONSE_EXAMPLE,
    RECOMMENDATION_RESPONSE_EXAMPLE,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendation_service import recommend


router = APIRouter(prefix="/api/v1", tags=["recommendations"])


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Genera una recomendación explicable",
    description=(
        "Valida los hechos de una alternativa, ejecuta el motor de reglas y "
        "añade el índice auxiliar de conveniencia sin alterar las reglas críticas."
    ),
    responses={
        200: {
            "description": "Recomendación validada y explicable.",
            "content": {
                "application/json": {
                    "examples": {
                        "alternativa_ideal": {
                            "summary": "Alternativa ideal con índice complementario",
                            "value": RECOMMENDATION_RESPONSE_EXAMPLE,
                        },
                        "regla_critica": {
                            "summary": "Presupuesto muy excedido",
                            "value": RECOMMENDATION_CRITICAL_RESPONSE_EXAMPLE,
                        },
                    }
                }
            },
        },
        422: {
            "description": "JSON ausente, inválido o inconsistente.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "presupuesto"],
                                "msg": "Input should be greater than 0",
                                "type": "greater_than",
                            }
                        ]
                    }
                }
            },
        },
        500: {
            "description": "Error interno no controlado del servicio.",
        },
    },
)
def create_recommendation(
    request: RecommendationRequest,
) -> RecommendationResponse:
    try:
        return recommend(request)
    except InferenceError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Error controlado del motor de inferencia: {exc}",
        ) from exc
