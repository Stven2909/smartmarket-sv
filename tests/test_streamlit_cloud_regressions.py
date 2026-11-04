"""Streamlit regression checks for Cloud asset failures and service isolation."""

import json
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import recommend
from demo.streamlit_app import (
    ApiClientError,
    call_health_endpoint,
    call_recommendation_api,
    metric_cards_html,
)

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "demo" / "streamlit_app.py"


def test_metric_cards_are_server_rendered_html_without_lazy_metric_widgets():
    html = metric_cards_html(
        [
            ("Decisión experta", "EXCELENTE"),
            ("Regla ganadora", "R06"),
            ("Reglas activadas", 3),
            ("Índice auxiliar", "78.11/100"),
        ]
    )
    assert html.count('class="sm-stat-card"') == 4
    assert 'role="group"' in html
    assert "EXCELENTE" in html
    assert "78.11/100" in html
    assert "Metric." not in html

    source = APP.read_text(encoding="utf-8")
    assert not re.search(r"\bst\.metric\s*\(", source)
    assert not re.search(r"\b\w+\.metric\s*\(", source)
    assert ".sm-stat-grid" in source


def test_untrusted_text_cannot_inject_html_into_stat_cards():
    html = metric_cards_html(
        [('<img src=x onerror="alert(1)">', '<script>alert("x")</script>')]
    )
    assert "<img" not in html
    assert "<script" not in html
    assert "&lt;img" in html
    assert "&lt;script" in html
    assert "aria-label=" in html


def test_stat_cards_support_empty_and_very_long_values():
    assert metric_cards_html([]) == ""
    html = metric_cards_html([("Referencia", "X" * 256)])
    assert "X" * 256 in html
    assert "sm-stat-card" in html


def test_sidebar_disallows_untrusted_api_url_redirection():
    source = APP.read_text(encoding="utf-8")
    assert 'st.sidebar.text_input("URL del servicio Python"' not in source
    assert "base_url = api_base_url()" in source
    assert "st.sidebar.caption" in source


class FakeResponse:
    def __init__(self, data=None, status_code=200, invalid=False):
        self.data = data
        self.status_code = status_code
        self.invalid = invalid
        self.text = "debug message from upstream"

    def json(self):
        if self.invalid:
            raise ValueError("Invalid JSON from external API")
        return self.data


@pytest.mark.parametrize("response", [
    FakeResponse(invalid=True),
    FakeResponse(data=[]),
    FakeResponse(data="not an object"),
])
def test_bad_successful_api_response_is_controlled(monkeypatch, response):
    def fake_post(url, *, json, timeout, headers):
        return response

    monkeypatch.setattr("demo.streamlit_app.requests.post", fake_post)
    monkeypatch.setattr("demo.streamlit_app.api_auth_headers", lambda: {})
    with pytest.raises(ApiClientError, match="API devolvió"):
        call_recommendation_api({"request_id": "test"}, base_url="http://testserver")


def test_health_never_sends_server_secret_in_public_probe(monkeypatch):
    def fake_get(url, *, timeout):
        assert url == "http://testserver/health"
        return FakeResponse(data={"status": "ok"})

    monkeypatch.setattr("demo.streamlit_app.requests.get", fake_get)
    monkeypatch.setattr(
        "demo.streamlit_app.api_auth_headers",
        lambda: {"X-API-Key": "private-service-key"},
    )
    assert call_health_endpoint("http://testserver") == {"status": "ok"}


def test_live_recommendation_renders_all_four_stat_values_without_metric_chunk():
    scenario = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))[0]
    facts = scenario["facts"]
    result = recommend(RecommendationRequest.model_validate(facts)).model_dump(mode="json")
    test_app = AppTest.from_file(str(APP))
    test_app.session_state["latest_recommendation"] = result
    test_app.session_state["latest_facts"] = facts
    test_app.run(timeout=30)

    assert not test_app.exception
    metrics_html = [item.value for item in test_app.markdown if "sm-stat-grid" in item.value]
    assert metrics_html, "The result panel must show the summary values."
    merged = "\n".join(metrics_html)
    assert "Decisión experta" in merged
    assert result["nivel_recomendacion"] in merged
    assert "Índice auxiliar" in merged
    assert "Regla ganadora" in merged
    assert "Reglas activadas" in merged
    assert "Metric." not in merged


@pytest.mark.parametrize(
    "tab",
    ["Laboratorio", "Comparador", "Sensibilidad", "Base de conocimiento"],
)
def test_all_four_tabs_render_without_api_on_initial_load(tab, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No remote requests expected during tab rendering")

    monkeypatch.setattr("demo.streamlit_app.requests.get", fail_if_called)
    monkeypatch.setattr("demo.streamlit_app.requests.post", fail_if_called)
    at = AppTest.from_file(str(APP))
    at.session_state["active_tab"] = tab
    at.run(timeout=30)
    assert not at.exception
    assert len(at.tabs) == 4


def test_cloud_version_is_pinned_to_a_ci_tested_release():
    requirements = (ROOT / "demo" / "requirements.txt").read_text(encoding="utf-8")
    assert "streamlit==1.66.1" in requirements
