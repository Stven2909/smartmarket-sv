import asyncio

import httpx

from app.main import app
from app.schemas.chatbot import ChatResponse
from app.schemas.recommendation import RecommendationResponse


RECOMMEND_REQUEST = {
    "request_id": "chat-contract-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.50,
    "presupuesto": 50.00,
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


def api_request(method: str, path: str, **kwargs):
    async def send_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def get_real_recommendation() -> tuple[dict, RecommendationResponse]:
    recommendation_response = api_request(
        "POST",
        "/api/v1/recommend",
        json=RECOMMEND_REQUEST,
    )
    assert recommendation_response.status_code == 200
    parsed = RecommendationResponse.model_validate(recommendation_response.json())
    return recommendation_response.json(), parsed


def ask_with_real_recommendation(message: str):
    recommendation_json, recommendation = get_real_recommendation()
    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": message,
            "facts": RECOMMEND_REQUEST,
            "recommendation": recommendation_json,
        },
    )
    return response, recommendation


def test_chat_uses_the_real_recommend_endpoint_response():
    response, recommendation = ask_with_real_recommendation(
        "¿Por qué se recomienda esta alternativa?"
    )
    parsed = ChatResponse.model_validate(response.json())

    assert response.status_code == 200
    assert parsed.request_id == recommendation.request_id
    assert parsed.intent == "EXPLICACION"
    assert parsed.supported is True
    assert parsed.response.startswith("Te recomiendo esta opción porque")


def test_chat_preserves_new_recommendation_fields():
    response, recommendation = ask_with_real_recommendation(
        "¿Cuál es el índice de conveniencia?"
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "INDICE"
    assert f"{recommendation.indice_conveniencia:.2f}" in response.json()[
        "response"
    ]
    assert recommendation.componentes_conveniencia
    assert recommendation.pesos_conveniencia


def test_chat_answers_about_winning_rule_from_real_recommendation():
    response, recommendation = ask_with_real_recommendation(
        "¿Cuál es la regla ganadora?"
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "REGLA_GANADORA"
    assert recommendation.winning_rule in response.json()["response"]


def test_chat_answers_about_losing_rules_from_real_recommendation():
    response, recommendation = ask_with_real_recommendation(
        "¿Qué reglas perdedoras se activaron?"
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "REGLAS_PERDEDORAS"
    assert recommendation.losing_rules
    assert all(rule_id in response.json()["response"] for rule_id in recommendation.losing_rules)


def test_chat_fallback_when_recommendation_is_null():
    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Cuál es el índice de conveniencia?",
            "request_id": "fallback-001",
            "facts": RECOMMEND_REQUEST,
            "recommendation": None,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "request_id": "fallback-001",
        "intent": "NO_DISPONIBLE",
        "response": (
            "El asistente explicativo no está disponible en este momento. "
            "La recomendación principal continúa disponible."
        ),
        "supported": False,
    }


def test_chat_fallback_can_use_request_id_from_facts():
    response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Cuál es la regla ganadora?",
            "facts": {**RECOMMEND_REQUEST, "request_id": "facts-001"},
            "recommendation": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "facts-001"
    assert response.json()["supported"] is False
