import asyncio

import httpx
import pytest

from app.main import app
from app.schemas.chatbot import ChatResponse
from app.schemas.recommendation import RecommendationResponse
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION

LARAVEL_PAYLOAD = {
    "request_id": "lista-42-sucursal-3",
    "alternativa_id": "sucursal-3",
    "costo_total": 42.50,
    "presupuesto": 50.00,
    "ahorro": 11.25,
    "distancia_km": 2.30,
    "distancia_adicional_km": 0.80,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def api_request(method: str, path: str, **kwargs):
    """Ejecuta requests ASGI contra la aplicación sin levantar un servidor."""

    async def send_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def recommend_payload(**changes) -> dict:
    return {**LARAVEL_PAYLOAD, **changes}


def get_recommendation() -> tuple[dict, RecommendationResponse]:
    response = api_request(
        "POST",
        "/api/v1/recommend",
        json=LARAVEL_PAYLOAD,
    )
    assert response.status_code == 200
    body = response.json()
    return body, RecommendationResponse.model_validate(body)


def test_laravel_payload_is_accepted_and_returns_http_200():
    response = api_request(
        "POST",
        "/api/v1/recommend",
        json=LARAVEL_PAYLOAD,
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "lista-42-sucursal-3"
    assert response.json()["nivel_recomendacion"] == "EXCELENTE"


def test_recommendation_response_contains_all_public_contract_fields():
    body, parsed = get_recommendation()

    assert set(body) == {
        "request_id",
        "nivel_recomendacion",
        "accion_sugerida",
        "explicacion",
        "reglas_activadas",
        "prioridad_aplicada",
        "hechos_derivados",
        "version_reglas",
        "winning_rule",
        "losing_rules",
        "trace",
        "version_contrato",
        "indice_conveniencia",
        "clasificacion_conveniencia",
        "componentes_conveniencia",
        "pesos_conveniencia",
    }
    assert parsed.request_id == LARAVEL_PAYLOAD["request_id"]


def test_recommendation_contains_winning_rule():
    _, recommendation = get_recommendation()

    assert recommendation.winning_rule == "R06"
    assert recommendation.winning_rule in recommendation.reglas_activadas


def test_recommendation_contains_losing_rules():
    _, recommendation = get_recommendation()

    assert recommendation.losing_rules == ["R07"]
    assert all(
        rule_id in recommendation.reglas_activadas for rule_id in recommendation.losing_rules
    )


def test_recommendation_contains_convenience_index_components_and_weights():
    body, recommendation = get_recommendation()

    assert recommendation.indice_conveniencia == 82.39
    assert recommendation.clasificacion_conveniencia == "ALTA_CONVENIENCIA"
    assert set(recommendation.componentes_conveniencia or {}) == {
        "ahorro",
        "disponibilidad",
        "distancia",
        "tiempo",
        "promociones",
    }
    assert recommendation.pesos_conveniencia == {
        "ahorro": 0.35,
        "disponibilidad": 0.25,
        "distancia": 0.2,
        "tiempo": 0.15,
        "promociones": 0.05,
    }
    assert body["componentes_conveniencia"]["disponibilidad"] == 1.0


def test_recommendation_contains_contract_and_rules_versions():
    _, recommendation = get_recommendation()

    assert recommendation.version_contrato == CONTRACT_VERSION
    assert recommendation.version_reglas == RULES_VERSION


def test_recommend_to_chat_flow_uses_the_real_recommendation_without_mutation():
    recommendation_body, recommendation = get_recommendation()
    original_recommendation = recommendation_body.copy()

    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Por qué se recomienda esta alternativa?",
            "facts": LARAVEL_PAYLOAD,
            "recommendation": recommendation_body,
        },
    )

    parsed = ChatResponse.model_validate(response.json())
    assert response.status_code == 200
    assert parsed.request_id == recommendation.request_id
    assert parsed.intent == "EXPLICACION"
    assert parsed.supported is True
    assert recommendation_body == original_recommendation
    assert recommendation.nivel_recomendacion == "EXCELENTE"
    assert recommendation.accion_sugerida


@pytest.mark.parametrize(
    ("message", "intent", "expected"),
    [
        (
            "¿Cuál es el índice de conveniencia?",
            "INDICE",
            "82.39",
        ),
        (
            "¿Qué regla ganó?",
            "REGLA_GANADORA",
            "R06",
        ),
        (
            "¿Qué reglas perdedoras se activaron?",
            "REGLAS_PERDEDORAS",
            "R07",
        ),
    ],
)
def test_chat_answers_questions_about_new_recommendation_fields(message, intent, expected):
    recommendation_body, _ = get_recommendation()

    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": message,
            "facts": LARAVEL_PAYLOAD,
            "recommendation": recommendation_body,
        },
    )

    parsed = ChatResponse.model_validate(response.json())
    assert response.status_code == 200
    assert parsed.intent == intent
    assert parsed.supported is True
    assert expected in parsed.response


def test_chat_accepts_recommendation_null_without_history_or_conversation_id():
    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Cuál es el índice de conveniencia?",
            "request_id": "lista-42-sucursal-3",
            "facts": LARAVEL_PAYLOAD,
            "recommendation": None,
        },
    )

    parsed = ChatResponse.model_validate(response.json())
    assert response.status_code == 200
    assert parsed.intent == "NO_DISPONIBLE"
    assert parsed.supported is False
    assert "no está disponible" in parsed.response


def test_chat_does_not_invent_internal_rules_or_product_names_in_normal_text():
    recommendation_body, _ = get_recommendation()

    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Por qué se recomienda esta alternativa?",
            "facts": LARAVEL_PAYLOAD,
            "recommendation": recommendation_body,
        },
    )

    text = response.json()["response"]
    assert "R06" not in text
    assert "R07" not in text
    assert "dentro_presupuesto" not in text
    assert "winning_rule" not in text
    assert "losing_rules" not in text
    assert "producto inventado" not in text.lower()


@pytest.mark.parametrize(
    "field_name",
    ["presupuesto", "distancia_km", "tiempo_estimado_min"],
)
def test_laravel_null_required_values_are_rejected(field_name):
    response = api_request(
        "POST",
        "/api/v1/recommend",
        json=recommend_payload(**{field_name: None}),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "forbidden_field",
    ["score", "penalizacion_distancia", "costo_tiempo"],
)
def test_laravel_optimizer_fields_are_rejected_by_python_contract(
    forbidden_field,
):
    response = api_request(
        "POST",
        "/api/v1/recommend",
        json=recommend_payload(**{forbidden_field: 1.0}),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("changes", "winning_rule"),
    [
        ({"costo_total": 56.0}, "R01"),
        ({"productos_esenciales_disponibles": 5}, "R02"),
    ],
)
def test_critical_rule_responses_are_preserved(changes, winning_rule):
    response = api_request(
        "POST",
        "/api/v1/recommend",
        json=recommend_payload(**changes),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["nivel_recomendacion"] == "NO_RECOMENDABLE"
    assert body["winning_rule"] == winning_rule
    assert body["indice_conveniencia"] is not None
    assert "información complementaria" in body["explicacion"]


def test_same_laravel_payload_is_repeatable():
    first = api_request(
        "POST",
        "/api/v1/recommend",
        json=LARAVEL_PAYLOAD,
    )
    second = api_request(
        "POST",
        "/api/v1/recommend",
        json=LARAVEL_PAYLOAD,
    )

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
