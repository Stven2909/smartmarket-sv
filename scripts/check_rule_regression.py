"""Puerta de calidad de reglas para GitHub Actions (HU-14).

Compara dos archivos JSON de reglas sobre escenarios reproducibles.
No escribe reglas, no invoca la red ni necesita credenciales de GitHub.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.rule_auditor import _representative_requests, audit_rules
from app.expert_system.rule_loader import load_rules
from app.schemas.rule_regression import (
    RegressionScenario,
    RuleRegressionRequest,
    RuleSnapshot,
)
from app.services.rule_regression_service import compare_rule_versions

BLOCKING_FINDINGS = frozenset(
    {
        "ID_DUPLICADO",
        "CONDICIONES_INCOMPATIBLES",
        "HECHO_NO_BOOLEANO",
        "CONDICIONES_DUPLICADAS",
        "SALIDAS_DIVERGENTES",
        "REGLA_SOMBREADA",
    }
)


def scenarios_from_file(path: Path) -> list[RegressionScenario]:
    """Valida los escenarios de la demostración con el contrato de Python."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("La lista de escenarios de prueba está vacía o es inválida.")
    return [
        RegressionScenario.model_validate(
            {"nombre": row["name"], "hechos": row["facts"]}
        )
        for row in raw
    ]


def _cases(
    demo: list[RegressionScenario], *, representative: bool
) -> list[RegressionScenario]:
    result = list(demo)
    if representative:
        for index, request in enumerate(_representative_requests(), start=1):
            result.append(
                RegressionScenario(
                    nombre=f"Clase sintética {index:04}",
                    hechos=request,
                )
            )
    return result


def check_changes(
    baseline_path: Path,
    proposed_path: Path,
    scenarios_path: Path,
    *,
    representative: bool = True,
) -> dict[str, Any]:
    """Evalúa el mismo motor con dos snapshots; bloquea pérdidas de protección."""

    previous = RuleSnapshot(
        etiqueta="versión base", reglas=load_rules(baseline_path)
    )
    candidate = RuleSnapshot(
        etiqueta="versión propuesta", reglas=load_rules(proposed_path)
    )
    demo_cases = scenarios_from_file(scenarios_path)
    cases = _cases(demo_cases, representative=representative)
    audit = audit_rules(candidate.reglas)

    baseline_issues = audit_rules(previous.reglas)
    base_blocking = {
        (issue.tipo, tuple(issue.reglas))
        for issue in baseline_issues.hallazgos
        if issue.tipo in BLOCKING_FINDINGS
    }
    # Solo los hallazgos nuevos bloquean. Un problema anterior sigue
    # señalándose, pero no impide una corrección parcial de las reglas.
    issues = [
        issue.model_dump(mode="json")
        for issue in audit.hallazgos
        if issue.tipo in BLOCKING_FINDINGS
        and (issue.tipo, tuple(issue.reglas)) not in base_blocking
    ]
    total = {
        "casos": 0,
        "cambios_nivel": 0,
        "cambios_regla": 0,
        "cambios_activaciones": 0,
        "cambios_explicacion": 0,
        "regresiones_criticas": 0,
        "perdidas_proteccion": 0,
    }
    critical_examples: list[dict[str, Any]] = []
    ordinary_examples: list[dict[str, Any]] = []
    for start in range(0, len(cases), 10):
        response = compare_rule_versions(
            RuleRegressionRequest(
                anterior=previous,
                propuesta=candidate,
                escenarios=cases[start : start + 10],
            )
        )
        total["casos"] += response.escenarios_evaluados
        total["cambios_nivel"] += response.cambios_nivel
        total["cambios_regla"] += response.cambios_regla_ganadora
        total["cambios_activaciones"] += response.cambios_activaciones
        total["cambios_explicacion"] += response.cambios_explicacion
        total["regresiones_criticas"] += response.regresiones_criticas
        for row in response.resultados:
            missing_critical = sorted(
                (set(row.reglas_activas_anteriores) & CRITICAL_RULE_IDS)
                - set(row.reglas_activas_propuestas)
            )
            if missing_critical:
                total["perdidas_proteccion"] += 1
            relevant = (
                row.cambio_nivel
                or row.cambio_regla
                or row.cambio_activaciones
                or missing_critical
            )
            dangerous = row.regresion_critica or bool(missing_critical)
            destination = critical_examples if dangerous else ordinary_examples
            if relevant and len(destination) < 15:
                destination.append(
                    {
                        "escenario": row.escenario,
                        "nivel_anterior": row.nivel_anterior,
                        "nivel_propuesto": row.nivel_propuesto,
                        "regla_anterior": row.regla_anterior,
                        "regla_propuesta": row.regla_propuesta,
                        "regresion_critica": row.regresion_critica,
                        "protecciones_perdidas": missing_critical,
                    }
                )

    blocked = bool(
        issues
        or total["regresiones_criticas"]
        or total["perdidas_proteccion"]
    )
    return {
        "resultado": "BLOQUEADO" if blocked else "APROBADO",
        "huella_anterior": response.huella_anterior,
        "huella_propuesta": response.huella_propuesta,
        "cambios_reglas": [
            change.model_dump(mode="json") for change in response.cambios_reglas
        ],
        "metricas": total,
        "hallazgos_nuevos": issues,
        "ejemplos": (critical_examples + ordinary_examples)[:15],
        "advertencias": [
            "Se comparan las mismas entradas con dos bases aisladas de reglas.",
            "Las pérdidas de cobertura de reglas R01–R05 son bloqueantes "
            "incluso cuando el resultado sigue siendo NO_RECOMENDABLE.",
            "Una muestra sin cambios no demuestra equivalencia universal.",
            "Este control no modifica data/rules.json ni las reglas en Render.",
        ],
    }


def markdown_summary(result: dict[str, Any]) -> str:
    """Resumen breve y legible para la pestaña Summary de GitHub Actions."""

    metrics = result["metricas"]
    lines = [
        "## HU-14 · Regresión automática de reglas",
        "",
        f"**Resultado:** {result['resultado']}",
        "",
        "| Métrica | Total |",
        "|---|---:|",
        *[
            f"| {name.replace('_', ' ').capitalize()} | {count} |"
            for name, count in metrics.items()
        ],
        f"| Anomalías estructurales nuevas | {len(result['hallazgos_nuevos'])} |",
        "",
        "Los escenarios son sintéticos, no datos comerciales.",
        "Una comparación aprobada no acredita equivalencia universal.",
        "",
    ]
    if result["ejemplos"]:
        lines.extend(
            [
                "### Ejemplos de cambios observados",
                "",
                "| Escenario | Antes | Propuesta | Protección perdida |",
                "|---|---|---|---|",
            ]
        )
        for row in result["ejemplos"]:
            label = str(row["escenario"]).replace("|", "/").replace("\n", " ")
            before = (
                f"{row['nivel_anterior']} / {row['regla_anterior'] or '-'}"
            )
            after = f"{row['nivel_propuesto']} / {row['regla_propuesta'] or '-'}"
            lost = ", ".join(row["protecciones_perdidas"]) or "-"
            lines.append(f"| {label} | {before} | {after} | {lost} |")
        lines.append("")
    if result["hallazgos_nuevos"]:
        lines.extend(
            ["### Anomalías nuevas", ""]
            + [
                "- "
                + item["tipo"]
                + " en "
                + ", ".join(item["reglas"])
                for item in result["hallazgos_nuevos"][:15]
            ]
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bloquea regresiones críticas entre rules.json base y propuesta."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, default=Path("data/scenarios.json"))
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)

    try:
        result = check_changes(args.baseline, args.candidate, args.scenarios)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        message = f"ERROR: No se pudo validar la propuesta: {exc}"
        print(message, file=sys.stderr)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with Path(summary).open("a", encoding="utf-8") as handle:
                handle.write("## HU-14 · Error de validación\n\n" + message + "\n")
        return 2

    if args.json_output:
        args.json_output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    summary_text = markdown_summary(result)
    print(summary_text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(summary_text)
    return 1 if result["resultado"] == "BLOQUEADO" else 0


if __name__ == "__main__":
    raise SystemExit(main())
