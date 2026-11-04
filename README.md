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
- **Inferencia por lotes (HU-24):** opcionalmente recibe hasta 50 alternativas en una sola solicitud HTTP, preserva su orden, IDs y evaluación independiente, sin calcular ni cambiar el ranking de Laravel.
- **Despliegue ligero:** Streamlit instala solo las dependencias de la interfaz y calcula únicamente la pestaña activa; Render difiere el motor PDF y cachea las reglas estáticas y la auditoría bajo demanda.
- **Motor de reglas R01–R16:** aplica condiciones lógicas y prioridades configuradas en JSON.
- **Resolución de conflictos:** identifica la regla ganadora y las demás reglas activadas.
- **Trazabilidad:** conserva los hechos derivados, cada comparación y las condiciones específicas que no se cumplen.
- **Control de coherencia HU-25:** una auditoría de pruebas contrasta hechos derivados, condiciones de las dieciséis reglas, resolución de prioridades, dictamen, explicación e índice; no consume recursos durante peticiones HTTP.
- **Identificación exacta de reglas (HU-22):** devuelve la huella SHA-256 de las definiciones vigentes en la cabecera HTTP `X-Expert-Rules-SHA256` de `/api/v1/recommend`, `/api/v1/knowledge` y `/ready`; sin campos adicionales en JSON ni trabajo en segundo plano.
- **Cobertura de reglas:** ejecuta nueve escenarios de prueba y muestra activaciones, victorias, conflictos y casos sin regla en la interfaz.
- **Índice de conveniencia:** calcula una puntuación complementaria de 0 a 100 con pesos explícitos.
- **Calibración reproducible HU-31:** compara cinco perfiles alternativos de pesos en el mismo motor, registra cambios de dictamen y comprueba riesgos críticos, sin modificar los pesos del despliegue.
- **Comparación de alternativas:** ordena de 2 a 10 opciones, explica sus posiciones y advierte cuando los totales de productos sugieren listas distintas.
- **Importación CSV/JSON (HU-15):** Streamlit valida hasta 750 filas y distingue datos manuales, escenarios sintéticos y referencias web, sin añadir campos al motor.
- **Pruebas basadas en propiedades (HU-16):** Hypothesis comprueba determinismo, condiciones excluyentes, prioridades críticas y monotonía del índice auxiliar.
- **Regresión de código (HU-17):** compara en procesos aislados el commit base y el candidato sobre 3443 escenarios, detectando cambios de umbrales, pesos y activación crítica.
- **Compatibilidad Laravel (HU-18):** valida mediante HTTP en memoria los 14 hechos y respuestas esperadas a partir de casos sintéticos basados en el contrato PHP de Steven.
- **Benchmark del motor (HU-19):** mide mediana, p95 y memoria en CI sin despertar Render.
- **Análisis de sensibilidad:** muestra cómo cambia una recomendación ante variaciones hipotéticas del precio, distancia, tiempo, promociones y disponibilidad de esenciales.
- **Diagnóstico experto:** identifica riesgos críticos y condiciones pendientes de las reglas favorables, sin modificar los hechos recibidos.
- **Auditoría de reglas (HU-11):** identifica duplicados, condiciones incompatibles, reglas sombreadas y coincidencias controladas por prioridad con 3402 escenarios sintéticos.
- **Comparador de versiones (HU-13):** identifica cambios de dictamen, ganador, activaciones y explicación entre dos bases de reglas sin modificar la versión publicada.
- **Control de regresiones en CI (HU-14):** revisa propuestas de cambio en `data/rules.json` sobre 3411 casos sintéticos y falla cuando detecta pérdidas de protección crítica o nuevas anomalías estructurales.
- **Informe académico PDF (HU-12):** integra ranking, trazas de las dieciséis reglas, sensibilidad, versiones y auditoría en un documento descargable.
- **Chatbot explicativo:** responde preguntas sobre una recomendación ya calculada mediante detección de intenciones y plantillas.
- **Interfaz interactiva:** permite probar escenarios, inspeccionar resultados, comparar alternativas y consultar la base de conocimiento.
- **Paneles resistentes en Streamlit Cloud:** sustituye todas las métricas dinámicas por tarjetas HTML seguras, adapta el diseño a móvil y evita mostrar resultados obsoletos ante errores.
- **Tablas ligeras y legibles:** presenta las tablas de hechos, auditoría, diagnóstico y comparación como HTML escapado en lugar de 16 componentes interactivos con carga JavaScript adicional.
- **API REST:** expone las funcionalidades a través de FastAPI y valida las solicitudes con Pydantic.
- **Seguridad del canal backend → motor (HU-23):** protege los endpoints de negocio con `X-API-Key` en producción, admite rotación temporal y desactiva caché en las respuestas de la API. La autenticación de usuarios finales permanece en Laravel.
- **Endurecimiento HU-26:** activa protección automáticamente en Render, permite una clave independiente para Streamlit, limita a 512 KiB cada cuerpo HTTP de la API y audita las dependencias Python en GitHub Actions.
- **Protección de la demo HU-27:** con clave independiente para Streamlit, limita el número de peticiones por minuto sin aplicar esa cuota al backend Laravel ni mantener tareas residentes.

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
    │ R01–R16         │  │ determinista    │  │ explicativo      │
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

Las dieciséis reglas se almacenan en [`data/rules.json`](data/rules.json).

| Regla | Criterio principal | Resultado |
|---|---|---|
| R01 | Presupuesto excedido en más del 10 % | `NO_RECOMENDABLE` |
| R02 | Faltan productos esenciales | `NO_RECOMENDABLE` |
| R03 | Distancia adicional elevada con ahorro bajo | `NO_RECOMENDABLE` |
| R04 | Tiempo elevado con ahorro bajo | `NO_RECOMENDABLE` |
| R05 | Compra distribuida entre tres o más supermercados | `NO_RECOMENDABLE` |
| R06 | Presupuesto, esenciales, distancia, tiempo y una parada favorables | `EXCELENTE` |
| R07 | Presupuesto y esenciales cubiertos con promociones aplicables | `BUENA` |
| R08 | Dos supermercados con ahorro alto, esenciales completos y presupuesto respetado | `BUENA` |
| R09 | Ningún producto disponible | `NO_RECOMENDABLE` |
| R10 | Cobertura inferior al 50 % de productos, con alguno disponible | `NO_RECOMENDABLE` |
| R11 | Compra completa en una tienda, trayecto ≤5 km y ≤30 min, ahorro ≥3 y sin promociones | `BUENA` |
| R12 | Menos del 80 % de la lista disponible sin esenciales declarados | `NO_RECOMENDABLE` |
| R13 | Esenciales cubiertos y cobertura parcial, con costo y traslado razonables | `BUENA` |
| R14 | Compra completa con ahorro alto y balance ponderado ≥75 puntos, viaje moderado | `BUENA` |
| R15 | Compra completa sin descuentos, índice ≥50 puntos y viaje moderado | `BUENA` |
| R16 | Esenciales cubiertos, 80–99 % disponible, ahorro medio e índice ≥60 puntos | `BUENA` |

**Ampliación HU-28:** R09 y R10 protegen contra una falsa recomendación favorable cuando existe disponibilidad nula o inferior a la mitad; R11 permite una alternativa completa, equilibrada y sin promociones. R08 ya no se activa si faltan productos esenciales. Los nuevos umbrales son criterios del prototipo que deberán validarse con casos reales. La matriz histórica de Streamlit se amplió entonces mediante escenarios separados, respetando los límites del endpoint. `RULES_VERSION=1.1.0`, mientras que `CONTRACT_VERSION=1.0.0` y el payload Laravel siguen iguales. [Diseño, límites y pruebas](docs/hu28-ampliacion-reglas.md).

**Ampliación HU-29:** R12 evita declarar excelente una alternativa con cobertura baja y cero esenciales definidos; R13 distingue una compra parcialmente completa (BUENA) de una excelente cuando faltan muchos opcionales. El límite del 80 % es una política del prototipo y debe calibrarse con ejemplos reales. En esa fase, la matriz de Streamlit revisaba R01–R13 en tres lotes (9, 3 y 2). `RULES_VERSION=1.2.0`, `THRESHOLDS_VERSION=1.2.0`, `CONTRACT_VERSION=1.0.0`. [Razones, límites y pruebas](docs/hu29-cobertura-reglas.md).

**Ampliación HU-30 (vigente):** R14–R16 incorporan el índice de conveniencia calculado con los cinco pesos del motor a la evaluación de casos comerciales concretos. R14 exige conveniencia alta (≥75); R15 exige conveniencia no baja (≥50) y R16 un índice sólido (≥60). Ningún peso puede revocar los riesgos críticos. La matriz de cobertura revisa las dieciséis reglas en solo dos peticiones de 9 y 8 escenarios. `RULES_VERSION=1.3.0`, `THRESHOLDS_VERSION=1.3.0` y `CONTRACT_VERSION=1.0.0`. [Criterios y límites](docs/hu30-reglas-ponderadas.md).

**Calibración HU-31 (vigente):** `python -m scripts.calibrate_convenience_weights --with-grid` contrasta cinco perfiles de pesos con los 17 escenarios de demostración y 3404 representantes sintéticos. La CI valida que ningún perfil invalide una protección crítica; no elige automáticamente un perfil "mejor". El motor continúa con los pesos originales, pero corrige la comparación de R16 para aplicar 60 puntos **sin redondear**. Esta precisión queda trazada mediante `RULES_VERSION=1.3.1`, `THRESHOLDS_VERSION=1.3.1`; el contrato continúa en `1.0.0`. [Guía de calibración y límites](docs/hu31-calibracion-pesos.md).

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
| `POST` | `/api/v1/recommend/batch` | Infiere 1–50 alternativas por petición sin reordenarlas (opcional) |
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

## Reparación de Streamlit Cloud

En la demostración se detectó un fallo de carga del módulo JavaScript `Metric.*.js`. Los indicadores se renderizan ahora como HTML escapado y adaptable, sin depender de ese recurso dinámico. Las tablas de resultados pequeñas también se renderizan como HTML estático para reducir módulos dinámicos, con límite de 100 filas visibles y acceso a la evidencia JSON para los datos completos. La dependencia de Streamlit en `demo/requirements.txt` queda fijada en `1.66.1` (verificada en CI). La URL del servicio Python ya no puede ser modificada por usuarios de la demo; se configura solo en el servidor.

**Advertencia:** las pruebas automáticas de Streamlit ejecutan Python, pero no garantizan que Streamlit Cloud entregue sus módulos JS al navegador. Una pantalla en blanco, un spinner permanente o recursos `.js` inaccesibles también pueden indicar problemas de Cloud, caché del navegador o conectividad. Revisa los logs del despliegue y sigue la [guía de reparación y verificación](docs/reparacion-streamlit-cloud-2026-11.md). Aun cuando las pruebas pasen, no consideres resuelto el incidente hasta validar el sitio publicado en un navegador real.

## Configuración

| Variable | Uso |
|---|---|
| `SMARTMARKET_API_URL` | Dirección base del servicio FastAPI utilizada por Streamlit |
| `SMARTMARKET_ENV` | En Render usa `production`; cualquier entorno explícito salvo `local/dev/development/test/testing` exige API key |
| `SMARTMARKET_API_KEY` | Secreto principal del servidor Python, obligatorio cuando `SMARTMARKET_ENV` indica un entorno desplegado |
| `SMARTMARKET_API_KEY_PREVIOUS` | Clave anterior opcional y temporal durante una rotación |
| `SMARTMARKET_API_KEY_STREAMLIT` | En Render: clave secundaria opcional, distinta de la de Laravel; puede revocarse independientemente |
| `SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE` | En Render: máximo de peticiones por minuto de la clave independiente Streamlit (predeterminado 60; válido 1–600) |

Streamlit utiliza `http://127.0.0.1:8001` por defecto. Los endpoints `/api/v1/*` requieren `X-API-Key` cuando existe un secreto de servidor o el entorno está protegido. `/health` y `/ready` permanecen públicos; el resto devuelve `401` sin clave válida. En un entorno protegido sin clave principal, el motor devuelve `503` en lugar de permitir acceso anónimo.

**Streamlit también utiliza credenciales de servidor:** en Community Cloud, abre la aplicación → Settings → Secrets y guarda `SMARTMARKET_API_URL` (URL HTTPS de Render) y `SMARTMARKET_API_KEY` (el secreto vigente en Render). La interfaz ya incluye `X-API-Key` en las llamadas de API desde Python, no desde el navegador. El botón **Verificar conexión** sigue disponible en la barra lateral; la URL y el secreto no pueden editarse desde la demo. Nunca copies estas variables al código fuente ni a React.

**Importante:** Render define automáticamente `RENDER=true` y nuestro servicio lo reconoce como un entorno desplegado, que exige la clave principal. Aunque falte `SMARTMARKET_ENV`, la API no queda abierta por ese motivo. En desarrollo local continúa el modo sin clave. Antes de considerar el despliegue seguro, configura ambos secretos en Render y la clave correspondiente `EXPERT_SYSTEM_API_KEY` en Laravel. Nunca expongas la clave del servidor en React/Streamlit ni confundas `X-API-Key` con la autenticación de usuarios finales.

No incluyas claves reales en el código, el README ni archivos versionados. Ver [HU-23: seguridad y rotación de claves](docs/seguridad-api-hu23.md).

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
python -m pip install -r requirements-dev.txt ruff
python -m pytest -q
ruff check app demo scripts tests
```

La suite comprueba reglas, clasificaciones, resolución de conflictos, auditoría de consistencia, comparación de versiones, importación CSV/JSON, pruebas generativas de invariantes, detección de regresiones, generación y lectura de informes PDF, validación HTTP, trazabilidad, índice de conveniencia, diagnóstico experto, comparación, sensibilidad, valores no finitos, chatbot y renderizado básico de Streamlit.

[Datos de exposición: 300 alternativas y 61 referencias de precios](docs/importacion-datos-y-propiedades.md). [Regresiones HU-17, pruebas Laravel HU-18 y rendimiento HU-19](docs/regresiones-integracion-benchmark.md). [Guía de optimización y reposo](docs/optimizacion-reposo.md). [Historias de usuario con criterios de aceptación](docs/historias-de-usuario.md). El flujo de integración continua ejecuta lint, pruebas y, en solicitudes de cambio que modifican `data/rules.json`, el [control automático de regresiones](docs/ci-regresion-reglas.md). Para exigir que un PR con CI fallido no pueda fusionarse, se debe configurar la protección de rama en GitHub.

## Alcance

El sistema experto Python actúa como un **servicio de inferencia independiente y sin estado**. El backend Laravel prepara y envía los 14 hechos de cada alternativa mediante `POST /api/v1/recommend`; Python valida la solicitud, deriva hechos, evalúa las reglas y devuelve un resultado explicable en JSON. No recopila precios, administra productos, consulta supermercados ni obtiene información mediante scraping. La interfaz Streamlit y los escenarios de ejemplo sirven para demostrar y probar el servicio sin depender de que Laravel esté disponible.

## Licencia

Distribuido bajo la [licencia MIT](LICENSE).


## Sincronización y alcance de integración

Las mejoras del servicio se integran por PR en nuestro `main`. Para publicar los mismos commits en la rama `expert-system-python` del compañero, sin modificar `develop`, utiliza la [guía de sincronización segura](docs/sincronizacion-upstream-expert.md) y `scripts/sync_upstream_expert.ps1`: verifica el historial y publica solo por avance rápido, sin `--force`. La rama espejo `expert-system-python` de **nuestro fork** se mantiene por avance rápido con el workflow `.github/workflows/sync-python-mirror.yml` cuando cambia `main`. Esta sincronización interna **no sustituye** la publicación en el repositorio del equipo, que requiere permisos de escritura específicos.

En la integración, Python **solo recibe hechos, ejecuta las reglas y devuelve JSON**. No modifica el ranking económico, el ETL, las bases de datos ni la interfaz Laravel/React. El contrato de 14 campos se contrasta con `develop` en modo lectura mediante `python -m scripts.check_laravel_contract --upstream`.

[Contrato actual y despliegue HU-20/HU-21](docs/contrato-integracion-develop-2026-11-03.md) · [Huella de reglas HU-22](docs/hu22-huella-reglas.md) · [Seguridad API HU-23](docs/seguridad-api-hu23.md) · [Inferencia por lotes HU-24](docs/inferencia-lotes-hu24.md) · [Estabilidad Streamlit Cloud](docs/reparacion-streamlit-cloud-2026-11.md) · [Coherencia de inferencias HU-25](docs/hu25-coherencia-inferencia.md).


### Auditoría de seguridad reproducible (HU-26)

El servicio exige `X-API-Key` en Render, separa opcionalmente la credencial de Streamlit con `SMARTMARKET_API_KEY_STREAMLIT`, limita solicitudes JSON a 512 KiB y analiza dependencias con `pip-audit` en CI. Para verificar sin clave los cuatro endpoints públicos/privados desde tu propia red: `python -m scripts.security_probe --base-url https://sistema-experto-fork.onrender.com`. Se recomienda revisar las pruebas y las limitaciones antes de declarar seguro un despliegue: [HU-26 — auditoría de seguridad](docs/auditoria-seguridad-hu26.md).


### Cuota de la demo pública (HU-27)

Después de configurar una clave **distinta** para Streamlit, el motor aplica un presupuesto de peticiones por minuto al consumidor Streamlit, sin restringir la clave principal de Laravel. Cuando se supera, la API devuelve HTTP 429 y `Retry-After`; no se ejecutan procesos ni pings periódicos. La cuota es compartida por los visitantes y por proceso, y no sustituye la restricción de acceso a la página. Consulta [HU-27 — límite de la demo pública](docs/hu27-proteccion-demo-publica.md).
