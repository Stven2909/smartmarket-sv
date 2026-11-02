"""Diagnóstico declarativo basado en la traza, sin alterar hechos ni reglas."""

from app.expert_system.classifiers import THRESHOLDS
from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.rule_loader import load_rules
from app.schemas.diagnosis import (
    CriticalRisk,
    DiagnosisRequest,
    DiagnosisResponse,
    MissingCondition,
    RuleOpportunity,
)
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import recommend


def _orientation(name: str, item: RecommendationRequest) -> str:
    """Describe un requisito observable, sin crear ni estimar datos comerciales."""

    descriptions = {
        "dentro_presupuesto": (
            f"Costo actual: {item.costo_total:.2f}; presupuesto: {item.presupuesto:.2f}. "
            "Revisar el costo para que no supere el presupuesto."
        ),
        "todos_esenciales_disponibles": (
            "Comprobar disponibilidad de "
            f"{item.productos_esenciales_totales - item.productos_esenciales_disponibles} "
            "producto(s) esencial(es) pendiente(s)."
        ),
        "distancia_cercana": (
            f"Distancia adicional actual: {item.distancia_adicional_km:.2f} km. "
            f"La condición requiere como máximo {THRESHOLDS['distancia_cercana_max_km']:.2f} km."
        ),
        "tiempo_bajo": (
            f"Tiempo estimado: {item.tiempo_estimado_min:.2f} min. "
            f"La condición requiere como máximo {THRESHOLDS['tiempo_bajo_max_min']:.2f} min."
        ),
        "una_parada": (
            f"Cantidad actual de supermercados: {item.numero_supermercados}. "
            "La condición exige exactamente uno."
        ),
        "dos_paradas": (
            f"Cantidad actual de supermercados: {item.numero_supermercados}. "
            "La condición exige exactamente dos."
        ),
        "ahorro_alto": (
            f"Ahorro informado: {item.ahorro:.2f}. "
            f"El umbral de ahorro alto es {THRESHOLDS['ahorro_alto_min']:.2f}."
        ),
        "promociones_relevantes": (
            "No hay promociones aplicables registradas en los hechos. "
            "Solo indicar que existen si fueron comprobadas por el origen de datos."
        ),
    }
    return descriptions.get(name, f"Revisar la condición '{name}' en los datos de entrada.")


def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """Muestra oportunidades lógicas y riesgos sin proponer hechos ficticios."""

    facts = request.alternativa
    result = recommend(facts)
    rule_map = {rule.id: rule for rule in load_rules()}
    trace_map = {entry["rule_id"]: entry for entry in result.trace}

    risks = [
        CriticalRisk(regla=rule.id, motivo=rule.result.explanation)
        for rule in sorted(rule_map.values(), key=lambda r: (r.priority, r.id))
        if rule.id in CRITICAL_RULE_IDS and rule.id in result.reglas_activadas
    ]
    opportunities = []
    for rule in rule_map.values():
        if rule.result.level not in {"BUENA", "EXCELENTE"}:
            continue
        audit = trace_map[rule.id]
        missing = [
            MissingCondition(
                hecho=name,
                valor_esperado=condition["expected"],
                valor_actual=condition["actual"],
                orientacion=_orientation(name, facts),
            )
            for name, condition in audit["conditions"].items()
            if not condition["matched"]
        ]
        opportunities.append(
            RuleOpportunity(
                regla=rule.id,
                nivel_posible=rule.result.level,
                prioridad=rule.priority,
                condiciones_cumplidas=len(audit["matched_conditions"]),
                condiciones_totales=len(audit["conditions"]),
                activa=audit["activated"],
                faltantes=missing,
            )
        )
    opportunities.sort(
        key=lambda option: (
            len(option.faltantes),
            0 if option.nivel_posible == "EXCELENTE" else 1,
            option.prioridad,
            option.regla,
        )
    )

    if risks:
        summary = (
            "Existen reglas críticas activas. Cumplir una condición favorable "
            "no garantiza una recomendación positiva mientras persistan esos riesgos."
        )
    elif result.winning_rule is None:
        summary = (
            "Ninguna regla ganó. Se muestran requisitos pendientes de las reglas favorables, "
            "pero no se asegura que se alcancen."
        )
    else:
        summary = (
            f"El dictamen actual es {result.nivel_recomendacion}, determinado por "
            f"{result.winning_rule}. Se muestran las condiciones de las otras reglas favorables."
        )

    return DiagnosisResponse(
        alternativa_id=facts.alternativa_id,
        nivel_actual=result.nivel_recomendacion,
        regla_ganadora=result.winning_rule,
        riesgos_criticos=risks,
        oportunidades=opportunities,
        resumen=summary,
        advertencias=[
            "Los requisitos se derivan de reglas actuales, no de predicciones ni precios reales.",
            "Las condiciones son lógicas y no constituyen una optimización automática.",
            "No se modifican los hechos enviados por el backend.",
        ],
    )
