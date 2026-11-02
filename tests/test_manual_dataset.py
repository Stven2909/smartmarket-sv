"""HU-15: importación segura de hechos, procedencia y datos corruptos."""

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.schemas.recommendation import RecommendationRequest
from demo.manual_dataset import MAX_ROWS, import_dataset

BASE = {
    "request_id": "muestra-01",
    "alternativa_id": "super-a",
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def csv_bytes(rows, *, extras=None):
    records = [{**item, **(extras or {})} for item in rows]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue().encode("utf-8")


def test_csv_imports_all_fourteen_facts_without_metadata_leakage():
    rows = [
        {**BASE, "alternativa_id": f"super-{i}", "request_id": f"r{i}"}
        for i in range(1, 6)
    ]
    report = import_dataset(
        csv_bytes(rows, extras={"nombre": "Escenario", "procedencia": "sintetico"}),
        "muestras.csv",
    )
    assert report.errors == []
    assert len(report.scenarios) == 5
    assert {row["metadata"]["procedencia"] for row in report.scenarios} == {
        "sintetico"
    }
    assert all(len(item["facts"]) == 14 for item in report.scenarios)
    assert all(
        RecommendationRequest.model_validate(item["facts"])
        for item in report.scenarios
    )


def test_json_accepts_nested_facts_and_preserves_explicit_provenance():
    obj = {
        "escenarios": [
            {
                "nombre": "Compra capturada",
                "facts": BASE,
                "procedencia": "manual_real",
                "fecha_observacion": "2026-11-02",
                "tienda": "Tienda de demostración",
                "notas": "Datos transcritos por el equipo",
            }
        ]
    }
    outcome = import_dataset(json.dumps(obj).encode(), "capturas.json")
    assert outcome.errors == []
    assert outcome.scenarios[0]["facts"] == BASE
    assert any("no fueron verificadas" in w for w in outcome.warnings)
    assert "tienda" not in outcome.scenarios[0]["facts"]


def test_web_reference_requires_valid_url_and_date():
    candidate = {
        **BASE, "procedencia": "mixto_referencia_web",
        "fecha_observacion": "2026-11-02",
        "fuente_url": "https://www.superselectos.com/products?category=033",
        "notas": "Costo ilustrativo: inventario no verificado",
    }
    result = import_dataset(csv_bytes([candidate]), "publico.csv")
    assert not result.errors
    assert result.scenarios[0]["metadata"]["fuente_url"].startswith("https://")
    assert result.warnings
    candidate["fuente_url"] = "javascript:alert(1)"
    assert import_dataset(csv_bytes([candidate]), "publico.csv").errors


@pytest.mark.parametrize(
    "changes",
    [
        {"costo_total": "NaN"},
        {"ahorro": "Infinity"},
        {"presupuesto": "0"},
        {"productos_disponibles": "10.5"},
        {"productos_esenciales_disponibles": 9, "productos_disponibles": 8},
        {"productos_esenciales_totales": 11},
        {"promociones_aplicables": "talvez"},
        {"numero_supermercados": 0},
        {"costo_total": -1},
    ],
)
def test_invalid_numeric_boolean_and_stock_are_rejected(changes):
    rows = [{**BASE, **changes}]
    result = import_dataset(csv_bytes(rows), "invalido.csv")
    assert result.errors
    assert result.scenarios == []


def test_partial_bad_file_is_rejected_wholly():
    rows = [
        BASE,
        {**BASE, "alternativa_id": "super-b", "costo_total": "invalido"},
    ]
    result = import_dataset(csv_bytes(rows), "compras.csv")
    assert result.errors
    assert result.scenarios == []
    assert result.total_rows == 2


def test_duplicate_ids_do_not_pass():
    items = [BASE, {**BASE, "request_id": "otro"}]
    result = import_dataset(csv_bytes(items), "duplicados.csv")
    assert any("duplicado" in error for error in result.errors)


@pytest.mark.parametrize(
    "content,name",
    [
        (b"", "empty.csv"),
        (b"\xff", "bad.csv"),
        (b"not_a_csv", "not.txt"),
        (b"{", "invalid.json"),
        (b'{"escenarios":{}}', "bad.json"),
        (b"{}", "without_data.json"),
        (b'[{"x":null}]', "missing.json"),
        (b'[{"x":NaN}]', "nonfinite.json"),
    ],
)
def test_bad_encoding_or_structure_is_reported(content, name):
    result = import_dataset(content, name)
    assert result.errors
    assert result.scenarios == []


def test_too_many_rows_or_large_file_are_rejected():
    cases = [
        {**BASE, "alternativa_id": f"i-{number}"}
        for number in range(MAX_ROWS + 1)
    ]
    assert import_dataset(csv_bytes(cases), "large.csv").errors
    assert import_dataset(b"x" * 2_000_001, "large.csv").errors


def test_comparison_tab_has_upload_option_without_contacting_render(monkeypatch):
    import requests

    def reject(*args, **kwargs):
        raise AssertionError("No se debe consultar Render al abrir la pestaña.")

    monkeypatch.setattr(requests, "post", reject)
    monkeypatch.setattr(requests, "get", reject)
    path = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"
    app = AppTest.from_file(str(path))
    app.session_state["active_tab"] = "Comparador"
    app.run(timeout=20)
    assert not app.exception
    assert any(radio.label == "Origen de las alternativas" for radio in app.radio)
    assert not app.exception


def test_streamlit_entrypoint_imports_from_demo_directory():
    """Reproduce la ruta de arranque de Streamlit Community Cloud."""

    demo = Path(__file__).resolve().parents[1] / "demo"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import streamlit_app; assert callable(streamlit_app.import_dataset)",
        ],
        cwd=demo,
        capture_output=True,
        text=True,
        timeout=25,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_widget_and_server_agree_on_two_mb_upload_limit():
    from demo.manual_dataset import MAX_BYTES

    assert MAX_BYTES == 2_000_000
    script = (Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py")
    assert "max_upload_size=2" in script.read_text(encoding="utf-8")
