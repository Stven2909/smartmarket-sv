"""Regresión comparativa determinista entre versiones aisladas de las reglas."""

import json
from hashlib import sha256

from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.inference_engine import run_inference_with_rules
from app.expert_system.models import ProductionRule
from app.schemas.rule_regression import (
    RuleChange,
    RuleRegressionRequest,
    RuleRegressionResponse,
    RuleSnapshot,
    ScenarioRegression,
)


def _fingerprint(snapshot: RuleSnapshot) -> str:
    rules = [
        rule.model_dump(mode="json")
        for rule in sorted(snapshot.reglas, key=lambda item: item.id)
    ]
    raw = json.dumps(rules, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


def _diff_rules(before: list[ProductionRule], after: list[ProductionRule]) -> list[RuleChange]:
    baseline = {rule.id: rule for rule in before}
    candidate = {rule.id: rule for rule in after}
    changes: list[RuleChange] = []

    for identifier in sorted(set(baseline) | set(candidate)):
        if identifier not in baseline:
            changes.append(RuleChange(regla=identifier, tipo="AGREGADA", campos=[]))
            continue
        if identifier not in candidate:
            changes.append(RuleChange(regla=identifier, tipo="RETIRADA", campos=[]))
            continue

        old = baseline[identifier].model_dump(mode="json")
        new = candidate[identifier].model_dump(mode="json")
        changed = [
            key for key in sorted(old)
            if old[key] != new[key]
        ]
        if changed:
            changes.append(
                RuleChange(regla=identifier, tipo="MODIFICADA", campos=changed)
            )
    return changes


def compare_rule_versions(request: RuleRegressionRequest) -> RuleRegressionResponse:
    """Evalúa idénticos hechos con ambas versiones, sin modificar producción."""

    changes = _diff_rules(request.anterior.reglas, request.propuesta.reglas)
    results = []
    for scenario in request.escenarios:
        before = run_inference_with_rules(scenario.hechos, request.anterior.reglas)
        after = run_inference_with_rules(scenario.hechos, request.propuesta.reglas)
        before_critical = bool(
            set(before["activated_rules"]) & CRITICAL_RULE_IDS
        )
        critical_regression = (
            before_critical
            and before["level"] == "NO_RECOMENDABLE"
            and after["level"] in {"BUENA", "EXCELENTE"}
        )
        results.append(
            ScenarioRegression(
                escenario=scenario.nombre,
                alternativa_id=scenario.hechos.alternativa_id,
                nivel_anterior=before["level"],
                nivel_propuesto=after["level"],
                regla_anterior=before["winning_rule"],
                regla_propuesta=after["winning_rule"],
                reglas_activas_anteriores=before["activated_rules"],
                reglas_activas_propuestas=after["activated_rules"],
                explicacion_anterior=before["explanation"],
                explicacion_propuesta=after["explanation"],
                indice_anterior=before["indice_conveniencia"],
                indice_propuesto=after["indice_conveniencia"],
                cambio_nivel=before["level"] != after["level"],
                cambio_regla=before["winning_rule"] != after["winning_rule"],
                cambio_activaciones=before["activated_rules"] != after["activated_rules"],
                cambio_explicacion=before["explanation"] != after["explanation"],
                regresion_critica=critical_regression,
            )
        )

    count_critical = sum(row.regresion_critica for row in results)
    warnings = [
        "Las etiquetas de versión son proporcionadas por el solicitante; "
        "las huellas SHA-256 identifican el contenido efectivo de cada base.",
        "Las diferencias proceden solo de los hechos ensayados. "
        "No son una garantía de equivalencia para todos los escenarios posibles.",
        "No se aplican cambios a data/rules.json ni al endpoint /recommend.",
        "El índice auxiliar usa los mismos hechos y pesos; "
        "comparar únicamente reglas no modifica ese índice.",
    ]
    if count_critical:
        warnings.append(
            "Se detectó al menos una regresión crítica: una alternativa con "
            "riesgo activo en la versión anterior pasó a nivel favorable. "
            "Revisar prioridades y reglas antes de cualquier publicación."
        )

    return RuleRegressionResponse(
        version_anterior=request.anterior.etiqueta,
        version_propuesta=request.propuesta.etiqueta,
        huella_anterior=_fingerprint(request.anterior),
        huella_propuesta=_fingerprint(request.propuesta),
        reglas_agregadas=sum(x.tipo == "AGREGADA" for x in changes),
        reglas_retiradas=sum(x.tipo == "RETIRADA" for x in changes),
        reglas_modificadas=sum(x.tipo == "MODIFICADA" for x in changes),
        cambios_reglas=changes,
        escenarios_evaluados=len(results),
        cambios_nivel=sum(x.cambio_nivel for x in results),
        cambios_regla_ganadora=sum(x.cambio_regla for x in results),
        cambios_activaciones=sum(x.cambio_activaciones for x in results),
        cambios_explicacion=sum(x.cambio_explicacion for x in results),
        regresiones_criticas=count_critical,
        resultados=results,
        advertencias=warnings,
    )
