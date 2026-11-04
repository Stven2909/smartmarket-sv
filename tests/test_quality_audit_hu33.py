"""The offline HU-33 guard must fail if safety explanations are removed."""

import json

import pytest

from app.expert_system.inference_engine import run_inference
from scripts import audit_decision_quality
from scripts.audit_decision_quality import (
    TARGETED,
    audit_quality,
    main,
    quality_cases,
)


def test_quality_audit_includes_documented_cases_and_targeted_boundaries():
    cases = quality_cases()
    assert len(cases) == 17 + len(TARGETED) == 27
    ids = [name for name, _ in cases]
    assert len(ids) == len(set(ids))
    assert {"r07-trayecto-extremo", "r08-trayecto-extremo",
            "r10-prioridad-sobre-r03"}.issubset(ids)


def test_quality_audit_finds_cases_to_review_without_fabricating_rejection():
    result = audit_quality(quality_cases())
    assert result["resultado"] == "APROBADO"
    assert result["total"] == 27
    assert result["total_violaciones"] == 0
    assert result["favorables"] > 0
    assert result["alertas"]["TRAYECTO_A_REVISAR"] > 0
    assert result["alertas"]["INDICE_BAJO_CON_DICTAMEN_FAVORABLE"] > 0
    assert result["alertas"]["SIN_ESENCIALES_IDENTIFICADOS"] > 0
    assert result["activaciones_criticas"] > 0
    assert "R07" in result["reglas_favorables"]
    assert "R08" in result["reglas_favorables"]


@pytest.mark.parametrize("case_id", [
    "r07-trayecto-extremo",
    "r10-prioridad-sobre-r03",
])
def test_guard_rejects_missing_positive_or_critical_explanation(
    monkeypatch, case_id,
):
    cases = [item for item in quality_cases() if item[0] == case_id]
    original = run_inference

    def corrupted(item):
        result = original(item)
        result["explanation"] = "Texto sin evidencia ni advertencias."
        return result

    monkeypatch.setattr(audit_decision_quality, "run_inference", corrupted)
    assert audit_quality(cases)["resultado"] == "BLOQUEADO"
    assert audit_quality(cases)["total_violaciones"] > 0


def test_cli_creates_readable_report_with_no_secret_or_production_write(tmp_path):
    target = tmp_path / "hu33-audit.json"
    assert main(["--json-output", str(target)]) == 0
    result = json.loads(target.read_text(encoding="utf-8"))
    assert result["total"] == 27
    assert result["tipo_datos"] == "SINTETICOS_NO_ETIQUETADOS"
    assert result["resultado"] == "APROBADO"


def test_no_cases_and_negative_example_limits_are_rejected():
    with pytest.raises(ValueError):
        audit_quality([])
    with pytest.raises(ValueError):
        audit_quality(quality_cases(), max_examples=-1)
