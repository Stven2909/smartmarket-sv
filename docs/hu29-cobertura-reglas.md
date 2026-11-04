# HU-29 — Cobertura de la lista y nuevas reglas

R12 (prioridad 2, crítica) rechaza alternativas con menos del 80 % de productos disponibles cuando no hay esenciales definidos. Sin esta regla, la condición `todos_esenciales_disponibles` puede ser verdadera por igualdad 0 = 0 y producir un EXCELENTE engañoso. R13 (prioridad 4) concede BUENA, no EXCELENTE, si todos los esenciales definidos están cubiertos, pero la cobertura total es inferior al 80 %, el presupuesto se respeta y una sola tienda tiene distancia adicional ≤5 km y tiempo ≤30 min.

El umbral 80 % es una **política del prototipo**, no evidencia estadística. Las nuevas reglas se basan exclusivamente en los 14 campos actuales de Laravel, con 16 campos de respuesta sin modificaciones. `RULES_VERSION` y `THRESHOLDS_VERSION` pasan a 1.2.0, mientras que `CONTRACT_VERSION` permanece 1.0.0.

Se añaden escenarios en `data/scenarios_hu29.json`, regresiones en `tests/test_coverage_guards_hu29.py` y una tercera solicitud en la matriz de cobertura de Streamlit (grupos de 9, 3 y 2 escenarios, sin exceder el máximo de 10 por comparación).

## Qué no se debe inventar

Con los 14 hechos existentes no conocemos costos de combustible y reparto, frescura de precios, equivalencias de unidad, vigencia de promociones ni stock real. Estos criterios deben esperar a que Laravel los envíe con un contrato versionado y ejemplos comerciales verificables. El proyecto Python no edita `develop` ni reordena el ranking económico.
