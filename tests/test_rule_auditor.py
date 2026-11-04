"""HU-11: análisis preventivo sin cambiar las decisiones de R01–R08."""

import asyncio
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest

from app.expert_system.classifiers import derive_facts
from app.expert_system.inference_engine import evaluate_rule
from app.expert_system.models import RuleResult
from app.expert_system.rule_auditor import audit_rules
from app.expert_system.rule_loader import load_rules
from app.main import app
from app.schemas.recommendation import RecommendationRequest
from app.schemas.rule_audit import RuleAuditResponse

RULES = load_rules()


def get(path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get(path, **kwargs)

    return asyncio.run(send())


def finding_types(report):
    return [issue.tipo for issue in report.hallazgos]


def test_current_rules_have_no_structural_findings():
    report = audit_rules()
    assert report.version_reglas
    assert report.reglas_evaluadas == 8
    assert report.escenarios_sinteticos == 2430
    assert not report.hallazgos
    assert {row.regla for row in report.cobertura} == {
        f"R{number:02}" for number in range(1, 9)
    }
    assert all(row.activaciones > 0 for row in report.cobertura)


def test_known_overlap_is_resolved_and_has_valid_reproducible_witness():
    report = audit_rules()
    pair = next(
        row for row in report.solapamientos if row.reglas == ["R06", "R07"]
    )
    assert pair.ganador_por_prioridad == "R06"
    assert pair.niveles == ["EXCELENTE", "BUENA"]
    assert pair.conflicto_de_nivel
    assert pair.casos_coincidentes > 0
    witness = RecommendationRequest.model_validate(pair.ejemplo)
    facts = derive_facts(witness)
    selected = [rule for rule in RULES if rule.id in pair.reglas]
    assert all(evaluate_rule(rule, facts) for rule in selected)
    assert pair.resuelto_por_prioridad


def test_rules_that_cannot_overlap_do_not_report_overlap():
    report = audit_rules()
    pairs = {frozenset(row.reglas) for row in report.solapamientos}
    assert frozenset(("R01", "R06")) not in pairs
    assert frozenset(("R01", "R07")) not in pairs
    assert frozenset(("R06", "R08")) not in pairs


def test_same_priority_overlap_uses_rule_id_for_tie_break():
    report = audit_rules()
    pair = next(
        row for row in report.solapamientos if row.reglas == ["R03", "R04"]
    )
    assert pair.ganador_por_prioridad == "R03"
    assert pair.niveles == ["NO_RECOMENDABLE", "NO_RECOMENDABLE"]


def test_identical_conditions_flag_duplicate_and_shadowed_rule():
    original = next(rule for rule in RULES if rule.id == "R06")
    twin = original.model_copy(update={"id": "R99", "priority": 15})
    report = audit_rules([original, twin])
    assert "CONDICIONES_DUPLICADAS" in finding_types(report)
    assert "REGLA_SOMBREADA" in finding_types(report)
    assert "SALIDAS_DIVERGENTES" not in finding_types(report)


def test_identical_conditions_with_different_results_are_flagged():
    original = next(rule for rule in RULES if rule.id == "R06")
    conflicting = original.model_copy(
        update={
            "id": "R99",
            "priority": 12,
            "result": RuleResult(
                level="NO_RECOMENDABLE",
                action="Otra acción",
                explanation="Otra conclusión",
            ),
        }
    )
    report = audit_rules([original, conflicting])
    assert "CONDICIONES_DUPLICADAS" in finding_types(report)
    assert "SALIDAS_DIVERGENTES" in finding_types(report)
    assert len(report.solapamientos) == 1
    assert report.solapamientos[0].ganador_por_prioridad == "R06"


def test_general_rule_shadows_specific_rule():
    original = next(rule for rule in RULES if rule.id == "R01")
    specific = original.model_copy(
        update={
            "id": "R99",
            "priority": 2,
            "conditions": {
                "presupuesto_muy_excedido": True,
                "ahorro_alto": True,
            },
        }
    )
    report = audit_rules([original, specific])
    assert "REGLA_SOMBREADA" in finding_types(report)
    assert "CONDICIONES_DUPLICADAS" not in finding_types(report)


def test_incompatible_true_facts_are_reported_without_fake_witness():
    original = RULES[0]
    impossible = original.model_copy(
        update={
            "conditions": {
                "dentro_presupuesto": True,
                "presupuesto_muy_excedido": True,
            }
        }
    )
    report = audit_rules([impossible])
    assert "CONDICIONES_INCOMPATIBLES" in finding_types(report)
    assert "SIN_ACTIVACION_EN_MUESTRA" in finding_types(report)
    assert report.cobertura[0].activaciones == 0


def test_exhaustive_partition_all_false_is_impossible():
    impossible = RULES[0].model_copy(
        update={
            "conditions": {
                "ahorro_bajo": False,
                "ahorro_medio": False,
                "ahorro_alto": False,
            }
        }
    )
    report = audit_rules([impossible])
    assert "CONDICIONES_INCOMPATIBLES" in finding_types(report)


def test_stock_implication_is_checked_for_consistent_counts():
    impossible = RULES[0].model_copy(
        update={
            "conditions": {
                "todos_productos_disponibles": True,
                "todos_esenciales_disponibles": False,
            }
        }
    )
    report = audit_rules([impossible])
    assert "CONDICIONES_INCOMPATIBLES" in finding_types(report)


def test_numeric_derived_fact_cannot_be_treated_as_a_boolean():
    impossible = RULES[0].model_copy(
        update={"conditions": {"diferencia_presupuesto": True}}
    )
    report = audit_rules([impossible])
    assert "HECHO_NO_BOOLEANO" in finding_types(report)
    assert report.cobertura[0].activaciones == 0


def test_duplicate_ids_are_reported_without_touching_rule_loader():
    duplicate = RULES[0].model_copy()
    report = audit_rules([RULES[0], duplicate])
    assert "ID_DUPLICADO" in finding_types(report)


def test_report_is_deterministic_and_does_not_mutate_rules():
    rules = load_rules()
    before = [rule.model_dump() for rule in rules]
    first = audit_rules(rules)
    second = audit_rules(rules)
    assert first.model_dump() == second.model_dump()
    assert [rule.model_dump() for rule in rules] == before


def test_get_audit_http_and_original_contract_are_unchanged():
    response = get("/api/v1/rule-audit")
    assert response.status_code == 200
    parsed = RuleAuditResponse.model_validate(response.json())
    assert parsed.reglas_evaluadas == 8
    spec = get("/openapi.json").json()
    assert "/api/v1/rule-audit" in spec["paths"]
    assert len(spec["components"]["schemas"]["RecommendationRequest"]["properties"]) == 14
    assert len(spec["components"]["schemas"]["RecommendationResponse"]["properties"]) == 16


def test_audit_uses_same_api_key_as_other_endpoints(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "audit-test-key")
    assert get("/api/v1/rule-audit").status_code == 401
    assert get(
        "/api/v1/rule-audit",
        headers={"X-API-Key": "audit-test-key"},
    ).status_code == 200


def test_streamlit_audit_button_fetches_real_asgi_report(monkeypatch):
    import requests

    def fake_get(url, *, timeout, headers, allow_redirects):
        assert allow_redirects is False
        assert url.endswith("/api/v1/rule-audit")
        assert timeout > 0
        return get("/api/v1/rule-audit", headers=headers)

    monkeypatch.setattr(requests, "get", fake_get)
    path = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    at = AppTest.from_file(str(path))
    at.session_state["active_tab"] = "Base de conocimiento"
    at.run(timeout=20)
    assert not at.exception
    button = next(
        item for item in at.button if item.label == "Auditar base de conocimiento"
    )
    button.click()
    at.run(timeout=20)
    assert not at.exception
    assert at.session_state["rule_audit_report"]["reglas_evaluadas"] == 8
    assert at.session_state["rule_audit_report"]["escenarios_sinteticos"] == 2430
