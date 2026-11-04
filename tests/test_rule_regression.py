"""HU-13: pruebas reproducibles del control preventivo de versiones."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from app.expert_system.inference_engine import run_inference
from app.expert_system.rule_loader import load_rules
from app.main import app
from app.schemas.rule_regression import RuleRegressionRequest, RuleRegressionResponse
from app.services.rule_regression_service import compare_rule_versions
from demo.streamlit_app import load_scenarios


def rules():
    return [rule.model_dump(mode="json") for rule in load_rules()]


def scenarios():
    return [
        {"nombre": row["name"], "hechos": row["facts"]}
        for row in load_scenarios()
    ]


def payload(before=None, after=None, cases=None):
    return {
        "anterior": {"etiqueta": "v1", "reglas": before if before is not None else rules()},
        "propuesta": {"etiqueta": "v2", "reglas": after if after is not None else rules()},
        "escenarios": cases if cases is not None else scenarios(),
    }


def priority_variant(rule_id, priority):
    changed = rules()
    next(rule for rule in changed if rule["id"] == rule_id)["priority"] = priority
    return changed


def api(method, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_identical_snapshots_do_not_create_false_regressions():
    request = RuleRegressionRequest.model_validate(payload())
    report = compare_rule_versions(request)
    assert report.escenarios_evaluados == 9
    assert report.huella_anterior == report.huella_propuesta
    assert report.reglas_agregadas == 0
    assert report.reglas_retiradas == 0
    assert report.reglas_modificadas == 0
    assert report.cambios_nivel == 0
    assert report.cambios_regla_ganadora == 0
    assert report.cambios_activaciones == 0
    assert report.cambios_explicacion == 0
    assert report.regresiones_criticas == 0


def test_priority_change_r06_yields_explainable_difference_on_same_facts():
    request = RuleRegressionRequest.model_validate(
        payload(after=priority_variant("R06", 7))
    )
    report = compare_rule_versions(request)
    row = next(item for item in report.resultados if item.escenario == "Compra ideal")
    assert row.nivel_anterior == "EXCELENTE"
    assert row.regla_anterior == "R06"
    assert row.nivel_propuesto == "BUENA"
    assert row.regla_propuesta == "R07"
    assert row.cambio_nivel and row.cambio_regla
    assert row.cambio_explicacion
    assert not row.cambio_activaciones
    assert row.indice_anterior == row.indice_propuesto
    assert report.reglas_modificadas == 1
    assert report.cambios_reglas[0].regla == "R06"
    assert report.cambios_reglas[0].campos == ["priority"]
    assert report.huella_anterior != report.huella_propuesta


def test_critical_regression_is_detected_in_synthetic_two_store_case():
    source = scenarios()[0]
    case = {
        **source,
        "nombre": "Riesgo esencial con ahorro alto",
        "hechos": {
            **source["hechos"],
            "alternativa_id": "caso-critico",
            "numero_supermercados": 2,
            "productos_disponibles": 9,
            "productos_esenciales_disponibles": 5,
        },
    }
    request = RuleRegressionRequest.model_validate(
        payload(after=priority_variant("R02", 9), cases=[case])
    )
    result = compare_rule_versions(request)
    item = result.resultados[0]
    assert item.nivel_anterior == "NO_RECOMENDABLE"
    assert item.regla_anterior == "R02"
    assert item.nivel_propuesto == "BUENA"
    assert item.regla_propuesta == "R08"
    assert "R02" in item.reglas_activas_propuestas
    assert item.regresion_critica
    assert result.regresiones_criticas == 1
    assert any("regresión crítica" in notice for notice in result.advertencias)


def test_change_of_only_explanation_does_not_count_as_level_change():
    updated = rules()
    next(r for r in updated if r["id"] == "R06")["result"]["explanation"] = (
        "Conclusión académica revisada."
    )
    request = RuleRegressionRequest.model_validate(
        payload(after=updated, cases=scenarios()[:1])
    )
    report = compare_rule_versions(request)
    assert report.cambios_nivel == 0
    assert report.cambios_regla_ganadora == 0
    assert report.cambios_activaciones == 0
    assert report.cambios_explicacion == 1
    assert report.cambios_reglas[0].campos == ["result"]


def test_added_and_removed_rules_are_detected():
    current = rules()
    changed = [r for r in current if r["id"] != "R07"]
    added = json.loads(json.dumps(current[-1]))
    added["id"] = "R09"
    changed.append(added)
    report = compare_rule_versions(
        RuleRegressionRequest.model_validate(
            payload(after=changed, cases=scenarios()[:2])
        )
    )
    assert report.reglas_agregadas == 1
    assert report.reglas_retiradas == 1
    assert {(row.regla, row.tipo) for row in report.cambios_reglas} == {
        ("R07", "RETIRADA"),
        ("R09", "AGREGADA"),
    }


def test_baseline_simulation_is_same_as_production_for_all_cases():
    request = RuleRegressionRequest.model_validate(payload())
    report = compare_rule_versions(request)
    for case, result in zip(request.escenarios, report.resultados, strict=True):
        reference = run_inference(case.hechos)
        assert result.nivel_anterior == reference["level"]
        assert result.regla_anterior == reference["winning_rule"]
        assert result.reglas_activas_anteriores == reference["activated_rules"]
        assert result.indice_anterior == reference["indice_conveniencia"]


def test_hashes_are_stable_for_rule_order_and_do_not_trust_labels():
    original = rules()
    reversed_rules = list(reversed(original))
    request = RuleRegressionRequest.model_validate(
        payload(before=original, after=reversed_rules)
    )
    report = compare_rule_versions(request)
    assert report.huella_anterior == report.huella_propuesta
    assert report.version_anterior != report.version_propuesta
    assert report.cambios_nivel == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"escenarios": []},
        {"escenarios": scenarios() * 2},
        {"propuesta": {"etiqueta": "", "reglas": rules()}},
        {
            "propuesta": {
                "etiqueta": "x",
                "reglas": [*rules(), rules()[0]],
            }
        },
        {
            "propuesta": {
                "etiqueta": "x",
                "reglas": [
                    {**rules()[0], "conditions": {"no_existe": True}}
                ],
            }
        },
        {
            "propuesta": {
                "etiqueta": "x",
                "reglas": [
                    {**rules()[0], "conditions": {"diferencia_presupuesto": True}}
                ],
            }
        },
    ],
)
def test_malformed_snapshot_or_case_count_is_rejected(bad):
    with pytest.raises(ValidationError):
        RuleRegressionRequest.model_validate({**payload(), **bad})


def test_endpoint_and_openapi_preserve_laravel_recommendation_contract():
    doc = payload(after=priority_variant("R06", 7))
    result = api("POST", "/api/v1/rule-regression", json=doc)
    assert result.status_code == 200, result.text
    report = RuleRegressionResponse.model_validate(result.json())
    assert report.cambios_nivel >= 1
    openapi = api("GET", "/openapi.json").json()
    assert "/api/v1/rule-regression" in openapi["paths"]
    props = openapi["components"]["schemas"]
    assert len(props["RecommendationRequest"]["properties"]) == 14
    assert len(props["RecommendationResponse"]["properties"]) == 16
    assert api("POST", "/api/v1/rule-regression", json={"escenarios": []}).status_code == 422


def test_api_key_is_required_when_configured(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "regression-secret")
    data = payload(after=priority_variant("R06", 7), cases=scenarios()[:2])
    assert api("POST", "/api/v1/rule-regression", json=data).status_code == 401
    assert api(
        "POST", "/api/v1/rule-regression",
        json=data, headers={"X-API-Key": "regression-secret"},
    ).status_code == 200


def test_streamlit_comparison_click_reaches_real_api(monkeypatch):
    import requests

    def fake_get(url, *, timeout, headers, allow_redirects):
        assert allow_redirects is False
        assert url.endswith("/api/v1/knowledge")
        return api("GET", "/api/v1/knowledge", headers=headers)

    def fake_post(url, *, json, timeout, headers, allow_redirects):
        assert allow_redirects is False
        assert url.endswith("/api/v1/rule-regression")
        return api("POST", "/api/v1/rule-regression", json=json, headers=headers)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script))
    at.session_state["active_tab"] = "Base de conocimiento"
    at.run(timeout=20)
    assert not at.exception
    next(b for b in at.button if b.label == "Cargar reglas actuales para comparar").click()
    at.run(timeout=20)
    assert not at.exception
    next(b for b in at.button if b.label == "Comparar versiones de reglas").click()
    at.run(timeout=20)
    assert not at.exception
    report = at.session_state["regression_result"]
    assert report["cambios_nivel"] >= 1
    assert report["reglas_modificadas"] == 1
