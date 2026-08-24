import asyncio

import httpx
import requests

from app.main import app
from app.schemas.chatbot import ChatResponse
from app.schemas.recommendation import RecommendationResponse
from demo.streamlit_app import ApiClientError, call_health_endpoint, load_scenarios


def api_request(method: str, path: str, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_all_demo_scenarios_work_through_recommendation_api():
    for scenario in load_scenarios():
        response = api_request("POST", "/api/v1/recommend", json=scenario["facts"])

        assert response.status_code == 200, scenario["id"]
        parsed = RecommendationResponse.model_validate(response.json())
        assert parsed.request_id == scenario["facts"]["request_id"]
        assert parsed.nivel_recomendacion in {
            "EXCELENTE",
            "BUENA",
            "NO_RECOMENDABLE",
        }


def test_all_demo_scenarios_work_through_chat_api():
    for scenario in load_scenarios():
        recommendation_response = api_request("POST", "/api/v1/recommend", json=scenario["facts"])
        chat_response = api_request(
            "POST",
            "/api/v1/chat",
            json={
                "message": "¿Por qué se recomienda esta alternativa?",
                "facts": scenario["facts"],
                "recommendation": recommendation_response.json(),
            },
        )

        assert chat_response.status_code == 200, scenario["id"]
        parsed = ChatResponse.model_validate(chat_response.json())
        assert parsed.request_id == scenario["facts"]["request_id"]
        assert parsed.response.strip()


def test_recommendation_is_repeatable_for_same_scenario():
    scenario = load_scenarios()[0]

    first = api_request("POST", "/api/v1/recommend", json=scenario["facts"])
    second = api_request("POST", "/api/v1/recommend", json=scenario["facts"])

    assert first.json() == second.json()


def test_incorrect_api_url_is_reported(monkeypatch):
    def fail_connection(*args, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("demo.streamlit_app.requests.get", fail_connection)

    try:
        call_health_endpoint("http://invalid-host.test")
    except ApiClientError as exc:
        assert "No se pudo conectar" in str(exc)
    else:
        raise AssertionError("Se esperaba un error de conexión")
