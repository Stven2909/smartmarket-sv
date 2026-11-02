"""HU-19: benchmark local y acotado del motor, sin solicitudes de red."""

import argparse
import json
import os
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import recommend

DEFAULT_CASES = Path(__file__).resolve().parents[1] / "data" / "scenarios.json"


def benchmark(iterations: int, scenarios: Path = DEFAULT_CASES) -> dict:
    """Calienta el motor y mide inferencia, no HTTP ni arranque de Render."""

    if not 10 <= iterations <= 100_000:
        raise ValueError("Se requieren entre 10 y 100000 iteraciones.")
    raw = json.loads(scenarios.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("No hay escenarios de prueba.")
    requests = [
        RecommendationRequest.model_validate(item["facts"]) for item in raw
    ]
    for item in requests:
        recommend(item)
    tracemalloc.start()
    latencies = []
    started = time.perf_counter()
    for i in range(iterations):
        item = requests[i % len(requests)]
        begin = time.perf_counter_ns()
        result = recommend(item)
        latencies.append((time.perf_counter_ns() - begin) / 1_000_000)
        if result.indice_conveniencia is None:
            raise ValueError("El motor no devolvió el índice.")
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    sorted_times = sorted(latencies)
    p95 = sorted_times[max(0, (95 * iterations + 99) // 100 - 1)]
    return {
        "iteraciones": iterations,
        "escenarios_distintos": len(requests),
        "mediana_ms": round(statistics.median(latencies), 4),
        "p95_ms": round(p95, 4),
        "max_ms": round(max(latencies), 4),
        "throughput_por_segundo": round(iterations / elapsed, 2),
        "memoria_pico_tracemalloc_kib": round(peak / 1024, 2),
        "alcance": (
            "Medición local del motor calentado; tracemalloc añade sobrecarga. "
            "No es latencia de Render, no incluye red ni inicio en frío."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark local sin red")
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = benchmark(args.iterations, args.scenarios)
        if args.json_output:
            args.json_output.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        summary_path = os.getenv("GITHUB_STEP_SUMMARY")
        if summary_path:
            with Path(summary_path).open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n## HU-19 · Benchmark del motor (sin red)\n\n"
                    f"- Iteraciones: {result['iteraciones']}\n"
                    f"- Mediana: {result['mediana_ms']} ms\n"
                    f"- p95: {result['p95_ms']} ms\n"
                    f"- Pico tracemalloc: {result['memoria_pico_tracemalloc_kib']} KiB\n"
                    "\nNo representa latencia de alojamiento ni RSS del proceso.\n"
                )
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"Benchmark no válido: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
