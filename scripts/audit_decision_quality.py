"""HU-33: deterministic quality audit of favorable expert recommendations.

Read-only. Reports potential policy review, never changes weights, verdicts,
rule definitions, credentials or customer data. The sample is synthetic.
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.decision_quality import (
    INCOMPLETE_EXCELLENT,
    LOW_INDEX,
    NO_ESSENTIALS_DEFINED,
    TRAVEL_REVIEW,
    decision_quality_advisories,
    decision_quality_flags,
)
from app.expert_system.inference_engine import run_inference
from app.schemas.recommendation import RecommendationRequest
from scripts.calibrate_convenience_weights import load_cases

EXTREME = {
    "request_id": "hu33-audit",
    "alternativa_id": "hu33-alternativa",
    "costo_total": 45.0,
    "presupuesto": 50.0,
    "ahorro": 11.0,
    "distancia_km": 101.0,
    "distancia_adicional_km": 100.0,
    "tiempo_estimado_min": 200.0,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 5,
    "productos_esenciales_totales": 5,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}

TARGETED: tuple[tuple[str, dict[str, Any]], ...] = (
    ("r07-trayecto-extremo", {}),
    ("r08-trayecto-extremo", {"numero_supermercados": 2,
                             "promociones_aplicables": False}),
    ("r07-debajo-umbrales", {"distancia_adicional_km": 7.99,
                             "tiempo_estimado_min": 44.99}),
    ("r07-exacto-8-km", {"distancia_adicional_km": 8.0,
                          "tiempo_estimado_min": 44.99}),
    ("r07-exacto-45-min", {"distancia_adicional_km": 7.99,
                            "tiempo_estimado_min": 45.0}),
    ("r13-cobertura-parcial", {"ahorro": 1, "distancia_km": 1,
                                "distancia_adicional_km": 1,
                                "tiempo_estimado_min": 10,
                                "productos_disponibles": 5,
                                "productos_esenciales_disponibles": 1,
                                "productos_esenciales_totales": 1,
                                "promociones_aplicables": False}),
    ("r06-lista-incompleta", {"ahorro": 1, "distancia_km": 1,
                                  "distancia_adicional_km": 1,
                                  "tiempo_estimado_min": 10,
                                  "productos_disponibles": 8,
                                  "productos_esenciales_disponibles": 1,
                                  "productos_esenciales_totales": 1,
                                  "promociones_aplicables": False}),
    ("sin-esenciales-completa", {"ahorro": 10,
                                   "distancia_km": 1,
                                   "distancia_adicional_km": 1,
                                   "tiempo_estimado_min": 10,
                                   "productos_esenciales_disponibles": 0,
                                   "productos_esenciales_totales": 0}),
    ("sin-esenciales-cobertura-70", {"ahorro": 10,
                                       "distancia_km": 1,
                                       "distancia_adicional_km": 1,
                                       "tiempo_estimado_min": 10,
                                       "productos_disponibles": 7,
                                       "productos_esenciales_disponibles": 0,
                                       "productos_esenciales_totales": 0}),
    ("r10-prioridad-sobre-r03", {"ahorro": 1,
                                  "distancia_adicional_km": 9,
                                  "tiempo_estimado_min": 30,
                                  "productos_disponibles": 3,
                                  "productos_esenciales_disponibles": 1,
                                  "productos_esenciales_totales": 1,
                                  "promociones_aplicables": False}),
)


def quality_cases(*, with_grid: bool = False):
    cases = load_cases(with_grid=with_grid)
    for name, changes in TARGETED:
        cases.append(
            (name, RecommendationRequest.model_validate({
                **EXTREME, **changes,
                "alternativa_id": name,
            }))
        )
    return cases


def audit_quality(
    cases: list[tuple[str, RecommendationRequest]],
    *,
    max_examples: int = 12,
) -> dict[str, Any]:
    if not cases:
        raise ValueError("Se requieren escenarios sintéticos.")
    if not 0 <= max_examples <= 100:
        raise ValueError("max_examples debe estar entre 0 y 100.")

    counts: Counter[str] = Counter()
    rules: Counter[str] = Counter()
    problems: list[str] = []
    examples: list[dict[str, Any]] = []

    for identifier, request in cases:
        outcome = run_inference(request)
        winner = outcome["winning_rule"]
        active_critical = set(outcome["activated_rules"]) & CRITICAL_RULE_IDS
        is_favorable = outcome["level"] in {"BUENA", "EXCELENTE"}
        flags = decision_quality_flags(
            level=outcome["level"],
            facts=outcome["facts"],
            convenience_classification=outcome["clasificacion_conveniencia"],
        )
        counts["escenarios"] += 1
        if is_favorable:
            counts["favorables"] += 1
            rules[winner or "SIN_REGLA"] += 1
            for flag in flags:
                counts[flag] += 1

        if active_critical:
            counts["activaciones_criticas"] += 1
            if is_favorable or winner not in CRITICAL_RULE_IDS:
                problems.append(f"{identifier}: protección crítica no prevaleció")
            if f"determinada por la regla {winner}." not in outcome["explanation"]:
                problems.append(f"{identifier}: nota crítica no cita al ganador")

        if is_favorable:
            facts = outcome["facts"]
            checks = (
                (TRAVEL_REVIEW, facts["distancia_lejana"] or facts["tiempo_alto"]),
                (LOW_INDEX, outcome["clasificacion_conveniencia"] == "BAJA_CONVENIENCIA"),
                (INCOMPLETE_EXCELLENT,
                 outcome["level"] == "EXCELENTE"
                 and facts["porcentaje_productos_disponibles"] < 100),
                (NO_ESSENTIALS_DEFINED, facts["sin_esenciales_definidos"]),
            )
            for flag, condition in checks:
                if bool(condition) != (flag in flags):
                    problems.append(f"{identifier}: bandera {flag} no coincide con los hechos")
            for message in decision_quality_advisories(flags, request):
                if message not in outcome["explanation"]:
                    problems.append(f"{identifier}: falta advertencia comercial")
            if flags and len(examples) < max_examples:
                examples.append({
                    "escenario": identifier,
                    "ganadora": winner,
                    "nivel": outcome["level"],
                    "indice": outcome["indice_conveniencia"],
                    "advertencias": list(flags),
                })

    return {
        "tipo_datos": "SINTETICOS_NO_ETIQUETADOS",
        "total": counts["escenarios"],
        "favorables": counts["favorables"],
        "activaciones_criticas": counts["activaciones_criticas"],
        "alertas": {
            name: counts[name]
            for name in (TRAVEL_REVIEW, LOW_INDEX, INCOMPLETE_EXCELLENT, NO_ESSENTIALS_DEFINED)
        },
        "reglas_favorables": dict(sorted(rules.items())),
        "violaciones": problems[:25],
        "total_violaciones": len(problems),
        "ejemplos": examples,
        "resultado": "BLOQUEADO" if problems else "APROBADO",
        "limite": (
            "No hay datos de consumidores, combustible, precio de la promoción "
            "ni costo neto del viaje; las advertencias no cambian el dictamen."
        ),
    }


def markdown_summary(result: dict[str, Any]) -> str:
    lines = [
        "## HU-33 · Auditoría de advertencias comerciales",
        "",
        f"**Resultado:** {result['resultado']}",
        f"**Casos sintéticos:** {result['total']}",
        f"**Favorables:** {result['favorables']}",
        "",
        "| Advertencia | Casos |",
        "|---|---:|",
    ]
    lines.extend(
        f"| {flag} | {value} |" for flag, value in result["alertas"].items()
    )
    lines += [
        "",
        f"**Incoherencias bloqueantes:** {result['total_violaciones']}",
        "",
        "Los conteos no son tasas reales de compra ni prueban precisión comercial.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-grid", action="store_true")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit_quality(quality_cases(with_grid=args.with_grid))
        summary = markdown_summary(result)
        print(summary)
        if args.json_output:
            args.json_output.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if github_summary:
            with Path(github_summary).open("a", encoding="utf-8") as handle:
                handle.write(summary)
        return int(result["resultado"] == "BLOQUEADO")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Auditoría comercial inválida: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
