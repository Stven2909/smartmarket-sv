# HU-30 — Reglas de conveniencia ponderada R14–R16

## Problema que resuelve

Antes de esta fase, el motor calculaba un índice de 0 a 100 con cinco factores y lo presentaba como información secundaria. La selección de la regla ganadora casi nunca utilizaba ese índice, de modo que escenarios diferentes en ahorro, disponibilidad o recorrido podían terminar en el mismo dictamen provisional.

La mejora agrega **tres reglas comerciales específicas**, sin convertir el índice en una autorización universal ni reemplazar las reglas de seguridad de presupuesto y esenciales.

## Pesos vigentes

| Factor | Peso | Normalización |
|---|---:|---|
| Ahorro | 35 % | `min(ahorro / 20, 1)` |
| Productos disponibles | 25 % | `disponibles / total` |
| Distancia adicional | 20 % | `max(0, 1 - distancia_adicional_km / 20)` |
| Tiempo estimado | 15 % | `max(0, 1 - tiempo_estimado_min / 120)` |
| Promociones aplicables | 5 % | 1 cuando existen, 0 en caso contrario |

La suma es 100 %. Las referencias de 20 unidades de ahorro, 20 km y 120 minutos son criterios **del prototipo**. El ahorro se interpreta tal como Laravel lo envía: no es un porcentaje, no descuenta el combustible y no demuestra por sí solo rentabilidad.

## Reglas propuestas

| Regla | Condiciones adicionales a compra dentro del presupuesto y una parada | Resultado |
|---|---|---|
| R14 — Compra completa y alto balance | Todos los productos disponibles, distancia adicional entre 2 y 8 km, tiempo entre 20 y 45 min, ahorro al menos 10 unidades, sin promociones y puntuación **alta (≥75)** | BUENA: considerar ahorro y costo real del viaje |
| R15 — Compra completa con poco ahorro | Compra completa, distancia y tiempo moderados como arriba, ahorro inferior a 3, sin promociones y puntuación **no baja (≥50)** | BUENA: reconocer disponibilidad completa sin fingir gran descuento |
| R16 — Compra casi completa con balance suficiente | Esenciales definidos y cubiertos, faltan opcionales pero cobertura al menos 80 %, distancia adicional ≤5 km, tiempo ≤30 min, ahorro entre 3 y 10 unidades, sin promociones e índice **≥60** | BUENA con advertencia de completar opcionales |

Estos tres umbrales son políticas revisables. En particular, **60 puntos** no es una clasificación independiente: es un nivel intermedio deliberado para evitar que el requisito ponderado de R16 sea redundante dentro de sus condiciones.

Las reglas favorables tienen prioridad 7, por detrás de las protecciones críticas y de R06. R01 (presupuesto muy excedido), R02 (esenciales faltantes), R03/R04 (viaje desfavorable), R05 (fragmentación), R09/R10/R12 (cobertura deficiente) **siempre prevalecen** ante una regla ponderada. El índice alto jamás transforma por sí solo una alternativa en EXCELENTE.

## Contrato, versiones y costos

No cambian las 14 propiedades obligatorias recibidas de Laravel ni las 16 propiedades de respuesta. Se agregan tres hechos derivados booleanos en la traza y respuesta: `conveniencia_alta`, `conveniencia_no_baja` y `conveniencia_solida`. Se mantiene `CONTRACT_VERSION=1.0.0`, y `RULES_VERSION=1.3.0` y `THRESHOLDS_VERSION=1.3.0` identifican la lógica ampliada. El SHA-256 de las reglas cambia para trazabilidad.

Los cálculos se ejecutan localmente con la configuración existente de pesos. No hay bases de datos, llamadas externas, tareas en segundo plano ni procesos para mantener despierto Render.

## Escenarios y pruebas

`data/scenarios_hu30.json` contiene tres ejemplos para mostrar las reglas nuevas. `tests/test_weighted_rules_hu30.py` comprueba que el índice realmente modifica las condiciones de activación, que las reglas críticas dominan y que la auditoría independiente concuerda con las trazas.

En Streamlit, **Base de conocimiento → Evaluar cobertura** agrupa los 17 escenarios históricos y nuevos en **dos peticiones** de comparación (9 + 8), respetando el máximo de diez alternativas de ese endpoint. Las pruebas sobre el contrato de Laravel y la puerta de regresión de reglas se ejecutan en CI antes de fusionar la actualización.

## Límites

Este diseño no debe interpretarse como un modelo de aprendizaje automático entrenado. Los pesos son manuales, configurados para la demostración. No hemos validado con preferencias de consumidores reales que 35 % de ahorro sea siempre el factor principal; hay que calibrar pesos y umbrales con entrevistas, datos confiables y contraejemplos.

No contamos con costos de reparto, combustible, caducidad de descuentos, unidades equivalentes ni inventario actualizado en los 14 hechos. Son mejoras pendientes para una futura integración coordinada; Python no inventa esos datos ni modifica el `develop` del compañero.
