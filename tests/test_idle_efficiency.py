"""Regresiones del consumo en reposo y arranque de los dos servicios."""

import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.expert_system.rule_auditor import _cached_default_audit, audit_rules
from app.expert_system.rule_loader import _cached_production_rules, load_rules

ROOT = Path(__file__).resolve().parents[1]


def test_fastapi_import_does_not_load_the_pdf_engine():
    """La generación de PDF debe ser opcional y no penalizar el cold start."""

    process = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import app.main, sys; "
                "assert not any(x == 'reportlab' or x.startswith('reportlab.') "
                "for x in sys.modules), 'ReportLab se importó al iniciar la API'; "
                "print('cold-start-import-ok')"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr


def test_audit_is_lazy_cached_and_returns_independent_results():
    _cached_default_audit.cache_clear()
    assert _cached_default_audit.cache_info().currsize == 0
    first = audit_rules()
    assert _cached_default_audit.cache_info().misses == 1
    assert first.escenarios_sinteticos == 2430
    first.resumen = "texto mutado en consumidor"
    first.cobertura.clear()
    second = audit_rules()
    assert second.resumen != first.resumen
    assert len(second.cobertura) == 8
    assert _cached_default_audit.cache_info().hits == 1


def test_rule_loader_reuses_parsed_rules_without_leaking_mutations():
    _cached_production_rules.cache_clear()
    first = load_rules()
    assert _cached_production_rules.cache_info().misses == 1
    first[0].priority = 999
    second = load_rules()
    assert second[0].priority != 999
    assert _cached_production_rules.cache_info().hits == 1


def test_separate_deployment_dependencies_are_minimal():
    api = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    frontend = (ROOT / "demo" / "requirements.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "fastapi" in api and "reportlab" in api
    assert "streamlit" not in api and "pytest" not in api
    assert "pypdf" not in api and "httpx" not in api
    assert "streamlit" in frontend and "requests" in frontend
    assert "fastapi" not in frontend and "reportlab" not in frontend
    assert "-r requirements.txt" in dev
    assert "-r demo/requirements.txt" in dev
    workflow = (
        ROOT / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    assert "pip install -r requirements-dev.txt ruff" in workflow


def test_inactive_tabs_do_not_construct_hidden_controls():
    script = ROOT / "demo" / "streamlit_app.py"
    app = AppTest.from_file(str(script)).run(timeout=20)
    assert not app.exception
    assert len(app.tabs) == 4
    assert app.selectbox
    assert not app.multiselect
    assert not any(
        button.label in {"Auditar base de conocimiento", "Generar informe académico PDF"}
        for button in app.button
    )


def test_knowledge_tab_is_available_without_rendering_lab():
    script = ROOT / "demo" / "streamlit_app.py"
    app = AppTest.from_file(str(script))
    app.session_state["active_tab"] = "Base de conocimiento"
    app.run(timeout=20)
    assert not app.exception
    assert len(app.tabs) == 4
    assert any(button.label == "Auditar base de conocimiento" for button in app.button)
    assert not any(button.label == "Verificar escenario" for button in app.button)
