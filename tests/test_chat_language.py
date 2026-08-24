import asyncio

import httpx

from app.chatbot.chatbot_service import chat
from app.chatbot.intent_detector import detect_intent
from app.main import app
from app.schemas.chatbot import ChatRequest
from app.schemas.recommendation import RecommendationResponse

IDEAL_FACTS = {
    "request_id": "language-001",
    "alternativa_id": "supermercado-1",
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

IDEAL_RECOMMENDATION = RecommendationResponse(
    request_id="language-001",
    nivel_recomendacion="EXCELENTE",
    accion_sugerida="Comprar todo en esta alternativa.",
    explicacion="Cumple el presupuesto y las condiciones principales.",
    reglas_activadas=["R06", "R07"],
    prioridad_aplicada="CONVENIENCIA",
    hechos_derivados={
        "dentro_presupuesto": True,
        "todos_esenciales_disponibles": True,
        "distancia_cercana": True,
        "tiempo_bajo": True,
        "una_parada": True,
        "promociones_relevantes": True,
        "ahorro_alto": True,
        "todos_productos_disponibles": True,
    },
    version_reglas="1.0.0",
    winning_rule="R06",
    losing_rules=["R07"],
    indice_conveniencia=82.39,
    clasificacion_conveniencia="ALTA_CONVENIENCIA",
    componentes_conveniencia={
        "ahorro": 0.5625,
        "disponibilidad": 1.0,
        "distancia": 0.96,
        "tiempo": 0.9,
        "promociones": 1.0,
    },
    pesos_conveniencia={
        "ahorro": 0.35,
        "disponibilidad": 0.25,
        "distancia": 0.20,
        "tiempo": 0.15,
        "promociones": 0.05,
    },
)


def make_chat(message: str, *, facts=None, recommendation=IDEAL_RECOMMENDATION):
    return ChatRequest(
        message=message,
        facts=facts or IDEAL_FACTS,
        recommendation=recommendation,
    )


def api_request(method: str, path: str, **kwargs):
    async def send_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send_request())


def test_explanation_is_human_and_action_oriented():
    response = chat(make_chat("¿Por qué se recomienda esta opción?"))

    assert response.response == (
        "Te recomiendo esta opción porque la compra está dentro de tu presupuesto, "
        "tu lista incluye todos los productos esenciales y el recorrido adicional "
        "es corto."
    )


def test_budget_inside_response_uses_two_decimals():
    response = chat(make_chat("¿Me alcanza el presupuesto?"))

    assert response.response == (
        "La compra cuesta $42.50 y tu presupuesto es de $50.00. Te quedan $7.50 disponibles."
    )


def test_budget_exceeded_response_includes_action():
    response = chat(
        make_chat(
            "¿Me alcanza el presupuesto?",
            facts={**IDEAL_FACTS, "costo_total": 68.00},
        )
    )

    assert response.response == (
        "Esta compra supera tu presupuesto por $18.00. Puedes quitar productos "
        "no esenciales o buscar una opción más económica."
    )


def test_savings_response_is_natural():
    response = chat(make_chat("¿Cuánto ahorro?"))

    assert response.response == (
        "Con esta opción ahorrarías aproximadamente $11.25 frente a la alternativa más cara."
    )


def test_distance_response_uses_total_and_additional_distance():
    response = chat(make_chat("¿Qué tan lejos está?"))

    assert response.response == (
        "El recorrido adicional es de 0.80 km. La distancia total hasta la sucursal es de 2.30 km."
    )


def test_time_response_uses_minutes():
    response = chat(make_chat("¿Cuánto tiempo tardaré?"))

    assert response.response == "El traslado estimado es de 12 minutos."


def test_complete_products_response_is_clear():
    response = chat(make_chat("¿Están disponibles mis productos?"))

    assert response.response == (
        "Los 10 productos de tu lista están disponibles "
        "y los 6 productos esenciales están completos."
    )


def test_incomplete_products_response_is_actionable():
    response = chat(
        make_chat(
            "¿Qué productos faltan?",
            facts={
                **IDEAL_FACTS,
                "productos_disponibles": 7,
                "productos_esenciales_disponibles": 5,
            },
        )
    )

    assert response.response == (
        "Hay 7 de 10 productos disponibles. Revisa especialmente los productos "
        "esenciales antes de comprar."
    )


def test_improve_response_is_actionable():
    response = chat(make_chat("¿Qué puedo hacer para mejorar?"))

    assert response.response == (
        "Para mejorar esta opción puedes reducir productos no esenciales, buscar "
        "una alternativa más cercana o elegir una tienda con mayor disponibilidad."
    )


def test_index_response_translates_internal_classification():
    response = chat(make_chat("¿Cuál es el índice de conveniencia?"))

    assert response.response == "Esta alternativa tiene una conveniencia alta: 82.39 sobre 100."
    assert "ALTA_CONVENIENCIA" not in response.response


def test_winning_rule_response_explains_code_in_human_language():
    response = chat(make_chat("¿Qué regla ganó?"))

    assert "R06" in response.response
    assert "condiciones más importantes de compra" in response.response
    assert "dentro de tu presupuesto" in response.response


def test_losing_rules_response_explains_other_factors():
    response = chat(make_chat("¿Qué reglas perdieron?"))

    assert "R07" in response.response
    assert "promociones aplicables" in response.response
    assert "no fueron el motivo principal" in response.response


def test_help_response_lists_user_facing_topics():
    response = chat(make_chat("¿Qué puedes hacer?"))

    assert response.response == (
        "Puedo ayudarte a entender el presupuesto, el ahorro, la distancia, "
        "el tiempo, los productos disponibles, las promociones y la recomendación."
    )


def test_unavailable_response_uses_explicit_status():
    response = chat(
        ChatRequest(
            message="¿Cuál es el índice?",
            request_id="language-fallback-001",
            facts=IDEAL_FACTS,
            recommendation=None,
        )
    )

    assert response.intent == "NO_DISPONIBLE"
    assert response.supported is False
    assert response.response == (
        "El asistente explicativo no está disponible en este momento. "
        "La recomendación principal continúa disponible."
    )


def test_questions_with_and_without_accents_are_supported():
    assert detect_intent("¿Cuál es el índice de conveniencia?") == "INDICE"
    assert detect_intent("Cual es el indice de conveniencia?") == "INDICE"
    assert detect_intent("¿Qué regla ganó?") == "REGLA_GANADORA"
    assert detect_intent("Que regla gano?") == "REGLA_GANADORA"


def test_normal_responses_hide_internal_names_and_rule_codes():
    normal_questions = (
        "¿Por qué se recomienda?",
        "¿Me alcanza el presupuesto?",
        "¿Cuánto ahorro?",
        "¿Qué tan lejos está?",
        "¿Cuánto tiempo tardaré?",
        "¿Qué productos faltan?",
        "¿Qué puedo hacer para mejorar?",
        "¿Qué puedes hacer?",
    )
    internal_names = (
        "R01",
        "R02",
        "R03",
        "R04",
        "R05",
        "R06",
        "R07",
        "R08",
        "dentro_presupuesto",
        "ahorro_alto",
        "distancia_cercana",
        "tiempo_bajo",
        "promociones_relevantes",
        "prioridad_aplicada",
        "losing_rules",
        "hecho derivado",
        "regla ganadora",
    )

    for question in normal_questions:
        response = chat(make_chat(question)).response
        assert not any(term in response for term in internal_names), response


def test_real_api_keeps_recommendation_metadata_and_chat_uses_it():
    recommendation_response = api_request(
        "POST",
        "/api/v1/recommend",
        json=IDEAL_FACTS,
    )
    recommendation_body = recommendation_response.json()
    chat_response = api_request(
        "POST",
        "/api/v1/chat",
        json={
            "message": "¿Cuál es el índice de conveniencia?",
            "facts": IDEAL_FACTS,
            "recommendation": recommendation_body,
        },
    )

    assert recommendation_response.status_code == 200
    assert chat_response.status_code == 200
    for field in (
        "request_id",
        "nivel_recomendacion",
        "accion_sugerida",
        "reglas_activadas",
        "winning_rule",
        "losing_rules",
        "trace",
        "indice_conveniencia",
        "clasificacion_conveniencia",
        "componentes_conveniencia",
        "pesos_conveniencia",
    ):
        assert field in recommendation_body
    assert "82.39" in chat_response.json()["response"]


def test_chat_does_not_change_level_or_action():
    before = IDEAL_RECOMMENDATION.model_dump()

    chat(make_chat("¿Por qué se recomienda?"))

    assert IDEAL_RECOMMENDATION.nivel_recomendacion == before["nivel_recomendacion"]
    assert IDEAL_RECOMMENDATION.accion_sugerida == before["accion_sugerida"]


def test_chat_responses_are_deterministic():
    request = make_chat("¿Por qué se recomienda esta opción?")

    assert chat(request) == chat(request)
