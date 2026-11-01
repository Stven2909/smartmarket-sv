# Chat del Sistema Experto — Preguntas que soporta

> Documento interno de referencia. Describe los temas que el asistente explicativo
> puede responder y ejemplos de preguntas que funcionan / no funcionan.

---

## Cómo funciona el chat

1. El usuario escribe una pregunta en `ExpertChat.tsx`.
2. Laravel reconstruye los facts desde la corrida de optimización persistida
   (`resultado_json`) y llama a `POST /api/v1/chat` en el Sistema Experto (Python).
3. Python clasifica la **intención** (`intent`) y devuelve una respuesta con
   `supported: true/false`.
4. Si `supported: false` → se muestran **sugerencias de preguntas** en la UI
   (chips clicables) en vez del texto de ayuda genérico.
5. Si el experto no responde (timeout/conexión) → fallback `NO_DISPONIBLE`
   con un mensaje controlado.

---

## 7 temas que el chat SÍ puede responder

Cada tema tiene un `intent` asociado en Python. Las preguntas deben referirse
a la **alternativa que se está mostrando** (la que tiene el badge del Sistema
Experto).

### 1. Recomendación (`EXPLICACION`)

> "¿Por qué me recomiendas esta alternativa?"
> "¿Por qué NO me recomiendas esta tienda?"
> "Explicame esta recomendación"

El experto explica por qué la alternativa es buena/mala basándose en la regla
ganadora (R01–R08).

### 2. Presupuesto (`PRESUPUESTO`)

> "¿La compra cabe en mi presupuesto?"
> "¿Cuánto me falta o me sobra del presupuesto?"
> "¿Esta alternativa es economicamente viable?"

Devuelve el costo total, el presupuesto y la diferencia.

### 3. Ahorro (`AHORRO`)

> "¿Cuánto me ahorro con esta alternativa?"
> "¿Cuál es la diferencia de precio con la más cara?"
> "¿Vale la pena el ahorro?"

Devuelve el monto de ahorro respecto a la alternativa más costosa.

### 4. Productos disponibles (`PRODUCTOS`)

> "¿Todos los productos de mi lista están disponibles?"
> "¿Cuántos productos consigo aquí?"
> "¿Faltan productos esenciales?"

Devuelve cuántos productos hay disponibles de los totales.

### 5. Distancia (`DISTANCIA`)

> "¿Qué tan lejos queda esta tienda?"
> "¿Cuántos kilómetros hay que recorrer?"
> "¿Es cercana o lejana esta sucursal?"

Devuelve la distancia en km y la distancia adicional respecto a la más cercana.

### 6. Tiempo (`TIEMPO`)

> "¿Cuánto tiempo tardo en llegar?"
> "¿Cuántos minutos me toma el viaje?"
> "¿Es rápido llegar a esta tienda?"

Devuelve el tiempo estimado de traslado en minutos.

### 7. Promociones (`PROMOCIONES`)

> "¿Hay promociones aplicables en esta tienda?"
> "¿Me conviene por las promociones?"
> "¿Qué promociones puedo usar?"

Devuelve si hay promociones aplicables y su impacto en el ahorro.

---

## Qué NO puede responder

Si el usuario pregunta sobre algo que no está en los facts (historial de
compras, opiniones de otros usuarios, disponibilidad futura, precios de
otros países, etc.), Python devuelve `intent: AYUDA` con `supported: false`.

Ejemplos de preguntas que devuelven texto de ayuda genérico:

- "¿Cuál es el mejor supermercado?" (demasiado vago)
- "¿Cuánto gasté el mes pasado?" (no tiene historial)
- "¿Qué productos me faltan?" (los facts ya incluyen esta info; mejor
  preguntar "¿Todos los productos están disponibles?")
- "¿Me conviene ir caminando?" (no calcula rutas alternativas)
- "¿Hay otro supermercado mejor?" (el chat solo comenta la alternativa
  seleccionada)

---

## Sugerencias para la UI

Cuando `supported: false` y no es fallback `NO_DISPONIBLE`, mostrar estos
chips clicables en `ExpertChat.tsx`:

```text
¿Por qué me recomiendas esto?
¿Cuánto ahorro?
¿Cabe en mi presupuesto?
¿Están todos los productos?
¿Qué tan lejos queda?
```

Cada chip, al hacer clic, envía la pregunta correspondiente al chat.
