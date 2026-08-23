from app.expert_system.inference_engine import run_inference
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
)
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION


def recommend(request: RecommendationRequest) -> RecommendationResponse:
    """Adapta la salida interna del experto al contrato HTTP estable."""

    result = run_inference(request)

    return RecommendationResponse(
        request_id=request.request_id,
        nivel_recomendacion=result["level"],
        accion_sugerida=result["action"],
        explicacion=result["explanation"],
        reglas_activadas=result["activated_rules"],
        prioridad_aplicada=result["priority_category"] or "SIN_REGLA",
        hechos_derivados=result["facts"],
        version_reglas=RULES_VERSION,
        version_contrato=CONTRACT_VERSION,
        winning_rule=result["winning_rule"],
        losing_rules=result["losing_rules"],
        trace=result["trace"],
        indice_conveniencia=result["indice_conveniencia"],
        clasificacion_conveniencia=result["clasificacion_conveniencia"],
        componentes_conveniencia=result["componentes_conveniencia"],
        pesos_conveniencia=result["pesos_conveniencia"],
    )
