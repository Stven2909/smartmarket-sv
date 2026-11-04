# HU-28 — Reglas R09–R11 y protección contra recomendaciones incompletas

## Alcance y justificación

Se amplía el motor de **8 a 11 reglas** sin modificar el contrato HTTP de Laravel: se conservan exactamente **14 hechos de entrada** y **16 campos de respuesta**. Los nuevos criterios usan los datos que Laravel ya envía. La clasificación conserva los tres niveles existentes y sigue ejecutándose de manera determinista, con prioridades y traza explicable.

### Nuevas reglas

| Regla | Tipo | Condiciones | Resultado |
|---|---|---|---|
| R09 — Sin productos disponibles | Crítica, prioridad 2 | `productos_disponibles == 0` | `NO_RECOMENDABLE` |
| R10 — Cobertura extremadamente baja | Crítica, prioridad 2 | Al menos un producto disponible, pero `productos_disponibles/productos_totales < 50 %` | `NO_RECOMENDABLE` |
| R11 — Compra completa y equilibrada sin promociones | Favorable, prioridad 7 | Dentro del presupuesto; **todos** los productos disponibles; una parada; distancia adicional ≤ 5 km; tiempo ≤ 30 minutos; ahorro ≥ 3 unidades monetarias; sin promociones | `BUENA` |

**R09 y R10** evitan el caso en que una lista sin ningún producto marcado como esencial parece cumplir automáticamente «todos los esenciales disponibles» aunque no haya productos en el supermercado. **R11** permite recomendar una compra verdaderamente completa y moderada sin obligar al usuario a tener promociones o cumplir simultáneamente las condiciones más estrictas de la excelente R06.

Los límites de **50 %, 5 km, 30 min y 3 unidades de ahorro** son **políticas explícitas para el prototipo**, no resultados de investigación de preferencias de consumidores ni umbrales universales. Conviene revisarlos con casos reales y con el equipo. La diferencia de monedas se mantiene: el motor no convierte monedas ni interpreta cantidades fuera del contrato.

### Corrección R08

R08 (dos supermercados con ahorro alto) ahora también requiere `todos_esenciales_disponibles=true`. Antes podía activarse como una recomendación `BUENA` pese a faltar esenciales, aunque R02 prevaleciera y la conclusión final siguiera siendo negativa. Con el ajuste, también desaparece esa señal favorable inconsistente del diagnóstico.

### Prioridades y explicaciones

- R01–R05 conservan condiciones y prioridad. R09/R10 se agregan a las **reglas críticas** con prioridad 2. Cuando R02 coincide, gana R02 por menor ID.
- R06 (`EXCELENTE`) conserva su lógica anterior. R07 sigue representando promociones verificadas por el backend, y R08 conserva sus demás restricciones.
- R11 se activa solo para compras **completas** y **sin promociones**. R06 conserva prioridad sobre R11 cuando ambas se activan.
- La respuesta muestra los IDs nuevos en `reglas_activadas`, `winning_rule`, `losing_rules` y la `trace`, en el mismo formato de siempre. El índice auxiliar mantiene exactamente los mismos pesos y su interpretación.
- `RULES_VERSION=1.1.0` y `THRESHOLDS_VERSION=1.1.0`; `CONTRACT_VERSION=1.0.0` sigue igual. La cabecera `X-Expert-Rules-SHA256` cambia automáticamente para identificar la base revisada.

## Pruebas y escenarios

Los nueve escenarios históricos de `data/scenarios.json` siguen siendo el conjunto pequeño para los endpoints opcionales de comparación, diagnóstico y exportación (límite de 10 alternativas por solicitud). El caso «sin regla» ahora tiene **un opcional pendiente**, para seguir evaluando el retorno provisional.

Los tres casos nuevos están separados en `data/scenarios_hu28.json`: sin stock, 20 % de cobertura y compra equilibrada sin promoción. **No** se envían los doce en una única solicitud a endpoints que limitan la lista a diez. Se evalúan individualmente por el contrato original.

El auditor de reglas extiende su rejilla representativa de **2430 a 3402 escenarios** para incluir cero productos y cobertura inferior al 50 %. El control de cambios basado en reglas revisa **3411 casos** (3402 de rejilla y nueve clásicos). El control de comportamiento de código incluye las clases y límites adicionales.

Las pruebas comprueban los límites exactos (49 % frente a 50 %, 5 frente a 5.01 km, 30 frente a 30.01 minutos, 3 frente a 2.99 de ahorro), la protección de reglas críticas, el diagnóstico, la independencia de orden y la conservación del contrato.

## Límites y riesgos pendientes

- Esta mejora **no afirma** que exista una mejor alternativa en otro supermercado ni que el descuento justifique el costo de combustible/entrega. El índice de conveniencia es un apoyo, no una probabilidad.
- La regla R11 usa el ahorro absoluto actual porque Laravel lo envía así; no infiere un porcentaje de descuento. Para mejorar la comparabilidad económica es aconsejable acordar **campos opcionales** en una futura versión del contrato, manteniendo la versión 1.0.0 vigente hasta que ambos sistemas migren.
- R05 (tres tiendas) y R08 (dos tiendas) están disponibles para pruebas sintéticas, pero el optimizador actual de Laravel envía normalmente una alternativa física con una sola tienda. No se debe simular una ruta múltiple sin información confirmada.
- No se alteraron el ETL, la normalización de productos, el ranking de Laravel, el frontend React ni `develop` del compañero.

**Próximo trabajo sugerido:** recoger contraejemplos con datos reales, evaluar falsos positivos/negativos por regla, y establecer acuerdos de metadatos opcionales como frescura del precio, costos de entrega, unidades de presentación y promociones comprobadas, antes de inventar más criterios numéricos.
