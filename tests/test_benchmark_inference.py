"""HU-19: benchmark de duración acotada, sin peticiones de red."""

from pathlib import Path

from scripts.benchmark_inference import benchmark, main

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_returns_finite_positive_latency_and_memory():
    result = benchmark(20)
    assert result["iteraciones"] == 20
    assert result["escenarios_distintos"] == 9
    assert 0 <= result["mediana_ms"] <= result["p95_ms"] <= result["max_ms"]
    assert result["throughput_por_segundo"] > 0
    assert result["memoria_pico_tracemalloc_kib"] > 0
    assert "no incluye red" in result["alcance"]


def test_cli_json_can_be_read_and_never_contacts_render(tmp_path, monkeypatch):
    import json

    import requests

    def block(*_args, **_kwargs):
        raise AssertionError("El benchmark no debe llamar a Render.")

    monkeypatch.setattr(requests, "get", block)
    monkeypatch.setattr(requests, "post", block)
    output = tmp_path / "benchmark.json"
    assert main(["--iterations", "25", "--json-output", str(output)]) == 0
    value = json.loads(output.read_text(encoding="utf-8"))
    assert value["iteraciones"] == 25


def test_rejects_invalid_iteration_counts():
    for n in (0, -5, 100_001):
        try:
            benchmark(n)
            raise AssertionError("Debe rechazar iteraciones no válidas")
        except ValueError:
            pass


def test_ci_includes_benchmark_without_stress_toward_remote_services():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert "python -m scripts.benchmark_inference --iterations 300" in ci
    assert "curl " not in ci
