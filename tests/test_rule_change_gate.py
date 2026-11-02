"""HU-14: puerta de calidad de reglas, sin modificar archivos de producción."""

import json
from pathlib import Path

from scripts.check_rule_regression import (
    check_changes,
    main,
    markdown_summary,
    scenarios_from_file,
)

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules.json"
SCENARIOS = ROOT / "data" / "scenarios.json"


def save_modified(tmp_path, edit):
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    edit(rules)
    path = tmp_path / "proposed-rules.json"
    path.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
    return path


def change_priority(rule_id, priority):
    def edit(rules):
        next(rule for rule in rules if rule["id"] == rule_id)["priority"] = priority

    return edit


def test_original_rules_pass_with_all_representative_scenarios():
    result = check_changes(RULES, RULES, SCENARIOS)
    assert result["resultado"] == "APROBADO"
    assert result["metricas"]["casos"] == 2439
    assert result["metricas"]["regresiones_criticas"] == 0
    assert result["metricas"]["perdidas_proteccion"] == 0
    assert result["hallazgos_nuevos"] == []
    assert result["huella_anterior"] == result["huella_propuesta"]


def test_benign_priority_change_is_allowed_but_reported(tmp_path):
    proposed = save_modified(tmp_path, change_priority("R06", 7))
    result = check_changes(
        RULES, proposed, SCENARIOS, representative=False
    )
    assert result["resultado"] == "APROBADO"
    assert result["metricas"]["casos"] == 9
    assert result["metricas"]["cambios_nivel"] == 1
    assert result["metricas"]["regresiones_criticas"] == 0
    assert any(item["escenario"] == "Compra ideal" for item in result["ejemplos"])
    assert "Regresión automática" in markdown_summary(result)


def test_critical_promotion_overrides_are_blocked_in_full_grid(tmp_path):
    proposed = save_modified(tmp_path, change_priority("R02", 9))
    result = check_changes(RULES, proposed, SCENARIOS)
    assert result["resultado"] == "BLOQUEADO"
    assert result["metricas"]["casos"] == 2439
    assert result["metricas"]["regresiones_criticas"] > 0
    assert any(item["regresion_critica"] for item in result["ejemplos"])


def test_silent_loss_of_risk_rule_is_blocking_even_without_positive_result(tmp_path):
    proposed = save_modified(
        tmp_path,
        lambda rules: rules.__setitem__(
            slice(None), [rule for rule in rules if rule["id"] != "R01"]
        ),
    )
    result = check_changes(
        RULES, proposed, SCENARIOS, representative=False
    )
    assert result["resultado"] == "BLOQUEADO"
    assert result["metricas"]["perdidas_proteccion"] > 0


def test_new_structural_contradiction_is_rejected(tmp_path):
    def contradiction(rules):
        next(rule for rule in rules if rule["id"] == "R06")["conditions"] = {
            "dentro_presupuesto": True,
            "presupuesto_muy_excedido": True,
        }

    proposed = save_modified(tmp_path, contradiction)
    result = check_changes(
        RULES, proposed, SCENARIOS, representative=False
    )
    assert result["resultado"] == "BLOQUEADO"
    assert any(
        issue["tipo"] == "CONDICIONES_INCOMPATIBLES"
        for issue in result["hallazgos_nuevos"]
    )


def test_narrative_only_changes_are_allowed_without_misleading_level_change(tmp_path):
    def edit(rules):
        next(rule for rule in rules if rule["id"] == "R06")["result"][
            "explanation"
        ] = "Explicación revisada del prototipo."

    proposed = save_modified(tmp_path, edit)
    result = check_changes(
        RULES, proposed, SCENARIOS, representative=False
    )
    assert result["resultado"] == "APROBADO"
    assert result["metricas"]["cambios_nivel"] == 0
    assert result["metricas"]["cambios_explicacion"] >= 1
    assert result["huella_anterior"] != result["huella_propuesta"]


def test_invalid_json_fails_closed(tmp_path, capsys):
    invalid = tmp_path / "invalid-rules.json"
    invalid.write_text("{invalid json", encoding="utf-8")
    status = main(
        [
            "--baseline", str(RULES),
            "--candidate", str(invalid),
            "--scenarios", str(SCENARIOS),
        ]
    )
    assert status == 2
    assert "ERROR" in capsys.readouterr().err


def test_cli_writes_summary_and_returns_correct_exit_code(tmp_path, monkeypatch):
    summary = tmp_path / "step-summary.md"
    output = tmp_path / "result.json"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    proposed = save_modified(tmp_path, change_priority("R06", 7))
    status = main(
        [
            "--baseline", str(RULES),
            "--candidate", str(proposed),
            "--scenarios", str(SCENARIOS),
            "--json-output", str(output),
        ]
    )
    assert status == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["resultado"] == "APROBADO"
    assert report["metricas"]["casos"] == 2439
    assert "HU-14" in summary.read_text(encoding="utf-8")


def test_representative_scenarios_have_valid_payloads_and_expected_count():
    scenarios = scenarios_from_file(SCENARIOS)
    assert len(scenarios) == 9
    assert {scenario.nombre for scenario in scenarios} >= {
        "Compra ideal",
        "Presupuesto muy excedido",
    }


def test_gate_script_and_workflow_are_wired_for_pull_requests():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert "pull_request:" in workflow
    assert "Gate - Rule regressions on pull requests" in workflow
    assert "github.event.pull_request.base.sha" in workflow
    assert "python -m scripts.check_rule_regression" in workflow
    assert "data/rules.json" in workflow
