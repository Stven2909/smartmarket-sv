# Sistema Experto de Recomendación — SmartMarket SV (v1.0)

> Este documento describe el Sistema Experto como un componente propio, pensado también como
> entregable para la materia de Sistemas Expertos. Se integra con SmartMarket SV mediante una
> API, pero puede entenderse y evaluarse de forma independiente.

---

## 1. Objetivo

Construir un Sistema Experto que, a partir de los resultados numéricos del Motor de Optimización
de SmartMarket SV (costo, distancia, tiempo, promociones, score), determine **qué tan
recomendable** es cada opción de compra y **explique el motivo** de esa recomendación en lenguaje
simple.

> **Laravel calcula. El Sistema Experto razona.**
> El Motor de Optimización obtiene resultados cuantitativos (costos, distancias, tiempo,
> puntuaciones). El Sistema Experto interpreta esos resultados mediante reglas de negocio para
> generar una recomendación explicable para el usuario.

---

## 2. Dominio del problema

El dominio son las decisiones de compra de una familia salvadoreña: dado un conjunto de opciones
(comprar todo en un supermercado, dividir la compra entre dos, etc.), cada una con su costo,
distancia y ahorro asociado, ¿cuál conviene más y por qué?

Es un dominio adecuado para un sistema basado en reglas porque:
- El conocimiento puede expresarse con reglas claras del tipo "si el ahorro es pequeño y la
  distancia es grande, no vale la pena cambiar de supermercado".
- Las decisiones deben ser **explicables** (el usuario quiere saber el porqué, no solo el qué).
- No se necesita "aprender" de datos históricos de forma probabilística — el conocimiento ya lo
  tiene el equipo y puede codificarse directamente como reglas.

---

## 3. Hechos (facts)

Un Sistema Experto trabaja con hechos, pero no todos tienen el mismo origen. Distinguimos entre
**hechos primarios** (observables del dominio) y **hechos derivados** (ya calculados por el Motor
de Optimización antes de llegar al Sistema Experto).

### 3.1 Hechos primarios (provienen del dominio)

| Hecho | Descripción | Ejemplo |
|---|---|---|
| `precio` | Precio de un producto en un supermercado. | $2.15 |
| `promocion_activa` | Si existe una promoción vigente para un producto. | Sí / No |
| `distancia_km` | Distancia en kilómetros hasta el supermercado. | 3.2 km |
| `productos_disponibles` | Cuántos productos de la lista están disponibles ahí. | 8 de 8 |
| `presupuesto` | Presupuesto máximo que definió el usuario. | $100 |

### 3.2 Hechos derivados (ya calculados por el Motor de Optimización)

| Hecho | Descripción | Ejemplo |
|---|---|---|
| `costo_total` | Costo de la lista completa en ese supermercado. | $45.30 |
| `ahorro` | Diferencia de costo frente a la opción más cara. | $7.80 |
| `distancia_adicional` | Distancia extra frente al supermercado más cercano. | 5 km |
| `tiempo_estimado` | Minutos estimados de traslado. | 15 min |
| `numero_supermercados` | En cuántos supermercados habría que dividir la compra. | 1, 2 o 3+ |
| **`score`** | Puntaje final calculado por el Motor de Optimización (ver `02-arquitectura.md`, sección 4.1). | 87.25 |

Separar ambos tipos de hechos deja clara la división de responsabilidades: el Sistema Experto
nunca recalcula nada que Laravel ya calculó, solo razona sobre esos resultados. Incluir el
`score` como hecho de entrada permite reglas más limpias (ej. `SI score >= 90 ENTONCES...`) en
vez de tener que recalcular condiciones que el Motor de Optimización ya resolvió.

---

## 4. Variables de salida

| Variable | Valores posibles |
|---|---|
| `nivel_recomendacion` | 🟢 Excelente / 🟡 Buena / 🔴 No recomendable |
| `explicacion` | Texto en lenguaje natural con el motivo de la recomendación. |
| `accion_sugerida` | Ej. "Comprar todo aquí", "Dividir la compra", "Buscar promociones", "Sugerir segunda parada". |
| `reglas_activadas` | (Uso interno) Lista de identificadores de las reglas que dispararon para este caso — ver sección 8. |

---

## 5. Estrategia de inferencia

Se eligió **encadenamiento hacia adelante (Forward Chaining)**: el sistema parte de un conjunto de
hechos conocidos (enviados por el Motor de Optimización) y evalúa todas las reglas disponibles
para determinar cuáles aplican, hasta producir una recomendación. No se intenta demostrar una
hipótesis específica de antemano (lo cual correspondería a *Backward Chaining*), sino evaluar un
caso concreto a partir de los datos ya conocidos — que es exactamente el problema que resuelve
SmartMarket SV cada vez que un usuario pide una recomendación.

```
        Hechos (facts)
              │
              ▼
     Motor de inferencia
     (evalúa todas las reglas
      contra los hechos del caso)
              │
              ▼
   Base de conocimientos
   ┌──────────────────┐
   │ Regla 1  SI...THEN│
   ├──────────────────┤
   │ Regla 2  SI...THEN│
   ├──────────────────┤
   │ Regla 3  SI...THEN│
   │       ...         │
   └──────────────────┘
              │
              ▼
   Conclusión + explicación
```

---

## 6. Política de resolución de conflictos

Es posible que más de una regla se active para el mismo caso, y que sus conclusiones no
coincidan (por ejemplo, una regla de ahorro dice "Excelente" mientras una regla de distancia dice
"No recomendable"). Para resolverlo, se define una **jerarquía de prioridad** entre categorías de
reglas:

```
Prioridad 1 — Presupuesto
Prioridad 2 — Disponibilidad de productos
Prioridad 3 — Tiempo / distancia
Prioridad 4 — Ahorro
Prioridad 5 — Promociones
```

**Regla de desempate:** si dos o más reglas producen conclusiones distintas para el mismo caso,
gana la conclusión de la regla que pertenece a la categoría de mayor prioridad. Esto refleja el
criterio de negocio real: no importa cuánto se ahorre si el presupuesto no alcanza, o si faltan
productos esenciales — esas condiciones pesan más que el ahorro o las promociones.

---

## 7. Base de conocimientos (reglas)

En lugar de definir reglas sueltas hasta llegar a un número arbitrario, las reglas se derivaron
cubriendo sistemáticamente los escenarios relevantes del dominio:

| Dimensión | Escenarios posibles |
|---|---|
| Disponibilidad | Todos disponibles / Falta uno / Faltan varios |
| Presupuesto | Dentro / Ligeramente fuera / Muy fuera |
| Distancia | Cercano / Medio / Muy lejos |
| Promociones | No existen / Existen / Relevantes a la lista |
| División de la compra | Un supermercado / Dos / Tres o más |
| Tiempo de traslado | Poco / Mucho |
| Ahorro | Bajo / Medio / Alto |

De esa combinación surgen las siguientes reglas base (formato `SI... ENTONCES...`):

```
R1  Opción ideal
SI      productos_disponibles = todos
Y       presupuesto = dentro
Y       score >= 90
ENTONCES nivel_recomendacion = "Excelente".

R2  Ahorro alto compensa
SI      productos_disponibles = todos
Y       presupuesto = dentro
Y       ahorro = alto
ENTONCES nivel_recomendacion = "Excelente".

R3  Falta un producto, hay alternativa cercana
SI      falta exactamente 1 producto
Y       existe un supermercado alternativo a menos de 1 km
ENTONCES accion_sugerida = "Sugerir segunda parada", nivel_recomendacion = "Buena".

R4  Faltan varios productos
SI      faltan varios productos de la lista
ENTONCES descartar este supermercado, nivel_recomendacion = "No recomendable".

R5  Presupuesto ligeramente excedido
SI      presupuesto = ligeramente_fuera
ENTONCES accion_sugerida = "Buscar promociones o sustitutos", nivel_recomendacion = "Buena".

R6  Presupuesto muy excedido
SI      presupuesto = muy_fuera
ENTONCES nivel_recomendacion = "No recomendable", sugerir replantear la lista.

R7  Muy lejos y poco ahorro
SI      distancia = muy_lejos
Y       ahorro = bajo
ENTONCES nivel_recomendacion = "No recomendable".

R8  Cercano con ahorro razonable
SI      distancia = cercano
Y       ahorro ∈ {medio, alto}
ENTONCES nivel_recomendacion = "Excelente" o "Buena" (según score).

R9  Empate técnico, deciden las promociones
SI      diferencia_precio entre dos supermercados < 5%
Y       uno de ellos tiene promociones relevantes a la lista
ENTONCES priorizar el supermercado con promociones.

R10  Compra demasiado fragmentada
SI      numero_supermercados >= 3
ENTONCES nivel_recomendacion = "No recomendable" (demasiada fragmentación de la compra).

R11  Dividir la compra sí conviene
SI      numero_supermercados = 2
Y       ahorro_total > costo_traslado_extra
ENTONCES accion_sugerida = "Dividir la compra", nivel_recomendacion = "Buena".

R12  Mucho tiempo y poco ahorro
SI      tiempo_estimado = mucho
Y       ahorro = bajo
ENTONCES nivel_recomendacion = "No recomendable".

R13  Poco tiempo y ahorro medio
SI      tiempo_estimado = poco
Y       ahorro = medio
ENTONCES nivel_recomendacion = "Excelente".

R14  Caso ambiguo — ahorro alto con tiempo alto
SI      ahorro = alto
Y       tiempo_estimado = mucho
ENTONCES aplicar política de resolución de conflictos (sección 6): el tiempo/distancia
         (prioridad 3) pesa más que el ahorro (prioridad 4) salvo que el ahorro supere un umbral
         significativo definido por el equipo (ej. > $10).

R15  Opción estándar sin diferenciadores
SI      no hay promociones relevantes
Y       presupuesto = dentro
Y       productos_disponibles = todos
ENTONCES nivel_recomendacion = "Buena" (opción válida, sin ventajas ni desventajas notables).
```

Cada regla, además de su conclusión, genera una frase de explicación en lenguaje simple (ver
sección 8).

---

## 8. Explicabilidad y trazabilidad

La explicabilidad es uno de los pilares de un Sistema Experto: el usuario no solo debe recibir un
resultado, sino el motivo detrás de él. Esto se maneja en **dos niveles**:

**Nivel técnico (interno, para depuración y mantenimiento):** el motor de inferencia conserva qué
reglas se activaron para llegar a la conclusión final.

```json
"reglas_activadas": ["R2", "R9"]
```

**Nivel de usuario (lo que ve la persona en la aplicación):** una explicación en lenguaje natural,
generada a partir de las reglas activadas, sin exponer los identificadores técnicos:

> *"Se recomienda comprar en este supermercado porque cumple con el presupuesto, dispone de todos
> los productos y el ahorro obtenido compensa el desplazamiento."*

Mantener ambos niveles no añade complejidad significativa (es solo registrar qué reglas
dispararon antes de generar el texto final), pero permite que el equipo depure el comportamiento
del sistema cuando una recomendación no parezca correcta, sin tener que adivinar qué regla la
causó.

---

## 9. Motor de inferencia

El motor de inferencia es el componente que toma los hechos de un caso (sección 3) y los evalúa
contra todas las reglas de la base de conocimientos (sección 7) siguiendo la estrategia de
Forward Chaining (sección 5) y la política de resolución de conflictos (sección 6).

**Tecnología:** por definir durante la fase de implementación. Candidatos en evaluación: PyKnow,
CLIPS (vía `clipspy`), Durable Rules, u otro motor de reglas en Python. La elección específica no
afecta el diseño del dominio, los hechos ni las reglas descritos en este documento — solo cambia
cómo se implementan técnicamente.

Si el curso solicita construir el motor de inferencia desde cero (en lugar de usar una librería
existente), este documento sigue siendo válido: los hechos, reglas, estrategia de inferencia y
política de conflictos ya definidos se pueden implementar directamente con estructuras de datos
propias y un ciclo de evaluación simple (recorrer reglas, verificar condiciones, aplicar
prioridad en caso de conflicto).

---

## 10. Arquitectura del servicio

El Sistema Experto vive como un servicio independiente, escrito en Python, expuesto mediante una
API (FastAPI). Nunca se ejecuta dentro de Laravel ni el frontend lo llama directamente.

```
Laravel (Motor de Optimización)
        │
        │  POST /api/expert/recommend
        ▼
   Sistema Experto (Python)
        │
        │  Motor de inferencia evalúa los hechos contra las reglas
        ▼
   Respuesta con nivel + explicación (+ reglas activadas, uso interno)
        │
        ▼
   Laravel se la pasa al frontend (React)
```

---

## 11. Contrato de la API

**Petición (Laravel → Sistema Experto):**
```json
{
  "costo_total": 45.30,
  "ahorro": 7.80,
  "score": 87.25,
  "distancia": 3.2,
  "distancia_adicional": 5,
  "tiempo_estimado": 15,
  "productos_disponibles": 8,
  "productos_totales": 8,
  "numero_supermercados": 1,
  "promociones_aplicables": true,
  "presupuesto": 100
}
```

**Respuesta exitosa (Sistema Experto → Laravel):**
```json
{
  "nivel_recomendacion": "Excelente",
  "accion_sugerida": "Comprar todo aquí",
  "explicacion": "Se encontraron todos los productos, el ahorro es significativo y el recorrido adicional es mínimo.",
  "reglas_activadas": ["R1", "R2"]
}
```

**Errores:**

| Código | Significado | Cuándo ocurre |
|---|---|---|
| 400 | *Bad Request* | La petición no tiene el formato JSON esperado. |
| 422 | Hechos inválidos | Los datos llegaron con el formato correcto, pero con valores inconsistentes (ej. `costo_total` negativo). |
| 500 | Error interno | Falla inesperada del motor de inferencia. |

Este contrato debe quedar **congelado** antes de que ambos equipos (Track A y Track B, ver
`03-plan-implementacion.md`) avancen en paralelo, para evitar retrabajo si cambia a mitad de
camino.

---

## 12. Casos de prueba

| Caso | Hechos de entrada (resumen) | Resultado esperado |
|---|---|---|
| 1 | Ahorro alto, todos los productos disponibles, dentro de presupuesto | 🟢 Excelente, "Comprar todo aquí" |
| 2 | Ahorro bajo ($1.50), distancia adicional alta (10 km) | 🔴 No recomendable, no cambiar de supermercado |
| 3 | Falta 1 producto, alternativa a 800m | 🟡 Buena, "Sugerir segunda parada" |
| 4 | Costo total supera el presupuesto | 🟡 Buena, "Buscar promociones o sustitutos" |
| 5 | Dos supermercados con diferencia de precio menor al 5%, uno con más promociones | 🟢 Excelente, priorizar el de más promociones |
| **6 (ambiguo)** | Ahorro alto ($12) **pero** tiempo adicional alto (45 min) | Se resuelve por la política de la sección 6 (R14): el tiempo pesa más que el ahorro salvo que este supere el umbral definido — este caso es el que realmente pone a prueba la base de conocimientos, no solo la aplicación de una regla aislada. |

Estos casos deben probarse tanto de forma aislada (solo el Sistema Experto, con datos de prueba)
como en la fase de Integración (con datos reales que produce Laravel).

---

## 13. Limitaciones

- El Sistema Experto depende de datos ya validados por el pipeline de ingesta de SmartMarket SV
  (ver `02-arquitectura.md`, sección 5); no verifica por sí mismo si un precio es correcto.
- Las recomendaciones están basadas en reglas definidas por el equipo, no en aprendizaje
  automático — el sistema no "mejora solo" con más datos, requiere que alguien actualice la base
  de conocimientos.
- Si cambian los hábitos de consumo, el mercado, o las políticas comerciales de los
  supermercados, será necesario revisar y actualizar las reglas manualmente.
- El sistema no sustituye el criterio del usuario: entrega una recomendación explicable basada en
  la información disponible, pero la decisión final siempre queda en manos de la persona.

---

## 14. Relación con el resto de SmartMarket SV

- El Motor de Optimización (Laravel) hace los **cálculos** (matemáticas: costo, distancia, tiempo, score).
- El Sistema Experto (Python) hace el **razonamiento** (interpreta esos cálculos y decide qué tan
  buena es la opción, con una explicación).
- Gracias al pipeline de datos descrito en `02-arquitectura.md` (sección 5), el Sistema Experto
  siempre recibe datos ya validados — no necesita preocuparse por si un precio es correcto o si
  un producto está duplicado, eso ya se resolvió antes.
- Si el Sistema Experto no está disponible por cualquier motivo, SmartMarket SV sigue funcionando
  con las recomendaciones básicas del Motor de Optimización (Principio de Arquitectura #4).
