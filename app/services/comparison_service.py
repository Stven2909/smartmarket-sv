"""Comparación experta determinista de alternativas independientes."""

from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.schemas.comparison import (
    ComparisonRequest,
    ComparisonResponse,
    RankedAlternative,
)
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import recommend

RANKING_CRITERION = (
    "Primero la conclusión experta (EXCELENTE, BUENA, sin regla, riesgo crítico); "
    "después el índice auxiliar de conveniencia, el costo y el ID como desempates. "
    "El índice no convierte una alternativa de riesgo en recomendable."
)


def _tier(result: RecommendationResponse) -> int:
    if result.nivel_recomendacion == "EXCELENTE":
        return 0
    if result.nivel_recomendacion == "BUENA":
        return 1
    if result.winning_rule is None:
        return 2
    return 3


def _sort_key(
    item: tuple[str, float, RecommendationResponse],
) -> tuple[int, float, float, str]:
    alternative_id, cost, result = item
    index = result.indice_conveniencia or 0.0
    return (_tier(result), -index, cost, alternative_id)


def compare_alternatives(request: ComparisonRequest) -> ComparisonResponse:
    """Evalúa por separado y ordena sin cambiar la inferencia de cada opción."""

    evaluated = [
        (option.alternativa_id, option.costo_total, recommend(option))
        for option in request.alternativas
    ]
    ranked = sorted(evaluated, key=_sort_key)
    alternatives: list[RankedAlternative] = []
    for position, (alternative_id, cost, result) in enumerate(ranked, start=1):
        critical = bool(set(result.reglas_activadas) & CRITICAL_RULE_IDS)
        if critical:
            reason = (
                "Existe una regla de riesgo crítica. El índice es solo informativo."
            )
        elif result.winning_rule is None:
            reason = "Ninguna regla se activó; clasificación provisional."
        else:
            reason = (
                f"Regla {result.winning_rule}, nivel {result.nivel_recomendacion}; "
                f"índice auxiliar {result.indice_conveniencia:.2f}/100."
            )
        alternatives.append(
            RankedAlternative(
                posicion=position,
                alternativa_id=alternative_id,
                costo_total=cost,
                riesgo_critico=critical,
                motivo_posicion=reason,
                recomendacion=result,
            )
        )

    warnings = [
        "El ranking es una comparación académica del servicio Python, "
        "no sustituye el ordenamiento económico de Laravel.",
        "Los pesos y umbrales son parámetros explicables, no probabilidades "
        "ni valores aprendidos por inteligencia artificial.",
    ]
    if all(_tier(row.recomendacion) >= 2 for row in alternatives):
        warnings.append(
            "Ninguna opción tiene una regla favorable; la primera posición "
            "solo significa la menos desfavorable entre las comparadas."
        )

    return ComparisonResponse(
        mejor_alternativa_id=alternatives[0].alternativa_id,
        criterio_orden=RANKING_CRITERION,
        ranking=alternatives,
        advertencias=warnings,
    )
