"""HU-12: documento académico PDF, contrato, seguridad e interfaz."""

import asyncio
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from app.main import app
from app.schemas.evidence_report import EvidenceReportRequest
from app.services.evidence_report_service import build_evidence, generate_evidence_pdf
from demo.streamlit_app import load_scenarios


def source_scenarios(limit=9):
    return [
        {"nombre": s["name"], "hechos": s["facts"]}
        for s in load_scenarios()[:limit]
    ]


def source_request(limit=9):
    return EvidenceReportRequest.model_validate(
        {"procedencia": "sintetico", "escenarios": source_scenarios(limit)}
    )


def call_api(method, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def pdf_text(data):
    reader = PdfReader(BytesIO(data))
    return reader, "\n".join(page.extract_text() for page in reader.pages)


def test_evidence_bundle_uses_real_existing_services():
    payload = source_request()
    before = payload.model_dump()
    bundle = build_evidence(payload)
    assert len(bundle.comparison.ranking) == 9
    assert bundle.audit.escenarios_sinteticos == 2430
    assert len(bundle.audit.cobertura) == 8
    assert len(bundle.sensitivity) == 9
    assert all(len(item.escenarios) >= 4 for item in bundle.sensitivity)
    assert bundle.request.model_dump() == before
    assert bundle.comparison.mejor_alternativa_id


def test_pdf_has_complete_technical_evidence_for_nine_scenarios():
    report = generate_evidence_pdf(source_request())
    assert report.startswith(b"%PDF-")
    assert len(report) > 10000
    reader, content = pdf_text(report)
    assert len(reader.pages) >= 10
    for text in (
        "SmartMarket SV",
        "Informe técnico de inferencia y validación",
        "Comparación experta",
        "Cobertura de las reglas",
        "Auditoría de consistencia",
        "Solapamientos detectados",
        "Trazabilidad de las ocho reglas",
        "Sensibilidad hipotética",
        "Alcance y limitaciones",
        "EXCELENTE",
        "NO_RECOMENDABLE",
        "R06",
        "R07",
        "2430",
    ):
        assert text.lower() in content.lower(), text
    assert reader.metadata.title.startswith("SmartMarket SV")


def test_pdf_has_real_trace_and_sensitivity_for_small_report():
    data = generate_evidence_pdf(source_request(limit=2))
    reader, text = pdf_text(data)
    assert len(reader.pages) >= 4
    assert "Compra ideal" in text
    assert "Presupuesto muy excedido" in text
    assert "presupuesto_muy_excedido" in text
    assert "distancia_mas_2_km" in text
    assert "falta_un_esencial" in text
    assert "Regla" in text


def test_pdf_does_not_invent_data_provenance():
    request = EvidenceReportRequest.model_validate(
        {"escenarios": source_scenarios(limit=2)}
    )
    assert request.procedencia == "no_verificada"
    pdf = generate_evidence_pdf(request)
    _, text = pdf_text(pdf)
    assert "Procedencia declarada no verificada" in text


@pytest.mark.parametrize(
    "changes",
    [
        {"escenarios": source_scenarios(limit=1)},
        {"escenarios": source_scenarios() + source_scenarios(limit=2)},
        {
            "escenarios": source_scenarios(limit=2)
            + [{**source_scenarios(limit=1)[0], "nombre": "duplicado"}]
        },
        {
            "escenarios": [
                source_scenarios(limit=2)[0],
                {
                    **source_scenarios(limit=2)[1],
                    "hechos": {
                        **source_scenarios(limit=2)[1]["hechos"],
                        "presupuesto": 60.0,
                    },
                },
            ]
        },
    ],
)
def test_invalid_report_requests_are_rejected(changes):
    with pytest.raises(ValidationError):
        EvidenceReportRequest.model_validate(changes)


def test_endpoint_returns_pdf_headers_and_preserves_original_contract():
    payload = source_request(limit=2).model_dump(mode="json")
    response = call_api("POST", "/api/v1/evidence-report", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in response.headers["content-disposition"]
    assert "no-store" in response.headers["cache-control"]
    assert response.content.startswith(b"%PDF-")
    reader, content = pdf_text(response.content)
    assert len(reader.pages) >= 4
    assert "R01" in content
    spec = call_api("GET", "/openapi.json").json()
    assert "/api/v1/evidence-report" in spec["paths"]
    media_types = spec["paths"]["/api/v1/evidence-report"]["post"]["responses"]["200"]["content"]
    assert "application/pdf" in media_types
    models = spec["components"]["schemas"]
    assert len(models["RecommendationRequest"]["properties"]) == 14
    assert len(models["RecommendationResponse"]["properties"]) == 16


def test_endpoint_rejects_invalid_json_and_honors_api_key(monkeypatch):
    bad = call_api("POST", "/api/v1/evidence-report", json={"escenarios": []})
    assert bad.status_code == 422
    monkeypatch.setenv("SMARTMARKET_API_KEY", "ci-secret")
    data = source_request(limit=2).model_dump(mode="json")
    unauthorized = call_api("POST", "/api/v1/evidence-report", json=data)
    assert unauthorized.status_code == 401
    authorized = call_api(
        "POST", "/api/v1/evidence-report",
        json=data, headers={"X-API-Key": "ci-secret"},
    )
    assert authorized.status_code == 200
    assert authorized.content.startswith(b"%PDF-")


def test_streamlit_pdf_generation_and_download_button(monkeypatch):
    import requests

    def fake_post(url, *, json, timeout, headers, allow_redirects):
        assert allow_redirects is False
        assert url.endswith("/api/v1/evidence-report")
        assert timeout > 0
        assert json["procedencia"] == "sintetico"
        return call_api("POST", "/api/v1/evidence-report", json=json, headers=headers)

    monkeypatch.setattr(requests, "post", fake_post)
    script = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(script))
    at.session_state["active_tab"] = "Base de conocimiento"
    at.run(timeout=20)
    assert not at.exception
    assert len(at.tabs) == 4
    button = next(
        button
        for button in at.button
        if button.label == "Generar informe académico PDF"
    )
    button.click()
    at.run(timeout=30)
    assert not at.exception
    assert at.session_state["evidence_pdf"].startswith(b"%PDF-")
