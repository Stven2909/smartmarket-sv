# SmartMarket SV Expert Service

## Objetivo

SmartMarket SV es un MVP académico para analizar alternativas de compra de
supermercado considerando presupuesto, ahorro, disponibilidad, distancia,
tiempo de traslado y cantidad de supermercados.

El Sistema Experto no es un modelo de Machine Learning. Utiliza hechos,
hechos derivados, reglas de producción, prioridades, resolución de conflictos
y explicaciones deterministas.

## Arquitectura

```text
Streamlit --HTTP--> FastAPI --invoca--> Motor de inferencia
                         |
                         +-- Base de conocimiento JSON
                         +-- Chatbot determinista
```

Streamlit no importa `inference_engine.py`, `classifiers.py` ni
`chatbot_service.py`. FastAPI es la única fuente de verdad.

## Instalación

Desde PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecución de FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Documentación Swagger:

```text
http://127.0.0.1:8001/docs
```

## Ejecución de Streamlit

En una segunda terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run demo/streamlit_app.py
```

La interfaz normalmente estará disponible en:

```text
http://localhost:8501
```

La API puede configurarse con:

```powershell
$env:SMARTMARKET_API_URL = "http://127.0.0.1:8001"
```

## Endpoints

- `GET /health`: disponibilidad del servicio.
- `POST /api/v1/recommend`: genera una recomendación.
- `POST /api/v1/chat`: explica una recomendación mediante intenciones y plantillas.

## Escenarios de prueba

La demo carga `data/scenarios.json`, que contiene:

- Compra ideal.
- Presupuesto muy excedido.
- Productos esenciales faltantes.
- Distancia lejana con ahorro bajo.
- Tiempo alto con ahorro bajo.
- Compra fragmentada.
- Promociones relevantes.
- Dos supermercados con ahorro alto.
- Caso sin regla dominante.

Todos pueden editarse desde Streamlit antes de enviarse a la API.

## Ejemplo de respuesta

```json
{
  "request_id": "scenario-ideal",
  "nivel_recomendacion": "EXCELENTE",
  "accion_sugerida": "Comprar todo en esta alternativa.",
  "explicacion": "Cumple el presupuesto, incluye los esenciales y requiere un recorrido conveniente.",
  "reglas_activadas": ["R06", "R07"],
  "prioridad_aplicada": "CONVENIENCIA",
  "hechos_derivados": {
    "dentro_presupuesto": true,
    "ahorro_alto": true,
    "distancia_cercana": true
  },
  "version_reglas": "1.0.0",
  "winning_rule": "R06"
}
```

## Pruebas automatizadas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas cubren esquemas, hechos derivados, reglas, inferencia, APIs,
chatbot, escenarios, errores de conexión y repetibilidad.

## Errores conocidos

- Si FastAPI está apagado, Streamlit muestra un error de conexión.
- Un JSON inválido o inconsistente devuelve HTTP 422.
- Un error interno de FastAPI devuelve HTTP 500.
- Si `data/scenarios.json` no existe o está corrupto, la demo muestra el error.
- La validación local de Streamlit es preventiva; FastAPI sigue validando el
  contrato de forma definitiva.

## Limitaciones del MVP

- No utiliza SQLite.
- No integra Laravel ni React.
- No tiene autenticación.
- No usa IA generativa.
- No realiza scraping.
- No conserva historial permanente de conversaciones.
- Los datos actuales son simulados y se almacenan en JSON.
