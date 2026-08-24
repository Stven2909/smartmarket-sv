# SmartMarket SV — Sistema Experto

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Demo-FF4B4B?logo=streamlit&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![CI](https://github.com/Stven2909/smartmarket-sv/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/licencia-MIT-green)

Sistema Experto determinista que recomienda la mejor alternativa de compra de supermercado según **presupuesto, ahorro, disponibilidad, distancia, tiempo de traslado y cantidad de tiendas**, explicando cada recomendación de forma trazable.

> Proyecto académico para las materias de **Emprendedurismo** y **Sistemas Expertos** — parte del ecosistema [SmartMarket SV](https://github.com/Stven2909/smartmarket-sv).

---

## ¿Qué es?

Un motor de inferencia clásico basado en **reglas de producción**. No es Machine Learning: no entrena modelos ni genera salidas probabilísticas. Cada conclusión se construye con hechos, hechos derivados y reglas priorizadas, por lo que **la misma entrada siempre produce la misma salida y la misma explicación**.

```text
Entrada (alternativa de compra)
        │
        ▼
┌─────────────────────┐
│  Hechos base        │  presupuesto, ahorro, distancia, tiempo…
│  Hechos derivados   │  dentro_presupuesto, ahorro_alto, distancia_cercana…
│  Reglas R01–R08     │  condiciones + prioridad + acción
└─────────────────────┘
        │
        ▼
Resolución de conflictos ──► Nivel + Acción + Explicación + Trazabilidad
```

## Cómo funciona

1. **Clasificación de hechos**: los valores numéricos se convierten en categorías (ahorro alto, distancia lejana, tiempo medio, etc.) mediante umbrales centralizados y versionados.
2. **Encadenamiento hacia adelante**: el motor evalúa las reglas contra los hechos derivados.
3. **Resolución de conflictos**: cuando varias reglas aplican, gana la de mayor prioridad; en empate decide el ID de regla. Determinista siempre.
4. **Explicación trazable**: para cada regla se conserva qué condiciones cumplió, cuáles no y por qué se activó o rechazó.
5. **Índice de conveniencia** *(capa complementaria)*: un puntaje ponderado de 0 a 100 (ahorro, disponibilidad, distancia, tiempo y promociones) que enriquece la respuesta sin alterar jamás una conclusión crítica de las reglas R01–R05.

## Tecnologías

| Capa | Tecnología | Rol |
|---|---|---|
| Motor | Python 3.12+ | Lógica puro, sin dependencias externas |
| Conocimiento | JSON | Base de reglas y escenarios versionados |
| API | FastAPI + Pydantic v2 | Contrato validado y documentación automática |
| Servidor | Uvicorn | Servidor ASGI |
| Interfaz | Streamlit | Demo interactiva editable |
| Pruebas | Pytest | Cobertura de reglas, inferencia, API y chatbot |

## Características

- **Recomendación explicada**: nivel (`EXCELENTE` … `NO_RECOMENDABLE`), acción sugerida y justificación en lenguaje natural.
- **Chatbot determinista**: responde intenciones sobre la recomendación mediante plantillas, sin IA generativa.
- **Consultas de trazabilidad**: explica el índice de conveniencia, la regla ganadora y las reglas perdedoras usando la respuesta real de `/recommend`.
- **Base de conocimiento declarativa**: las reglas viven en `data/rules.json`, no en código — editarlas no requiere programar.
- **Escenarios de prueba editables**: compra ideal, presupuesto excedido, productos faltantes, compra fragmentada, promociones y más.
- **Respuestas repetibles**: ideal para evaluación académica y pruebas automatizadas.

## Arquitectura

```text
Streamlit ──HTTP──► FastAPI ──► Motor de inferencia
                        │
                        ├── Base de conocimiento (data/rules.json)
                        └── Chatbot determinista
```

La interfaz consume todo por HTTP; toda la lógica vive en el servicio.

## Responsabilidades de integración

Python valida los hechos, ejecuta las reglas, calcula hechos derivados e
índice, y responde `/api/v1/recommend` y `/api/v1/chat`. Laravel calcula los
datos de negocio, construye el payload oficial, omite llamadas con datos
obligatorios nulos, aplica timeout/retry y ejecuta el fallback. React consume
únicamente Laravel: muestra la recomendación amigable, conserva el fallback y
envía las preguntas al backend. Ninguna de las dos capas debe duplicar el
motor de inferencia.

El payload oficial usa `lista-42-sucursal-3` como `request_id` y contiene solo
hechos validados. `score`, `penalizacion_distancia`, combustible, vehículo y
SQL no forman parte del contrato Python.

## Inicio rápido

```powershell
# 1. Entorno virtual
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 2. API (terminal 1)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# 3. Demo web (terminal 2)
.\.venv\Scripts\python.exe -m streamlit run demo/streamlit_app.py
```

Swagger UI: <http://127.0.0.1:8001/docs> · Demo: <http://localhost:8501>

## API

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Disponibilidad del servicio |
| `POST` | `/api/v1/recommend` | Genera recomendación con explicación y trazabilidad |
| `POST` | `/api/v1/chat` | Explica una recomendación vía intenciones |

En producción se exige el header `X-API-Key` (valor definido en la variable de entorno `SMARTMARKET_API_KEY`). Sin esa variable configurada —por ejemplo en desarrollo local— la API queda abierta. `/health` siempre es público.

El chatbot acepta la respuesta real de `/api/v1/recommend` en el campo
`recommendation`. Puede responder preguntas como:

- `¿Cuál es el índice de conveniencia?`
- `¿Cuál es la regla ganadora?`
- `¿Qué reglas perdedoras se activaron?`
- `NO_DISPONIBLE` se utiliza cuando no existe una recomendación que explicar.

Si Python no pudo generar una recomendación, Laravel puede enviar
`"recommendation": null` junto con `request_id`. El endpoint mantiene la
respuesta HTTP `200`, informa `supported: false` y no inventa índice ni reglas.

### Lenguaje del chatbot

Las respuestas normales están redactadas para usuarios comunes: muestran
presupuesto, ahorro, kilómetros, minutos, disponibilidad e índice sin exponer
variables internas como `dentro_presupuesto` o `ahorro_alto`. Los códigos
`R01`–`R08`, `winning_rule`, `losing_rules` y la prioridad solo aparecen si el
usuario pregunta explícitamente por reglas o por el funcionamiento técnico.

El chatbot es determinista, local y basado en plantillas. No utiliza IA
generativa, modelos externos ni historial permanente. Como el contrato solo
contiene cantidades, no inventa nombres de productos.

Ejemplo de respuesta de `/recommend`:

```json
{
  "request_id": "scenario-ideal",
  "nivel_recomendacion": "EXCELENTE",
  "accion_sugerida": "Comprar todo en esta alternativa.",
  "explicacion": "Cumple el presupuesto, incluye los esenciales y requiere un recorrido conveniente.",
  "reglas_activadas": ["R06", "R07"],
  "hechos_derivados": {
    "dentro_presupuesto": true,
    "ahorro_alto": true,
    "distancia_cercana": true
  },
  "version_reglas": "1.0.0"
}
```

## Estructura del proyecto

```text
app/
├── expert_system/      # Motor: reglas, inferencia, clasificadores, índice
├── api/                # Endpoints FastAPI
├── chatbot/            # Detector de intenciones y plantillas
├── schemas/            # Modelos Pydantic del contrato
└── services/           # Orquestación
data/
├── rules.json          # Base de conocimiento (R01–R08)
└── scenarios.json      # Escenarios de demostración
demo/streamlit_app.py   # Interfaz web
tests/                  # Suite Pytest
docs/                   # Contrato de API y guías
```

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Cubren esquemas, hechos derivados, reglas, motor de inferencia, endpoints, chatbot, escenarios y repetibilidad.

La compatibilidad Laravel se valida adicionalmente en
`tests/test_phase12_compatibility.py`: prueba el payload oficial, el flujo
`/recommend` → `/chat`, índice, reglas críticas, fallback, nulos, campos
prohibidos y resultados deterministas.

## Limitaciones del MVP

- Datos simulados almacenados en JSON (sin base de datos).
- Sin autenticación ni historial permanente de conversaciones.
- Sin scraping ni integración con supermercados reales.

## Licencia

[MIT](LICENSE)
