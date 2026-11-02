# HU-17 a HU-19: regresiones entre commits, integración Laravel y rendimiento

## HU-17 — Comparar el código realmente ejecutado

La antigua puerta de calidad de `data/rules.json` revisaba las reglas pero no probaba el código anterior de clasificación. El nuevo paso **Gate - Code behavior regression on pull requests** resuelve esto ejecutando el mismo conjunto de entradas en **dos procesos Python aislados**:

1. La rama candidata genera 9 escenarios documentados, 2430 clases sintéticas y 30 casos próximos a los umbrales fijos publicados: **2469 casos**.
2. El CI calcula un snapshot con el código del Pull Request.
3. Git extrae el commit base real en un `worktree` temporal. Un proceso independiente importa las bibliotecas de ese worktree y calcula otro snapshot sobre **exactamente los mismos hechos**.
4. Se comparan nivel, regla ganadora, reglas activadas e índice de conveniencia.

La ejecución se activa automáticamente en los PR que modifican `app/expert_system/`, `app/services/recommendation_service.py`, `app/schemas/recommendation.py` o `data/rules.json`. Las funciones `generate`, `snapshot` y `compare` de `scripts/behavior_guard.py` no necesitan Internet, credenciales, Render ni Streamlit.

**El CI falla** si una regla crítica R01–R05 pierde activación, una alternativa rechazada por esas reglas pasa a un nivel favorable, cambia el contrato de 14/16 campos, o el índice auxiliar sufre una variación superior a **10 puntos** en cualquier caso analizado. Los cambios menores se muestran pero no se bloquean automáticamente. La política de diez puntos es una salvaguarda de revisión, **no un umbral establecido científicamente** y puede revisarse con justificación.

El control antiguo HU-14 sigue disponible para duplicados, sombras y contradicciones en `rules.json`. Para impedir la fusión de un PR de CI fallido, hay que configurar la protección de rama `main` para exigir el check `CI / test`.

**Limitación:** 2469 casos acotados no demuestran equivalencia universal; tampoco sustituyen las pruebas automáticas de propiedades o las mediciones con usuarios. Las modificaciones de versiones históricas de Python o Pydantic que impidan importar el snapshot base se tratan como errores de CI, no se ignoran.

## HU-18 — Contrato de integración sin escribir en `develop`

Se revisaron estos archivos de `Stven2909/smartmarket-sv` en el commit de `develop` `513946f7de5028fc65773ddca6888b03fd249381`:

- `backend-laravel/app/Services/Optimization/OptimizationService.php` — `construirPayload` prepara exactamente los catorce hechos del contrato Python, formando `request_id` como `lista-{id}-sucursal-{id}` y `alternativa_id` como `sucursal-{id}`. Cada alternativa física se evalúa por separado; online y otros casos con distancia/tiempo desconocidos pueden omitirse.
- `backend-laravel/app/Services/ExpertSystemService.php` — envía cada payload a `POST /api/v1/recommend` y correlaciona la respuesta mediante `request_id`. Utiliza `X-API-Key` solo si está configurada.
- `backend-laravel/config/services.php` — configura la URL, reintentos y timeout de la integración.

`tests/fixtures/laravel_expert_payloads.json` contiene ejemplos **sintéticos** que reproducen el formato PHP; no se extraen datos reales de compras. `tests/test_laravel_contract_fixture.py` ejecuta FastAPI **en memoria** (ASGITransport) para verificar niveles de decisión, IDs, ocho trazas, seguridad y 422 ante hechos inválidos. Se comprueba explícitamente que los campos de recomendación sigan siendo **14 de entrada y 16 de salida**.

**No se ha probado Laravel ejecutándose contra Render en producción** ni se ha modificado `develop`. Los fixtures quedan vinculados a un commit revisado: cualquier modificación posterior de Steven requerirá volver a contrastarlos.

**Observación de integración:** actualmente Laravel tiene `EXPERT_SYSTEM_TIMEOUT` configurable con un valor por defecto de **15 segundos** en `config/services.php`, mientras que Streamlit concede 90 segundos para un posible arranque en frío. Si Render gratuito tarda más de 15 segundos en despertar, Laravel podría declarar la integración no disponible, incluso si el motor funciona. La decisión de ajustar ese tiempo corresponde al propietario de Laravel, no a la API Python.

## HU-19 — Benchmark ligero, sin servicios remotos

`scripts/benchmark_inference.py` mide únicamente la función `recommend` localmente tras calentar las reglas. Reporta:

- Mediana de tiempo de inferencia (ms).
- Percentil 95 y máximo (ms).
- Iteraciones por segundo.
- Pico de asignaciones observado por `tracemalloc` (KiB).

CI ejecuta **300 iteraciones** sin tráfico HTTP. Para mediciones locales repetidas:

```bash
python -m scripts.benchmark_inference --iterations 1000 --json-output benchmark.json
```

No se impone en CI un límite rígido de milisegundos: las máquinas hospedadas pueden tener rendimientos distintos y producir fallas espurias. El benchmark falla si la inferencia presenta errores o datos inválidos. `tracemalloc` agrega sobrecarga y no equivale a memoria RSS total; no mide Render, arranque en frío, red, disco ni latencia HTTP. Las cifras de CI son referencias técnicas, no garantías de desempeño.

## Verificación

```bash
python -m pip install -r requirements-dev.txt ruff
ruff check app demo scripts tests
python -m pytest -q tests/test_behavior_guard.py
python -m pytest -q tests/test_laravel_contract_fixture.py
python -m pytest -q tests/test_benchmark_inference.py
python -m pytest -q
```

No se añaden APIs, servicios residentes, pings de keep-alive, escritura en reglas ni procesos adicionales en Render. Toda la lógica es de prueba y observabilidad en desarrollo y GitHub Actions.
