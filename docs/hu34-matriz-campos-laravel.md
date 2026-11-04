# HU-34 — Matriz de campos Laravel, trazabilidad e interpretación de esenciales

**Alcance:** análisis de los 14 hechos de entrada del servicio Python. Los datos
de los ejemplos son sintéticos, no representan clientes reales. El contrato
HTTP conserva **14 entradas / 16 campos superiores de respuesta** y las reglas
siguen siendo **R01–R16**, sin cambios en pesos ni en `data/rules.json`.
`develop` y Laravel son de solo lectura.

## Qué importa para la decisión

Conviene distinguir tres tipos de información:
- **Restricciones y reglas discretas:** presupuesto, cobertura de esenciales,
  distancia adicional, tiempo, cantidad de tiendas, cobertura total y ahorro.
  No necesitan necesariamente un coeficiente adicional.
- **Puntuación auxiliar:** solo ahorro (35 %), disponibilidad de productos
  (25 %), distancia **adicional** (20 %), tiempo (15 %) y existencia de
  promociones (5 %). La puntuación no invalida reglas críticas.
- **Identidad/contexto:** identificadores y `distancia_km`. Es incorrecto
  asignarles automáticamente peso comercial para que "todos los campos cuenten".

## Matriz de trazabilidad de los 14 campos

Las validaciones además de `ge/gt` incluyen coherencia entre recuentos y
rechazo de `NaN`/infinito. La columna de reglas contiene ejemplos relevantes,
no afirma enumerar todas las reglas alcanzables indirectamente.

| Entrada de Laravel | Validación | Hechos o uso principal | Reglas de ejemplo | Peso en índice |
|---|---|---|---|---|
| `request_id` | Texto no vacío, <=256 | Correlación petición/respuesta | Ninguna | No |
| `alternativa_id` | Texto no vacío, <=256 | Identificación en lote y comparador | Ninguna | No |
| `costo_total` | Número >=0; operaciones finitas | Dentro/exceso de presupuesto y diferencia | R01, R06, R07, R08 | No directamente |
| `presupuesto` | Número >0; operaciones finitas | Dentro/exceso de presupuesto | R01, R06, R07, R08 | No |
| `ahorro` | Número >=0 | Ahorro bajo/medio/alto | R03, R04, R08, R11, R14–R16 | 35 % |
| `distancia_km` | Número >=0 | Contexto de viaje; no leído por las reglas actuales | Ninguna | No |
| `distancia_adicional_km` | Número >=0 | Cercana/media/lejana, distancia razonable | R03, R06, R11, R14–R16 | 20 % |
| `tiempo_estimado_min` | Número >=0 | Tiempo bajo/medio/alto, razonable | R04, R06, R11, R14–R16 | 15 % |
| `productos_disponibles` | Entero >=0 y <=total; coherencia con esenciales | Cobertura y disponibilidad parcial/total | R09–R16 | 25 % junto al total |
| `productos_totales` | Entero >0, >=disponibles/esenciales | Denominador de cobertura | R09–R16 | 25 % junto a disponibles |
| `productos_esenciales_disponibles` | Entero >=0 y <=esenciales totales y productos disponibles | Esenciales completos o faltantes | R02, R06–R08, R13, R16 | Sin peso independiente |
| `productos_esenciales_totales` | Entero >=0 y <=productos totales | Define esenciales o ausencia de definición | R02, R12, R13, R16 | Sin peso independiente |
| `numero_supermercados` | Entero >=1 | Una/dos paradas, fragmentación | R05, R06, R08, R11, R14–R16 | No |
| `promociones_aplicables` | Booleano | Presencia de promoción declarada | R07, R11, R14–R16 | 5 % |

**Interpretación:** `productos_disponibles` y `productos_totales` forman
una única proporción ponderada, no 25 % cada uno. Los esenciales actúan como
restricción de seguridad, no como otro 25 % que duplicaría disponibilidad.
`ahorro` se recibe en unidades monetarias absolutas, sin combustible,
entrega, caducidad de descuentos ni normalización por ingreso/presupuesto.

## Hallazgo reproducible: cero productos esenciales definidos

Si `productos_esenciales_totales=0`, la validación exige que
`productos_esenciales_disponibles=0`; entonces la igualdad
`todos_esenciales_disponibles = (0 == 0)` es verdadera. Eso no demuestra
cobertura de esenciales: **no se etiquetó ninguno**.

Con todos los demás hechos iguales y coherentes, existen estas decisiones
admisibles por las reglas actuales:

| Condición sintética | Ganadora | Dictamen | Interpretación |
|---|---|---|---|
| Sin esenciales definidos, 100 % de lista, una tienda cercana | R06 | EXCELENTE | Advertir ausencia de clasificación de esenciales |
| Sin esenciales definidos, 100 %, viaje medio y promoción | R07 | BUENA | Advertir ausencia de clasificación de esenciales |
| Sin esenciales definidos, 100 %, dos tiendas y ahorro alto | R08 | BUENA | Advertir ausencia de clasificación de esenciales |
| Sin esenciales definidos, 70 % de lista | R12 | NO_RECOMENDABLE | Prevalece protección de cobertura; no se añade aviso a favorables |
| Sin esenciales definidos, 80 % de lista, una tienda cercana | R06 | EXCELENTE | Advertir esenciales no declarados y lista incompleta |

**HU-34 agrega `SIN_ESENCIALES_IDENTIFICADOS` como señal de calidad**, solo
cuando la conclusión es favorable. La señal se expresa dentro del texto
`explicacion` ya existente y, por reutilización de HU-33, aparece también
en diagnóstico y comparador. No altera ganador, nivel, prioridad ni puntuación
y no incorpora campos nuevos al JSON. No implica que realmente falten
esenciales o que el usuario deba designarlos.

## Pruebas metamórficas incorporadas

`tests/test_input_field_coverage_hu34.py` verifica:

1. Partición exhaustiva y exclusiva de los 14 campos entre identificación,
   contexto y campos evaluados.
2. Cambiar solo IDs mantiene el dictamen, los hechos, la traza y la puntuación.
   Cambia la correlación en la respuesta, no la lógica comercial.
3. Cambiar solo `distancia_km` conserva idéntica respuesta del motor actual
   (hasta que se acuerde cómo utilizarla). La distancia que sí cuenta es
   `distancia_adicional_km`.
4. Cambios válidos de presupuesto, costo, esenciales, tiendas, distancia
   adicional, tiempo, ahorro, stock y promociones producen cambios trazables
   en el dictamen o el índice según corresponda.
5. Casos de cero esenciales en R06/R07/R08 y protección R12.
6. Contrato HTTP 14/16 preservado.

`scripts.audit_decision_quality --with-grid` incluye dos escenarios
adicionales para auditar la advertencia y la prioridad R12 (3431 casos en
total: 17 documentados + 3404 representativos + 10 dirigidos).

```bash
pytest -q tests/test_input_field_coverage_hu34.py
python -m scripts.audit_decision_quality --with-grid
pytest -q
```

## Hallazgos pendientes de política comercial

- Confirmar con el equipo si `productos_esenciales_totales=0` equivale a
  "no hay esenciales" o a "no se ha clasificado la lista". El contrato no
  permite distinguir esas dos situaciones; no cambiar el veto ni imponer
  una etiqueta obligatoria sin acuerdo.
- Evitar contar `distancia_km` y `distancia_adicional_km` como dos costos
  si representan parte del mismo recorrido. La definición exacta proviene de
  Laravel y de la experiencia de compra, no de la ponderación Python.
- Un booleano de promociones no prueba descuento efectivo ni vigencia.
- Para evaluar ahorro neto, requerir variables reales de transporte y
  comparar alternativas con una misma lista. Los 5 pesos no están
  calibrados a decisiones humanas etiquetadas.

**No se presenta esta matriz como validación estadística, prueba de calidad
comercial externa ni evidencia de compras reales.**
