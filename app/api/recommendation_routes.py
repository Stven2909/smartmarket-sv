from fastapi import APIRouter, HTTPException, Response

from app.expert_system.inference_engine import InferenceError
from app.expert_system.rule_loader import RuleLoaderError
from app.expert_system.rules_fingerprint import current_rules_fingerprint
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
        503: {"description": "La base de reglas no está disponible."},
    },
)
def create_recommendation(
    request: RecommendationRequest,
    response: Response,
) -> RecommendationResponse:
    try:
        result = recommend(request)
        # Observabilidad no invasiva: no se agregan campos al JSON de respuesta.
        response.headers["X-Expert-Rules-SHA256"] = current_rules_fingerprint()
        return result
    except RuleLoaderError as exc:
        raise HTTPException(
            status_code=503,
            detail="La base de reglas del sistema experto no está disponible.",
        ) from exc
    except InferenceError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Error controlado del motor de inferencia: {exc}",
        ) from exc
