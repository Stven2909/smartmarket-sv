"""Check that simple Streamlit views remain functional without JS DataFrame chunks."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from streamlit.testing.v1 import AppTest

from demo import streamlit_app as demo

APP = Path(__file__).resolve().parents[1] / "demo" / "streamlit_app.py"


def test_static_table_escapes_html_and_keeps_headers_and_values():
    html = demo.static_table_html([
        {"Regla": "R06", "Detalle": "<script>alert('x')</script>"},
        {"Regla": "R07", "Detalle": "Ahorro & disponibilidad"},
    ])
    assert '<th scope="col">Regla</th>' in html
    assert "R06" in html and "R07" in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "Ahorro &amp; disponibilidad" in html
    assert 'class="sm-table-scroll"' in html
    assert 'tabindex="0"' in html


def test_static_table_handles_empty_and_missing_cells():
    assert demo.static_table_html([]) == ""
    assert "N/D" in demo.static_table_html(
        [{"Hecho": "ahorro", "Valor": None}, {"Hecho": "tiempo"}]
    )


def test_static_table_caps_rows_without_truncating_header():
    html = demo.static_table_html(
        [{"Indice": index} for index in range(150)], max_rows=7
    )
    assert html.count("<tr>") == 8  # header + 7 body rows
    assert "<td>6</td>" in html
    assert "<td>7</td>" not in html


@pytest.mark.parametrize("limit", [0, -1])
def test_static_table_rejects_invalid_row_limit(limit):
    with pytest.raises(ValueError, match="max_rows"):
        demo.static_table_html([{"a": 1}], max_rows=limit)


def test_all_api_views_stop_using_heavy_dataframe_and_json_widgets():
    source = APP.read_text(encoding="utf-8")
    assert "st.dataframe(" not in source
    assert "st.json(" not in source
    assert "render_static_table(" in source
    assert "render_json_static(" in source


def test_static_table_render_uses_html_only(monkeypatch):
    markdown = MagicMock()
    monkeypatch.setattr(demo.st, "markdown", markdown)
    demo.render_static_table([{"Regla": "R06", "Valor": 1}])
    markdown.assert_called_once()
    args, kwargs = markdown.call_args
    assert "sm-data-table" in args[0]
    assert kwargs["unsafe_allow_html"] is True


def test_app_test_renders_without_dataframe_widgets():
    at = AppTest.from_file(str(APP)).run(timeout=30)
    assert not at.exception
    assert len(at.tabs) == 4


def test_environment_api_key_is_used_as_server_side_http_header(monkeypatch):
    monkeypatch.setenv("SMARTMARKET_API_KEY", "private-test-value")
    monkeypatch.setenv("SMARTMARKET_API_URL", "https://example-render.invalid")
    assert demo.api_auth_headers() == {"X-API-Key": "private-test-value"}
    assert demo.api_base_url() == "https://example-render.invalid"


def test_streamlit_secrets_fallback_is_supported_without_exposing_key(monkeypatch):
    monkeypatch.delenv("SMARTMARKET_API_KEY", raising=False)
    monkeypatch.delenv("SMARTMARKET_API_URL", raising=False)
    monkeypatch.setattr(
        demo.st,
        "secrets",
        {
            "SMARTMARKET_API_KEY": "private-test-value",
            "SMARTMARKET_API_URL": "https://example-render.invalid",
        },
    )
    assert demo.api_auth_headers() == {"X-API-Key": "private-test-value"}
    assert demo.api_base_url() == "https://example-render.invalid"
