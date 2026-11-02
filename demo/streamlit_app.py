import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st

# Streamlit Cloud ejecuta este archivo desde demo/ y puede no incluir
# la raíz del repositorio en sys.path. Los tests lo importan como paquete.
try:
    from demo.manual_dataset import import_dataset
except ModuleNotFoundError as exc:
    if exc.name != "demo":
        raise
    from manual_dataset import import_dataset

DEFAULT_API_BASE_URL = "http://127.0.0.1:8001"
# Espera pasiva ante un posible arranque en frío; no realiza peticiones periódicas.
REQUEST_TIMEOUT_SECONDS = 90
SCENARIOS_PATH = Path(__file__).resolve().parents[1] / "data" / "scenarios.json"


class ScenarioLoadError(ValueError):
    """Error comprensible al cargar los escenarios de demostración."""


class ApiClientError(RuntimeError):
    """Error controlado al comunicarse con FastAPI."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@st.cache_data(show_spinner=False, max_entries=4)
def load_scenarios(path: Path | None = None) -> list[dict[str, Any]]:
    scenarios_path = Path(path) if path is not None else SCENARIOS_PATH

    try:
        raw_data = json.loads(scenarios_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScenarioLoadError(
            f"No se encontró el archivo de escenarios: {scenarios_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ScenarioLoadError(
            f"JSON de escenarios inválido: línea {exc.lineno}, columna {exc.colno}"
        ) from exc
    except OSError as exc:
        raise ScenarioLoadError(f"No se pudo leer el archivo de escenarios: {exc}") from exc

    if not isinstance(raw_data, list) or not raw_data:
        raise ScenarioLoadError("El archivo de escenarios debe contener una lista no vacía.")

    for index, scenario in enumerate(raw_data):
        if not isinstance(scenario, dict):
            raise ScenarioLoadError(f"El escenario {index} debe ser un objeto JSON.")
        if not scenario.get("id") or not scenario.get("name"):
            raise ScenarioLoadError(f"El escenario {index} requiere id y name.")
        if not isinstance(scenario.get("facts"), dict):
            raise ScenarioLoadError(
                f"El escenario {scenario.get('id', index)} requiere un objeto facts."
            )

    return raw_data


def api_base_url() -> str:
    configured_url = os.getenv("SMARTMARKET_API_URL", "").strip()

    if not configured_url:
        try:
            configured_url = str(st.secrets.get("SMARTMARKET_API_URL", "")).strip()
        except (FileNotFoundError, KeyError):
            configured_url = ""

    return (configured_url or DEFAULT_API_BASE_URL).rstrip("/")


def api_auth_headers() -> dict[str, str]:
    key = os.getenv("SMARTMARKET_API_KEY", "").strip()

    if not key:
        try:
            key = str(st.secrets.get("SMARTMARKET_API_KEY", "")).strip()
        except (FileNotFoundError, KeyError):
            key = ""

    return {"X-API-Key": key} if key else {}


def validate_payload(payload: dict[str, Any]) -> list[str]:
    """Valida localmente el formulario antes de enviarlo a FastAPI."""

    errors: list[str] = []
    if not str(payload.get("request_id", "")).strip():
        errors.append("Request ID es obligatorio.")
    if not str(payload.get("alternativa_id", "")).strip():
        errors.append("Alternativa ID es obligatorio.")

    non_negative_fields = {
        "costo_total": "Costo total",
        "ahorro": "Ahorro",
        "distancia_km": "Distancia",
        "distancia_adicional_km": "Distancia adicional",
        "tiempo_estimado_min": "Tiempo estimado",
        "productos_disponibles": "Productos disponibles",
        "productos_esenciales_disponibles": "Productos esenciales disponibles",
    }
    for field, label in non_negative_fields.items():
        if float(payload.get(field, -1)) < 0:
            errors.append(f"{label} no puede ser negativo.")

    if float(payload.get("presupuesto", 0)) <= 0:
        errors.append("Presupuesto debe ser mayor que cero.")
    if int(payload.get("productos_totales", 0)) <= 0:
        errors.append("Productos totales debe ser mayor que cero.")
    if int(payload.get("productos_esenciales_totales", 0)) < 0:
        errors.append("Productos esenciales totales no puede ser negativo.")
    if int(payload.get("numero_supermercados", 0)) < 1:
        errors.append("Número de supermercados debe ser como mínimo uno.")
    if int(payload.get("productos_disponibles", 0)) > int(payload.get("productos_totales", 0)):
        errors.append("Productos disponibles no puede superar productos totales.")
    if int(payload.get("productos_esenciales_disponibles", 0)) > int(
        payload.get("productos_esenciales_totales", 0)
    ):
        errors.append(
            "Productos esenciales disponibles no puede superar productos esenciales totales."
        )
    total = int(payload.get("productos_totales", 0))
    disponibles = int(payload.get("productos_disponibles", 0))
    esenciales_total = int(payload.get("productos_esenciales_totales", 0))
    esenciales_disponibles = int(payload.get("productos_esenciales_disponibles", 0))
    if esenciales_total > total:
        errors.append("Productos esenciales totales no puede superar productos totales.")
    if esenciales_disponibles > disponibles:
        errors.append("Productos esenciales disponibles no puede superar productos disponibles.")
    if disponibles - esenciales_disponibles > total - esenciales_total:
        errors.append("Productos opcionales disponibles no pueden superar su total.")
    return errors


def _response_detail(response: requests.Response) -> str:
    try:
        detail = response.json().get("detail")
        if isinstance(detail, list):
            return "; ".join(
                item.get("msg", str(item)) if isinstance(item, dict) else str(item)
                for item in detail
            )
        if detail:
            return str(detail)
    except (ValueError, AttributeError):
        pass
    return response.text or "Sin detalle de error."


def call_health_endpoint(base_url: str | None = None) -> dict[str, Any]:
    url = f"{(base_url or api_base_url()).rstrip('/')}/health"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers=api_auth_headers())
    except requests.Timeout as exc:
        raise ApiClientError("La API tardó demasiado en responder.") from exc
    except requests.RequestException as exc:
        raise ApiClientError(f"No se pudo conectar con FastAPI: {exc}") from exc

    if response.status_code >= 400:
        raise ApiClientError(
            f"FastAPI respondió HTTP {response.status_code}: {_response_detail(response)}",
            response.status_code,
        )
    return response.json()


def _post_json(path: str, payload: dict[str, Any], base_url: str | None = None) -> dict[str, Any]:
    url = f"{(base_url or api_base_url()).rstrip('/')}{path}"
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=api_auth_headers(),
        )
    except requests.Timeout as exc:
        raise ApiClientError("La API tardó demasiado en responder.") from exc
    except requests.RequestException as exc:
        raise ApiClientError(f"No se pudo conectar con FastAPI: {exc}") from exc

    if response.status_code >= 400:
        raise ApiClientError(
            f"FastAPI respondió HTTP {response.status_code}: {_response_detail(response)}",
            response.status_code,
        )
    return response.json()


def call_recommendation_api(payload: dict[str, Any], base_url: str | None = None) -> dict[str, Any]:
    return _post_json("/api/v1/recommend", payload, base_url)


def call_comparison_api(
    alternatives: list[dict[str, Any]], base_url: str | None = None
) -> dict[str, Any]:
    """Compara opciones usando exclusivamente el servicio Python."""
    return _post_json("/api/v1/compare", {"alternativas": alternatives}, base_url)


def call_rule_regression_api(
    baseline: dict[str, Any],
    proposed: dict[str, Any],
    scenarios: list[dict[str, Any]],
    base_url: str | None = None,
) -> dict[str, Any]:
    """Compara snapshots sin escribir sobre la base de reglas publicada."""

    return _post_json(
        "/api/v1/rule-regression",
        {
            "anterior": baseline,
            "propuesta": proposed,
            "escenarios": [
                {"nombre": item["name"], "hechos": item["facts"]}
                for item in scenarios
            ],
        },
        base_url,
    )


def call_sensitivity_api(
    alternative: dict[str, Any], base_url: str | None = None
) -> dict[str, Any]:
    """Ejecuta escenarios hipotéticos en la API sin depender de otros sistemas."""
    return _post_json("/api/v1/sensitivity", {"alternativa": alternative}, base_url)


def call_diagnosis_api(
    alternative: dict[str, Any], base_url: str | None = None
) -> dict[str, Any]:
    """Explica reglas pendientes y riesgos usando los hechos recibidos."""
    return _post_json("/api/v1/diagnosis", {"alternativa": alternative}, base_url)


def call_knowledge_api(base_url: str | None = None) -> dict[str, Any]:
    """Lee reglas y parámetros de la API; nunca ejecuta el motor en la interfaz."""
    url = f"{(base_url or api_base_url()).rstrip('/')}/api/v1/knowledge"
    try:
        response = requests.get(
            url, timeout=REQUEST_TIMEOUT_SECONDS, headers=api_auth_headers()
        )
    except requests.Timeout as exc:
        raise ApiClientError("La API tardó demasiado en responder.") from exc
    except requests.RequestException as exc:
        raise ApiClientError(f"No se pudo conectar con FastAPI: {exc}") from exc
    if response.status_code >= 400:
        raise ApiClientError(
            f"FastAPI respondió HTTP {response.status_code}: {_response_detail(response)}",
            response.status_code,
        )
    return response.json()


def call_rule_audit_api(base_url: str | None = None) -> dict[str, Any]:
    """Consulta el informe de consistencia sin evaluar ni modificar compras."""
    url = f"{(base_url or api_base_url()).rstrip('/')}/api/v1/rule-audit"
    try:
        response = requests.get(
            url, timeout=REQUEST_TIMEOUT_SECONDS, headers=api_auth_headers()
        )
    except requests.Timeout as exc:
        raise ApiClientError("La auditoría tardó demasiado en responder.") from exc
    except requests.RequestException as exc:
        raise ApiClientError(f"No se pudo conectar con FastAPI: {exc}") from exc
    if response.status_code >= 400:
        raise ApiClientError(
            f"FastAPI respondió HTTP {response.status_code}: {_response_detail(response)}",
            response.status_code,
        )
    return response.json()


def call_evidence_report_api(
    scenarios: list[dict[str, Any]], base_url: str | None = None
) -> bytes:
    """Solicita un PDF real; la interfaz no replica el motor experto."""

    url = f"{(base_url or api_base_url()).rstrip('/')}/api/v1/evidence-report"
    payload = {
        "procedencia": "sintetico",
        "escenarios": [
            {"nombre":item["name"], "hechos":item["facts"]}
            for item in scenarios
        ],
    }
    try:
        response = requests.post(
            url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS,
            headers=api_auth_headers(),
        )
    except requests.Timeout as exc:
        raise ApiClientError("La generación del informe tardó demasiado.") from exc
    except requests.RequestException as exc:
        raise ApiClientError(f"No se pudo conectar con FastAPI: {exc}") from exc
    if response.status_code >= 400:
        raise ApiClientError(
            f"FastAPI respondió HTTP {response.status_code}: {_response_detail(response)}",
            response.status_code,
        )
    if (
        not response.headers.get("content-type", "").startswith("application/pdf")
        or not response.content.startswith(b"%PDF-")
    ):
        raise ApiClientError("FastAPI no devolvió un documento PDF válido.")
    return response.content


def call_chat_api(
    message: str,
    facts: dict[str, Any],
    recommendation: dict[str, Any],
    base_url: str | None = None,
) -> dict[str, Any]:
    return _post_json(
        "/api/v1/chat",
        {
            "message": message,
            "facts": facts,
            "recommendation": recommendation,
        },
        base_url,
    )


def render_recommendation(
    result: dict[str, Any], *, widget_key: str = "laboratory"
) -> None:
    """Panel de auditoría: conclusión, pesos, hechos y explicación de reglas."""

    level = result.get("nivel_recomendacion", "DESCONOCIDO")
    index = result.get("indice_conveniencia")
    score = float(index) if isinstance(index, (int, float)) else None
    rule = result.get("winning_rule")
    activated = result.get("reglas_activadas", [])
    facts = result.get("hechos_derivados", {})

    with st.container(border=True):
        if level == "EXCELENTE":
            st.success("Alternativa favorable según las reglas")
        elif level == "BUENA":
            st.info("Alternativa aceptable según las reglas")
        else:
            st.warning("No recomendable o sin una regla favorable")

        a, b, c, d = st.columns(4)
        a.metric("Decisión experta", level)
        b.metric("Índice auxiliar", f"{score:.2f}/100" if score is not None else "N/D")
        c.metric("Regla ganadora", rule or "Ninguna")
        d.metric("Reglas activadas", len(activated))
        if score is not None:
            st.progress(max(0.0, min(score / 100.0, 1.0)))
        st.caption(
            "El índice es un indicador ponderado, no una probabilidad ni una confianza "
            "estadística. Las reglas críticas mantienen prioridad."
        )

    st.subheader("Decisión y justificación")
    st.write(f"**Acción:** {result.get('accion_sugerida', 'Sin acción')}")
    st.write(result.get("explicacion", "Sin explicación disponible."))
    st.caption(
        f"Solicitud: {result.get('request_id', 'N/D')} · "
        f"Categoría: {result.get('prioridad_aplicada', 'SIN_REGLA')} · "
        f"Reglas: {result.get('version_reglas', 'N/D')}"
    )

    st.subheader("Por qué obtuvo ese índice")
    weights = result.get("pesos_conveniencia") or {}
    components = result.get("componentes_conveniencia") or {}
    labels = {
        "ahorro": "Ahorro",
        "disponibilidad": "Disponibilidad",
        "distancia": "Distancia adicional",
        "tiempo": "Tiempo estimado",
        "promociones": "Promociones",
    }
    if weights and components:
        contribution_rows = [
            {
                "Criterio": labels.get(key, key),
                "Peso (%)": round(float(weight) * 100, 1),
                "Valor normalizado": round(float(components.get(key, 0)), 3),
                "Puntos aportados": round(
                    float(weight) * float(components.get(key, 0)) * 100, 2
                ),
            }
            for key, weight in weights.items()
        ]
        st.dataframe(contribution_rows, hide_index=True, use_container_width=True)
    else:
        st.info("Este servicio no incluyó el desglose ponderado.")

    with st.expander("Hechos derivados usados por el motor"):
        st.dataframe(
            [{"Hecho": name, "Valor": str(value)} for name, value in facts.items()],
            hide_index=True,
            use_container_width=True,
        )

    with st.expander("Auditoría de las 8 reglas: condiciones y coincidencias"):
        trace = result.get("trace") or []
        if not trace:
            st.info("No se recibió la traza de inferencia.")
        else:
            audit_rows = []
            for entry in trace:
                for fact_name, condition in entry.get("conditions", {}).items():
                    audit_rows.append(
                        {
                            "Regla": entry.get("rule_id"),
                            "Activada": bool(entry.get("activated")),
                            "Hecho": fact_name,
                            "Esperado": str(condition.get("expected")),
                            "Observado": str(condition.get("actual")),
                            "Coincide": bool(condition.get("matched")),
                        }
                    )
            st.dataframe(audit_rows, hide_index=True, use_container_width=True)
            losing = result.get("losing_rules") or []
            st.caption(
                "Ganadora: "
                + (rule or "ninguna")
                + " · Otras activadas: "
                + (", ".join(losing) if losing else "ninguna")
            )

    with st.expander("JSON completo de evidencia"):
        st.code(json.dumps(result, ensure_ascii=False, indent=2), language="json")
    st.download_button(
        "Descargar evidencia JSON",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name="smartmarket-evidencia.json",
        mime="application/json",
        key=f"download_{widget_key}",
    )


def render_diagnosis_panel(base_url: str, facts: dict[str, Any] | None) -> None:
    """Diagnóstico opcional; solo consulta la API con hechos ya evaluados."""

    st.subheader("Diagnóstico de oportunidades")
    st.caption(
        "Explica los requisitos de las reglas favorables sin cambiar el costo, "
        "la disponibilidad o cualquier otro hecho del backend."
    )
    if facts is None:
        st.info("Primero ejecuta una recomendación en el laboratorio.")
        return

    if st.button("Diagnosticar alternativa", key="diagnosis_button"):
        try:
            st.session_state["latest_diagnosis"] = call_diagnosis_api(facts, base_url)
            st.session_state["diagnosis_input"] = facts.copy()
        except ApiClientError as exc:
            st.error(f"No se pudo obtener el diagnóstico: {exc}")
            return

    report = st.session_state.get("latest_diagnosis")
    if not report or st.session_state.get("diagnosis_input") != facts:
        return

    st.write(report["resumen"])
    risks = report.get("riesgos_criticos", [])
    if risks:
        st.warning(
            "Reglas críticas activas: "
            + ", ".join(risk["regla"] for risk in risks)
        )
        for risk in risks:
            st.write(f"**{risk['regla']}:** {risk['motivo']}")

    opportunities = report.get("oportunidades", [])
    st.dataframe(
        [
            {
                "Regla": item["regla"],
                "Nivel posible": item["nivel_posible"],
                "Cumple": (
                    f"{item['condiciones_cumplidas']}/{item['condiciones_totales']}"
                ),
                "Pendientes": len(item["faltantes"]),
                "Ya activa": "Sí" if item["activa"] else "No",
            }
            for item in opportunities
        ],
        hide_index=True,
        use_container_width=True,
    )
    for item in opportunities:
        with st.expander(
            f"{item['regla']} · {item['nivel_posible']} · "
            f"{len(item['faltantes'])} requisito(s) pendiente(s)"
        ):
            if not item["faltantes"]:
                st.write("Esta regla ya reúne todas sus condiciones.")
            else:
                for missing in item["faltantes"]:
                    st.write(f"**{missing['hecho']}:** {missing['orientacion']}")
    for notice in report.get("advertencias", []):
        st.caption(notice)
    st.download_button(
        "Descargar diagnóstico JSON",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name="smartmarket-diagnostico.json",
        mime="application/json",
        key="download_diagnosis",
    )


def render_chatbot(facts: dict[str, Any] | None, recommendation: dict[str, Any] | None) -> None:
    st.header("Chatbot explicativo")
    if facts is None or recommendation is None:
        st.info("Primero obtén una recomendación para utilizar el chatbot.")
        return

    message = st.text_input("Escribe una pregunta", key="chat_message")
    if st.button("Preguntar", key="chat_button"):
        if not message.strip():
            st.warning("Escribe una pregunta antes de enviar.")
            return
        try:
            result = call_chat_api(message, facts, recommendation)
        except ApiClientError as exc:
            st.error(str(exc))
            return
        st.write(f"**Intent:** {result.get('intent', 'DESCONOCIDA')}")
        st.write(result.get("response", "Sin respuesta."))
        st.write(f"**Pregunta soportada:** {'sí' if result.get('supported') else 'no'}")


def _render_scenario_form(scenario: dict[str, Any]) -> dict[str, Any] | None:
    defaults = scenario["facts"]
    with st.form("recommendation_form"):
        request_id = st.text_input("Request ID", value=defaults["request_id"])
        alternativa_id = st.text_input("Alternativa ID", value=defaults["alternativa_id"])
        presupuesto = st.number_input(
            "Presupuesto", min_value=0.01, value=float(defaults["presupuesto"])
        )
        costo_total = st.number_input(
            "Costo total", min_value=0.0, value=float(defaults["costo_total"])
        )
        ahorro = st.number_input(
            "Ahorro", min_value=0.0, value=float(defaults["ahorro"]), step=0.01
        )
        distancia_km = st.number_input(
            "Distancia (km)", min_value=0.0, value=float(defaults["distancia_km"]), step=0.1
        )
        distancia_adicional_km = st.number_input(
            "Distancia adicional (km)",
            min_value=0.0,
            value=float(defaults["distancia_adicional_km"]),
            step=0.1,
        )
        tiempo_estimado_min = st.number_input(
            "Tiempo estimado (minutos)",
            min_value=0.0,
            value=float(defaults["tiempo_estimado_min"]),
            step=1.0,
        )
        productos_disponibles = st.number_input(
            "Productos disponibles",
            min_value=0,
            step=1,
            value=int(defaults["productos_disponibles"]),
        )
        productos_totales = st.number_input(
            "Productos totales", min_value=1, step=1, value=int(defaults["productos_totales"])
        )
        productos_esenciales_disponibles = st.number_input(
            "Productos esenciales disponibles",
            min_value=0,
            step=1,
            value=int(defaults["productos_esenciales_disponibles"]),
        )
        productos_esenciales_totales = st.number_input(
            "Productos esenciales totales",
            min_value=0,
            step=1,
            value=int(defaults["productos_esenciales_totales"]),
        )
        numero_supermercados = st.number_input(
            "Número de supermercados",
            min_value=1,
            step=1,
            value=int(defaults["numero_supermercados"]),
        )
        promociones_aplicables = st.checkbox(
            "Promociones aplicables", value=bool(defaults["promociones_aplicables"])
        )

        if st.form_submit_button("Obtener recomendación"):
            return {
                "request_id": request_id,
                "alternativa_id": alternativa_id,
                "costo_total": costo_total,
                "presupuesto": presupuesto,
                "ahorro": ahorro,
                "distancia_km": distancia_km,
                "distancia_adicional_km": distancia_adicional_km,
                "tiempo_estimado_min": tiempo_estimado_min,
                "productos_disponibles": productos_disponibles,
                "productos_totales": productos_totales,
                "productos_esenciales_disponibles": productos_esenciales_disponibles,
                "productos_esenciales_totales": productos_esenciales_totales,
                "numero_supermercados": numero_supermercados,
                "promociones_aplicables": promociones_aplicables,
            }
    return None


def render_comparison_tab(scenarios: list[dict[str, Any]], base_url: str) -> None:
    st.subheader("Comparador experto de alternativas")
    st.write(
        "Selecciona al menos dos escenarios. Python ejecutará el mismo motor experto "
        "en cada uno y explicará el orden de preferencia."
    )
    origin = st.radio(
        "Origen de las alternativas",
        ["Escenarios incluidos", "Archivo CSV/JSON"],
        horizontal=True,
        key="comparison_source",
    )
    if origin == "Archivo CSV/JSON":
        uploaded = st.file_uploader(
            "Cargar alternativas (CSV o JSON, hasta 2 MB y 750 filas)",
            type=["csv", "json"],
            max_upload_size=2,
            key="comparison_upload",
        )
        if uploaded is None:
            st.info("Selecciona un CSV o JSON con los 14 hechos y su procedencia.")
            return
        imported = import_dataset(uploaded.getvalue(), uploaded.name)
        if imported.errors:
            st.error(
                f"No se importó el archivo. Revisa sus {len(imported.errors)} "
                "observaciones antes de usarlo."
            )
            for issue in imported.errors:
                st.write(issue)
            return
        scenarios = imported.scenarios
        kinds = {}
        for item in scenarios:
            provenance = item["metadata"]["procedencia"]
            kinds[provenance] = kinds.get(provenance, 0) + 1
        st.success(f"Archivo validado: {len(scenarios)} alternativas.")
        st.caption(
            "Procedencia declarada: "
            + ", ".join(f"{kind} ({count})" for kind, count in sorted(kinds.items()))
        )
        for warning in imported.warnings:
            st.warning(warning)
        with st.expander("Revisar alternativas y fuentes"):
            st.dataframe(
                [
                    {
                        "Nombre": item["name"],
                        "ID": item["facts"]["alternativa_id"],
                        "Costo": item["facts"]["costo_total"],
                        "Presupuesto": item["facts"]["presupuesto"],
                        "Procedencia": item["metadata"]["procedencia"],
                        "Fuente": item["metadata"]["fuente_url"],
                    }
                    for item in scenarios
                ],
                hide_index=True,
                use_container_width=True,
            )
    # Identificar por ID evita colisiones entre nombres repetidos de tiendas.
    by_name = {
        f"{item['name']} · {item['facts']['alternativa_id']}": item
        for item in scenarios
    }
    names = list(by_name)
    selected = st.multiselect(
        "Alternativas para comparar",
        names,
        default=names[:3],
        max_selections=10,
        key="comparison_selection",
    )
    include_custom = False
    if st.session_state.get("latest_facts"):
        include_custom = st.checkbox(
            "Incluir mi última alternativa del laboratorio", value=False
        )

    if st.button("Comparar alternativas", type="primary", key="compare_button"):
        selected_payloads = [by_name[name]["facts"] for name in selected]
        if include_custom:
            selected_payloads.append(st.session_state["latest_facts"])
        identifiers = [item["alternativa_id"] for item in selected_payloads]
        budgets = {item["presupuesto"] for item in selected_payloads}
        if not 2 <= len(selected_payloads) <= 10:
            st.warning("Debes seleccionar entre 2 y 10 alternativas.")
        elif len(identifiers) != len(set(identifiers)):
            st.warning(
                "Las alternativas deben tener identificadores únicos. "
                "Cambia la ID del laboratorio o elimina el escenario repetido."
            )
        elif len(budgets) != 1:
            st.warning("Todas las opciones deben compartir el mismo presupuesto.")
        elif any(validate_payload(item) for item in selected_payloads):
            st.warning("Revisa los datos de las alternativas: hay casos no válidos.")
        else:
            try:
                comparison = call_comparison_api(selected_payloads, base_url)
                st.session_state["latest_comparison"] = comparison
            except ApiClientError as exc:
                st.error(f"No se pudo comparar: {exc}")
                st.info(
                    "El comparador requiere una versión del servicio Python "
                    "que incluya /api/v1/compare."
                )

    comparison = st.session_state.get("latest_comparison")
    if not comparison:
        st.info("Ejecuta una comparación para ver el ranking y su explicación.")
        return

    st.metric(
        "Mejor alternativa entre las evaluadas",
        comparison.get("mejor_alternativa_id", "N/D"),
    )
    st.caption(comparison.get("criterio_orden", ""))
    rows = comparison.get("ranking", [])
    st.dataframe(
        [
            {
                "Puesto": row.get("posicion"),
                "Alternativa": row.get("alternativa_id"),
                "Dictamen": row["recomendacion"].get("nivel_recomendacion"),
                "Regla": row["recomendacion"].get("winning_rule") or "Sin regla",
                "Índice auxiliar": row["recomendacion"].get("indice_conveniencia"),
                "Costo": row.get("costo_total"),
                "Riesgo": "Sí" if row.get("riesgo_critico") else "No",
            }
            for row in rows
        ],
        hide_index=True,
        use_container_width=True,
    )
    for warning in comparison.get("advertencias", []):
        st.caption(warning)
    for row in rows:
        title = f"#{row['posicion']} · {row['alternativa_id']}"
        with st.expander(title):
            st.write(row.get("motivo_posicion", ""))
            render_recommendation(
                row["recomendacion"], widget_key=f"comparison_{row['posicion']}"
            )


def render_sensitivity_tab(base_url: str) -> None:
    st.subheader("Análisis de sensibilidad de la recomendación")
    st.write(
        "Comprueba cómo cambia el resultado si sube el costo, aumenta el recorrido, "
        "desaparecen promociones o falta un producto esencial. "
        "Son pruebas hipotéticas, no predicciones."
    )
    original = st.session_state.get("latest_facts")
    if original is None:
        st.info("Primero evalúa una alternativa en la pestaña Laboratorio.")
        return

    if st.button("Ejecutar escenarios de sensibilidad", key="sensitivity_button"):
        try:
            st.session_state["latest_sensitivity"] = call_sensitivity_api(
                original, base_url
            )
            st.session_state["latest_sensitivity_facts"] = original.copy()
        except ApiClientError as exc:
            st.error(f"No se pudo ejecutar el análisis: {exc}")

    report = st.session_state.get("latest_sensitivity")
    if (
        not report
        or report.get("alternativa_id") != original["alternativa_id"]
        or st.session_state.get("latest_sensitivity_facts") != original
    ):
        st.info("Ejecuta el análisis para ver el efecto de cambios hipotéticos.")
        return

    st.metric(
        "Escenarios con una decisión diferente",
        report["cantidad_decisiones_distintas"],
    )
    st.write(report["interpretacion"])
    baseline = report["escenario_base"]
    st.caption(
        f"Resultado inicial: {baseline['nivel_recomendacion']} · "
        f"Regla {baseline.get('winning_rule') or 'ninguna'} · "
        f"Índice {baseline['indice_conveniencia']}/100"
    )
    st.dataframe(
        [
            {
                "Escenario": scenario["escenario"],
                "Dictamen": scenario["recomendacion"]["nivel_recomendacion"],
                "Regla": scenario["recomendacion"].get("winning_rule") or "Sin regla",
                "Variación índice": scenario["diferencia_indice"],
                "Cambia decisión": "Sí" if scenario["cambia_decision"] else "No",
            }
            for scenario in report["escenarios"]
        ],
        hide_index=True,
        use_container_width=True,
    )
    for scenario in report["escenarios"]:
        with st.expander(scenario["descripcion"]):
            st.json(scenario["cambios"])
            st.write(scenario["recomendacion"]["explicacion"])
    for notice in report.get("advertencias", []):
        st.caption(notice)


def build_coverage_report(
    comparison: dict[str, Any], scenarios: list[dict[str, Any]]
) -> dict[str, Any]:
    """Resume las trazas reales de la API para los escenarios de demostración."""

    scenario_names = {
        item["facts"]["alternativa_id"]: item["name"] for item in scenarios
    }
    ranked = comparison.get("ranking", [])
    rule_ids = sorted(
        {
            trace["rule_id"]
            for item in ranked
            for trace in item["recomendacion"].get("trace", [])
        }
    )
    counts = {
        rule_id: {"activations": 0, "wins": 0, "scenarios": []}
        for rule_id in rule_ids
    }
    scenario_rows = []
    no_winner = 0
    overlaps = 0

    for item in ranked:
        alternative_id = item["alternativa_id"]
        result = item["recomendacion"]
        active = result.get("reglas_activadas") or []
        winner = result.get("winning_rule")
        if winner is None:
            no_winner += 1
        if len(active) > 1:
            overlaps += 1
        for rule_id in active:
            if rule_id in counts:
                counts[rule_id]["activations"] += 1
                counts[rule_id]["scenarios"].append(
                    scenario_names.get(alternative_id, alternative_id)
                )
        if winner in counts:
            counts[winner]["wins"] += 1
        scenario_rows.append(
            {
                "Escenario": scenario_names.get(alternative_id, alternative_id),
                "Nivel": result.get("nivel_recomendacion"),
                "Ganadora": winner or "Sin regla",
                "Reglas activadas": ", ".join(active) if active else "Ninguna",
            }
        )

    return {
        "rules": [
            {
                "Regla": rule_id,
                "Activaciones": counts[rule_id]["activations"],
                "Victorias": counts[rule_id]["wins"],
                "Escenarios": ", ".join(counts[rule_id]["scenarios"]) or "Ninguno",
            }
            for rule_id in rule_ids
        ],
        "scenarios": scenario_rows,
        "no_winner": no_winner,
        "conflicts": overlaps,
        "total": len(ranked),
    }


def render_rule_coverage(
    scenarios: list[dict[str, Any]], base_url: str
) -> None:
    st.subheader("Matriz de cobertura de reglas")
    st.caption(
        "Ejecuta los escenarios de prueba contra la API Python. "
        "La matriz muestra reglas activadas, ganadoras y conflictos; "
        "no mide exactitud sobre datos comerciales."
    )
    if st.button("Evaluar cobertura", key="coverage_button"):
        if not 2 <= len(scenarios) <= 10:
            st.warning("La matriz requiere entre 2 y 10 escenarios de prueba.")
        else:
            try:
                result = call_comparison_api(
                    [scenario["facts"] for scenario in scenarios], base_url
                )
                st.session_state["rule_coverage"] = build_coverage_report(
                    result, scenarios
                )
            except ApiClientError as exc:
                st.error(f"No se pudo evaluar la cobertura: {exc}")

    report = st.session_state.get("rule_coverage")
    if report is None:
        return

    a, b, c = st.columns(3)
    a.metric("Escenarios evaluados", report["total"])
    b.metric("Sin regla ganadora", report["no_winner"])
    c.metric("Con varias reglas activas", report["conflicts"])
    st.dataframe(
        report["rules"], hide_index=True, use_container_width=True
    )
    st.dataframe(
        report["scenarios"], hide_index=True, use_container_width=True
    )
    missing = [
        item["Regla"] for item in report["rules"] if item["Activaciones"] == 0
    ]
    if missing:
        st.warning(
            "Reglas sin cobertura en estos escenarios: " + ", ".join(missing)
        )
    else:
        st.success("Las ocho reglas aparecen activadas en los escenarios evaluados.")


def render_rule_audit(base_url: str) -> None:
    """Muestra la auditoría independiente de la cobertura por escenarios."""

    st.subheader("Verificador de consistencia de reglas")
    st.caption(
        "Identifica condiciones incompatibles, duplicados, reglas sombreadas y "
        "solapamientos previstos. No cambia las reglas ni su prioridad."
    )
    if st.button("Auditar base de conocimiento", key="rule_audit_button"):
        try:
            st.session_state["rule_audit_report"] = call_rule_audit_api(base_url)
        except ApiClientError as exc:
            st.error(f"No se pudo realizar la auditoría: {exc}")
    report = st.session_state.get("rule_audit_report")
    if not report:
        st.info("Ejecuta la auditoría para inspeccionar la consistencia de R01–R08.")
        return

    first, second, third = st.columns(3)
    first.metric("Reglas", report["reglas_evaluadas"])
    second.metric("Hallazgos para revisar", len(report["hallazgos"]))
    third.metric("Pares que se solapan", len(report["solapamientos"]))
    st.write(report["resumen"])

    findings = report.get("hallazgos", [])
    if findings:
        st.warning("Hay observaciones que conviene revisar antes de editar las reglas.")
        st.dataframe(
            [
                {
                    "Tipo": issue["tipo"],
                    "Reglas": ", ".join(issue["reglas"]),
                    "Explicación": issue["detalle"],
                }
                for issue in findings
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.success("No se detectaron anomalías estructurales en la muestra evaluada.")

    overlaps = report.get("solapamientos", [])
    if overlaps:
        st.caption(
            "Los solapamientos no son necesariamente errores: el motor decide "
            "por prioridad y por ID si existe empate."
        )
        st.dataframe(
            [
                {
                    "Reglas": " / ".join(pair["reglas"]),
                    "Ganadora": pair["ganador_por_prioridad"],
                    "Niveles": " / ".join(pair["niveles"]),
                    "Conflicto de nivel": "Sí" if pair["conflicto_de_nivel"] else "No",
                    "Coincidencias sintéticas": pair["casos_coincidentes"],
                }
                for pair in overlaps
            ],
            hide_index=True,
            use_container_width=True,
        )
        with st.expander("Ejemplo sintético reproducible de un solapamiento"):
            st.json(overlaps[0]["ejemplo"])

    st.dataframe(
        [
            {
                "Regla": item["regla"],
                "Activaciones en la muestra": item["activaciones"],
            }
            for item in report.get("cobertura", [])
        ],
        hide_index=True,
        use_container_width=True,
    )
    for limitation in report.get("limitaciones", []):
        st.caption(limitation)
    st.download_button(
        "Descargar auditoría JSON",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        mime="application/json",
        file_name="smartmarket-auditoria-reglas.json",
        key="download_rule_audit",
    )


def render_rule_regression(
    scenarios: list[dict[str, Any]], base_url: str
) -> None:
    """Ensaya cambios aislados de prioridades sin modificar la API de producción."""

    st.subheader("Comparador de versiones de reglas")
    st.caption(
        "Simula una prioridad distinta sobre R01–R08 y compara los mismos "
        "escenarios contra ambas versiones. No publica cambios."
    )
    if st.button("Cargar reglas actuales para comparar", key="regression_load"):
        try:
            st.session_state["regression_knowledge"] = call_knowledge_api(base_url)
            st.session_state.pop("regression_result", None)
        except ApiClientError as exc:
            st.error(f"No se pudo consultar las reglas: {exc}")

    knowledge = st.session_state.get("regression_knowledge")
    if not knowledge:
        st.info("Carga la versión actual de las reglas para iniciar la simulación.")
        return

    rules = knowledge["rules"]
    ids = [rule["id"] for rule in rules]
    default_id = ids.index("R06") if "R06" in ids else 0
    selected = st.selectbox(
        "Regla que deseas simular",
        options=ids,
        index=default_id,
        key="regression_rule_id",
    )
    current_rule = next(item for item in rules if item["id"] == selected)
    current_priority = int(current_rule["priority"])
    default_new = 7 if selected == "R06" else current_priority + 1
    priority = int(
        st.number_input(
            "Nueva prioridad para la versión de prueba",
            min_value=1,
            max_value=100,
            value=min(default_new, 100),
            step=1,
            key="regression_new_priority",
        )
    )
    st.caption(
        f"Regla {selected}: prioridad vigente {current_priority}; "
        f"prioridad simulada {priority}. Un valor menor tiene mayor precedencia."
    )

    proposed_rules = json.loads(json.dumps(rules, ensure_ascii=False))
    for rule in proposed_rules:
        if rule["id"] == selected:
            rule["priority"] = priority

    fingerprint = json.dumps(
        [rules, selected, priority, scenarios],
        sort_keys=True,
        ensure_ascii=False,
    )
    if st.button("Comparar versiones de reglas", key="regression_compare"):
        if priority == current_priority:
            st.info(
                "La prioridad no cambió: ambas bases de reglas serían equivalentes."
            )
        try:
            st.session_state["regression_result"] = call_rule_regression_api(
                {
                    "etiqueta": knowledge["rules_version"] + " (vigente)",
                    "reglas": rules,
                },
                {
                    "etiqueta": "simulación de prioridad",
                    "reglas": proposed_rules,
                },
                scenarios,
                base_url,
            )
            st.session_state["regression_fingerprint"] = fingerprint
        except ApiClientError as exc:
            st.session_state.pop("regression_result", None)
            st.error(f"No se pudo comparar las reglas: {exc}")

    report = st.session_state.get("regression_result")
    if not report or st.session_state.get("regression_fingerprint") != fingerprint:
        return

    first, second, third, fourth = st.columns(4)
    first.metric("Casos evaluados", report["escenarios_evaluados"])
    second.metric("Cambios de nivel", report["cambios_nivel"])
    third.metric("Reglas ganadoras distintas", report["cambios_regla_ganadora"])
    fourth.metric("Regresiones críticas", report["regresiones_criticas"])

    if report["regresiones_criticas"]:
        st.error(
            "La simulación permitiría una recomendación favorable donde antes "
            "había una regla crítica activa. Revisar antes de publicar."
        )
    st.caption(
        f"SHA-256 vigente: {report['huella_anterior']} | "
        f"SHA-256 propuesta: {report['huella_propuesta']}"
    )
    st.dataframe(
        [
            {
                "Escenario": item["escenario"],
                "Nivel anterior": item["nivel_anterior"],
                "Nivel simulado": item["nivel_propuesto"],
                "Regla anterior": item["regla_anterior"] or "Ninguna",
                "Regla simulada": item["regla_propuesta"] or "Ninguna",
                "Cambio de nivel": "Sí" if item["cambio_nivel"] else "No",
                "Riesgo crítico": "Sí" if item["regresion_critica"] else "No",
            }
            for item in report["resultados"]
        ],
        hide_index=True,
        use_container_width=True,
    )
    with st.expander("Cambios en las reglas y explicaciones"):
        st.json(report["cambios_reglas"])
        for item in report["resultados"]:
            if item["cambio_explicacion"]:
                st.write(f"**{item['escenario']}**")
                st.write("Antes: " + item["explicacion_anterior"])
                st.write("Propuesta: " + item["explicacion_propuesta"])
    for warning in report.get("advertencias", []):
        st.caption(warning)
    st.download_button(
        "Descargar comparación JSON",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        mime="application/json",
        file_name="smartmarket-regresion-reglas.json",
        key="regression_download",
    )


def render_evidence_report(
    scenarios: list[dict[str, Any]], base_url: str
) -> None:
    """Descarga evidencia integral construida por la API Python."""

    st.subheader("Informe académico descargable")
    st.write(
        "Genera un PDF con el ranking, las ocho trazas por escenario, "
        "cobertura, solapamientos, umbrales, pesos y sensibilidad."
    )
    st.caption(
        f"Se utilizarán {len(scenarios)} escenarios sintéticos precargados. "
        "No se consulta Laravel ni se capturan datos de supermercados."
    )
    if st.button("Generar informe académico PDF", key="evidence_button"):
        if not 2 <= len(scenarios) <= 10:
            st.warning("El informe necesita entre 2 y 10 escenarios comparables.")
        else:
            try:
                with st.spinner("Preparando evidencia técnica..."):
                    st.session_state["evidence_pdf"] = call_evidence_report_api(
                        scenarios, base_url
                    )
            except ApiClientError as exc:
                st.session_state.pop("evidence_pdf", None)
                st.error(f"No fue posible generar el informe: {exc}")

    document = st.session_state.get("evidence_pdf")
    if document:
        st.success("El documento PDF está listo.")
        st.download_button(
            "Descargar informe académico PDF",
            data=document,
            file_name="smartmarket-informe-academico.pdf",
            mime="application/pdf",
            key="download_evidence_pdf",
        )


def render_knowledge_tab(base_url: str) -> None:
    st.subheader("Base de conocimiento y criterios del experto")
    st.write(
        "La inferencia es determinista: se evalúan las condiciones de cada regla, "
        "pueden activarse varias y gana la de mayor prioridad. No se entrena un modelo."
    )
    if st.button("Cargar reglas y parámetros de la API", key="knowledge_button"):
        try:
            st.session_state["knowledge_snapshot"] = call_knowledge_api(base_url)
        except ApiClientError as exc:
            st.error(f"No se pudo consultar la base de conocimiento: {exc}")

    knowledge = st.session_state.get("knowledge_snapshot")
    if not knowledge:
        st.info(
            "Carga la base de conocimiento para ver las reglas reales del servicio "
            "Python. No se necesita Laravel."
        )
        return

    rules = knowledge.get("rules", [])
    st.metric("Reglas de producción vigentes", len(rules))
    st.caption(
        f"Versión de reglas: {knowledge.get('rules_version', 'N/D')} · "
        f"Versión de umbrales: {knowledge.get('thresholds_version', 'N/D')}"
    )
    st.dataframe(
        [
            {
                "Regla": rule["id"],
                "Nombre": rule["name"],
                "Prioridad": rule["priority"],
                "Dictamen": rule["result"]["level"],
                "Condiciones AND": len(rule["conditions"]),
            }
            for rule in rules
        ],
        hide_index=True,
        use_container_width=True,
    )
    for rule in sorted(rules, key=lambda item: (item["priority"], item["id"])):
        with st.expander(
            f"{rule['id']} · {rule['name']} · prioridad {rule['priority']}"
        ):
            st.write(f"**Conclusión:** {rule['result']['level']}")
            st.write(f"**Acción:** {rule['result']['action']}")
            st.write(f"**Justificación:** {rule['result']['explanation']}")
            st.json(rule["conditions"])

    st.subheader("Umbrales documentados")
    st.dataframe(
        [
            {"Parámetro": name, "Valor": value}
            for name, value in knowledge.get("thresholds", {}).items()
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Pesos del índice auxiliar")
    st.dataframe(
        [
            {"Factor": name, "Peso (%)": round(float(weight) * 100, 1)}
            for name, weight in knowledge.get("weights", {}).items()
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Los umbrales y pesos son parámetros del prototipo. "
        "Su coherencia se evalúa con casos de prueba y análisis de sensibilidad."
    )


def main() -> None:
    st.set_page_config(
        page_title="SmartMarket SV · Laboratorio experto",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        .block-container {max-width: 1200px; padding-top: 2rem;}
        [data-testid="stMetric"] {
            background: rgba(42, 118, 98, 0.065);
            border: 1px solid rgba(80, 150, 135, 0.20);
            border-radius: 14px;
            padding: 16px;
        }
        [data-testid="stMetricValue"] {font-size: 1.45rem;}
        [data-testid="stDataFrame"] {border-radius: 12px; overflow: hidden;}
        [data-testid="stExpander"] {border-radius: 12px;}
        .sm-hero {
            background: linear-gradient(118deg, #092b2a 0%, #0e5a4c 57%, #18856e 100%);
            color: #fff; padding: 30px 32px; border-radius: 20px;
            margin-bottom: 22px; box-shadow: 0 8px 28px rgba(3, 36, 29, .15);
        }
        .sm-kicker {
            font-size: .77rem; letter-spacing: .14em; text-transform: uppercase;
            font-weight: 700; opacity: .78; margin: 0 0 8px 0;
        }
        .sm-hero h1 {font-size: 2.1rem; margin: 0; color: #fff;}
        .sm-hero p {font-size: .98rem; opacity: .9; margin: 10px 0 0 0;}
        </style>
        <section class="sm-hero">
          <p class="sm-kicker">Sistema experto · Laboratorio académico</p>
          <h1>SmartMarket SV</h1>
          <p>Decisiones transparentes · Reglas verificables · Comparación explicable</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    base_url = st.sidebar.text_input("URL del servicio Python", value=api_base_url())
    st.sidebar.caption(
        "Interfaz de demostración del servicio experto Python. "
        "En la aplicación integrada, Laravel proporciona los hechos por HTTP."
    )
    if st.sidebar.button("Verificar conexión", key="health_button"):
        try:
            health = call_health_endpoint(base_url)
            st.sidebar.success(f"API disponible: {health.get('status', 'ok')}")
        except ApiClientError as exc:
            st.sidebar.error(str(exc))

    try:
        scenarios = load_scenarios()
    except ScenarioLoadError as exc:
        st.error(str(exc))
        return

    # Desde Streamlit 1.55, solo se ejecuta la pestaña seleccionada.
    # Evita construir tablas, controles y JSON de las otras tres vistas
    # en cada rerun de un formulario.
    lab, comparison_tab, sensitivity_tab, knowledge = st.tabs(
        ["Laboratorio", "Comparador", "Sensibilidad", "Base de conocimiento"],
        key="active_tab",
        on_change="rerun",
    )
    if lab.open:
        with lab:
            st.subheader("Prueba una recomendación")
            st.caption("Elige un escenario y modifica sus hechos antes de ejecutar.")
            scenario_by_name = {scenario["name"]: scenario for scenario in scenarios}
            selected_name = st.selectbox("Escenario", list(scenario_by_name))
            selected = scenario_by_name[selected_name]
            st.caption("Escenario de prueba · " + selected["description"])

            payload = _render_scenario_form(selected)
            if payload is not None:
                errors = validate_payload(payload)
                if errors:
                    for error in errors:
                        st.warning(error)
                else:
                    try:
                        result = call_recommendation_api(payload, base_url)
                        st.session_state["latest_recommendation"] = result
                        st.session_state["latest_facts"] = payload
                    except ApiClientError as exc:
                        st.error(str(exc))

            latest_result = st.session_state.get("latest_recommendation")
            latest_facts = st.session_state.get("latest_facts")
            if latest_result is not None:
                st.header("Resultado de la inferencia")
                render_recommendation(latest_result)
                render_diagnosis_panel(base_url, latest_facts)
            render_chatbot(latest_facts, latest_result)

    if comparison_tab.open:
        with comparison_tab:
            render_comparison_tab(scenarios, base_url)
    if sensitivity_tab.open:
        with sensitivity_tab:
            render_sensitivity_tab(base_url)
    if knowledge.open:
        with knowledge:
            render_knowledge_tab(base_url)
            render_rule_coverage(scenarios, base_url)
            render_rule_audit(base_url)
            render_rule_regression(scenarios, base_url)
            render_evidence_report(scenarios, base_url)


if __name__ == "__main__":
    main()
