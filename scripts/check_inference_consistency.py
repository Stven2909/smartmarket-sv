"""HU-25: independent, read-only consistency checks for an expert decision.

This module is run by tests/CI, not inside the FastAPI request path.
It never modifies Laravel, rules, a database or the production response.
"""

from app.expert_system.classifiers import derive_facts
from app.expert_system.convenience_index import (
    CRITICAL_RULE_IDS,
    calculate_convenience_index,
)
from app.expert_system.explanation_builder import DEFAULT_CONCLUSION
from app.expert_system.models import ProductionRule
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse


def check_inference_consistency(
    request: RecommendationRequest,
    answer: RecommendationResponse,
    rules: list[ProductionRule] | None = None,
) -> list[str]:
    """Return exact, actionable violations without changing the recommendation."""
    if rules is None:
        rules = load_rules()
    errors: list[str] = []
    expected_facts = derive_facts(request)
    if answer.request_id != request.request_id:
        errors.append("request_id no coincide con la solicitud")
    if answer.hechos_derivados != expected_facts:
        errors.append("hechos_derivados no coinciden con los hechos calculados")

    ordered = sorted(rules, key=lambda rule: rule.id)
    known = {rule.id: rule for rule in ordered}
    entries = answer.trace
    if [item.get("rule_id") for item in entries] != [rule.id for rule in ordered]:
        errors.append("trace no contiene exactamente las reglas ordenadas por ID")

    active: list[ProductionRule] = []
    for rule in ordered:
        entry = next((x for x in entries if x.get("rule_id") == rule.id), None)
        if entry is None:
            continue
        expected_matched: list[str] = []
        expected_unmatched: list[str] = []
        conditions = entry.get("conditions")
        if not isinstance(conditions, dict) or set(conditions) != set(rule.conditions):
            errors.append(f"{rule.id}: conditions no reflejan la definición de reglas")
            continue

        for name, expected_value in rule.conditions.items():
            actual_value = expected_facts.get(name)
            matched = (
                type(actual_value) is type(expected_value)
                and actual_value == expected_value
            )
            (expected_matched if matched else expected_unmatched).append(name)
            evidence = conditions[name]
            if not isinstance(evidence, dict) or evidence != {
                "expected": expected_value,
                "actual": actual_value,
                "matched": matched,
            }:
                errors.append(f"{rule.id}: evidencia incorrecta para {name}")

        activated = not expected_unmatched
        if activated:
            active.append(rule)
        if entry.get("evaluated") is not True or entry.get("activated") is not activated:
            errors.append(f"{rule.id}: bandera de activación incorrecta")
        if entry.get("matched_conditions") != expected_matched:
            errors.append(f"{rule.id}: condiciones coincidentes inconsistentes")
        if entry.get("unmatched_conditions") != expected_unmatched:
            errors.append(f"{rule.id}: condiciones pendientes inconsistentes")
        reason = (
            "Todas las condiciones se cumplieron."
            if activated else
            "Condiciones no cumplidas: " + ", ".join(expected_unmatched) + "."
        )
        if entry.get("reason") != reason:
            errors.append(f"{rule.id}: explicación de condiciones incorrecta")

    active_ids = [rule.id for rule in active]
    if answer.reglas_activadas != active_ids:
        errors.append("reglas_activadas no coincide con la evaluación de todas las reglas")

    priority_order = sorted(active, key=lambda rule: (rule.priority, rule.id))
    winner = priority_order[0] if priority_order else None
    expected_losers = [rule.id for rule in priority_order[1:]]
    if answer.winning_rule != (winner.id if winner else None):
        errors.append("winning_rule no respeta prioridad e ID")
    if answer.losing_rules != expected_losers:
        errors.append("losing_rules no respeta el orden de resolución de conflictos")

    if winner is not None:
        if answer.nivel_recomendacion != winner.result.level:
            errors.append("nivel_recomendacion contradice la regla ganadora")
        if answer.accion_sugerida != winner.result.action:
            errors.append("accion_sugerida contradice la regla ganadora")
        if not answer.explicacion.startswith(winner.result.explanation):
            errors.append("explicacion no corresponde a la regla ganadora")
        if answer.prioridad_aplicada != winner.category:
            errors.append("prioridad_aplicada contradice la regla ganadora")
    else:
        if answer.nivel_recomendacion != DEFAULT_CONCLUSION["level"]:
            errors.append("Sin regla, el nivel debe ser provisional NO_RECOMENDABLE")
        if answer.prioridad_aplicada != "SIN_REGLA":
            errors.append("Sin regla, prioridad_aplicada debe ser SIN_REGLA")

    if any(rule.id in CRITICAL_RULE_IDS for rule in active):
        if answer.nivel_recomendacion != "NO_RECOMENDABLE":
            errors.append("Una regla crítica activada exige NO_RECOMENDABLE")

    convenience = calculate_convenience_index(request)
    if answer.indice_conveniencia != convenience["indice_conveniencia"]:
        errors.append("indice_conveniencia no corresponde a sus componentes")
    if answer.clasificacion_conveniencia != convenience["clasificacion_conveniencia"]:
        errors.append("clasificacion_conveniencia no corresponde al índice")
    if answer.componentes_conveniencia != convenience["componentes_conveniencia"]:
        errors.append("componentes_conveniencia no corresponden a los hechos")
    if answer.pesos_conveniencia != convenience["pesos"]:
        errors.append("pesos_conveniencia no corresponden a los pesos vigentes")

    # This also makes it obvious if rule definitions were replaced without
    # updating the trace in a later release.
    if set(answer.reglas_activadas) - set(known):
        errors.append("reglas_activadas contiene IDs inexistentes")
    return errors
