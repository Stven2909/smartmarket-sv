import json
from pathlib import Path

import pytest
import requests

from demo.streamlit_app import (
    REQUEST_TIMEOUT_SECONDS,
    ApiClientError,
    ScenarioLoadError,
    call_recommendation_api,
    load_scenarios,
    validate_payload,
)


def test_loads_scenarios_correctly():
    scenarios = load_scenarios()

    assert len(scenarios) == 9
    assert scenarios[0]["id"] == "escenario-ideal"


def test_negative_scenarios_are_available():
    scenario_ids = {scenario["id"] for scenario in load_scenarios()}

    assert "presupuesto-muy-excedido" in scenario_ids
    assert "productos-esenciales-faltantes" in scenario_ids
    assert "distancia-lejana-ahorro-bajo" in scenario_ids
    assert "tiempo-alto-ahorro-bajo" in scenario_ids
    assert "compra-fragmentada" in scenario_ids


def test_missing_scenarios_file_raises_clear_error(tmp_path):
    with pytest.raises(ScenarioLoadError, match="No se encontró"):
        load_scenarios(tmp_path / "missing.json")


def test_invalid_scenarios_json_raises_clear_error(tmp_path):
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{no es json", encoding="utf-8")

    with pytest.raises(ScenarioLoadError, match="JSON de escenarios inválido"):
        load_scenarios(invalid_path)


def test_scenario_requires_facts(tmp_path):
    invalid_path = tmp_path / "without-facts.json"
    invalid_path.write_text(
        json.dumps([{"id": "scenario-1", "name": "Sin hechos"}]),
        encoding="utf-8",
    )

    with pytest.raises(ScenarioLoadError, match="requiere un objeto facts"):
        load_scenarios(invalid_path)


def test_validate_payload_rejects_inconsistent_product_counts():
    errors = validate_payload(
        {
            "request_id": "demo",
            "alternativa_id": "market",
            "presupuesto": 50,
            "costo_total": 40,
            "ahorro": 5,
            "distancia_km": 1,
            "distancia_adicional_km": 1,
            "tiempo_estimado_min": 10,
            "productos_disponibles": 8,
            "productos_totales": 7,
            "productos_esenciales_disponibles": 6,
            "productos_esenciales_totales": 5,
            "numero_supermercados": 1,
        }
    )

    assert any("Productos disponibles" in error for error in errors)
    assert any("Productos esenciales disponibles" in error for error in errors)


def test_validate_payload_rejects_negative_and_zero_values():
    errors = validate_payload(
        {
            "request_id": "",
            "alternativa_id": "",
            "presupuesto": 0,
            "costo_total": -1,
            "ahorro": 0,
            "distancia_km": 0,
            "distancia_adicional_km": 0,
            "tiempo_estimado_min": 0,
            "productos_disponibles": 0,
            "productos_totales": 0,
            "productos_esenciales_disponibles": 0,
            "productos_esenciales_totales": 0,
            "numero_supermercados": 0,
        }
    )

    assert any("obligatorio" in error for error in errors)
    assert any("no puede ser negativo" in error for error in errors)
    assert any("mayor que cero" in error for error in errors)


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text

    def json(self):
        return self._body


def test_ideal_scenario_can_be_sent_to_api(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout, headers=None):
        captured.update({"url": url, "json": json, "timeout": timeout, "headers": headers})
        return FakeResponse(200, {"nivel_recomendacion": "EXCELENTE"})

    monkeypatch.setattr("demo.streamlit_app.requests.post", fake_post)
    scenario = load_scenarios()[0]

    result = call_recommendation_api(scenario["facts"])

    assert result["nivel_recomendacion"] == "EXCELENTE"
    assert captured["url"].endswith("/api/v1/recommend")
    assert captured["json"]["request_id"] == "scenario-ideal"
    assert captured["timeout"] == REQUEST_TIMEOUT_SECONDS


def test_api_timeout_is_handled(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.Timeout("timeout")

    monkeypatch.setattr("demo.streamlit_app.requests.post", fake_post)

    with pytest.raises(ApiClientError, match="demasiado"):
        call_recommendation_api({})


def test_api_422_is_handled(monkeypatch):
    monkeypatch.setattr(
        "demo.streamlit_app.requests.post",
        lambda *args, **kwargs: FakeResponse(
            422,
            {"detail": [{"msg": "campo requerido"}]},
        ),
    )

    with pytest.raises(ApiClientError, match="HTTP 422.*campo requerido"):
        call_recommendation_api({})


def test_api_500_is_handled(monkeypatch):
    monkeypatch.setattr(
        "demo.streamlit_app.requests.post",
        lambda *args, **kwargs: FakeResponse(500, text="error interno"),
    )

    with pytest.raises(ApiClientError, match="HTTP 500.*error interno"):
        call_recommendation_api({})


def test_streamlit_uses_http_without_importing_internal_engine():
    source = Path("demo/streamlit_app.py").read_text(encoding="utf-8")

    assert "requests.post" in source
    assert "inference_engine" not in source
    assert "classifiers" not in source
    assert "chatbot_service" not in source
