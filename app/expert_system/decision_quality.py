"""Advisory-only guards for commercially questionable positive decisions.

These flags never decide a level, change the winning rule or estimate missing
fuel, delivery or opportunity costs. They reuse already-derived facts.
"""

from app.schemas.recommendation import RecommendationRequest

FAVORABLE_LEVELS = frozenset({"BUENA", "EXCELENTE"})
TRAVEL_REVIEW = "TRAYECTO_A_REVISAR"
LOW_INDEX = "INDICE_BAJO_CON_DICTAMEN_FAVORABLE"
INCOMPLETE_EXCELLENT = "EXCELENTE_CON_LISTA_INCOMPLETA"


def decision_quality_flags(
    *,
    level: str,
    facts: dict[str, bool | float],
    convenience_classification: str | None,
) -> tuple[str, ...]:
    """Report conflicts of interpretation, not failed expert-system rules."""

    if level not in FAVORABLE_LEVELS:
        return ()

    flags: list[str] = []
    if facts.get("distancia_lejana") is True or facts.get("tiempo_alto") is True:
        flags.append(TRAVEL_REVIEW)
    if convenience_classification == "BAJA_CONVENIENCIA":
        flags.append(LOW_INDEX)
    coverage = facts.get("porcentaje_productos_disponibles")
    if (
        level == "EXCELENTE"
        and isinstance(coverage, (int, float))
        and coverage < 100
    ):
        flags.append(INCOMPLETE_EXCELLENT)
    return tuple(flags)


def decision_quality_advisories(
    flags: tuple[str, ...],
    request: RecommendationRequest,
) -> list[str]:
    """Explain the flags using only the original 14 facts, without estimates."""

    warnings = []
    if TRAVEL_REVIEW in flags:
        warnings.append(
            "Aviso comercial: el trayecto de "
            f"{request.distancia_adicional_km:.2f} km adicionales y "
            f"{request.tiempo_estimado_min:.2f} min alcanza al menos uno "
            "de los umbrales de desplazamiento alto del prototipo "
            "(8 km adicionales o 45 min). Compruebe el costo real del traslado "
            "antes de considerar el ahorro o la promoción como ventaja neta."
        )
    if LOW_INDEX in flags:
        warnings.append(
            "Aviso comercial: el índice ponderado es bajo pese al dictamen "
            "favorable. La regla ganadora no garantiza que esta opción "
            "sea la más conveniente entre las disponibles."
        )
    if INCOMPLETE_EXCELLENT in flags:
        coverage = request.productos_disponibles / request.productos_totales * 100
        warnings.append(
            "Aviso comercial: EXCELENTE se refiere a los criterios de la "
            f"regla, no a la lista completa; solo {coverage:.1f}% "
            "de los productos está disponible. Revise los opcionales faltantes."
        )
    return warnings
