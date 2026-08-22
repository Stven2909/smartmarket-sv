from typing import Any

from app.expert_system.classifiers import derive_facts
from app.expert_system.conflict_resolver import resolve_conflicts
from app.expert_system.explanation_builder import build_inference_result
from app.expert_system.models import ProductionRule
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest


class InferenceError(ValueError):
    """Error controlado durante la evaluación de hechos y reglas."""


def _evaluate_rule_with_trace(
    rule: ProductionRule, facts: dict[str, bool | float]
) -> tuple[bool, dict[str, Any]]:
    condition_trace: dict[str, dict[str, Any]] = {}
    missing_facts: list[str] = []

    for fact_name, expected_value in rule.conditions.items():
        if fact_name not in facts:
            missing_facts.append(fact_name)
            condition_trace[fact_name] = {
                "expected": expected_value,
                "actual": None,
                "matched": False,
            }
            continue

        actual_value = facts[fact_name]
        matched = type(actual_value) is type(expected_value) and (
            actual_value == expected_value
        )
        condition_trace[fact_name] = {
            "expected": expected_value,
            "actual": actual_value,
            "matched": matched,
        }

    if missing_facts:
        raise InferenceError(
            f"La regla {rule.id} requiere hechos inexistentes: "
            f"{', '.join(sorted(missing_facts))}"
        )

    activated = all(
        condition["matched"] for condition in condition_trace.values()
    )
    matched_conditions = [
        name for name, condition in condition_trace.items() if condition["matched"]
    ]
    unmatched_conditions = [
        name
        for name, condition in condition_trace.items()
        if not condition["matched"]
    ]

    trace = {
        "rule_id": rule.id,
        "evaluated": True,
        "activated": activated,
        "conditions": condition_trace,
        "matched_conditions": matched_conditions,
        "unmatched_conditions": unmatched_conditions,
        "reason": (
            "Todas las condiciones se cumplieron."
            if activated
            else "Una o más condiciones no se cumplieron."
        ),
    }
    return activated, trace


def evaluate_rule(
    rule: ProductionRule, facts: dict[str, bool | float]
) -> bool:
    """Evalúa una regla con lógica AND y devuelve si se activó."""

    activated, _ = _evaluate_rule_with_trace(rule, facts)
    return activated


def get_activated_rules(
    rules: list[ProductionRule], facts: dict[str, bool | float]
) -> list[ProductionRule]:
    """Devuelve todas las reglas cuyas condiciones se cumplieron."""

    activated_rules: list[ProductionRule] = []
    for rule in rules:
        if evaluate_rule(rule, facts):
            activated_rules.append(rule)
    return activated_rules


def _evaluate_all_rules(
    rules: list[ProductionRule], facts: dict[str, bool | float]
) -> tuple[list[ProductionRule], list[dict[str, Any]]]:
    activated_rules: list[ProductionRule] = []
    trace: list[dict[str, Any]] = []

    for rule in rules:
        activated, rule_trace = _evaluate_rule_with_trace(rule, facts)
        trace.append(rule_trace)
        if activated:
            activated_rules.append(rule)

    return activated_rules, trace


def run_inference(
    request: RecommendationRequest, rules_path=None
) -> dict[str, Any]:
    """Ejecuta el flujo completo de inferencia para una solicitud validada."""

    facts = derive_facts(request)
    rules = load_rules(rules_path)
    activated_rules, trace = _evaluate_all_rules(rules, facts)
    conflict = resolve_conflicts(activated_rules)

    return build_inference_result(
        facts=facts,
        trace=trace,
        activated_rules=activated_rules,
        conflict=conflict,
    )
