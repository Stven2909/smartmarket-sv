# Historias de usuario — Sistema experto SmartMarket SV

## Visión y límites

Como módulo de apoyo a decisiones de compra, el sistema experto recibe por HTTP los hechos de cada alternativa, valida su estructura, aplica ocho reglas de producción y devuelve conclusiones trazables. Su propósito es **explicar y contrastar decisiones** y permitir pruebas reproducibles, no recopilar información de supermercados ni modificar la optimización propia de Laravel.

**Alcance de estas historias:** servicio Python, API FastAPI, Streamlit como laboratorio de demostración y pruebas. No contemplan cambios en `develop`, bases de datos comerciales, extracción automática de precios ni evaluación de especialistas externos. Los escenarios de prueba son sintéticos. En la integración, Laravel proporciona los hechos; Python no los captura.

### Prioridad y estado

| ID | Historia resumida | Prioridad | Estado |
|---|---|---|---|
| HU-01 | Recibir y validar los hechos de compra | Alta | Implementada |
| HU-02 | Conocer el dictamen y la regla determinante | Alta | Implementada |
| HU-03 | Distinguir riesgos críticos y requisitos favorables | Alta | Implementada |
| HU-04 | Identificar condiciones pendientes sin fabricar valores | Alta | Implementada en esta mejora |
| HU-05 | Comparar alternativas con prioridad experta | Alta | Implementada |
| HU-06 | Explorar cambios hipotéticos de una alternativa | Alta | Implementada |
| HU-07 | Consultar las razones mediante el chatbot | Media | Implementada |
| HU-08 | Auditar cobertura de las ocho reglas | Alta | Implementada |
| HU-09 | Rechazar hechos inconsistentes y valores inválidos | Alta | Implementada |
| HU-10 | Proteger rutas y comprobar la integración HTTP | Alta | Implementada |
| HU-11 | Detectar automáticamente contradicciones al revisar reglas | Media | Implementada |
| HU-12 | Exportar un informe completo de decisiones y pruebas | Media | Implementada |
| HU-13 | Detectar regresiones entre dos snapshots de reglas | Alta | Implementada |

## Historias y criterios de aceptación

### HU-01 — Validar hechos de entrada

**Como** sistema que recibe datos del backend, **quiero** validar los 14 hechos de una alternativa **para** evitar decisiones a partir de datos imposibles o parciales.

**Criterios de aceptación:**
- Dado un JSON válido, `POST /api/v1/recommend` devuelve HTTP 200.
- Si falta presupuesto o existen conteos inconsistentes, responde HTTP 422.
- Se admiten cero productos esenciales; no se admiten productos esenciales disponibles por encima de su total.
- Los datos no numéricos, `NaN` e infinitos no se usan en la inferencia.
- Ninguna modificación de esta historia obliga a modificar el contrato de Laravel.

**Evidencia:** `tests/test_validation_improvements.py`, `tests/test_robustness_and_sensitivity.py`.

### HU-02 — Entender la recomendación

**Como** usuario que consulta una alternativa, **quiero** conocer nivel, regla ganadora, acción, hechos derivados y evaluación de condiciones **para** entender la decisión.

**Criterios de aceptación:**
- La respuesta indica `EXCELENTE`, `BUENA` o `NO_RECOMENDABLE`.
- Las ocho reglas aparecen evaluadas en `trace`, con razones de coincidencia o incumplimiento.
- Si se activan varias, la menor prioridad numérica determina la ganadora; hay un desempate determinista por ID.
- El índice de conveniencia no revoca una regla crítica.

**Evidencia:** `tests/test_inference_engine.py`, `tests/test_professional_api.py`.

### HU-03 — Detectar bloqueos críticos

**Como** analista, **quiero** distinguir todas las reglas críticas activas, no solo la ganadora, **para** evitar interpretar una recomendación favorable de manera equivocada.

**Criterios de aceptación:**
- El diagnóstico enumera las reglas críticas R01–R05 activadas, ordenadas por prioridad.
- Si R08 se activa junto con R02, sigue indicándose que hay riesgo crítico.
- La respuesta aclara que satisfacer una regla favorable no garantiza una compra recomendable si persisten riesgos.

**Evidencia:** `tests/test_diagnosis.py`.

### HU-04 — Comprender requisitos pendientes

**Como** estudiante que analiza una recomendación, **quiero** saber qué condiciones faltan para R06, R07 y R08 **para** justificar escenarios hipotéticos sin alterar los datos de entrada.

**Criterios de aceptación:**
- `POST /api/v1/diagnosis` acepta una alternativa con los mismos 14 hechos.
- Devuelve únicamente requisitos de las reglas favorables existentes y su estado actual.
- Muestra criterios y umbrales de presupuesto, distancia, tiempo, ahorro, disponibilidad y número de tiendas cuando correspondan.
- No inventa descuentos, precios, promociones, disponibilidad o valores de sustitución.
- Las sugerencias son orientativas; no cambian los hechos ni el resultado de `/recommend`.
- Streamlit muestra el diagnóstico de la última alternativa evaluada y no reutiliza uno anterior cuando cambian los hechos.

**Evidencia:** `tests/test_diagnosis.py`.

### HU-05 — Comparar alternativas

**Como** usuario que compara opciones, **quiero** ver un ranking experto explicable **para** distinguir conveniencia auxiliar y conclusiones basadas en reglas.

**Criterios de aceptación:**
- Se comparan de 2 a 10 alternativas con identificadores distintos y presupuesto común.
- Primero se considera el nivel de regla, luego el índice auxiliar y desempates deterministas.
- Las alternativas con riesgos críticos no superan a las favorables solo por su índice.
- Si parecen proceder de listas distintas, se devuelve una advertencia sin alterar el resultado.

**Evidencia:** `tests/test_comparison.py`, `tests/test_professional_api.py`.

### HU-06 — Explorar la estabilidad de una decisión

**Como** investigador, **quiero** comparar escenarios de cambio de costo, distancia, tiempo, promociones o esenciales **para** detectar decisiones sensibles a umbrales.

**Criterios de aceptación:**
- `POST /api/v1/sensitivity` conserva intacta la alternativa original.
- Las variaciones se etiquetan explícitamente como hipotéticas.
- Se compara nivel y regla ganadora antes y después.
- No se presenta la variación como probabilidad ni pronóstico.

**Evidencia:** `tests/test_robustness_and_sensitivity.py`, `tests/test_rule_boundaries.py`.

### HU-07 — Consultar por qué se tomó una decisión

**Como** usuario del asistente explicativo, **quiero** hacer preguntas sobre la recomendación **para** obtener respuestas comprensibles basadas en hechos ya calculados.

**Criterios de aceptación:**
- El chatbot explica regla ganadora, reglas competidoras, presupuesto, productos, distancia y promociones.
- No inventa datos cuando los hechos son insuficientes.
- El chatbot no recalcula ni cambia una decisión.

**Evidencia:** `tests/test_chat_language.py`, `tests/test_chat_contract.py`.

### HU-08 — Demostrar cobertura de conocimiento

**Como** estudiante que expone el sistema, **quiero** ejecutar escenarios por cada regla **para** demostrar cobertura, prioridades y casos sin regla ganadora.

**Criterios de aceptación:**
- Se utilizan los escenarios de ejemplo mediante la API.
- Se reportan activaciones, victorias, conflictos y casos sin regla.
- Las ocho reglas se activan al menos una vez en el conjunto de referencia.
- Se informa que los resultados son pruebas sintéticas y no una medición de exactitud del mercado.

**Evidencia:** `tests/test_decision_coverage.py`.

### HU-09 — Proteger la coherencia de las entradas

**Como** responsable del componente, **quiero** evitar que valores imposibles lleguen a las reglas **para** garantizar respuestas reproducibles.

**Criterios de aceptación:**
- Conteos esenciales y opcionales respetan los totales.
- Costo y presupuesto finitos con restricciones explícitas.
- Solicitudes repetidas con hechos idénticos obtienen el mismo resultado.

**Evidencia:** `tests/test_schemas.py`, `tests/test_rule_boundaries.py`.

### HU-10 — Exponer un servicio verificable

**Como** integrador del backend, **quiero** un contrato OpenAPI estable, salud del servicio y protección opcional por API key **para** consumir Python de forma controlada.

**Criterios de aceptación:**
- `/health` devuelve estado de disponibilidad.
- La autenticación por `X-API-Key` se aplica a los endpoints protegidos cuando está configurada.
- Los 14 campos de `RecommendationRequest` y 16 de `RecommendationResponse` permanecen inalterados.
- Las nuevas rutas son opcionales; Laravel puede seguir usando solo `/api/v1/recommend`.

**Evidencia:** `tests/test_contract.py`, `tests/test_diagnosis.py`.

## HU-11 — Verificador de consistencia del conocimiento

**Como** responsable de las reglas, **quiero** detectar duplicados, contradicciones, solapamientos y reglas sombreadas **para** identificar problemas antes de editar la base de conocimiento.

**Criterios de aceptación:**
- `GET /api/v1/rule-audit` devuelve un informe de solo lectura con la versión de reglas, cobertura sintética, hallazgos y pares de reglas que se activan simultáneamente.
- Las reglas con idénticas condiciones o salidas divergentes se señalan explícitamente.
- Se detectan restricciones mutuamente incompatibles de los hechos derivados y hechos numéricos usados como booleanos.
- Las reglas sombreadas se identifican cuando otra regla más general y de mayor prioridad impide que ganen.
- Los solapamientos legítimos, como R06 y R07, se informan con un ejemplo sintético y con la prioridad que resuelve el conflicto, sin presentarlos automáticamente como errores.
- La auditoría emplea 2430 casos sintéticos representativos, aclara sus límites y no modifica reglas ni decisiones.
- Se puede visualizar y descargar el informe desde **Base de conocimiento** de Streamlit; se respeta `X-API-Key` cuando está configurada.

**Evidencia:** `tests/test_rule_auditor.py`, [metodología de auditoría](auditoria-consistencia-reglas.md).

## HU-12 — Informe académico de evidencias descargable

**Como** expositor o investigador, **quiero** exportar un informe completo en PDF **para** conservar y presentar las decisiones, trazas y comprobaciones técnicas de una misma selección de escenarios.

**Criterios de aceptación:**
- El endpoint `POST /api/v1/evidence-report` acepta de 2 a 10 escenarios con IDs únicos y presupuesto compartido.
- Genera un PDF paginado con fecha UTC, versiones, cobertura, ranking, trazas R01–R08, pesos, umbrales, auditoría y sensibilidad por alternativa.
- El reporte declara si los casos fueron etiquetados como sintéticos o su procedencia no está verificada.
- La respuesta es `application/pdf`, con descarga HTTP y `Cache-Control: no-store`; no se persiste en servidor.
- La ruta requiere `X-API-Key` cuando la protección de la API está configurada.
- Streamlit ofrece generar y descargar el PDF desde la pestaña Base de conocimiento.
- La nueva ruta no modifica `/recommend`, sus 14 hechos de entrada, 16 campos de salida ni las reglas vigentes.
- Las pruebas abren el PDF, extraen texto, inspeccionan las secciones y verifican errores y seguridad.

**Evidencia:** `tests/test_evidence_report.py` y [manual del informe](informe-academico.md).

## HU-13 — Comparación segura de versiones de reglas

**Como** mantenedor del motor, **quiero** comparar dos versiones de reglas sobre los mismos hechos **para** detectar regresiones antes de publicar cambios.

**Criterios de aceptación:**
- `POST /api/v1/rule-regression` acepta dos snapshots completos y de 1 a 10 escenarios de prueba.
- Devuelve decisiones anteriores y propuestas, reglas ganadoras, activaciones, explicaciones y cambios por escenario.
- Identifica reglas agregadas, retiradas y modificadas y calcula huellas SHA-256 de cada snapshot; las etiquetas aportadas por el usuario no acreditan su identidad histórica.
- Marca regresiones críticas cuando un rechazo respaldado por reglas R01–R05 pasa a un nivel favorable.
- Las reglas suministradas se validan; solicitudes inválidas responden HTTP 422.
- El comparador evalúa con el mismo motor pero sin modificar `data/rules.json` ni `POST /api/v1/recommend`.
- Streamlit permite simular cambios de prioridad, ver diferencias y descargar el resultado en JSON, sin editar reglas publicadas.
- Se respeta `X-API-Key` cuando está configurada y se documenta que la muestra no prueba equivalencia universal.

**Evidencia:** `tests/test_rule_regression.py` y [guía técnica](comparador-versiones-reglas.md).

## Historias propuestas para otras iteraciones

**Pendientes posibles:** ampliar en el futuro los escenarios de regresión con más combinaciones de hechos y revisar automáticamente cambios propuestos en PR, sin alterar la integración existente.

### Definición de terminado

Una historia se considera terminada cuando tiene implementación acotada, pruebas automáticas verdes, contratos documentados y una comprobación funcional en Streamlit cuando modifica la interfaz. Estar propuesta o documentada no equivale a estar implementada.
