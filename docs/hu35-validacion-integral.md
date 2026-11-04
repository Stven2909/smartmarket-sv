# HU-35 — Validación integral y matriz de aceptación del sistema experto

## Objetivo

Verificar si el servicio experto SmartMarket SV responde de manera
**consistente con criterios de aceptación explícitos**, incluyendo situaciones
favorables, riesgos críticos, reglas en conflicto y fronteras numéricas.
No cambiar el motor para hacerlo coincidir artificialmente con resultados
comerciales aún no acordados.

**Entregables:** `data/scenarios_hu35.json` (oráculos esperados revisables),
`scripts/validate_recommendation_matrix.py` (auditoría desconectada de la
red), `tests/test_acceptance_matrix_hu35.py` (HTTP y paridad entre solicitudes)
y un control obligatorio en la CI.

## Qué se verifica realmente

El conjunto combina **17 escenarios históricos** con **32 casos nuevos**
construidos manualmente:

| Grupo | Interpretación y ejemplos |
|---|---|
| Referencia | Se demuestra que R01 a R16 ganan al menos una vez; hay también un caso sin regla |
| Contradicción | Dos o más reglas activas, veto crítico frente a promoción, seis críticos simultáneos |
| Frontera | Presupuesto exactamente 10 %, ahorro 3/10, distancia 2/8 km, tiempo 20/45 min, cobertura 49/50/80 % |
| Ponderación | R14 en torno a 75 puntos y R16 en torno a 60; no confundir puntuación mostrada y umbral real |
| Incertidumbre | Cero esenciales definidos aunque el sistema reciba 100 % u 80 % de lista |
| Advertencia | Promociones o dos supermercados a 100 km adicionales/200 minutos; excelente con opcionales pendientes |
| Provisional | Ausencia de regla ganadora; `NO_RECOMENDABLE` no significa automáticamente un veto crítico |
| Crítico | Esenciales faltantes, stock cero, cobertura muy baja, viaje desfavorable con ahorro bajo |

Aparte hay **8 entradas intencionalmente inválidas** para comprobar
rechazo: presupuesto cero o ausente, cantidades imposibles, esenciales
inconsistentes, campo no esperado, cero supermercados e identificador vacío.

Los resultados esperados del archivo JSON son **independientes de lo que
el motor produzca en ejecución**. Cada caso declara `winner`,
`level` y, cuando importa, reglas que deben activarse, hechos booleanos
en la frontera y advertencias esperadas. Si alguien cambia la regla, su
prioridad o su clasificador, la CI bloquea el desacuerdo en lugar de
regenerar silenciosamente el resultado esperado.

## Ejemplos representativos

| Caso | Ganadora esperada | Nivel | Motivo |
|---|---|---|---|
| Compra ideal y cercana | R06 | EXCELENTE | Esenciales y trayecto satisfacen condiciones |
| Presupuesto 10 % excedido exacto | Ninguna | NO_RECOMENDABLE provisional | R01 exige más de 10 % |
| Presupuesto 10 % excedido y un centavo | R01 | NO_RECOMENDABLE crítico | R01 prevalece |
| Seis reglas críticas simultáneas | R01 | NO_RECOMENDABLE crítico | Prioridad 1 precede prioridades 2–4 |
| Cobertura 49 % con esenciales completos | R10 | NO_RECOMENDABLE crítico | Menor del 50 % |
| Cobertura 50 % y esenciales completos | R13 | BUENA | La frontera excluye R10 pero hay opcionales faltantes |
| Cobertura 80 % y esenciales completos | R06 | EXCELENTE con aviso | R13 exige cobertura menor del 80 % |
| Distancia 7.99 km + ahorro 2.99 | R15 | BUENA | R03 comienza a partir de 8 km, se exige índice suficiente |
| Distancia 8 km + ahorro 2.99 | R03 | NO_RECOMENDABLE | Prevalece veto crítico |
| Promoción con distancia 8 km + ahorro 2.99 | R03 | NO_RECOMENDABLE | Una promoción no evita el veto |
| Promoción con distancia 100 km/200 min y ahorro 11 | R07 | BUENA con avisos | Falta política comercial sobre costo neto |
| Sin esenciales definidos, lista al 70 % | R12 | NO_RECOMENDABLE | Protección de cobertura inferior al 80 % |
| Sin esenciales definidos, lista al 100 % | R06 | EXCELENTE con aviso | No se ha confirmado clasificación de esenciales |
| R14 14.499 de ahorro, recorrido moderado | Ninguna | NO_RECOMENDABLE provisional | El índice real queda justo debajo de 75 |
| R14 14.5 de ahorro, recorrido moderado | R14 | BUENA | El índice real alcanza 75 |

Todos son resultados **según las reglas actuales**, no declaraciones
universales sobre qué debería comprar una persona. Los casos de
`NO_RECOMENDABLE` sin regla son provisionales, a diferencia de
los que tienen `winning_rule` crítico.

## Controles automáticos

La auditoría valida:

1. Concordancia exacta con las respuestas esperadas manualmente.
2. Activación de condiciones de reglas según los hechos, traza
   completa, prioridad de conflictos y coherencia de la explicación
   (usa la verificación independiente HU-25).
3. Protección de las ocho reglas críticas ante cualquier
   otra regla positiva activada.
4. Advertencias esperadas de HU-33/HU-34 y que sus mensajes aparezcan
   en la explicación sin alterar el dictamen.
5. Cobertura de **16/16 reglas ganadoras** y rechazo de los 8
   payloads incorrectos por el esquema.
6. En tests HTTP locales, igualdad exacta entre
   `POST /api/v1/recommend`, `POST /api/v1/recommend/batch` y
   `recommend()` sin servidor externo; compatibilidad del JSON
   de 14 entradas y 16 campos superiores de respuesta, huella de
   reglas y cabeceras anti-caché.
7. Rechazo de una matriz alterada, un resultado esperado equivocado
   y una advertencia comercial eliminada, sin depender de datos reales.

### Reproducir

```bash
python -m scripts.validate_recommendation_matrix
python -m scripts.validate_recommendation_matrix --json-output hu35-evidencia.json
pytest -q tests/test_acceptance_matrix_hu35.py
pytest -q
```

En GitHub Actions la misma auditoría se ejecuta tras las puertas
HU-14/HU-17, calibración HU-31 y auditoría HU-33. Su resumen contiene
casos por grupo, victorias por regla y violaciones. Salida distinta de
cero bloquea el cambio. La auditoría no crea tareas residentes ni
requiere internet, credenciales ni datos de usuarios.

## Revisión y mantenimiento

La matriz es una especificación académica de la política **actual**, no
una medición de precisión. Si se aprueba comercialmente otra regla o un
umbral, habrá que justificar el criterio con ejemplos antes de modificar
`data/rules.json`; actualizar los casos afectados con revisión explícita
y mantener el historial de cambios en la PR correspondiente. No
regenerar los oráculos desde el comportamiento que se está evaluando.

El motor conserva los pesos 35/25/20/15/5, las 16 reglas, el contrato
Laravel 14/16 y `develop` intactos. Las incidencias HU-33/34 siguen
abiertas para determinar el **costo neto de traslados** y el significado
operativo de **cero esenciales declarados**.

## Límites y exposición

Una CI satisfactoria demuestra consistencia, cobertura por escenarios
y cumplimiento de un contrato. **No demuestra que los consumidores
reales prefieran estas recomendaciones**, ni que existan descuentos
efectivos, ni que las distancias y ahorros representen compras reales.
No está demostrado el despliegue de este commit en Render o Streamlit;
esta validación es local y en GitHub Actions.
