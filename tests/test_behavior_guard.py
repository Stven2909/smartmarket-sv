"""HU-17: comparación de ejecutables y protecciones de seguridad."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.behavior_guard import (
    EXPECTED_INPUTS,
    capture,
    compare,
    main,
    make_cases,
    summary,
)

ROOT = Path(__file__).resolve().parents[1]


def snapshots():
    cases = make_cases(ROOT / "data" / "scenarios.json")
    return cases, capture(cases)


def test_full_snapshot_covers_fixed_threshold_boundaries_and_3404_classes():
    cases, result = snapshots()
    assert len(cases) == 3443
    assert len(result["casos"]) == len(cases)
    assert len(result["contrato_entrada"]) == 14
    assert set(result["contrato_entrada"]) == EXPECTED_INPUTS
    assert len({x["id"] for x in cases}) == len(cases)


def test_same_commit_is_approved_without_differences():
    _, snapshot = snapshots()
    report = compare(snapshot, snapshot)
    assert report["resultado"] == "APROBADO"
    assert report["metricas"]["cambios_nivel"] == 0
    assert report["metricas"]["cambios_indice"] == 0
    assert report["metricas"]["perdidas_proteccion"] == 0
    assert report["metricas"]["casos"] == 3443
    assert "HU-17" in summary(report)


def test_classifier_regression_reactivating_r01_is_detected_even_with_same_rules():
    _, old = snapshots()
    current = json.loads(json.dumps(old))
    item = next(
        i for i in current["casos"] if "R01" in i["activadas"]
    )
    item["activadas"] = [x for x in item["activadas"] if x != "R01"]
    item["nivel"] = "BUENA"
    item["ganadora"] = "R07"
    result = compare(old, current)
    assert result["resultado"] == "BLOQUEADO"
    assert result["metricas"]["perdidas_proteccion"] == 1
    assert result["metricas"]["regresiones_criticas"] == 1
    assert result["ejemplos"][0]["riesgo"]


def test_loss_of_critical_activation_blocks_even_when_level_stays_rejected():
    _, old = snapshots()
    current = json.loads(json.dumps(old))
    item = next(i for i in current["casos"] if "R02" in i["activadas"])
    item["activadas"].remove("R02")
    report = compare(old, current)
    assert report["resultado"] == "BLOQUEADO"
    assert report["metricas"]["perdidas_proteccion"] == 1
    assert report["metricas"]["regresiones_criticas"] == 0


def test_weight_shift_above_ten_points_is_blocked():
    _, old = snapshots()
    current = json.loads(json.dumps(old))
    current["casos"][0]["indice"] = min(100, old["casos"][0]["indice"] + 25)
    assert compare(old, current)["resultado"] == "BLOQUEADO"


def test_small_index_shift_is_reported_but_permitted():
    _, old = snapshots()
    current = json.loads(json.dumps(old))
    current["casos"][0]["indice"] = old["casos"][0]["indice"] - 2
    report = compare(old, current)
    assert report["resultado"] == "APROBADO"
    assert report["metricas"]["cambios_indice"] == 1
    assert report["metricas"]["saltos_indice_grandes"] == 0


def test_fail_closed_on_unaligned_snapshot_or_invalid_contract():
    _, old = snapshots()
    invalid = json.loads(json.dumps(old))
    invalid["casos"].pop()
    try:
        compare(old, invalid)
        raise AssertionError("La comparación debería rechazar muestras diferentes")
    except ValueError:
        pass
    invalid = json.loads(json.dumps(old))
    invalid["contrato_entrada"] = []
    try:
        compare(old, invalid)
        raise AssertionError("La comparación debería rechazar contratos diferentes")
    except ValueError:
        pass


def test_cli_runs_without_importing_baseline_code_into_candidate(tmp_path):
    cases = tmp_path / "cases.json"
    snap = tmp_path / "snap.json"
    assert main(
        [
            "generate", "--scenarios", str(ROOT / "data" / "scenarios.json"),
            "--output", str(cases),
        ]
    ) == 0
    assert main(
        ["snapshot", "--cases", str(cases), "--output", str(snap)]
    ) == 0
    assert main(
        ["compare", "--baseline", str(snap), "--candidate", str(snap)]
    ) == 0


def test_modified_classifier_in_isolated_code_copy_blocks_critical_loss(tmp_path):
    """Ejecuta otra implementación, no un snapshot artificialmente editado."""

    baseline_cases = make_cases(ROOT / "data" / "scenarios.json")
    focus = baseline_cases[:9] + baseline_cases[-30:]
    before = capture(focus)
    isolated = tmp_path / "base"
    isolated.mkdir()
    shutil.copytree(ROOT / "app", isolated / "app")
    shutil.copytree(ROOT / "data", isolated / "data")

    classifier = isolated / "app" / "expert_system" / "classifiers.py"
    original = classifier.read_text(encoding="utf-8")
    marker = '"presupuesto_exceso_max_pct": 10.0'
    assert marker in original
    classifier.write_text(
        original.replace(marker, '"presupuesto_exceso_max_pct": 50.0'),
        encoding="utf-8",
    )
    cases = tmp_path / "cases.json"
    output = tmp_path / "candidate.json"
    cases.write_text(json.dumps(focus), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(isolated)}
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "behavior_guard.py"),
            "snapshot",
            "--cases", str(cases),
            "--output", str(output),
        ],
        cwd=isolated,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = compare(before, json.loads(output.read_text(encoding="utf-8")))
    assert report["resultado"] == "BLOQUEADO"
    assert report["metricas"]["perdidas_proteccion"] > 0


def test_workflow_uses_separate_git_worktree_and_correct_paths():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    assert "git worktree add --detach" in text
    assert 'PYTHONPATH="$RUNNER_TEMP/expert-baseline"' in text
    assert "scripts.behavior_guard" in text
    assert "--max-index-shift 10" in text
    assert "app/expert_system" in text
