import asyncio

import httpx
import pytest

from app.chatbot.chatbot_service import chat
from app.chatbot.intent_detector import detect_intent, normalize_text
from app.main import app
from app.schemas.chatbot import ChatRequest
from app.schemas.recommendation import RecommendationResponse

client_transport_app = app


def request(method: str, url: str, **kwargs):
    async def send_request():
        transport = httpx.ASGITransport(app=client_transport_app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(send_request())


FACTS = {
    "costo_total": 42.50,
    "presupuesto": 50.00,
    "ahorro": 1.50,
    "distancia_km": 10.0,
    "distancia_adicional_km": 10.0,
    "tiempo_estimado_min": 35,
    "productos_disponibles": 7,
    "productos_totales": 8,
    "productos_esenciales_disponibles": 5,
    "productos_esenciales_totales": 5,
    "numero_supermercados": 1,
    "promociones_aplicables": False,
}


RECOMMENDATION = RecommendationResponse(
    request_id="demo-002",
    nivel_recomendacion="NO_RECOMENDABLE",
    accion_sugerida="Elegir una alternativa más cercana",
    explicacion="El ahorro obtenido no compensa la distancia adicional requerida.",
    reglas_activadas=["R03"],
    prioridad_aplicada="DISTANCIA_AHORRO",
    hechos_derivados={
        "dentro_presupuesto": True,
        "ahorro_bajo": True,
        "distancia_lejana": True,
    },
    version_reglas="1.0.0",
)


def make_request(message: str, **changes) -> ChatRequest:
    payload = {
        "message": message,
        "facts": FACTS,
        "recommendation": RECOMMENDATION.model_dump(),
    }
    payload.update(changes)
    return ChatRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("message", "expected_intent"),
    [
        ("¿Por qué no se recomienda?", "EXPLICACION"),
        ("¿Me alcanza el presupuesto?", "PRESUPUESTO"),
        ("¿Cuánto ahorro?", "AHORRO"),
        ("¿Está lejos?", "DISTANCIA"),
        ("¿Cuánto tardaré?", "TIEMPO"),
        ("¿Faltan productos?", "PRODUCTOS"),
        ("¿Qué puedo hacer para mejorar?", "MEJORAR"),
        ("¿Cómo puedo obtener una mejor recomendación?", "MEJORAR"),
        ("¿Qué reglas se activaron?", "REGLAS"),
        ("¿Cuál es el índice de conveniencia?", "INDICE"),
        ("¿Cuál es la regla ganadora?", "REGLA_GANADORA"),
        ("¿Qué reglas perdedoras hubo?", "REGLAS_PERDEDORAS"),
        ("¿Qué puedes hacer?", "AYUDA"),
    ],
)
def test_detects_required_intents(message, expected_intent):
    assert detect_intent(message) == expected_intent


def test_normalizes_accents():
    assert normalize_text("¿Cuánto tardaré?") == "¿cuanto tardare?"


def test_detects_message_without_accents():
    assert detect_intent("Cuanto tardare?") == "TIEMPO"


def test_unknown_question_returns_ayuda_and_unsupported():
    response = chat(make_request("¿Cuál es el color favorito del supermercado?"))

    assert response.intent == "AYUDA"
    assert response.supported is False
    assert "Puedo ayudarte" in response.response


def test_budget_inside_limit_response():
    response = chat(
        make_request(
            "¿Me alcanza el presupuesto?",
            facts={**FACTS, "costo_total": 42.50, "presupuesto": 50.00},
        )
    )

    assert "$7.50" in response.response


def test_budget_exceeded_response():
    response = chat(
        make_request(
            "¿Cuánto excede la compra?",
            facts={**FACTS, "costo_total": 60.00, "presupuesto": 50.00},
        )
    )

    assert response.response == (
        "Esta compra supera tu presupuesto por $10.00. Puedes quitar productos "
        "no esenciales o buscar una opción más económica."
    )


def test_savings_response():
    response = chat(make_request("¿Cuánto ahorro?"))

    assert "$1.50" in response.response


def test_distance_response():
    response = chat(make_request("¿Cuál es la distancia adicional?"))

    assert "10.00 km" in response.response


def test_rules_response():
    response = chat(make_request("¿Qué reglas se activaron?"))

    assert "R03" in response.response
    assert "el ahorro es pequeño" in response.response
    assert "prioridad aplicada" in response.response


def test_chatbot_does_not_change_recommendation():
    response = chat(make_request("¿Por qué no se recomienda?"))

    assert response.intent == "EXPLICACION"
    assert RECOMMENDATION.nivel_recomendacion == "NO_RECOMENDABLE"
    assert RECOMMENDATION.accion_sugerida == "Elegir una alternativa más cercana"


def test_explanation_starts_lowercase_after_porque():
    recommendation = RECOMMENDATION.model_copy(
        update={
            "nivel_recomendacion": "EXCELENTE",
            "explicacion": "Cumple el presupuesto y requiere un recorrido conveniente.",
        }
    )

    response = chat(
        ChatRequest(
            message="¿Por qué se recomienda?",
            facts=FACTS,
            recommendation=recommendation,
        )
    )

    assert response.response.startswith("Te recomiendo esta opción porque")


def test_missing_data_is_reported():
    response = chat(make_request("¿Cuánto ahorro?", facts={}))

    assert response.response == "No tengo datos suficientes para responder esa pregunta."


def test_chat_endpoint_returns_200():
    response = request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Por qué no se recomienda esta alternativa?",
            "facts": FACTS,
            "recommendation": RECOMMENDATION.model_dump(),
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "demo-002"
    assert response.json()["intent"] == "EXPLICACION"
    assert response.json()["supported"] is True


def test_chat_request_without_recommendation_is_valid_fallback():
    response = request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Cuánto ahorro?",
            "facts": FACTS,
            "recommendation": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["supported"] is False
    assert response.json()["intent"] == "NO_DISPONIBLE"
    assert response.json()["response"] == (
        "El asistente explicativo no está disponible en este momento. "
        "La recomendación principal continúa disponible."
    )


def test_invalid_chat_request_still_returns_422_for_empty_message():
    response = request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "",
            "facts": FACTS,
            "recommendation": None,
        },
    )

    assert response.status_code == 422
