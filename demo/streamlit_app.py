import json
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st


DEFAULT_API_BASE_URL = "http://127.0.0.1:8001"
REQUEST_TIMEOUT_SECONDS = 10
SCENARIOS_PATH = Path(__file__).resolve().parents[1] / "data" / "scenarios.json"


class ScenarioLoadError(ValueError):
    """Error comprensible al cargar los escenarios de demostración."""


class ApiClientError(RuntimeError):
    """Error controlado al comunicarse con FastAPI."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


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
        raise ScenarioLoadError(
            f"No se pudo leer el archivo de escenarios: {exc}"
        ) from exc

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
    return os.getenv("SMARTMARKET_API_URL", DEFAULT_API_BASE_URL).rstrip("/")


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
    if int(payload.get("productos_esenciales_totales", 0)) <= 0:
        errors.append("Productos esenciales totales debe ser mayor que cero.")
    if int(payload.get("numero_supermercados", 0)) < 1:
        errors.append("Número de supermercados debe ser como mínimo uno.")
    if int(payload.get("productos_disponibles", 0)) > int(payload.get("productos_totales", 0)):
        errors.append("Productos disponibles no puede superar productos totales.")
    if int(payload.get("productos_esenciales_disponibles", 0)) > int(
        payload.get("productos_esenciales_totales", 0)
    ):
        errors.append(
            "Productos esenciales disponibles no puede superar "
            "productos esenciales totales."
        )
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
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
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


def _post_json(
    path: str, payload: dict[str, Any], base_url: str | None = None
) -> dict[str, Any]:
    url = f"{(base_url or api_base_url()).rstrip('/')}{path}"
    try:
        response = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
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


def call_recommendation_api(
    payload: dict[str, Any], base_url: str | None = None
) -> dict[str, Any]:
    return _post_json("/api/v1/recommend", payload, base_url)


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


def render_recommendation(result: dict[str, Any]) -> None:
    level = result.get("nivel_recomendacion", "DESCONOCIDO")
    if level == "EXCELENTE":
        st.success(level)
    elif level == "BUENA":
        st.warning(level)
    else:
        st.error(level)

    st.subheader("Request ID")
    st.code(result.get("request_id", "no disponible"))
    st.write(f"**Regla ganadora:** {result.get('winning_rule') or 'ninguna'}")
    st.subheader("Acción sugerida")
    st.write(result.get("accion_sugerida", "Sin acción disponible."))
    st.subheader("Explicación")
    st.write(result.get("explicacion", "Sin explicación disponible."))
    st.write(
        f"**Reglas activadas:** "
        f"{', '.join(result.get('reglas_activadas', [])) or 'ninguna'}"
    )
    st.write(f"**Prioridad aplicada:** {result.get('prioridad_aplicada', 'SIN_REGLA')}")
    st.write(f"**Versión de reglas:** {result.get('version_reglas', 'desconocida')}")
    st.subheader("Hechos derivados")
    facts = result.get("hechos_derivados", {})
    st.table(
        [{"Hecho": name, "Valor": str(value)} for name, value in facts.items()]
    )


def render_chatbot(
    facts: dict[str, Any] | None, recommendation: dict[str, Any] | None
) -> None:
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
        presupuesto = st.number_input("Presupuesto", min_value=0.01, value=float(defaults["presupuesto"]))
        costo_total = st.number_input("Costo total", min_value=0.0, value=float(defaults["costo_total"]))
        ahorro = st.number_input("Ahorro", min_value=0.0, value=float(defaults["ahorro"]), step=0.01)
        distancia_km = st.number_input("Distancia (km)", min_value=0.0, value=float(defaults["distancia_km"]), step=0.1)
        distancia_adicional_km = st.number_input("Distancia adicional (km)", min_value=0.0, value=float(defaults["distancia_adicional_km"]), step=0.1)
        tiempo_estimado_min = st.number_input("Tiempo estimado (minutos)", min_value=0.0, value=float(defaults["tiempo_estimado_min"]), step=1.0)
        productos_disponibles = st.number_input("Productos disponibles", min_value=0, step=1, value=int(defaults["productos_disponibles"]))
        productos_totales = st.number_input("Productos totales", min_value=1, step=1, value=int(defaults["productos_totales"]))
        productos_esenciales_disponibles = st.number_input("Productos esenciales disponibles", min_value=0, step=1, value=int(defaults["productos_esenciales_disponibles"]))
        productos_esenciales_totales = st.number_input("Productos esenciales totales", min_value=1, step=1, value=int(defaults["productos_esenciales_totales"]))
        numero_supermercados = st.number_input("Número de supermercados", min_value=1, step=1, value=int(defaults["numero_supermercados"]))
        promociones_aplicables = st.checkbox("Promociones aplicables", value=bool(defaults["promociones_aplicables"]))

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


def main() -> None:
    st.set_page_config(page_title="SmartMarket SV", page_icon="🛒")
    st.title("SmartMarket SV - Sistema Experto")

    base_url = st.sidebar.text_input("URL de FastAPI", value=api_base_url())
    if st.sidebar.button("Verificar estado del servicio"):
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

    scenario_by_name = {scenario["name"]: scenario for scenario in scenarios}
    selected_name = st.selectbox("Escenario", list(scenario_by_name))
    selected = scenario_by_name[selected_name]
    st.caption(selected["description"])

    payload = _render_scenario_form(selected)
    if payload is not None:
        validation_errors = validate_payload(payload)
        if validation_errors:
            for error in validation_errors:
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
        st.header("Resultado")
        render_recommendation(latest_result)
    render_chatbot(latest_facts, latest_result)


if __name__ == "__main__":
    main()
