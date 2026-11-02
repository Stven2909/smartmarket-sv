"""Contrato público sobrio, trazabilidad y coherencia semántica."""

import json
import re
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.chatbot.chatbot_service import chat
from app.expert_system.inference_engine import run_inference
from app.schemas.chatbot import ChatRequest
from app.schemas.comparison import ComparisonRequest
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.comparison_service import compare_alternatives
from app.services.recommendation_service import recommend

BASE = {
    "request_id": "verificacion-001",
    "alternativa_id": "tienda-a",
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}

EMOJI = re.compile(r"[\u2600-\u27BF\U0001F000-\U0001FAFF]")


def case(**overrides):
    return RecommendationRequest.model_validate({**BASE, **overrides})


def test_trace_explains_exact_unmatched_conditions():
    result = run_inference(case(distancia_adicional_km=4.0))
    r06 = next(item for item in result["trace"] if item["rule_id"] == "R06")
    assert r06["activated"] is False
    assert r06["unmatched_conditions"] == ["distancia_cercana"]
    assert r06["reason"] == "Condiciones no cumplidas: distancia_cercana."
    assert r06["conditions"]["distancia_cercana"]["expected"] is True
    assert r06["conditions"]["distancia_cercana"]["actual"] is False


def test_successful_trace_keeps_original_fields_and_reason():
    result = run_inference(case())
    r06 = next(item for item in result["trace"] if item["rule_id"] == "R06")
    assert r06["activated"] is True
    assert r06["reason"] == "Todas las condiciones se cumplieron."
    assert set(r06) == {
        "rule_id",
        "evaluated",
        "activated",
        "conditions",
        "matched_conditions",
        "unmatched_conditions",
        "reason",
    }


def test_chat_does_not_describe_a_rejection_as_favorable():
    request = case(costo_total=56.0)
    response = chat(
        ChatRequest(
            message="¿Cuál es la regla ganadora?",
            facts=request.model_dump(),
            recommendation=recommend(request),
        )
    )
    assert response.intent == "REGLA_GANADORA"
    assert response.response.startswith("La regla determinante es R01")
    assert "no se recomienda" in response.response
    assert "cumple las condiciones más importantes" not in response.response


def test_chat_recommendation_is_positive_when_expert_is_positive():
    request = case()
    response = chat(
        ChatRequest(
            message="¿Cuál es la regla ganadora?",
            facts=request.model_dump(),
            recommendation=recommend(request),
        )
    )
    assert response.response.startswith("La regla ganadora es R06")
    assert "EXCELENTE" in response.response


def test_comparison_warns_about_different_lists_without_rejecting():
    a = case()
    b = case(
        alternativa_id="tienda-b", productos_totales=11, productos_disponibles=10
    )
    result = compare_alternatives(ComparisonRequest(alternativas=[a, b]))
    assert len(result.ranking) == 2
    assert any("distintos totales" in item for item in result.advertencias)
    assert all(
        RecommendationResponse.model_validate(item.recomendacion)
        for item in result.ranking
    )


def test_comparison_does_not_warn_when_lists_match():
    a = case()
    b = case(alternativa_id="tienda-b", productos_disponibles=9)
    result = compare_alternatives(ComparisonRequest(alternativas=[a, b]))
    assert not any("distintos totales" in item for item in result.advertencias)


def test_public_api_responses_contain_no_emoji():
    a = case()
    b = case(alternativa_id="tienda-b", costo_total=56.0)
    outputs = [
        recommend(a).model_dump(mode="json"),
        recommend(b).model_dump(mode="json"),
        compare_alternatives(
            ComparisonRequest(alternativas=[a, b])
        ).model_dump(mode="json"),
    ]
    for output in outputs:
        assert EMOJI.search(json.dumps(output, ensure_ascii=False)) is None


def test_streamlit_uses_plain_labels_and_has_no_emoji():
    path = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    assert EMOJI.search(path.read_text(encoding="utf-8")) is None
    at = AppTest.from_file(str(path)).run(timeout=20)
    assert not at.exception
    assert [tab.label for tab in at.tabs] == [
        "Laboratorio",
        "Comparador",
        "Sensibilidad",
        "Base de conocimiento",
    ]
