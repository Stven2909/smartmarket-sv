# ADR-05: Tratamiento del CostoCombustible en el Motor de Optimización

**Estado:** Aceptado (revisado)
**Fecha:** 2026-08-21 (revisión el mismo día tras retroalimentación de equipo — Henry Barrientos)
**Contexto del proyecto:** SmartMarket SV — Fase 4 (DistanceService / OptimizationService)
**Relacionado con:** `02-arquitectura.md`, `04-sistema-experto.md`, regla de proyecto "Nunca inventar datos"

> **Nota de revisión:** la versión original de este ADR (sección 3) proponía dolarizar el combustible usando precios DGEHM citados + un supuesto de consumo declarado. Tras retroalimentación de equipo, se identificó un problema más profundo: `DistanceService` calcula distancia con **Haversine (línea recta)**, no ruta real, lo cual introduce un error sistemático adicional (subestimación típica de 20–40% en trazados urbanos no cuadriculados como San Salvador). Encadenar "distancia aproximada × precio citado × consumo supuesto" produce un número con apariencia de precisión (dólares, dos decimales) que en realidad arrastra tres capas de imprecisión. Se revisa la decisión para el MVP. Ver Sección 3 actualizada.

---

## 1. Contexto

La fórmula del motor de optimización es:

```
Score = α·CostoCompra + β·CostoCombustible + γ·CostoTiempo − δ·BeneficioPromociones
```

`CostoCombustible` fue introducido en **Fase 4** (commits `9cae1a5`, `f4ed8e5`), dentro de `DistanceService`, como parte del cálculo de costo total de ir a comprar a un supermercado determinado. No formaba parte del diseño original del comparador básico.

Actualmente se calcula con dos parámetros estáticos definidos en `config/optimization.php`:

- `km_por_litro`
- `precio_por_litro`

Ninguno de los dos refleja la realidad del usuario:

1. **`precio_por_litro`** no distingue gasolinera, zona del país, ni tipo de combustible (especial, regular, diésel). El precio real varía por gasolinera y por zona.
2. **`km_por_litro`** asume un vehículo genérico. No sabemos si el usuario tiene un vehículo a gasolina o diésel, ni su rendimiento real.
3. Ambos valores están **hardcodeados sin fuente citada**, lo cual entra en conflicto directo con la regla de proyecto de "no inventar datos o afirmaciones no verificables", ya aplicada previamente en los ensayos académicos.

## 2. Problema a resolver

- **Precisión:** el cálculo actual es una aproximación, no un dato real, y puede transmitir una falsa sensación de exactitud si no se etiqueta como tal.
- **Fricción de usuario:** pedirle al usuario que configure marca/modelo de vehículo, tipo de combustible y rendimiento antes de poder usar el comparador va en contra del principio de "entre menos pasos, mejor" del producto.
- **Defendibilidad académica:** en Sistemas Expertos, el motor debe presentarse como reglas transparentes y trazables, no como una caja negra con constantes arbitrarias.

## 3. Decisión (revisada)

**Para el MVP, no se dolariza `CostoCombustible`.** No se muestra al usuario una cifra en dólares de gasto de combustible, porque no se puede sostener con datos suficientemente confiables (ruta real desconocida, tipo de vehículo desconocido). Mostrar un número falso con apariencia de precisión es peor que no mostrarlo.

**Pero la distancia sí se conserva como factor del score**, de forma no monetizada. El trabajo de Fase 4 (`DistanceService`, cálculo Haversine) no se descarta — se usa como señal relativa de "qué tan lejos está este supermercado", no como costo en dólares.

### 3.1 Cambio en la fórmula del score

```
Score = α·CostoCompra + β·PenalizacionDistancia + γ·CostoTiempo − δ·BeneficioPromociones
```

- `CostoCombustible` (en $) se **retira** de la fórmula y de la UI para el MVP.
- Se introduce `PenalizacionDistancia`: una penalización relativa basada en la distancia Haversine ya calculada por `DistanceService`, normalizada (ej. 0–1 o 0–100) contra el resto de opciones evaluadas en esa comparación. No pretende ser un costo real, solo un criterio de desempate/orden.
- `β` se recalibra para este nuevo término (más bajo que `α`, mismo criterio que antes: el término menos verificable no domina la decisión).

### 3.2 UI

- Se elimina la línea "Combustible (estimado): $Y.YY" del desglose de resultado.
- Se puede mostrar distancia en km (dato objetivo que si tienen, vía Haversine) sin convertirla a dólares: *"Este supermercado está a ~3.2 km"*. Eso es informativo y no inventa nada.
- El desglose queda:

```
Costo productos:  $X.XX
Distancia:        ~3.2 km
Tiempo estimado:  $Z.ZZ
```

### 3.3 Ya no aplica la fricción de "configurar vehículo"

Al no dolarizar combustible, no hay necesidad de pedir tipo de vehículo, rendimiento, ni tipo de combustible en el MVP. Se elimina esa pantalla de "Parámetros de ahorro" del alcance actual.

### 3.4 Roadmap — v2 / feature premium

Dolarizar combustible con precisión real queda condicionado a integrar **Google Maps Distance Matrix API / Routes API** (ruta real conducida, no línea recta), que sí puede dar distancia y tiempo de viaje reales. Esto se documenta como funcionalidad candidata a versión de pago (Google Maps API tiene costo por uso, y calibrar tipo de vehículo/consumo del usuario es trabajo adicional de producto), consistente con el modelo de negocio de Emprendedurismo — no se implementa ahora.

Cuando se aborde en v2, retomar de esta misma ADR: fuente DGEHM para precio por litro (Sección 3.1 de la versión original, conservada en el historial de este archivo/git) y el criterio de declarar supuestos de consumo explícitamente si Maps no provee esa granularidad.

## 4. Justificación

Esta decisión respeta las reglas ya establecidas para el proyecto:

1. **"Nunca inventar datos"** → se retira la cifra en dólares que dependía de tres capas de estimación (Haversine + precio + consumo). Se conserva solo el dato que sí es directamente calculable (distancia).
2. **"Entre menos pasos para el usuario, mejor"** → al no dolarizar combustible, desaparece la necesidad de cualquier configuración de vehículo, incluso opcional.
3. **Consistencia entre cursos (Emprendedurismo / Sistemas Expertos)** → el motor sigue siendo "basado en reglas", ahora con un criterio más defendible: no se presentan cifras monetarias que el equipo no puede sostener con datos reales.

## 5. Alternativas descartadas

- **Dolarizar con precio DGEHM + consumo supuesto declarado** (propuesta original de este ADR): descartada porque, aunque el precio tiene fuente, la distancia base (Haversine) ya introduce un error sistemático significativo que invalida la precisión aparente del resultado final en dólares.
- **Mover a nota aclaratoria genérica sin desglose**: descartada, no resuelve el problema de fondo de trazabilidad del dato.
- **Quitar la distancia por completo del score**: descartada — la distancia relativa (no monetizada) sigue siendo información útil y sí es un dato que el sistema puede calcular con confianza razonable vía Haversine; no hay motivo para desperdiciar el trabajo de Fase 4.

## 6. Tareas derivadas (a registrar como issues de GitHub)

- [ ] `OptimizationService`: reemplazar término `CostoCombustible` ($) por `PenalizacionDistancia` (normalizada, sin unidad monetaria).
- [ ] Recalibrar/renombrar peso `β` en `config/optimization.php` para el nuevo término.
- [ ] Eliminar `km_por_litro` y `precio_por_litro` de `config/optimization.php` (o dejarlos comentados con nota de "reservado para v2 — ver ADR-05").
- [ ] `ComparisonService` / `ResultadoOptimizacion`: quitar el campo de combustible en dólares del payload de respuesta; agregar/confirmar campo de distancia en km si no existe ya.
- [ ] Frontend: quitar la línea "Combustible (estimado): $Y.YY" del desglose de resultado; mostrar distancia en km en su lugar.
- [ ] Frontend: eliminar cualquier pantalla/flujo de "Parámetros de ahorro" / configuración de vehículo si ya se había empezado.
- [ ] Revisar `04-sistema-experto.md` y cualquier contrato de API del microservicio Python por si documentan `CostoCombustible` en dólares — actualizar a `PenalizacionDistancia`.
- [ ] Correr suite de tests de Fase 4/5 (`DistanceService`, `OptimizationService`, `ComparisonService`) tras el cambio y confirmar que no truena nada relacionado a comparador ni historial de resultados.
- [ ] (v2 / backlog, no implementar ahora) Evaluar Google Maps Distance Matrix/Routes API para ruta real + dolarización de combustible como feature premium.

## 7. Fuentes

- Dirección General de Energía, Hidrocarburos y Minas (DGEHM) — Precios de Referencia: https://estadisticas.dgehm.gob.sv/combustibles/precios-referencia/ (fuente conservada para uso futuro en v2, ver Sección 3.4).
- Retroalimentación de equipo: Henry Barrientos, 21/8/2026 — observación sobre dependencia de datos de mapas/ruta real y variabilidad de tipos de vehículo.
