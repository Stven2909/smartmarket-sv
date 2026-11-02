# SmartMarket SV · Sistema Experto

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Interfaz-FF4B4B?logo=streamlit&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
[![CI](https://github.com/HenryBo06/Sistema-experto-fork/actions/workflows/ci.yml/badge.svg)](https://github.com/HenryBo06/Sistema-experto-fork/actions/workflows/ci.yml)
[![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-green)](LICENSE)

**SmartMarket SV** es un sistema experto basado en reglas de producción para evaluar y comparar alternativas de compra en supermercados. Analiza presupuesto, ahorro, disponibilidad de productos, distancia, tiempo estimado, promociones y cantidad de establecimientos.

Cada recomendación incluye su conclusión, una acción sugerida y la explicación de las reglas utilizadas. El motor es **determinista y explicable**: no utiliza aprendizaje automático ni modelos generativos para decidir.

**[Abrir demostración en Streamlit](https://sistema-experto-fork.streamlit.app)**

## Funcionalidades

- **Evaluación de alternativas:** clasifica una compra como `EXCELENTE`, `BUENA` o `NO_RECOMENDABLE`.
- **Motor de reglas R01–R08:** aplica condiciones lógicas y prioridades configuradas en JSON.
- **Resolución de conflictos:** identifica la regla ganadora y las demás reglas activadas.
- **Trazabilidad:** conserva los hechos derivados, cada comparación y las condiciones específicas que no se cumplen.
- **Cobertura de reglas:** ejecuta nueve escenarios de prueba y muestra activaciones, victorias, conflictos y casos sin regla en la interfaz.
- **Índice de conveniencia:** calcula una puntuación complementaria de 0 a 100 con pesos explícitos.
- **Comparación de alternativas:** ordena de 2 a 10 opciones, explica sus posiciones y advierte cuando los totales de productos sugieren listas distintas.
- **Análisis de sensibilidad:** muestra cómo cambia una recomendación ante variaciones hipotéticas del precio, distancia, tiempo, promociones y disponibilidad de esenciales.
- **Diagnóstico experto:** identifica riesgos críticos y condiciones pendientes de las reglas favorables, sin modificar los hechos recibidos.
- **Auditoría de reglas (HU-11):** identifica duplicados, condiciones incompatibles, reglas sombreadas y coincidencias controladas por prioridad con 2430 escenarios sintéticos.
- **Comparador de versiones (HU-13):** identifica cambios de dictamen, ganador, activaciones y explicación entre dos bases de reglas sin modificar la versión publicada.
- **Informe académico PDF (HU-12):** integra ranking, trazas de las ocho reglas, sensibilidad, versiones y auditoría en un documento descargable.
- **Chatbot explicativo:** responde preguntas sobre una recomendación ya calculada mediante detección de intenciones y plantillas.
- **Interfaz interactiva:** permite probar escenarios, inspeccionar resultados, comparar alternativas y consultar la base de conocimiento.
- **API REST:** expone las funcionalidades a través de FastAPI y valida las solicitudes con Pydantic.

## Arquitectura

```text
                    ┌───────────────────────────┐
                    │   Interfaz Streamlit      │
                    │  Laboratorio / Comparador │
                    └─────────────┬─────────────┘
                                  │ HTTP / JSON
                    ┌─────────────▼─────────────┐
                    │          FastAPI          │
                    │  Validación con Pydantic  │
                    └─────────────┬─────────────┘
                                  │
             ┌────────────────────┼─────────────────────┐
             │                    │                     │
    ┌────────▼────────┐  ┌────────▼────────┐  ┌─────────▼────────┐
    │ Motor experto   │  │ Comparador      │  │ Chatbot          │
    │ R01–R08         │  │ determinista    │  │ explicativo      │
    └────────┬────────┘  └─────────────────┘  └──────────────────┘
             │
    ┌────────▼──────────────────────────────────────┐
    │ Base de conocimiento JSON · Hechos derivados  │
    │ Índice ponderado · Traza de inferencia         │
    └───────────────────────────────────────────────┘
```

### Proceso de inferencia

1. **Validación:** se comprueban tipos, valores y consistencia de los conteos de productos.
2. **Derivación de hechos:** se calculan indicadores como `dentro_presupuesto`, `ahorro_alto` y `distancia_cercana`.
3. **Evaluación de reglas:** cada regla se comprueba mediante condiciones unidas por `AND`.
4. **Resolución de conflictos:** entre las reglas activadas gana la de menor número de prioridad; los empates se resuelven por ID.
5. **Explicación:** se genera una conclusión junto con la regla ganadora, las reglas restantes y la traza de condiciones.
6. **Índice auxiliar:** se calcula una puntuación ponderada que complementa, pero no reemplaza, la decisión experta.

El motor evalúa las reglas en **una sola pasada**; no realiza encadenamiento iterativo de nuevas conclusiones.

### Base de reglas

Las ocho reglas se almacenan en [`data/rules.json`](data/rules.json).

| Regla | Criterio principal | Resultado |
|---|---|---|
| R01 | Presupuesto excedido en más del 10 % | `NO_RECOMENDABLE` |
| R02 | Faltan productos esenciales | `NO_RECOMENDABLE` |
| R03 | Distancia adicional elevada con ahorro bajo | `NO_RECOMENDABLE` |
| R04 | Tiempo elevado con ahorro bajo | `NO_RECOMENDABLE` |
| R05 | Compra distribuida entre tres o más supermercados | `NO_RECOMENDABLE` |
| R06 | Presupuesto, esenciales, distancia, tiempo y una parada favorables | `EXCELENTE` |
| R07 | Presupuesto y esenciales cubiertos con promociones aplicables | `BUENA` |
| R08 | Dos supermercados con ahorro alto y presupuesto respetado | `BUENA` |

Si ninguna regla se activa, el sistema devuelve provisionalmente `NO_RECOMENDABLE` e indica que se requiere comparar otras opciones. Cuando el presupuesto se supera ligeramente (hasta el 10 %) sin activar otras reglas, la explicación y la acción indican explícitamente esa condición; no se inventa una regla ganadora. La regla R06 no presupone que todos los productos opcionales estén disponibles.

### Índice de conveniencia

El índice utiliza cinco componentes normalizados y ponderados:

| Componente | Peso |
|---|---:|
| Ahorro | 35 % |
| Disponibilidad de productos | 25 % |
| Distancia adicional | 20 % |
| Tiempo estimado | 15 % |
| Promociones | 5 % |
| **Total** | **100 %** |

La clasificación del índice es `ALTA_CONVENIENCIA` (desde 75), `CONVENIENCIA_MEDIA` (desde 50) o `BAJA_CONVENIENCIA` (menos de 50). **No representa una probabilidad ni la confianza de un modelo estadístico.** Las reglas críticas tienen precedencia sobre el índice.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.12+ | Implementación del motor y los servicios |
| FastAPI | Endpoints REST y esquema OpenAPI |
| Pydantic v2 | Contratos y validación de datos |
| Streamlit | Interfaz web interactiva |
| JSON | Reglas y escenarios de demostración |
| Pytest + HTTPX | Pruebas unitarias y de API |
| Ruff + GitHub Actions | Análisis estático e integración continua |

## Instalación y ejecución local

**Requisitos:** Python 3.12 o superior y `pip`.

```bash
git clone https://github.com/HenryBo06/Sistema-experto-fork.git
cd Sistema-experto-fork
python -m venv .venv
```

Activa el entorno virtual:

- **Windows (PowerShell):** ` .\.venv\Scripts\Activate.ps1 `
- **Linux/macOS:** `source .venv/bin/activate`

Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

Inicia la API:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

En otra terminal, con el entorno activado, inicia Streamlit:

```bash
python -m streamlit run demo/streamlit_app.py
```

- **API:** http://127.0.0.1:8001
- **Swagger UI:** http://127.0.0.1:8001/docs
- **Interfaz:** http://localhost:8501

La documentación Swagger/OpenAPI está disponible cuando no se configura una clave de API.

## API REST

| Método | Ruta | Función |
|---|---|---|
| `GET` | `/health` | Comprueba la disponibilidad del servicio |
| `POST` | `/api/v1/recommend` | Evalúa una alternativa y devuelve una recomendación explicable |
| `POST` | `/api/v1/compare` | Compara entre 2 y 10 alternativas |
| `GET` | `/api/v1/knowledge` | Consulta reglas, umbrales, pesos y versiones |
| `GET` | `/api/v1/rule-audit` | Audita consistencia, duplicados y solapamientos en modo lectura |
| `POST` | `/api/v1/rule-regression` | Compara dos snapshots de reglas y detecta regresiones críticas |
| `POST` | `/api/v1/evidence-report` | Genera un informe académico PDF con 2 a 10 escenarios |
| `POST` | `/api/v1/sensitivity` | Analiza la sensibilidad de una recomendación ante cambios hipotéticos |
| `POST` | `/api/v1/diagnosis` | Diagnostica reglas favorables pendientes y riesgos críticos |
| `POST` | `/api/v1/chat` | Explica una recomendación existente |

### Ejemplo de recomendación

Envía un JSON al endpoint `POST /api/v1/recommend`:

```json
{
  "request_id": "compra-001",
  "alternativa_id": "supermercado-a",
  "costo_total": 42.50,
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
  "promociones_aplicables": true
}
```

El resultado contiene, entre otros campos:

| Campo | Descripción |
|---|---|
| `nivel_recomendacion` | Conclusión experta |
| `accion_sugerida` | Acción propuesta para la alternativa |
| `explicacion` | Justificación textual |
| `reglas_activadas` | Reglas cuyas condiciones se cumplieron |
| `winning_rule` / `losing_rules` | Regla ganadora y restantes |
| `hechos_derivados` | Indicadores calculados a partir de la solicitud |
| `trace` | Evaluación detallada de las condiciones |
| `indice_conveniencia` | Índice auxiliar entre 0 y 100 |
| `componentes_conveniencia` / `pesos_conveniencia` | Desglose del cálculo |
| `version_reglas` / `version_contrato` | Versiones de la lógica y del contrato |

Las solicitudes inválidas o inconsistentes reciben `HTTP 422`. Los productos esenciales pueden tener total cero si no existen elementos marcados como esenciales; los conteos globales, esenciales y opcionales deben ser coherentes.

### Comparación de alternativas

`POST /api/v1/compare` recibe un objeto con la propiedad `alternativas`, que contiene entre 2 y 10 solicitudes del mismo formato anterior. Los IDs de alternativa deben ser únicos y todas deben compartir presupuesto.

El comparador evalúa individualmente cada alternativa y ordena por conclusión experta, índice auxiliar, menor costo y finalmente ID. La respuesta incluye un `ranking`, la mejor alternativa relativa y advertencias cuando corresponda. Una primera posición no implica que una alternativa sea recomendable si todas presentan condiciones desfavorables.

### Diagnóstico experto

`POST /api/v1/diagnosis` recibe `{ "alternativa": { ... } }` con los mismos 14 hechos de `/recommend`. Devuelve el dictamen y la regla actual, los riesgos críticos activos y una lista ordenada de oportunidades R06–R08 con las condiciones cumplidas y pendientes. Las orientaciones no estiman precios, no generan promociones y no modifican la solicitud. La vista **Diagnóstico de oportunidades** se encuentra en el Laboratorio de Streamlit.

### Análisis de sensibilidad

`POST /api/v1/sensitivity` recibe `{ "alternativa": { ... } }`, donde `alternativa` contiene los mismos 14 campos de `/recommend`. Calcula el resultado original y varios escenarios hipotéticos independientes: incremento de precio del 5 % o 10 %, 2 km adicionales, 15 minutos más, pérdida de promociones y falta de un producto esencial cuando corresponde. Devuelve el dictamen, la regla y la variación del índice en cada escenario, además del número de cambios de decisión. **No representa una predicción del futuro.** Consulta [la metodología de sensibilidad](docs/analisis-sensibilidad.md).

### Consulta del conocimiento y chatbot

`GET /api/v1/knowledge` permite inspeccionar la base de reglas y sus parámetros vigentes sin modificarlos.

`GET /api/v1/rule-audit` audita la consistencia de las reglas sin modificarlas, informa anomalías estructurales y solapamientos con ejemplos sintéticos reproducibles. El resultado es un informe de revisión, no una validación comercial ni una prueba formal universal. Consulta la [metodología de auditoría](docs/auditoria-consistencia-reglas.md).

`POST /api/v1/rule-regression` ejecuta dos snapshots proporcionados por el solicitante contra los mismos hechos y muestra las decisiones que cambian. Distingue cambios de dictamen y de explicación, señala regresiones críticas e identifica cada snapshot mediante una huella SHA-256. No publica reglas nuevas. Consulta la [guía de comparación de versiones](docs/comparador-versiones-reglas.md).

`POST /api/v1/evidence-report` genera un archivo PDF en memoria con los resultados de 2 a 10 alternativas de presupuesto común, trazas, ranking, sensibilidad y auditoría. Desde Streamlit se genera y descarga en **Base de conocimiento**. Consulta la [guía del informe PDF](docs/informe-academico.md).

`POST /api/v1/chat` recibe `message`, `facts` y la respuesta previa en `recommendation`. Las respuestas son deterministas y se basan en los hechos y la recomendación suministrados, sin generar nuevas conclusiones.

Para los contratos completos consulta [la documentación de la API](docs/api-contract.md) y [los ejemplos de integración](docs/laravel-integration.md).

## Configuración

| Variable | Uso |
|---|---|
| `SMARTMARKET_API_URL` | Dirección base del servicio FastAPI utilizada por Streamlit |
| `SMARTMARKET_API_KEY` | Clave opcional para proteger los endpoints de recomendación, comparación, conocimiento, sensibilidad y chatbot |

Streamlit utiliza `http://127.0.0.1:8001` por defecto. Cuando `SMARTMARKET_API_KEY` está definida en el servidor, los endpoints protegidos requieren la cabecera `X-API-Key`. El endpoint `/health` permanece público.

No incluyas claves reales en el código, el README ni archivos versionados.

## Estructura del repositorio

```text
app/
├── api/                # Rutas HTTP
├── chatbot/            # Detección de intenciones y respuestas
├── expert_system/      # Reglas, clasificadores, inferencia y ponderaciones
├── schemas/            # Modelos de entrada y salida
└── services/           # Servicios de recomendación y comparación
data/
├── rules.json          # Base de conocimiento
└── scenarios.json      # Escenarios de prueba y demostración
demo/
└── streamlit_app.py    # Laboratorio y comparador visual
docs/                   # Contratos y documentación técnica
tests/                  # Pruebas automatizadas
```

## Pruebas y calidad de código

```bash
python -m pytest -q
ruff check app demo tests
```

La suite comprueba reglas, clasificaciones, resolución de conflictos, auditoría de consistencia, comparación de versiones y detección de regresiones, generación y lectura de informes PDF, validación HTTP, trazabilidad, índice de conveniencia, diagnóstico experto, comparación, sensibilidad, valores no finitos, chatbot y renderizado básico de Streamlit.

[Historias de usuario con criterios de aceptación](docs/historias-de-usuario.md). El flujo de integración continua ejecuta las verificaciones de lint y pruebas.

## Alcance

El sistema experto Python actúa como un **servicio de inferencia independiente y sin estado**. El backend Laravel prepara y envía los 14 hechos de cada alternativa mediante `POST /api/v1/recommend`; Python valida la solicitud, deriva hechos, evalúa las reglas y devuelve un resultado explicable en JSON. No recopila precios, administra productos, consulta supermercados ni obtiene información mediante scraping. La interfaz Streamlit y los escenarios de ejemplo sirven para demostrar y probar el servicio sin depender de que Laravel esté disponible.

## Licencia

Distribuido bajo la [licencia MIT](LICENSE).
