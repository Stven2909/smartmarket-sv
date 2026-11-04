"""HU-31: reproducible, read-only sensitivity analysis of expert weight profiles.

No API calls, credentials, rule writes or deploy changes. These scenarios are
synthetic and cannot establish commercial accuracy or the optimal weights.
"""

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from statistics import mean
from typing import Any

from app.expert_system.convenience_config import (
    DEFAULT_CONVENIENCE_CONFIG,
    ConvenienceConfig,
)
from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.inference_engine import run_inference_with_rules
from app.expert_system.rule_auditor import _representative_requests
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest
from app.schemas.versions import RULES_VERSION

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_FILES = tuple(
    ROOT / "data" / name
    for name in (
        "scenarios.json",
        "scenarios_hu28.json",
        "scenarios_hu29.json",
        "scenarios_hu30.json",
    )
)

# Named hypotheses, NOT trained coefficients and NOT production settings.
PROFILES: dict[str, dict[str, float]] = {
    "actual": {
        "peso_ahorro": 0.35, "peso_disponibilidad": 0.25,
        "peso_distancia": 0.20, "peso_tiempo": 0.15,
        "peso_promociones": 0.05,
    },
    "priorizar_ahorro": {
        "peso_ahorro": 0.50, "peso_disponibilidad": 0.20,
        "peso_distancia": 0.15, "peso_tiempo": 0.10,
        "peso_promociones": 0.05,
    },
    "priorizar_disponibilidad": {
        "peso_ahorro": 0.20, "peso_disponibilidad": 0.40,
        "peso_distancia": 0.20, "peso_tiempo": 0.15,
        "peso_promociones": 0.05,
    },
    "priorizar_movilidad": {
        "peso_ahorro": 0.20, "peso_disponibilidad": 0.20,
        "peso_distancia": 0.30, "peso_tiempo": 0.25,
        "peso_promociones": 0.05,
    },
    "priorizar_promociones": {
        "peso_ahorro": 0.25, "peso_disponibilidad": 0.25,
        "peso_distancia": 0.15, "peso_tiempo": 0.15,
        "peso_promociones": 0.20,
    },
}


def configurations() -> dict[str, ConvenienceConfig]:
    # Validate profiles using exactly the production configuration model.
    return {
        name: replace(DEFAULT_CONVENIENCE_CONFIG, **values)
        for name, values in PROFILES.items()
    }


def load_cases(*, with_grid: bool = False) -> list[tuple[str, RecommendationRequest]]:
    """Read 17 known scenarios; optionally add 3404 synthetic boundary cases."""
    cases = []
    seen_ids: set[str] = set()
    for path in SCENARIO_FILES:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"Los escenarios no son una lista: {path}")
        for row in raw:
            case_id = str(row["id"])
            if not case_id or case_id in seen_ids:
                raise ValueError(f"Identificador de escenario vacío o duplicado: {case_id}")
            seen_ids.add(case_id)
            cases.append(
                (case_id, RecommendationRequest.model_validate(row["facts"]))
            )
    if with_grid:
        for number, request in enumerate(_representative_requests(), start=1):
            cases.append((f"representativo-{number:04}", request))
    return cases


def _has_critical(result: dict[str, Any]) -> bool:
    return bool(set(result["activated_rules"]) & CRITICAL_RULE_IDS)


def _is_critical_safe(result: dict[str, Any]) -> bool:
    if not _has_critical(result):
        return True
    return (
        result["level"] == "NO_RECOMENDABLE"
        and result["winning_rule"] in CRITICAL_RULE_IDS
    )


def calibrate(
    cases: list[tuple[str, RecommendationRequest]],
    *,
    max_examples: int = 8,
) -> dict[str, Any]:
    """Compare real inference (not just the numeric score) across profiles."""
    if not cases:
        raise ValueError("Se requiere al menos un escenario.")
    if not 0 <= max_examples <= 100:
        raise ValueError("max_examples debe estar entre 0 y 100.")
    rule_set = load_rules()
    profiles = configurations()

    baseline = [
        run_inference_with_rules(request, rule_set, config=profiles["actual"])
        for _, request in cases
    ]

    summaries = []
    for profile_name, config in profiles.items():
        levels: Counter[str] = Counter()
        winners: Counter[str] = Counter()
        stats: Counter[str] = Counter()
        deltas: list[float] = []
        examples = []

        for (case_id, request), before in zip(cases, baseline, strict=True):
            after = run_inference_with_rules(request, rule_set, config=config)
            levels[after["level"]] += 1
            winners[after["winning_rule"] or "SIN_REGLA"] += 1
            changed_level = before["level"] != after["level"]
            changed_rule = before["winning_rule"] != after["winning_rule"]
            if changed_level:
                stats["cambios_nivel"] += 1
                if before["level"] == "NO_RECOMENDABLE":
                    stats["provisional_o_rechazo_a_favorable"] += 1
                elif after["level"] == "NO_RECOMENDABLE":
                    stats["favorable_a_no_recomendable"] += 1
            if changed_rule:
                stats["cambios_regla_ganadora"] += 1
            if (
                before["clasificacion_conveniencia"]
                != after["clasificacion_conveniencia"]
            ):
                stats["cambios_categoria_indice"] += 1
            if not _is_critical_safe(after):
                stats["violaciones_criticas"] += 1
            if _has_critical(before) and not _has_critical(after):
                stats["protecciones_criticas_perdidas"] += 1
            deltas.append(
                after["indice_conveniencia"] - before["indice_conveniencia"]
            )
            if (changed_level or changed_rule) and len(examples) < max_examples:
                examples.append({
                    "escenario": case_id,
                    "nivel_antes": before["level"],
                    "nivel_despues": after["level"],
                    "regla_antes": before["winning_rule"],
                    "regla_despues": after["winning_rule"],
                    "indice_antes": before["indice_conveniencia"],
                    "indice_despues": after["indice_conveniencia"],
                })

        summaries.append({
            "perfil": profile_name,
            "pesos": config.weights(),
            "total": len(cases),
            "cambios_nivel": stats["cambios_nivel"],
            "cambios_regla_ganadora": stats["cambios_regla_ganadora"],
            "cambios_categoria_indice": stats["cambios_categoria_indice"],
            "provisional_o_rechazo_a_favorable": stats[
                "provisional_o_rechazo_a_favorable"
            ],
            "favorable_a_no_recomendable": stats["favorable_a_no_recomendable"],
            "violaciones_criticas": stats["violaciones_criticas"],
            "protecciones_criticas_perdidas": stats[
                "protecciones_criticas_perdidas"
            ],
            "variacion_media_indice_puntos": round(mean(deltas), 3),
            "niveles": dict(sorted(levels.items())),
            "reglas_ganadoras": dict(sorted(winners.items())),
            "ejemplos": examples,
        })

    return {
        "version_reglas": RULES_VERSION,
        "total_escenarios": len(cases),
        "perfiles": summaries,
        "decision": "MANTENER_PESOS_PRODUCCION_HASTA_TENER_ETIQUETAS_REALES",
        "limitaciones": [
            "Escenarios de demostración y rejilla sintética; no son compras reales.",
            "Cambios frente al perfil base no miden errores ni precisión comercial.",
            "Las diferencias no justifican por sí solas reajustar pesos de producción.",
            "El costo de transporte, promociones reales y entrega no se conocen.",
        ],
    }


def markdown_summary(report: dict[str, Any]) -> str:
    lines = [
        "## HU-31 · Sensibilidad de pesos del sistema experto",
        "",
        f"Casos sintéticos: **{report['total_escenarios']}**",
        "",
        "| Perfil | Cambios de nivel | Cambios de regla | Críticas vulneradas |",
        "|---|---:|---:|---:|",
    ]
    for row in report["perfiles"]:
        lines.append(
            f"| {row['perfil']} | {row['cambios_nivel']} | "
            f"{row['cambios_regla_ganadora']} | {row['violaciones_criticas']} |"
        )
    lines += [
        "",
        "**Decisión:** conservar los pesos de producción hasta contar "
        "con compras etiquetadas y preferencias reales.",
        "",
        "No es una estimación de precisión comercial ni un ajuste automático.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-grid", action="store_true",
        help="Añadir las 3404 combinaciones sintéticas del auditor.",
    )
    parser.add_argument(
        "--json-output", type=Path,
        help="Guardar resumen JSON; no modifica reglas ni secretos.",
    )
    args = parser.parse_args(argv)
    try:
        result = calibrate(load_cases(with_grid=args.with_grid))
        summary = markdown_summary(result)
        print(summary)
        if args.json_output:
            args.json_output.write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if any(
            profile["violaciones_criticas"]
            or profile["protecciones_criticas_perdidas"]
            for profile in result["perfiles"]
        ):
            return 1
        github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if github_summary:
            with Path(github_summary).open("a", encoding="utf-8") as handle:
                handle.write(summary)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Calibración inválida: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
