"""HU-17: evaluación diferencial entre dos commits independientes.

El mismo archivo de casos se ejecuta en procesos Python separados: uno para
el worktree del commit base y otro para el candidato. No importa código remoto
ni modifica archivos del motor; solo genera archivos temporales de evidencia.
"""

import argparse
import json
import os
import sys
from pathlib import Path

CRITICAL_IDS = frozenset({"R01", "R02", "R03", "R04", "R05"})
EXPECTED_INPUTS = frozenset(
    {
        "request_id", "alternativa_id", "costo_total", "presupuesto", "ahorro",
        "distancia_km", "distancia_adicional_km", "tiempo_estimado_min",
        "productos_disponibles", "productos_totales",
        "productos_esenciales_disponibles", "productos_esenciales_totales",
        "numero_supermercados", "promociones_aplicables",
    }
)
EXPECTED_OUTPUTS = frozenset(
    {
        "request_id", "nivel_recomendacion", "accion_sugerida", "explicacion",
        "reglas_activadas", "prioridad_aplicada", "hechos_derivados",
        "version_reglas", "winning_rule", "losing_rules", "trace",
        "version_contrato", "indice_conveniencia",
        "clasificacion_conveniencia", "componentes_conveniencia",
        "pesos_conveniencia",
    }
)


def make_cases(scenarios_path: Path) -> list[dict]:
    """Une nueve casos documentados, 2430 clases y puntos de frontera fijos."""

    from app.expert_system.rule_auditor import _representative_requests
    from app.schemas.recommendation import RecommendationRequest

    raw = json.loads(scenarios_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("Se requieren escenarios de demostración válidos.")
    cases = []
    for index, row in enumerate(raw, start=1):
        facts = RecommendationRequest.model_validate(row["facts"])
        cases.append(
            {"id": f"demo-{index:03}", "facts": facts.model_dump(mode="json")}
        )
    for index, item in enumerate(_representative_requests(), start=1):
        cases.append(
            {"id": f"clase-{index:04}", "facts": item.model_dump(mode="json")}
        )

    # Límites absolutos de la versión publicada y sus vecinos. Se usan como
    # referencia fija incluso cuando el candidato cambia los umbrales.
    example = cases[0]["facts"]
    changes = (
        ("presupuesto", (49.99, 50.0, 50.01)),
        ("costo_total", (50.0, 54.99, 55.0, 55.01, 56.0)),
        ("ahorro", (2.99, 3.0, 3.01, 9.99, 10.0, 10.01)),
        ("distancia_adicional_km", (1.99, 2.0, 2.01, 7.99, 8.0, 8.01)),
        ("tiempo_estimado_min", (19.99, 20.0, 20.01, 44.99, 45.0, 45.01)),
        ("numero_supermercados", (1, 2, 3, 4)),
    )
    for name, values in changes:
        for value in values:
            sample = {
                **example,
                "request_id": "frontera-fija",
                "alternativa_id": f"frontera-{len(cases):04}",
                name: value,
            }
            facts = RecommendationRequest.model_validate(sample)
            cases.append(
                {
                    "id": f"frontera-{len(cases):04}",
                    "facts": facts.model_dump(mode="json"),
                }
            )
    return cases


def capture(cases: list[dict]) -> dict:
    """Se ejecuta una vez por worktree, para evitar contaminación de imports."""

    from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
    from app.services.recommendation_service import recommend

    if set(RecommendationRequest.model_fields) != EXPECTED_INPUTS:
        raise ValueError("Cambió el contrato de 14 hechos que consume Laravel.")
    if set(RecommendationResponse.model_fields) != EXPECTED_OUTPUTS:
        raise ValueError("Cambió el contrato de respuesta de 16 campos.")
    result = []
    for row in cases:
        request = RecommendationRequest.model_validate(row["facts"])
        decision = recommend(request)
        result.append(
            {
                "id": row["id"],
                "nivel": decision.nivel_recomendacion,
                "ganadora": decision.winning_rule,
                "activadas": decision.reglas_activadas,
                "indice": decision.indice_conveniencia,
                "clasificacion": decision.clasificacion_conveniencia,
            }
        )
    return {"casos": result, "contrato_entrada": sorted(EXPECTED_INPUTS)}


def compare(baseline: dict, candidate: dict, max_index_shift: float = 10) -> dict:
    """La aprobación no depende de la etiqueta de commit ni de la fecha."""

    a = baseline.get("casos")
    b = candidate.get("casos")
    if not isinstance(a, list) or not isinstance(b, list) or not a:
        raise ValueError("Snapshots ausentes o vacíos.")
    if len(a) != len(b) or [x["id"] for x in a] != [x["id"] for x in b]:
        raise ValueError("Los snapshots no contienen los mismos casos ordenados.")
    if baseline.get("contrato_entrada") != candidate.get("contrato_entrada"):
        raise ValueError("Los contratos de entrada no coinciden.")
    metrics = {
        "casos": len(a),
        "cambios_nivel": 0,
        "cambios_regla": 0,
        "cambios_activaciones": 0,
        "cambios_indice": 0,
        "saltos_indice_grandes": 0,
        "regresiones_criticas": 0,
        "perdidas_proteccion": 0,
    }
    serious = []
    ordinary = []
    for old, new in zip(a, b, strict=True):
        old_critical = set(old["activadas"]) & CRITICAL_IDS
        new_critical = set(new["activadas"]) & CRITICAL_IDS
        loss = sorted(old_critical - new_critical)
        promotion = (
            bool(old_critical)
            and old["nivel"] == "NO_RECOMENDABLE"
            and new["nivel"] in {"BUENA", "EXCELENTE"}
        )
        jump = round(abs(new["indice"] - old["indice"]), 2)
        too_large = jump > max_index_shift
        metrics["cambios_nivel"] += old["nivel"] != new["nivel"]
        metrics["cambios_regla"] += old["ganadora"] != new["ganadora"]
        metrics["cambios_activaciones"] += old["activadas"] != new["activadas"]
        metrics["cambios_indice"] += jump > 0
        metrics["saltos_indice_grandes"] += too_large
        metrics["regresiones_criticas"] += promotion
        metrics["perdidas_proteccion"] += bool(loss)
        if promotion or loss or too_large or old["nivel"] != new["nivel"]:
            target = serious if (promotion or loss or too_large) else ordinary
            if len(target) < 15:
                target.append(
                    {
                        "caso": old["id"],
                        "antes": old["nivel"],
                        "despues": new["nivel"],
                        "regla_antes": old["ganadora"],
                        "regla_despues": new["ganadora"],
                        "protecciones_perdidas": loss,
                        "cambio_indice": jump,
                        "riesgo": promotion or bool(loss),
                    }
                )
    blocked = bool(
        metrics["regresiones_criticas"]
        or metrics["perdidas_proteccion"]
        or metrics["saltos_indice_grandes"]
    )
    return {
        "resultado": "BLOQUEADO" if blocked else "APROBADO",
        "metricas": metrics,
        "umbral_variacion_indice_puntos": max_index_shift,
        "ejemplos": (serious + ordinary)[:15],
        "limitacion": (
            "Muestra representativa y fronteras fijas: ausencia de diferencias "
            "no demuestra equivalencia universal. Se comparan ejecutables "
            "separados del commit base y candidato; no se publica ningún cambio."
        ),
    }


def summary(report: dict) -> str:
    lines = [
        "## HU-17: regresión del código de inferencia",
        "",
        f"**Resultado: {report['resultado']}**",
        "",
        "| Métrica | Total |",
        "|---|---:|",
    ]
    lines += [
        f"| {key.replace('_', ' ')} | {value} |"
        for key, value in report["metricas"].items()
    ]
    lines += [
        "",
        "Se bloquean pérdidas de protección, promociones de riesgo crítico y "
        "saltos del índice mayores que el umbral configurado.",
        "",
        report["limitacion"],
        "",
    ]
    for item in report["ejemplos"]:
        lines.append(
            f"- {item['caso']}: {item['antes']} / {item['regla_antes']} → "
            f"{item['despues']} / {item['regla_despues']}; "
            f"índice ±{item['cambio_indice']}; "
            f"protecciones perdidas {', '.join(item['protecciones_perdidas']) or '-'}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Regresión de cambios del motor")
    sub = parser.add_subparsers(dest="action", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--scenarios", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--cases", type=Path, required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    review = sub.add_parser("compare")
    review.add_argument("--baseline", type=Path, required=True)
    review.add_argument("--candidate", type=Path, required=True)
    review.add_argument("--max-index-shift", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        if args.action == "generate":
            content = make_cases(args.scenarios)
        elif args.action == "snapshot":
            content = capture(json.loads(args.cases.read_text(encoding="utf-8")))
        else:
            if not 0 < args.max_index_shift <= 100:
                raise ValueError("El límite de cambio del índice debe estar en (0,100].")
            content = compare(
                json.loads(args.baseline.read_text(encoding="utf-8")),
                json.loads(args.candidate.read_text(encoding="utf-8")),
                max_index_shift=args.max_index_shift,
            )
        if args.action == "compare":
            text = summary(content)
            print(text)
            target = os.getenv("GITHUB_STEP_SUMMARY")
            if target:
                with Path(target).open("a", encoding="utf-8") as handle:
                    handle.write(text)
        args.output.write_text(
            json.dumps(content, ensure_ascii=False, indent=2),
            encoding="utf-8",
        ) if args.action != "compare" else None
        return int(content["resultado"] == "BLOQUEADO") if args.action == "compare" else 0
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(f"ERROR de comparación: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
