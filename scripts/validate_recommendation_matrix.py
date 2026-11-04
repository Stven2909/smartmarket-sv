"""HU-35: independent, offline acceptance matrix for the 16 expert rules.

Expected winners and levels are explicitly reviewed in a synthetic JSON
fixture. This gate never rewrites expected outcomes using live inference.
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.decision_quality import (
    decision_quality_advisories,
    decision_quality_flags,
)
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION
from app.services.recommendation_service import recommend
from scripts.check_inference_consistency import check_inference_consistency

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data" / "scenarios_hu35.json"
ALLOWED_SOURCES = frozenset({
    "data/scenarios.json",
    "data/scenarios_hu28.json",
    "data/scenarios_hu29.json",
    "data/scenarios_hu30.json",
})
VALID_LEVELS = frozenset({"EXCELENTE", "BUENA", "NO_RECOMENDABLE"})


def _expected(row: dict[str, Any]) -> dict[str, Any]:
    expected = row.get("expected")
    if not isinstance(expected, dict):
        raise ValueError(f"{row.get('id')}: falta expected")
    if "winner" not in expected or "level" not in expected:
        raise ValueError(f"{row.get('id')}: expected requiere winner y level")
    if expected["level"] not in VALID_LEVELS:
        raise ValueError(f"{row.get('id')}: nivel esperado inválido")
    winner = expected["winner"]
    if winner is not None and (
        not isinstance(winner, str)
        or winner not in {rule.id for rule in load_rules()}
    ):
        raise ValueError(f"{row.get('id')}: regla ganadora esperada desconocida")
    for name in ("required_active", "expected_flags"):
        if name in expected and (
            not isinstance(expected[name], list)
            or not all(isinstance(item, str) for item in expected[name])
        ):
            raise ValueError(f"{row.get('id')}: {name} debe ser lista de textos")
    if "expected_facts" in expected and not isinstance(
        expected["expected_facts"], dict
    ):
        raise ValueError(f"{row.get('id')}: expected_facts debe ser objeto")
    return expected


def load_validation_matrix(
    path: Path = MATRIX,
) -> tuple[
    list[tuple[str, str, RecommendationRequest, dict[str, Any]]],
    list[tuple[str, dict[str, Any]]],
]:
    """Load curated oracle and reject duplicate, missing or invalid fixtures."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version_matriz") != "1.0":
        raise ValueError("Versión de la matriz HU-35 no reconocida")
    if payload.get("tipo_datos") != "SINTETICOS_NO_ETIQUETADOS":
        raise ValueError("HU-35 solo acepta datos sintéticos declarados")
    base = payload["base_request"]
    if not isinstance(base, dict):
        raise ValueError("base_request debe ser un objeto")

    rows: list[tuple[str, str, RecommendationRequest, dict[str, Any]]] = []
    seen: set[str] = set()
    source_data: dict[str, dict[str, dict[str, Any]]] = {}

    def register(case_id: str) -> None:
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Hay un ID de escenario vacío o inválido")
        if case_id in seen:
            raise ValueError(f"Escenario duplicado: {case_id}")
        seen.add(case_id)

    for entry in payload["reference_cases"]:
        name = entry["source"]
        if name not in ALLOWED_SOURCES:
            raise ValueError(f"Origen fuera de la lista de referencia: {name}")
        if name not in source_data:
            data = json.loads((ROOT / name).read_text(encoding="utf-8"))
            source_data[name] = {item["id"]: item["facts"] for item in data}
        case_id = entry["id"]
        register(case_id)
        if case_id not in source_data[name]:
            raise ValueError(f"{case_id}: ya no figura en {name}")
        request = RecommendationRequest.model_validate(source_data[name][case_id])
        rows.append((case_id, "referencia", request, _expected(entry)))

    for entry in payload["cases"]:
        case_id = entry["id"]
        register(case_id)
        changes = entry.get("changes", {})
        if not isinstance(changes, dict):
            raise ValueError(f"{case_id}: changes debe ser objeto")
        if not isinstance(entry.get("category"), str) or not entry["category"]:
            raise ValueError(f"{case_id}: category es obligatorio")
        request = RecommendationRequest.model_validate({
            **base,
            **changes,
            "request_id": f"hu35-{case_id}",
            "alternativa_id": f"hu35-{case_id}",
        })
        rows.append((case_id, entry["category"], request, _expected(entry)))

    invalid: list[tuple[str, dict[str, Any]]] = []
    for entry in payload["invalid_cases"]:
        case_id = entry["id"]
        register(case_id)
        invalid_payload = {**base, **entry.get("changes", {})}
        for field in entry.get("remove", []):
            invalid_payload.pop(field, None)
        invalid.append((case_id, invalid_payload))

    if not rows or not invalid or len(rows) < 17:
        raise ValueError("HU-35 requiere referencias, fronteras y datos inválidos")
    if len(RecommendationRequest.model_fields) != 14:
        raise ValueError("El contrato de solicitud dejó de contener 14 campos")
    if len(RecommendationResponse.model_fields) != 16:
        raise ValueError("El contrato de respuesta dejó de contener 16 campos")
    return rows, invalid


def audit_validation_matrix(
    rows: list[tuple[str, str, RecommendationRequest, dict[str, Any]]],
    invalid: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    """Check the manual oracle, explanation consistency and safe rejection."""

    errors: list[str] = []
    groups: Counter[str] = Counter()
    winners: Counter[str] = Counter()
    active_counts: Counter[str] = Counter()
    verified = 0

    for case_id, category, request, expected in rows:
        groups[category] += 1
        answer = recommend(request)
        problems = check_inference_consistency(request, answer)
        if answer.winning_rule != expected["winner"]:
            problems.append(
                f"ganadora: esperado {expected['winner']}, actual {answer.winning_rule}"
            )
        if answer.nivel_recomendacion != expected["level"]:
            problems.append(
                f"nivel: esperado {expected['level']}, actual {answer.nivel_recomendacion}"
            )

        actual_active = set(answer.reglas_activadas)
        for required in expected.get("required_active", []):
            if required not in actual_active:
                problems.append(f"no se activó la regla obligatoria {required}")
        flags = decision_quality_flags(
            level=answer.nivel_recomendacion,
            facts=answer.hechos_derivados,
            convenience_classification=answer.clasificacion_conveniencia,
        )
        required_flags = expected.get("expected_flags", [])
        if set(flags) != set(required_flags):
            problems.append(f"alertas esperadas {required_flags} frente a {list(flags)}")
        actual_advisories = decision_quality_advisories(flags, request)
        for advisory in actual_advisories:
            if advisory not in answer.explicacion:
                problems.append("falta advertencia comercial en la explicación")
        if not flags and "Aviso comercial:" in answer.explicacion:
            problems.append("advertencia comercial inesperada")

        for name, expected_value in expected.get("expected_facts", {}).items():
            actual_value = answer.hechos_derivados.get(name)
            if actual_value is None or (
                type(actual_value) is not type(expected_value)
                or actual_value != expected_value
            ):
                problems.append(
                    f"hecho {name}: esperado {expected_value}, actual {actual_value}"
                )

        if answer.version_contrato != CONTRACT_VERSION:
            problems.append("versión de contrato inesperada")
        if answer.version_reglas != RULES_VERSION:
            problems.append("versión de reglas inesperada")
        if any(rule in CRITICAL_RULE_IDS for rule in actual_active):
            if answer.nivel_recomendacion != "NO_RECOMENDABLE":
                problems.append("regla crítica activada con dictamen favorable")
            if answer.winning_rule not in CRITICAL_RULE_IDS:
                problems.append("regla crítica no prevalece por prioridad")
        if answer.winning_rule:
            winners[answer.winning_rule] += 1
        for rule in actual_active:
            active_counts[rule] += 1
        if not problems:
            verified += 1
        errors.extend(f"{case_id}: {problem}" for problem in problems)

    rejected = 0
    for case_id, candidate in invalid:
        try:
            RecommendationRequest.model_validate(candidate)
        except ValidationError:
            rejected += 1
        else:
            errors.append(f"{case_id}: payload inválido aceptado por el esquema")

    rule_ids = {rule.id for rule in load_rules()}
    uncovered = sorted(rule_ids - set(winners))
    if uncovered:
        errors.append(f"Reglas sin victoria en matriz: {', '.join(uncovered)}")
    if len(rule_ids) != 16:
        errors.append(f"Base de reglas esperada con 16 reglas; hay {len(rule_ids)}")

    return {
        "resultado": "BLOQUEADO" if errors else "APROBADO",
        "tipo_datos": "SINTETICOS_NO_ETIQUETADOS",
        "escenarios_validos": len(rows),
        "escenarios_verificados_sin_error": verified,
        "entradas_invalidas": len(invalid),
        "entradas_invalidas_rechazadas": rejected,
        "grupos": dict(sorted(groups.items())),
        "victorias_por_regla": dict(sorted(winners.items())),
        "activaciones_por_regla": dict(sorted(active_counts.items())),
        "reglas_sin_victoria": uncovered,
        "errores": errors[:40],
        "total_errores": len(errors),
        "limitaciones": (
            "Oráculos sintéticos acordes con reglas actuales; no son decisiones "
            "etiquetadas por compradores ni demuestran precisión comercial."
        ),
    }


def markdown_summary(result: dict[str, Any]) -> str:
    lines = [
        "## HU-35 · Matriz de aceptación de recomendaciones",
        "",
        f"**Resultado:** {result['resultado']}",
        f"**Escenarios válidos:** {result['escenarios_validos']}",
        "**Verificados sin error:** "
        f"{result['escenarios_verificados_sin_error']}",
        "**Payloads inválidos rechazados:** "
        f"{result['entradas_invalidas_rechazadas']}/{result['entradas_invalidas']}",
        f"**Reglas con victoria:** {len(result['victorias_por_regla'])}/16",
        f"**Incoherencias:** {result['total_errores']}",
        "",
        "| Tipo de caso | Escenarios |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {name} | {count} |"
        for name, count in result["grupos"].items()
    )
    if result["errores"]:
        lines.extend(["", "**Primeras incidencias:**"])
        lines.extend(f"- {issue}" for issue in result["errores"][:12])
    lines.extend([
        "",
        "Resultados sintéticos: no evalúan acierto ante personas ni compras reales.",
    ])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=MATRIX)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    try:
        rows, invalid = load_validation_matrix(args.fixture)
        result = audit_validation_matrix(rows, invalid)
        summary = markdown_summary(result)
        print(summary)
        if args.json_output:
            args.json_output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open(
                "a", encoding="utf-8"
            ) as output:
                output.write(summary)
        return 1 if result["resultado"] == "BLOQUEADO" else 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"Matriz HU-35 inválida: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
