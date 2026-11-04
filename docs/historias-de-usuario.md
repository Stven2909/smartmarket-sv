# Historias de usuario — Sistema experto SmartMarket SV

## Visión y límites

Como módulo de apoyo a decisiones de compra, el sistema experto recibe por HTTP los hechos de cada alternativa, valida su estructura, aplica once reglas de producción y devuelve conclusiones trazables. Su propósito es **explicar y contrastar decisiones** y permitir pruebas reproducibles, no recopilar información de supermercados ni modificar la optimización propia de Laravel.

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
| HU-14 | Ejecutar regresiones automáticamente en PR que cambian reglas | Alta | Implementada |
| HU-15 | Importar alternativas CSV/JSON con procedencia | Alta | Implementada |
| HU-16 | Ejecutar propiedades e invariantes del motor con Hypothesis | Alta | Implementada |
| HU-17 | Comparar código base y propuesto con escenarios fijos | Alta | Implementada |
| HU-18 | Validar el contrato enviado por Laravel sin tocar develop | Alta | Implementada |
| HU-19 | Medir rendimiento y memoria sin solicitudes remotas | Media | Implementada |
| HU-20 | Validar desbordamientos numéricos, readiness y cierre seguro en producción | Alta | Implementada; requiere configurar secretos al desplegar |
| HU-21 | Detectar cambios del contrato Laravel leyendo develop sin modificarlo | Alta | Implementada en CI |
| HU-22 | Identificar la base exacta de reglas usada en cada inferencia | Media | Implementada |
| HU-23 | Proteger la comunicación Laravel-Python con rotación y no-cache | Alta | Implementada; activar secretos en Render y Laravel |
| HU-24 | Permitir inferencias de hasta 50 alternativas por solicitud | Media | Implementada, opcional para Laravel |
| HU-25 | Verificar coherencia entre reglas, hechos, explicación, dictamen e índice | Alta | Implementada en pruebas de regresión |
| HU-26 | Endurecer Render, separar claves de servicio y escanear dependencias | Alta | Implementada; 4 comprobaciones externas de acceso correctas |
| HU-27 | Limitar el uso de la demo pública sin reducir la cuota de Laravel | Alta | Implementada; se activa con clave Streamlit independiente |
| HU-28 | Corregir casos de cobertura insuficiente y agregar compra equilibrada sin promociones | Alta | Implementada en reglas 1.1.0; verificar regresiones |
| HU-29 | Distinguir cobertura parcial con o sin esenciales declarados | Alta | Implementada en reglas 1.2.0, validación pendiente de cierre |
| HU-30 | Aprovechar los cinco pesos del índice en tres reglas explicables | Alta | Implementada y sujeta a validación de CI |
| HU-31 | Comparar pesos experimentalmente y proteger umbrales no redondeados | Alta | Implementada; conservar perfil de producción mientras falten datos etiquetados |

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
- Las once reglas aparecen evaluadas en `trace`, con razones de coincidencia o incumplimiento.
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
- La auditoría emplea 3402 casos sintéticos representativos, aclara sus límites y no modifica reglas ni decisiones.
- Se puede visualizar y descargar el informe desde **Base de conocimiento** de Streamlit; se respeta `X-API-Key` cuando está configurada.

**Evidencia:** `tests/test_rule_auditor.py`, [metodología de auditoría](auditoria-consistencia-reglas.md).

## HU-12 — Informe académico de evidencias descargable

**Como** expositor o investigador, **quiero** exportar un informe completo en PDF **para** conservar y presentar las decisiones, trazas y comprobaciones técnicas de una misma selección de escenarios.

**Criterios de aceptación:**
- El endpoint `POST /api/v1/evidence-report` acepta de 2 a 10 escenarios con IDs únicos y presupuesto compartido.
- Genera un PDF paginado con fecha UTC, versiones, cobertura, ranking, trazas R01–R11, pesos, umbrales, auditoría y sensibilidad por alternativa.
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

## HU-14 — Puerta de regresión automática de reglas

**Como** mantenedor, **quiero** comprobar automáticamente propuestas de cambios a `data/rules.json` **para** detectar fallos críticos antes de aceptar versiones nuevas.

**Criterios de aceptación:**
- El workflow CI ejecuta la comparación automáticamente en pull requests si cambia `data/rules.json`.
- Compara el archivo real del commit base del PR contra la propuesta utilizando los nueve casos de demostración y 3402 escenarios sintéticos representativos.
- Marca el job de CI como fallido cuando una compra antes rechazada por R01–R05 pasa a favorable o cuando se pierde la activación de una regla crítica.
- Rechaza anomalías estructurales nuevas, JSON inválido y snapshots inconsistentes.
- Permite cambios no críticos e informa diferencias sin bloquearlos injustificadamente.
- Publica métricas y ejemplos en GitHub Actions Job Summary.
- No escribe `rules.json`, no publica reglas ni modifica los contratos HTTP existentes.
- Documenta que exigir CI aprobado para fusionar es una configuración independiente de protección de la rama principal.

**Evidencia:** `tests/test_rule_change_gate.py`, `scripts/check_rule_regression.py`, `.github/workflows/ci.yml` y [guía de control](ci-regresion-reglas.md).

## HU-15 — Importación de alternativas manuales

**Como** expositor, **quiero** cargar cientos de alternativas con procedencia explícita **para** comparar datos preparados por nuestro equipo sin añadir tareas al backend Laravel.

**Criterios de aceptación:**
- La pestaña Comparador permite seleccionar CSV/JSON con los 14 hechos y metadatos opcionales de nombre, procedencia, fecha, URL y tienda.
- Valida UTF-8, máximo de 2 MB y 750 filas, enteros y conteos coherentes, ID único, números finitos y campos obligatorios.
- Los metadatos no forman parte del JSON enviado a `/api/v1/compare`.
- Se pueden seleccionar de 2 a 10 casos del mismo presupuesto.
- El archivo completo se rechaza ante filas corruptas; no realiza llamadas HTTP al cargarlo ni afirma autenticidad de datos `manual_real`.
- Incluye [300 alternativas sintéticas y 61 observaciones de precios públicos](importacion-datos-y-propiedades.md), explícitamente diferenciadas.

**Pruebas:** `tests/test_manual_dataset.py` y `tests/test_expo_datasets.py`.

## HU-16 — Pruebas basadas en propiedades

**Como** mantenedor, **quiero** generar muchas alternativas consistentes y comprobar propiedades del motor **para** detectar fallos que los ejemplos fijos podrían pasar por alto.

**Criterios de aceptación:**
- Hypothesis genera alternativas válidas y comprueba que las mismas entradas dan las mismas explicaciones y reglas ganadoras.
- Las regiones booleanas de presupuesto, ahorro, distancia, tiempo y disponibilidad son mutuamente excluyentes.
- Una regla crítica activada jamás permite una conclusión favorable.
- Reordenar las reglas no altera el dictamen ni la ganadora; aumentar distancia no mejora el índice, y aumentar ahorro no lo empeora.
- La suite verifica los umbrales R01/R02 y el round-trip JSON.
- Hypothesis solo se instala en el entorno de desarrollo/CI, no en Render ni Streamlit.

**Pruebas:** `tests/test_property_invariants.py`.

## HU-17 — Verificación de cambios de umbrales y pesos

**Como** mantenedor, **quiero** comprobar dos commits distintos sobre exactamente los mismos hechos **para** detectar cambios peligrosos aunque no se haya editado `rules.json`.

**Aceptación:** 3441 escenarios entre clases y fronteras, importaciones de dos worktrees aislados, detección de pérdidas R01–R05, degradaciones de seguridad, saltos de índice mayores de 10 puntos y contrato inalterado. Los cambios menores se informan sin bloquearlos. El CI no modifica producción.

## HU-18 — Pruebas de integración por contrato Laravel

**Como** integrador, **quiero** validar solicitudes con el formato real de `construirPayload` **para** anticipar incompatibilidades de Laravel antes de desplegar.

**Aceptación:** fixtures sintéticos vinculados a un commit de `develop`, 14/16 campos, correlación `request_id`, respuestas por regla, errores 422, encabezado `X-API-Key` y ejecución HTTP ASGI sin redes ni modificaciones de Steven.

## HU-19 — Benchmarks reproducibles de inferencia

**Como** desarrollador, **quiero** ver latencia y memoria del motor después del calentamiento **para** tener un punto de referencia y detectar pérdidas de eficiencia.

**Aceptación:** script que realiza 300 iteraciones de prueba local en CI, mediana y p95 en milisegundos, throughput, memoria asignada observada por `tracemalloc`, sin pings a Render ni límites inestables impuestos al runner.

**Evidencia y límites:** [guía de HU-17–HU-19](regresiones-integracion-benchmark.md).

## Historias propuestas para otras iteraciones

**Pendientes posibles:** ampliar escenarios de frontera cuando se modifiquen los clasificadores; coordinar pruebas ejecutando Laravel en un entorno de integración autorizado.

### Definición de terminado

Una historia se considera terminada cuando tiene implementación acotada, pruebas automáticas verdes, contratos documentados y una comprobación funcional en Streamlit cuando modifica la interfaz. Estar propuesta o documentada no equivale a estar implementada.


## HU-20 y HU-21 — Protección de la inferencia y compatibilidad con Laravel

Como propietario del servicio Python, quiero rechazar entradas que produzcan valores derivados no finitos y detectar cambios de los 14 hechos de entrada, para entregar recomendaciones consistentes sin asumir responsabilidades del ETL y del optimizador Laravel.

**Criterios de aceptación:** `POST /api/v1/recommend` conserva 14 campos de entrada y 16 de salida, rechaza desbordamientos con 422, usa la API key en producción con fallo seguro ante secreto ausente y expone `/ready` sin abrir conexión permanente. La CI lee el código de `develop` y compara los nombres de campo, endpoint y cabecera sin escribir en el repositorio del compañero. Las pruebas de integración siguen siendo sintéticas; se exige coordinación manual para desplegar los secretos.

**Evidencia:** `tests/test_operational_contract_hardening.py`, `scripts/check_laravel_contract.py` y `docs/contrato-integracion-develop-2026-11-03.md`.


## HU-22 — Huella verificable del conocimiento aplicado

Como integrador, quiero saber qué definiciones de reglas generaron una recomendación sin introducir campos JSON nuevos ni depender de Laravel, para facilitar la trazabilidad después de desplegar cambios.

**Criterios de aceptación:** el servicio calcula un SHA-256 estable sobre la representación JSON canónica de las reglas validadas (independiente del orden y de los espacios del archivo). `POST /api/v1/recommend`, `GET /api/v1/knowledge` y `GET /ready` exponen el mismo valor en la cabecera `X-Expert-Rules-SHA256`; las respuestas JSON conservan los 14 campos de entrada y 16 de salida de la recomendación. El valor se cachea por proceso y no genera llamadas remotas ni procesos residentes. Los fallos de carga de reglas devuelven un 503 controlado sin revelar rutas internas.

**Evidencia:** `tests/test_rules_fingerprint.py` y [huella y pruebas](hu22-huella-reglas.md).


## HU-23 — Seguridad de la API del sistema experto

Como responsable del servicio de inferencia, quiero verificar la identidad de la aplicación Laravel mediante `X-API-Key` y evitar que respuestas sean cacheadas, para mantener un canal entre servidores sin gestionar usuarios ni permisos de negocio.

**Criterios de aceptación:** todas las rutas `/api/v1/*` devuelven HTTP 401 cuando falta una clave válida y el ambiente está protegido. Un ambiente explícito distinto de `local/dev/development/test/testing` sin secreto principal devuelve 503 y no queda abierto por un error tipográfico del nombre. `SMARTMARKET_API_KEY_PREVIOUS` es opcional y solo funciona si está configurado el secreto principal; al eliminarla, la antigua clave deja de funcionar. Se conservan `/health` y `/ready` públicos, el contrato JSON de inferencia y la disponibilidad de la demostración local. Las respuestas API incluyen `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` y `Vary: X-API-Key`. La documentación interactiva queda desactivada cuando la aplicación arranca con un ambiente protegido.

**Límite:** la API key valida la **aplicación llamante**, no la sesión del usuario; corresponde a Laravel proteger listas de compra y credenciales de sus usuarios. La demo pública Streamlit no se vuelve privada por proteger FastAPI. El despliegue productivo requiere `SMARTMARKET_ENV`, `SMARTMARKET_API_KEY` y `EXPERT_SYSTEM_API_KEY` coordinados antes de declararse protegido.

**Evidencia:** `tests/test_api_security_boundaries.py` y [guía de seguridad HU-23](seguridad-api-hu23.md). No se modifica `develop` del compañero.


## HU-24 — Inferencia por lotes sin optimización económica

Como cliente de la API del sistema experto, quiero enviar varias alternativas válidas en una sola solicitud, para reducir la cantidad de llamadas de red, conservar los resultados individuales y permitir que Laravel integre esta alternativa cuando la necesite.

**Criterios de aceptación:** `POST /api/v1/recommend/batch` acepta 1–50 objetos del mismo `RecommendationRequest`, con `request_id` únicos y `extra=forbid`. Devuelve `resultados` en el orden original; cada elemento debe ser igual a la respuesta del endpoint individual de 16 campos. La ruta aplica `X-API-Key` y cabeceras de seguridad y mantiene `X-Expert-Rules-SHA256`. Ante un elemento inválido o un lote demasiado grande, rechaza toda la entrada con 422, sin escrituras o resultados parciales. El cliente Laravel no necesita cambiar para seguir llamando a `POST /api/v1/recommend`.

**Fuera de alcance:** elegir la mejor opción, sumar costos, obtener precios, ordenar resultados por conveniencia comercial y cambios en `develop`.

**Evidencia:** `tests/test_batch_recommendation.py` y [contrato del endpoint por lotes](inferencia-lotes-hu24.md).


## HU-25 — Coherencia de dictamen y explicación

Como responsable del servicio Python, quiero detectar incoherencias entre hechos derivados, trazas de condiciones, resolución de conflictos, respuesta textual y el índice, para evitar recomendaciones contradictorias aunque cada componente individual responda correctamente.

**Aceptación:** pruebas con los escenarios documentados, 200 combinaciones representativas y casos R01–R11 con/sin ganador. La auditoría independiente `scripts/check_inference_consistency.py` detecta alteraciones provocadas en `winning_rule`, `losing_rules`, `reglas_activadas`, `trace`, `nivel_recomendacion`, `accion_sugerida`, `explicacion`, hechos e índice. No se introduce validación redundante dentro del camino HTTP ni se cambian las reglas o los 14/16 campos del contrato.

**Evidencia:** [HU-25 y límites](hu25-coherencia-inferencia.md), `tests/test_inference_consistency.py`.


## HU-26 — Auditoría y protección del servidor gratuito

Como responsable del motor, quiero impedir que el servidor Render quede anónimo por una variable faltante, separar la credencial de Streamlit y rechazar cargas HTTP excesivas, para reducir exposiciones accidentales y consumo innecesario de memoria.

**Aceptación:** al detectar `RENDER=true` se rechazan peticiones sin `SMARTMARKET_API_KEY` aun si `SMARTMARKET_ENV` no está configurada; opcionalmente se acepta `SMARTMARKET_API_KEY_STREAMLIT` y se puede revocar sin invalidar la principal; los cuerpos HTTP mayores de 512 KiB generan 413 antes de parsear JSON. La CI examina dependencias instaladas con `pip-audit`. Se ofrece un verificador externo de cuatro GET sin secretos, sin falsamente declarar el hosting revisado cuando no haya conexión.

**Evidencia:** `tests/test_security_hardening_hu26.py`, `tests/test_security_external_probe.py`, `.github/workflows/python-security-audit.yml` y [auditoría HU-26](auditoria-seguridad-hu26.md).


## HU-27 — Protección ligera de recursos para Streamlit público

Como responsable del servicio Python, quiero una cuota por minuto para el consumidor Streamlit, para evitar consumo accidental excesivo en Render gratuito sin afectar las peticiones legítimas de Laravel.

**Aceptación:** si Streamlit usa un secreto distinto del principal, solo ese consumidor tiene un límite local por minuto (60 por defecto, ajustable de 1 a 600), sin timers ni tareas residentes. Al alcanzar el límite devuelve HTTP 429 con `Retry-After`. El servidor permite automáticamente nuevas peticiones al expirar la ventana. Las claves Laravel y de rotación siguen operativas. Una configuración de cuota inválida no desactiva la protección; si las dos claves son iguales, no se limita el token compartido para no castigar a Laravel. El código, las pruebas y el README explican que se requiere activar la clave independiente en Render y Streamlit Cloud.

**Evidencia:** `tests/test_streamlit_rate_limit.py` y [HU-27 — límites y configuración](hu27-proteccion-demo-publica.md).


## HU-28 — Nuevas reglas de cobertura y compra equilibrada

Como consumidor de recomendaciones Python, quiero rechazar alternativas sin stock o con menos del 50 % de cobertura, y reconocer compras completas y económicas sin promociones dentro de un recorrido razonable. Así las reglas dejan de considerar «excelente» una tienda prácticamente vacía y no requieren promociones para reconocer una compra viable.

**Aceptación:** R09 y R10 activan conclusiones críticas distintas para cero disponibilidad y 1–49 %; R11 devuelve `BUENA` con todos los productos, presupuesto respetado, una parada, ahorro ≥3, distancia adicional ≤5 km y tiempo ≤30 min, sin promociones. R08 deja de presentar una activación favorable si faltan esenciales. Se conserva el contrato HTTP 14/16 campos; `RULES_VERSION` sube a `1.1.0` pero `CONTRACT_VERSION` se mantiene en `1.0.0`. Escenarios nuevos separados para no exceder los límites HTTP de diez alternativas.

**Evidencia:** `tests/test_new_rule_cases_hu28.py`, `data/scenarios_hu28.json`, comparación de reglas en CI y [documentación de HU-28](hu28-ampliacion-reglas.md).


## HU-29 — Cobertura responsable de la lista

Como responsable del sistema experto, quiero evitar dictámenes EXCELENTE cuando la disponibilidad total es insuficiente y no hay esenciales declarados, y distinguir una alternativa parcialmente completa cuando sí están cubiertos, para entregar conclusiones prudentes con los 14 hechos actuales.

**Criterios de aceptación:** agregar R12 (sin esenciales y cobertura inferior al 80 %, crítica) y R13 (esenciales completos, cobertura inferior al 80 %, presupuesto y traslado razonables, BUENA), probar la frontera 80 %, mantener las reglas críticas prioritarias, conservar el contrato 14/16 y ampliar la cobertura de Streamlit a trece reglas en lotes permitidos.

**Evidencia:** `tests/test_coverage_guards_hu29.py`, `data/scenarios_hu29.json` y [documentación HU-29](hu29-cobertura-reglas.md). El umbral es una decisión del prototipo, no un dato estadístico; las reglas requieren contraste con compras reales.


## HU-30 — Puntuación ponderada que influye en decisiones justificables

Como responsable del motor, quiero que los cinco pesos explícitos de ahorro, disponibilidad, distancia, tiempo y promociones tengan efectos reales en escenarios de compra que antes quedaban provisionales, sin permitir que un índice alto oculte el incumplimiento de reglas críticas.

**Criterios de aceptación:** R14 reconoce compras completas con ahorro alto y conveniencia ponderada alta (≥75), R15 considera compras completas con poco ahorro si el balance es al menos 50, y R16 permite compras con todos los esenciales y cobertura de al menos 80 % si su índice alcanza 60, siempre bajo restricciones concretas de presupuesto, parada, recorrido y promociones. Pruebas comparan pares de escenarios con diferentes índices pero las mismas condiciones de negocio relevantes y comprueban que las protecciones críticas continúen ganando. La matriz Streamlit cubre R01–R16 en dos peticiones HTTP con 9 y 8 escenarios, sin cambiar el contrato de 14/16 campos.

**Evidencia:** `tests/test_weighted_rules_hu30.py`, `data/scenarios_hu30.json` y [HU-30 — políticas, pesos y límites](hu30-reglas-ponderadas.md). Los pesos son del prototipo y todavía necesitan calibración con compras reales; las nuevas reglas no convierten el índice en una probabilidad.


## HU-31 — Calibración segura de ponderaciones y trazabilidad

Como responsable de inferencia quiero comparar cinco perfiles explícitos de ponderaciones en el mismo motor que usa FastAPI, usando escenarios reproducibles, para saber qué dictámenes se ven afectados y proteger la base de reglas sin adoptar por error pesos no validados comercialmente.

**Criterios de aceptación:** los cinco perfiles suman 100 %, los valores NaN/infinitos se rechazan, el perfil actual reproduce exactamente la salida de `run_inference`, las 17 demostraciones y una rejilla adicional de 3404 ejemplos se ejecutan con perfil aislado, el reporte compara niveles/reglas/índices y bloquea pérdidas críticas, R16 usa el índice sin redondear, las pruebas y la CI validan estabilidad, y los 14/16 campos de Laravel no cambian. Sin escribir `rules.json`, secretos ni código del compañero.

**Evidencia:** `scripts/calibrate_convenience_weights.py`, `tests/test_calibration_hu31.py`, paso de CI y [metodología HU-31](hu31-calibracion-pesos.md). Los resultados son de sensibilidad sintética, no exactitud comercial.
