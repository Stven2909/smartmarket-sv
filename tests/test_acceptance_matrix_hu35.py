"""HU-35: manually expected outcomes, HTTP parity, and guard failure tests."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.main import app
from app.schemas.batch_recommendation import BatchRecommendationResponse
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.comparison_service import compare_alternatives
from app.services.recommendation_service import recommend
from scripts import validate_recommendation_matrix as acceptance

ROWS, INVALID = acceptance.load_validation_matrix()


def test_curated_oracle_covers_all_current_rules_and_extreme_categories():
    assert len(ROWS) == 49
    assert len(INVALID) == 8
    assert sum(category == "referencia" for _, category, _, _ in ROWS) == 17
    assert len({case_id for case_id, _, _, _ in ROWS}) == len(ROWS)
    assert len({case_id for case_id, _ in INVALID}) == len(INVALID)
    assert {expected["winner"] for _, _, _, expected in ROWS} == {
        None,
        *(f"R{number:02}" for number in range(1, 17)),
    }
    for _, _, request, expected in ROWS:
        assert isinstance(request, RecommendationRequest)
        assert expected["level"] in {"EXCELENTE", "BUENA", "NO_RECOMENDABLE"}


def test_all_expected_results_and_invalid_payloads_are_verified_offline():
    report = acceptance.audit_validation_matrix(ROWS, INVALID)
    assert report["resultado"] == "APROBADO", report["errores"]
    assert report["escenarios_validos"] == 49
    assert report["escenarios_verificados_sin_error"] == 49
    assert report["entradas_invalidas_rechazadas"] == 8
    assert report["total_errores"] == 0
    assert report["reglas_sin_victoria"] == []
    assert len(report["victorias_por_regla"]) == 16
    assert report["tipo_datos"] == "SINTETICOS_NO_ETIQUETADOS"


def test_manual_oracle_disagreement_blocks_even_if_inference_is_self_consistent():
    rows = list(ROWS)
    case_id, category, item, expected = rows[0]
    rows[0] = (case_id, category, item, {**expected, "winner": "R01"})
    result = acceptance.audit_validation_matrix(rows, INVALID)
    assert result["resultado"] == "BLOQUEADO"
    assert any("ganadora:" in error for error in result["errores"])


def test_commercial_advisory_removed_from_response_is_blocked(monkeypatch):
    original_recommend = acceptance.recommend
    target = [row for row in ROWS if row[0] == "r07-extremo-indice-bajo"]

    def compromised(item):
        result = original_recommend(item)
        return result.model_copy(update={"explicacion": "Sin advertencias."})

    monkeypatch.setattr(acceptance, "recommend", compromised)
    report = acceptance.audit_validation_matrix(target, [])
    assert report["resultado"] == "BLOQUEADO"
    assert any("falta advertencia" in error for error in report["errores"])


def test_cli_produces_inspectable_json_report(tmp_path):
    output = tmp_path / "hu35-validation.json"
    assert acceptance.main(["--json-output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["resultado"] == "APROBADO"
    assert report["escenarios_validos"] == 49
    assert report["tipo_datos"] == "SINTETICOS_NO_ETIQUETADOS"
    assert "precision" not in report


@pytest.mark.parametrize("mutation", ["source", "duplicate", "oracle"])
def test_invalid_or_tampered_fixture_fails_closed(tmp_path, mutation):
    raw = json.loads(acceptance.MATRIX.read_text(encoding="utf-8"))
    if mutation == "source":
        raw["reference_cases"][0]["source"] = "../private.json"
    elif mutation == "duplicate":
        raw["cases"][0]["id"] = raw["reference_cases"][0]["id"]
    else:
        del raw["cases"][0]["expected"]["winner"]
    path = tmp_path / "invalid-matrix.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        acceptance.load_validation_matrix(path)


def test_http_recommendation_and_batch_agree_with_oracle_and_each_other():
    async def run_http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            singles = []
            for identifier, _, request, expected in ROWS:
                response = await client.post(
                    "/api/v1/recommend",
                    json=request.model_dump(mode="json"),
                )
                assert response.status_code == 200, (identifier, response.text)
                parsed = RecommendationResponse.model_validate(response.json())
                assert parsed.winning_rule == expected["winner"], identifier
                assert parsed.nivel_recomendacion == expected["level"], identifier
                assert parsed.model_dump(mode="json") == recommend(
                    request
                ).model_dump(mode="json")
                assert len(response.json()) == 16
                assert len(parsed.trace) == 16
                assert response.headers["cache-control"] == "no-store"
                assert len(response.headers["x-expert-rules-sha256"]) == 64
                singles.append(parsed.model_dump(mode="json"))

            batch = await client.post(
                "/api/v1/recommend/batch",
                json={"alternativas": [
                    request.model_dump(mode="json")
                    for _, _, request, _ in ROWS
                ]},
            )
            assert batch.status_code == 200, batch.text
            parsed_batch = BatchRecommendationResponse.model_validate(batch.json())
            assert [
                result.model_dump(mode="json") for result in parsed_batch.resultados
            ] == singles
            assert batch.headers["cache-control"] == "no-store"
            assert len(batch.headers["x-expert-rules-sha256"]) == 64

            for invalid_id, invalid_payload in INVALID:
                rejected = await client.post(
                    "/api/v1/recommend", json=invalid_payload,
                )
                assert rejected.status_code == 422, invalid_id

    asyncio.run(run_http())



def test_comparison_with_oracle_examples_keeps_critical_risk_last():
    ids = [
        "escenario-ideal",
        "r07-extremo-indice-bajo",
        "presupuesto-excedido-ligero",
        "distancia-exacta-8-con-ahorro-bajo",
    ]
    by_id = {name: req for name, _, req, _ in ROWS}
    cases = [by_id[name] for name in ids]
    report = compare_alternatives(ComparisonRequest(alternativas=cases))
    assert [row.recomendacion.winning_rule for row in report.ranking] == [
        "R06", "R07", None, "R03",
    ]
    assert [row.riesgo_critico for row in report.ranking] == [
        False, False, False, True,
    ]
    assert report.mejor_alternativa_id == cases[0].alternativa_id
    assert any("advertencias comerciales" in note for note in report.advertencias)

    async def test_http():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/compare",
                json={"alternativas": [
                    item.model_dump(mode="json") for item in cases
                ]},
            )
            assert response.status_code == 200, response.text
            parsed = ComparisonResponse.model_validate(response.json())
            assert parsed.model_dump(mode="json") == report.model_dump(mode="json")

    asyncio.run(test_http())



def test_http_authentication_still_applies_to_validation_examples(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "hu35-fake-key")
    payload = ROWS[0][2].model_dump(mode="json")

    async def verify():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            without_key = await client.post("/api/v1/recommend", json=payload)
            assert without_key.status_code == 401
            good = await client.post(
                "/api/v1/recommend",
                json=payload,
                headers={"X-API-Key": "hu35-fake-key"},
            )
            assert good.status_code == 200
            assert "hu35-fake-key" not in good.text

    asyncio.run(verify())


def test_contract_fields_match_fixture_shape_exactly():
    assert len(RecommendationRequest.model_fields) == 14
    assert len(RecommendationResponse.model_fields) == 16
    assert Path(acceptance.MATRIX).is_file()
