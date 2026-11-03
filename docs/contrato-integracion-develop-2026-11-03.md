# HU-20 y HU-21 — Contrato fiable del sistema experto (solo Python)

Actualizado: 2026-11-03. Referencia de lectura para Laravel: `Stven2909/smartmarket-sv:develop`, commit `1cc886ad45a0bfbac156717ffc7ff6e10fbd716d`.

## Responsabilidades y límite de integración

- **Laravel / React (del compañero)** calculan costo, disponibilidad, distancia, tiempo, promociones, la mejor opción y la presentación. Laravel decide cuáles alternativas tienen datos suficientes para enviarlas.
- **Nuestro Python / FastAPI** recibe **exactamente 14 hechos** por alternativa, los valida, ejecuta las reglas, devuelve `RecommendationResponse` con 16 propiedades y explica la decisión en `/api/v1/chat`.
- Python **no extrae precios, no lee la base de datos de Laravel y no cambia el ranking económico de Laravel**. Ninguna tarea de este paquete modifica `develop`.

La estructura de `POST /api/v1/recommend` y sus respuestas normales se conserva. Un `request_id` válido se devuelve sin modificaciones.

## HU-20 — Robustez, disposición y seguridad

1. El contrato rechaza `request_id` y `alternativa_id` de más de 256 caracteres, conservando su formato libre actual.
2. Se rechazan con HTTP 422 los números finitos extremos cuya aritmética intermedia (`porcentaje_exceso_presupuesto` o `diferencia_presupuesto`) se desborda. No se impusieron umbrales monetarios arbitrarios ni se cambia el dictamen para entradas normales.
3. `GET /health` sigue siendo una comprobación ligera y pública de proceso. `GET /ready` comprueba que la base de reglas puede cargarse; si no es posible, devuelve 503 con mensaje genérico, sin filtrar rutas internas.
4. `SMARTMARKET_ENV=production` o `prod` **exige** que exista `SMARTMARKET_API_KEY`. Si se omite, las rutas de inferencia devuelven HTTP 503; si hay clave, requieren `X-API-Key` y devuelven 401 ante cabecera ausente o errónea. En desarrollo sin `SMARTMARKET_ENV` y sin clave se conserva el comportamiento anterior para facilitar pruebas.

### Despliegue coordinado (acción manual)

En Render del servicio Python configurar:

```text
SMARTMARKET_ENV=production
SMARTMARKET_API_KEY=<clave-secreta-fuerte>
```

En Laravel, **antes de activar la protección**, el responsable debe configurar `EXPERT_SYSTEM_API_KEY` con **la misma clave**, más `EXPERT_SYSTEM_URL`. No guardar claves en Git ni en archivos `.env.example`. El valor de `SMARTMARKET_ENV` no se establece automáticamente en entornos ya desplegados por esta modificación: hay que configurarlo en el hosting. Probar primero en ambiente de integración: HTTP 200 con encabezado correcto, 401 sin él, 503 si falta la clave en producción.

## HU-21 — Contrato Laravel leído sin escrituras

`scripts/check_laravel_contract.py` obtiene **solo el código fuente público** de dos archivos de `develop` mediante HTTPS:

- `backend-laravel/app/Services/Optimization/OptimizationService.php`
- `backend-laravel/app/Services/ExpertSystemService.php`

El verificador extrae los nombres declarados en el array de retorno de `construirPayload` y los compara con los 14 campos de `RecommendationRequest`. Además exige que el cliente use `/api/v1/recommend`, el envío por POST de `$payload`, la correlación mediante `request_id` y `X-API-Key`.

Se ejecuta al revisar el proyecto:

```bash
python -m scripts.check_laravel_contract --upstream
```

Si se tiene una copia local del código del compañero:

```bash
python -m scripts.check_laravel_contract \
  --producer-file ruta/OptimizationService.php \
  --client-file ruta/ExpertSystemService.php
```

GitHub Actions ejecuta el modo `--upstream` después de nuestras pruebas. Si `develop` cambia un campo, el paso falla y obliga a revisar el contrato antes de integrar cambios; esto **no escribe en su repositorio**.

**Límites de la comprobación:** es una verificación estática de claves, ruta HTTP y encabezado. No demuestra que Laravel se ejecute, que los números reflejen compras reales, que las respuestas se correlacionen bien en producción ni que los nombres de productos sean correctos. Esas pruebas deben hacerse con el compañero en un ambiente de integración. Las pruebas `tests/test_laravel_contract_fixture.py` continúan usando payloads sintéticos y quedan trazadas al commit consultado, nunca a ventas reales.

## Criterios para aprobar el cambio

- `pytest -q` y `ruff check app demo scripts tests` terminan sin errores.
- Las pruebas nuevas verifican 422 ante números extremos, 503 sin clave en producción, 401 ante clave incorrecta, 200 para payload correcto y estado `/ready`.
- El verificador detecta cambios de campos, endpoint y cabecera sin acceder a cuentas ni escribir en repositorios ajenos.
- Las reglas R01–R08 y la semántica del índice permanecen intactas en los escenarios compatibles.

## Mejoras para el compañero (no son trabajo de Python)

1. Diferenciar subtotales incompletos de una compra completa; no mostrar `mejor_opcion` como viable si faltan esenciales.
2. Hacer que el matching de productos considere marca, presentación, cantidad y unidad; hoy la similitud textual por sí sola puede mezclar variantes.
3. Verificar la estructura de la respuesta Python y que su `request_id` coincida con la alternativa antes de marcarla disponible.
4. Revisar latencias y reintentos HTTP por sucursal, consistencia de las sucursales en línea y vulnerabilidades npm.
5. Configurar el secreto compartido para habilitar la API protegida en producción.

Estas recomendaciones se entregan como observaciones; no se modifican `develop`, frontend ni Laravel desde este fork.
