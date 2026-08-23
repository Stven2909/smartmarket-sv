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

## Publicación para el equipo

Para compartir la interfaz con otros integrantes, Streamlit Community Cloud
publica `demo/streamlit_app.py` desde GitHub. Como la interfaz consume FastAPI
por HTTP, FastAPI debe publicarse aparte con una URL HTTPS. En Streamlit Cloud
se configura esa URL en **Settings > Secrets**:

```toml
SMARTMARKET_API_URL = "https://TU-API-FASTAPI.example.com"
```

No se debe usar `http://127.0.0.1:8001` en la nube. La guía completa está en
[docs/streamlit-cloud-deployment.md](docs/streamlit-cloud-deployment.md).

## Endpoints

- `GET /health`: disponibilidad del servicio.
- `POST /api/v1/recommend`: genera una recomendación.
- `POST /api/v1/chat`: explica una recomendación mediante intenciones y plantillas.

El contrato público está versionado como `1.0.0` y la base de reglas como
`1.0.0`. Los campos del índice auxiliar se exponen en la respuesta de
`/api/v1/recommend`; cuando Laravel envía una recomendación histórica al
chatbot, esos campos pueden omitirse por compatibilidad, pero el endpoint de
recomendación siempre los genera.

La especificación congelada está en [docs/api-contract.md](docs/api-contract.md),
[docs/openapi.json](docs/openapi.json) y
[docs/integration-payloads.json](docs/integration-payloads.json).

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

## Endurecimiento técnico Fase 9A

La configuración de umbrales de los clasificadores está centralizada en
`app/expert_system/classifiers.py` y tiene versión `1.0.0`:

| Clasificación | Umbral |
|---|---|
| Ahorro bajo | `< 3.00` |
| Ahorro medio | `>= 3.00` y `< 10.00` |
| Ahorro alto | `>= 10.00` |
| Distancia cercana | `<= 2 km` |
| Distancia media | `> 2 km` y `< 8 km` |
| Distancia lejana | `>= 8 km` |
| Tiempo bajo | `<= 20 min` |
| Tiempo medio | `> 20 min` y `< 45 min` |
| Tiempo alto | `>= 45 min` |
| Compra fragmentada | `>= 3 supermercados` |
| Presupuesto ligeramente excedido | exceso `> 0%` y `<= 10%` |
| Presupuesto muy excedido | exceso `> 10%` |

Si ninguna regla se activa, el nivel se mantiene como `NO_RECOMENDABLE` para
no romper el contrato actual. Esta salida no significa necesariamente que la
alternativa sea mala: indica que no se activó una regla específica de ventaja
o riesgo y que debe compararse con otras alternativas. La explicación lo
aclara explícitamente.

R08 continúa siendo una regla preliminar del MVP. Considera dos supermercados,
ahorro alto y presupuesto cumplido, pero todavía no modela costo de traslado,
tiempo adicional, distancia adicional, beneficio neto ni productos faltantes.

La trazabilidad conserva para cada regla el identificador, condiciones
esperadas, valores reales, condiciones cumplidas, condiciones incumplidas y
el motivo de activación o rechazo. El desempate se mantiene determinista por
prioridad y, en empate, por ID de regla.

## Índice auxiliar de conveniencia Fase 9B

El índice de conveniencia es una capa secundaria determinista; no reemplaza
el motor de reglas ni puede cambiar una conclusión crítica. Su configuración
está en `app/expert_system/convenience_config.py`, versión `1.0.0`:

| Parámetro | Valor |
|---|---:|
| Referencia de ahorro | `20.0` |
| Distancia máxima | `20.0 km` |
| Tiempo máximo | `120.0 min` |
| Peso del ahorro | `0.35` |
| Peso de disponibilidad | `0.25` |
| Peso de distancia | `0.20` |
| Peso de tiempo | `0.15` |
| Peso de promociones | `0.05` |

Los componentes se normalizan entre `0` y `1`, y el índice final entre `0` y
`100`. La clasificación es `ALTA_CONVENIENCIA` desde `75`,
`CONVENIENCIA_MEDIA` desde `50` hasta menos de `75`, y
`BAJA_CONVENIENCIA` por debajo de `50`.

Las reglas críticas son R01 a R05. Aunque se calcula el índice para mostrar
información complementaria, estas reglas conservan el nivel, la acción, la
regla ganadora, las reglas perdedoras y la trazabilidad originales. Cuando no
hay una regla crítica, el índice enriquece la recomendación existente, pero
tampoco sustituye su decisión.

Los valores de referencia son parámetros iniciales del MVP. Deben validarse y
calibrarse posteriormente con datos reales de compras, tiempos y distancias;
no se generan dinámicamente ni implican entrenamiento de Machine Learning.

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
