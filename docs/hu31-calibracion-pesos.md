# HU-31 — Calibración experimental y auditoría de sensibilidad de pesos

**Tipo de evidencia:** simulación determinista sobre casos diseñados para probar reglas y una rejilla sintética. **No hay compras etiquetadas por clientes reales**. El análisis identifica sensibilidad y riesgo, **no aprende ni determina automáticamente los pesos óptimos**.

## Pregunta y decisión

¿Cambiar la importancia relativa de ahorro, disponibilidad, distancia, tiempo o promociones modifica el dictamen o solo el índice? ¿Se mantienen las protecciones críticas? La decisión operativa es **conservar la configuración actual** hasta obtener ejemplos con juicio comercial y preferencias verificables.

La calibración usa el **mismo motor que atiende FastAPI** y permite introducir un `ConvenienceConfig` diferente solo en la ejecución interna. No hay endpoints adicionales, modificación de pesos en Render, bases de datos, llamadas de red ni procesos de fondo. `run_inference(request)` sigue usando exactamente el perfil anterior.

## Perfiles contrastados

| Perfil | Ahorro | Disponibilidad | Distancia | Tiempo | Promociones |
|---|---:|---:|---:|---:|---:|
| Actual en producción | 35 % | 25 % | 20 % | 15 % | 5 % |
| Priorizar ahorro | 50 % | 20 % | 15 % | 10 % | 5 % |
| Priorizar disponibilidad | 20 % | 40 % | 20 % | 15 % | 5 % |
| Priorizar movilidad | 20 % | 20 % | 30 % | 25 % | 5 % |
| Priorizar promociones | 25 % | 25 % | 15 % | 15 % | 20 % |

Los pesos suman siempre 100 %. Las configuraciones con `NaN` o infinito se rechazan, igual que referencias de normalización no finitas. Estos cinco perfiles son hipótesis, no personalizaciones aprendidas.

## Cómo reproducirlo

Desde la raíz del repositorio, con las dependencias de desarrollo instaladas:

```bash
# Análisis breve sobre los 17 ejemplos trazables
python -m scripts.calibrate_convenience_weights

# Análisis completo: 17 ejemplos + 3404 combinaciones de prueba
python -m scripts.calibrate_convenience_weights --with-grid

# Guardar evidencia legible por programas
python -m scripts.calibrate_convenience_weights \
  --with-grid --json-output weight-calibration.json

pytest -q tests/test_calibration_hu31.py
```

La CI ejecuta la calibración completa para cada commit y PR y publica una tabla de resultados en el resumen del trabajo. El JSON informa la distribución por nivel y regla, las variaciones de puntuación, los cambios de regla ganadora y nivel, los casos que cambian de favorable a no recomendable y viceversa, y las **violaciones de protecciones críticas**, que bloquean el proceso.

### Cómo interpretar la comparación

- **Cambio de índice:** indica sensibilidad matemática; no implica que la decisión comercial mejore.
- **Cambio de categoría:** cruza 50 o 75 puntos; no equivale automáticamente a una regla activa.
- **Cambio de regla ganadora:** el mismo conjunto de hechos activó una prioridad diferente.
- **Cambio de nivel:** la recomendación final cambia, por ejemplo de provisional a BUENA.
- **Cero violaciones críticas:** ninguna alternativa con una regla crítica activada terminó como favorable; esto es una invariante del motor, no una medición de precisión.

No se deben presentar porcentajes de cambios sobre la rejilla como si fueran tasas de acierto o proporciones de compradores. Hay sesgo deliberado hacia extremos y fronteras. Tampoco conviene elegir el perfil que produce más recomendaciones positivas: eso podría empeorar la calidad de las decisiones.

## Hallazgos de ingeniería

1. Antes de la mejora, la condición de R16 (`conveniencia_solida`) comparaba la puntuación **redondeada a dos decimales**. Un valor real de 59.996 puntos podía mostrarse como 60.00 y disparar una regla que exige al menos 60. Se compara ahora la puntuación original, mientras se mantiene el número redondeado para la presentación.
2. Antes solo el índice auxiliar aceptaba un parámetro `ConvenienceConfig`; las condiciones de reglas seguían utilizando los pesos por defecto. Ahora `derive_facts` y `run_inference_with_rules` reciben opcionalmente la misma configuración. Así el experimento contrasta dictámenes auténticos, no solo cifras alteradas.
3. Se refuerza la validación de los pesos y referencias de normalización con `math.isfinite`.
4. Se comprueba que la ejecución con el perfil `actual` sea idéntica al motor productivo y que los contratos HTTP sigan siendo de **14 campos de entrada y 16 de salida**.

## Despliegue y responsabilidad

Las reglas R01–R16, los cinco pesos predeterminados y la interfaz pública siguen configurados como antes. La corrección del borde de 60 puntos es un cambio semántico puntual, trazado mediante una versión de reglas de parche, sin cambiar `data/rules.json`.

Laravel sigue proporcionando los hechos; Python evalúa y responde. No se consulta ni modifica `develop` del compañero, su ranking económico, las claves de autenticación ni su base de datos.

## Siguiente etapa con datos reales

Para recomendar cambiar los pesos se requiere un conjunto separado de alternativas reales con etiqueta humana (por ejemplo: "la elegiría", "no la elegiría", razones y restricciones), cobertura de precios/fecha y costos adicionales. Después se pueden comparar tasas de acuerdo, errores críticos, estabilidad ante cambios pequeños y robustez por segmentos. No es suficiente ajustar a los mismos 17 escenarios que se utilizaron para diseñar las reglas.
