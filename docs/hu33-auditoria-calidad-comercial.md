# HU-33 — Auditoría de calidad comercial y advertencias explicables

## Motivación y decisión

La comparación de **16 reglas** reveló recomendaciones `BUENA` sustentadas
en promociones (R07) o ahorro alto con dos supermercados (R08), incluso con
recorridos adicionales o tiempos excesivos. No es necesariamente un fallo del
sistema experto: R03/R04 rechazan viaje desfavorable **solo si el ahorro es bajo**,
y el contrato de 14 hechos no comunica el precio del combustible, parqueo,
reparto, vigencia de ofertas ni valor económico del tiempo.

**Decisión de HU-33:** conservar los dictámenes y prioridades vigentes,
pero advertir al consumidor cuando una regla favorable pueda interpretarse
equivocadamente. No se inventan costos, no se agregan reglas R17/R18, no
se cambian pesos ni se reajusta el ranking de Laravel.

## Casos concretos

Los ejemplos usan presupuestos y listas ficticias:

| Escenario | Dictamen según reglas | Índice | Riesgo de interpretación |
|---|---|---:|---|
| R07: promociones, ahorro 11, 100 km adicionales, 200 min | BUENA | 49.25 | Trayecto alto + índice bajo |
| R08: ahorro 11, dos tiendas, 100 km adicionales, 200 min | BUENA | 44.25 | Trayecto alto + índice bajo |
| R13: esenciales completos, 50 % lista disponible, 1 km y 10 min | BUENA | 47.00 | Índice bajo y opcionales faltantes |\n| R06: esenciales completos, 80 % lista disponible, 1 km y 10 min | EXCELENTE | 54.50 | Lista incompleta pese a nivel excelente |

Con 50 % disponible, **R13 prevalece sobre R06** por su prioridad; con
80 % disponible, R06 sí puede ganar y clasificar como `EXCELENTE` aunque
falten opcionales. La advertencia informa de ese límite sin alterar el
dictamen ni imponer una preferencia comercial no validada.

## Tres advertencias deterministas

- `TRAYECTO_A_REVISAR`: recomendación favorable con
  `distancia_lejana=true` (8 km o más adicionales) **o**
  `tiempo_alto=true` (45 minutos o más). Los umbrales existentes
  clasifican el contexto: **no prueban** que el viaje tenga pérdida neta.
- `INDICE_BAJO_CON_DICTAMEN_FAVORABLE`: dictamen favorable con
  `clasificacion_conveniencia=BAJA_CONVENIENCIA`.
  El índice auxiliar no anula reglas ni calcula utilidad monetaria.
- `EXCELENTE_CON_LISTA_INCOMPLETA`: dictamen `EXCELENTE` con menos
  de 100 % de productos disponibles. Por debajo del 80 %, R13 puede
  prevalecer sobre R06 por prioridad.

Se incluyen frases explicativas usando **solo los hechos recibidos**.
No se crean propiedades de entrada ni de salida: los 14 hechos, los
16 campos de respuesta, el contrato `1.0.0`, los pesos y la
huella de `data/rules.json` se mantienen. `RULES_VERSION=1.3.2`
identifica la misma lógica de inferencia; `THRESHOLDS_VERSION=1.3.2`
corrige la discrepancia de metadatos que quedó después de HU-32.

Las advertencias se muestran en:
1. `/api/v1/recommend`: se agregan al texto `explicacion` de las
   recomendaciones positivas afectadas.
2. Diagnóstico: las mismas advertencias aparecen en el campo
   `advertencias` ya existente.
3. Comparador: se avisa cuando existen opciones con advertencias,
   sin alterar la clasificación ni el orden.

## Defecto corregido en trazabilidad

Antes, si se activaban varias reglas críticas, la explicación seleccionaba
la primera por ID y podía citar una regla diferente a la ganadora por
prioridad. Por ejemplo R03 (prioridad 3) y R10 (prioridad 2) coincidían:
**R10** ganaba, pero el texto mencionaba **R03**.
Ahora la nota cita a la regla **ganadora real**.

## Auditoría automatizada reproducible

```bash
pytest -q tests/test_decision_quality_hu33.py tests/test_quality_audit_hu33.py

# Casos históricos + casos extremos y fronteras específicos de HU-33.
python -m scripts.audit_decision_quality

# 17 documentados + 3404 sintéticos + 10 escenarios dirigidos = 3431.
python -m scripts.audit_decision_quality --with-grid

# Exportación opcional, sin modificar datos ni API.
python -m scripts.audit_decision_quality \
  --with-grid --json-output quality-audit.json
```

La CI ejecuta la auditoría completa, comprueba que toda
recomendación favorable potencialmente engañosa presente las advertencias
correspondientes, que una regla crítica nunca resulte favorable y que la
explicación identifique la regla crítica ganadora. Cualquier incoherencia
de estos tipos bloquea la compilación. Se mantiene la auditoría HU-31
sobre los mismos cinco perfiles y 3421 casos sintéticos.

### Métricas y límites

Los conteos son **frecuencias dentro de un muestreo deliberado**, no
porcentaje de usuarios, predicciones de consumo, tasa de errores comerciales
ni una calibración óptima de pesos. Tampoco se asegura que un trayecto marcado
deba rechazarse: es una oportunidad de revisión.

Para una política nueva que convierta estas advertencias en rechazo, se
necesitarían escenarios comerciales etiquetados y un criterio aprobado sobre
costo de transporte, ahorro neto y tolerancia al viaje. `distancia_km`
se recibe como dato de contexto; el índice y los clasificadores usan
`distancia_adicional_km` para evitar una ponderación doble no justificada.

**No se modifica `develop`**, Laravel, React ni la configuración de
Render/Streamlit. Los nuevos análisis no se ejecutan de fondo en producción
y la inferencia añade únicamente tres comprobaciones locales de calidad
si la conclusión fue favorable.
