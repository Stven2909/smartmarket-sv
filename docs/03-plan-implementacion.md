# SmartMarket SV — Plan de Implementación

> Documento de trabajo del equipo. Aquí vive el "cómo y en qué orden" se construye el proyecto.
> A diferencia de `02-arquitectura.md` (que ya está congelada), este documento sí puede irse
> actualizando a medida que avanza el desarrollo (marcar tareas como hechas, ajustar fechas, etc.).

---

## 1. Objetivo

Definir el orden de construcción de SmartMarket SV y del Sistema Experto, de manera que ambos
equipos (o ambas partes del mismo equipo) puedan avanzar en paralelo la mayor parte del tiempo,
sin bloquearse entre sí ni tener que rehacer trabajo.

---

## 2. Organización del equipo

El proyecto se trabaja como **dos proyectos que colaboran**, no como uno solo:

```
                 SmartMarket SV
        ┌──────────────────────────┐
        │                          │
   Track A                     Track B
   (Laravel + React)            (Sistema Experto — Python)
```

- **Track A** construye todo lo que no requiere razonamiento por reglas: catálogo, comparador,
  motor de optimización, mapa, presupuesto, panel administrativo, frontend.
- **Track B** construye el Sistema Experto de forma aislada, con datos de prueba al inicio, y se
  conecta al final del proceso (fase de Integración).

Ambos tracks comparten desde el primer día un mismo acuerdo: el **contrato JSON** (cómo se hablan
Laravel y Python) — ver Fase 0B.

---

## 3. Roadmap (orden de construcción)

### Fase 0A — Organización del proyecto
- Repositorio en GitHub, con convención de ramas (branches) y de nombres.
- Tablero de tareas (GitHub Projects o Trello).
- Definir cómo se van a repartir las tareas y con qué frecuencia se revisan avances (sprint
  planning).

### Fase 0B — Arquitectura y diseño previo
- Diagrama de la base de datos (ERD).
- Casos de uso principales.
- **Contrato JSON congelado** entre Laravel y el Sistema Experto (qué información se envía y qué
  se recibe de vuelta — esto no debe cambiar después sin que ambos equipos lo sepan).
- Documentación de esa API en formato OpenAPI (una forma estándar de describir endpoints: qué
  reciben, qué devuelven, qué errores pueden dar).
- Bocetos (wireframes) de las pantallas principales.

*A partir de aquí, Track A y Track B pueden avanzar en paralelo.*

### Fase 1 — Base de datos y autenticación (Track A)
- Tablas principales: productos, categorías, supermercados, usuarios.
- Login con Laravel Sanctum, con roles (administrador / usuario).
- **Seeders** (datos de ejemplo generados automáticamente) y un archivo `demo_products.json` con
  productos de prueba — así todo el equipo trabaja con los mismos datos de ejemplo desde el día
  uno, en vez de que cada quien tenga su propia base de datos vacía o distinta.

### Fase 2 — Catálogo Maestro y Normalización (Track A)
- Construcción del Catálogo Maestro (la lista "oficial" de productos).
- Reglas simples de normalización (ver `02-arquitectura.md`, sección 5).
- Buscador Universal de Productos — la primera pantalla ya funcional y mostrable.

### Fase 3 — Comparador de Lista de Compras (Track A)
- El usuario arma una lista y el sistema calcula el costo total en cada supermercado.
- Segunda pantalla ya demostrable.

> **Nota de integración (fuera del orden original de fases):** durante la integración del
> frontend (`frontend-react/`) se construyeron dos endpoints que pertenecían a fases posteriores:
>
> - `GET /api/sucursales` (`SucursalController@index`) — lista las sucursales con su
>   supermercado (`with('supermercado')`) para poblar la vista de ubicación del frontend.
>   Es trabajo de la Fase 4 (Mapa).
> - `GET /api/promociones` (`PromocionController@index`) — lista los precios con
>   `tiene_promocion = true` (con `producto.categoria` y `sucursal.supermercado`). **Adelanta
>   trabajo de la Fase 5** (Promociones). El controlador solo devuelve datos: el ahorro y el
>   porcentaje de descuento los calcula el frontend (adaptador `promotionFromApi`) comparando
>   `precio_normal` vs `precio_final`; no hay ranking ni lógica de negocio en el backend.
>
> **Pruebas de funcionamiento (integración frontend):**
> - `OPTIONS /api/sucursales` con `Origin: http://localhost:5173` → 204 con
>   `Access-Control-Allow-Origin: http://localhost:5173` y `Access-Control-Allow-Headers: authorization,content-type`.
> - `GET /api/sucursales` → 4 sucursales, cada una con su `supermercado`.
> - `GET /api/promociones` → 2 promociones (Leche entera y Gaseosa, @Walmart), con
>   `tiene_promocion: true` y el objeto `sucursal.supermercado` anidado.
> - `GET /api/productos/buscar?q=leche` → 1 resultado con `precios_actuales[].sucursal.supermercado`
>   (2 precios: 2.10 @Super Selectos y 1.95 @Walmart).
> - `npm run build` en `frontend-react/` → `tsc -b && vite build` sin errores ni warnings.

### Fase 4 — Mapa y Motor de Optimización (Track A)
- Ubicación de supermercados y cálculo de distancias.
- Implementación del Score (con sus pesos configurables).
- Planificador de presupuesto.

### Fase 5 — Promociones e Historial (Track A)
- Historial de precios (con precio normal / promoción / tipo de promoción).
- Promociones filtradas según la lista activa del usuario.
- Historial de compras.

### Fase 6 — Sistema Experto (Track B — ver detalle en `04-sistema-experto.md`)
Empieza en paralelo desde la Fase 0B (con un servicio "vacío" que solo responde datos de prueba),
pero el diseño real de las reglas espera a tener datos reales de la Fase 4:

- **P0 — Diseño del conocimiento**: definir los hechos (facts), variables y reglas antes de
  programar nada. Esta es la parte que más se evalúa en la materia de Sistemas Expertos.
- **P1 — Servicio básico**: levantar el servicio en Python que recibe y responde el contrato JSON
  ya acordado (aunque al inicio solo devuelva una respuesta de prueba).
- **P2 — Motor de reglas**: instalar y configurar la tecnología elegida para el motor de
  inferencia.
- **P3 — Reglas reales**: escribir las reglas usando datos reales que ya produjo la Fase 4.
- **P4 — Explicaciones**: que cada recomendación venga acompañada de un motivo en palabras
  simples (no solo un resultado).

### Fase 7 — Integración (Track A + Track B se unen)
```
Laravel → (petición HTTP) → Sistema Experto (Python) → respuesta → React
```
- Pruebas con datos reales: ahorro alto/bajo, distancia corta/larga, productos faltantes.
- Manejo de errores: ¿qué pasa si el Sistema Experto no responde a tiempo? (el sistema debe seguir
  funcionando solo con el Motor de Optimización).

### Fase 8 — Experiencia de usuario
- Pulir el frontend: estados de carga, mensajes de error, que se vea bien en celular
  (responsive), accesibilidad básica.
- Terminar la configuración de la PWA (para que se pueda "instalar" en el celular).

### Fase 9 — Pruebas y despliegue
- Pruebas automatizadas de las partes más importantes (ver `02-arquitectura.md`, sección 8).
- Subir el proyecto a Render/Railway (backend y Sistema Experto), Vercel (frontend) y
  Supabase/Neon (base de datos).
- Ensayo completo de la demo antes de la entrega o defensa.

---

## 4. Sobre el frontend: ¿empezar antes o después?

React puede empezar a construirse **desde el Sprint 1**, en paralelo con todo lo demás — pero
únicamente si el contrato JSON de la Fase 0B ya está definido y acordado. Mientras tanto, el
equipo de frontend puede avanzar con:

- Bocetos y componentes reutilizables (botones, tarjetas, formularios).
- Datos de prueba simples (no necesariamente el contrato final).

Si el contrato JSON todavía está en discusión, es mejor esperar a cerrarlo antes de conectar datos
simulados "reales", para no tener que rehacer ese trabajo después.

---

## 5. Definition of Done (¿cuándo consideramos que algo "ya está terminado"?)

Una tarea no se marca como terminada solo porque "ya funciona". Debe cumplir:

| Estado | Qué significa |
|---|---|
| En progreso | Ya se empezó a desarrollar. |
| En revisión | Está esperando que otro integrante lo revise. |
| Probado | Se probó y funciona correctamente. |
| Documentado | Quedó explicado (en la API o en el código) qué hace y cómo se usa. |
| Terminado | Cumple con todo lo de la lista de abajo. |

**Checklist para marcar algo como "Terminado":**
- [ ] Código implementado
- [ ] Sin errores conocidos importantes
- [ ] Probado (al menos manualmente)
- [ ] Documentado
- [ ] Revisado por otro integrante del equipo
- [ ] Integrado con el resto del sistema (si aplica)

---

## 6. Riesgos y cómo los vamos a manejar

| Riesgo | Qué podría pasar | Cómo lo mitigamos |
|---|---|---|
| Un supermercado cambia su página web | Si automatizamos la obtención de precios, un cambio en el sitio puede romper esa parte. | El panel administrativo permite seguir cargando precios a mano mientras se arregla. |
| El Sistema Experto se atrasa | Track A podría quedarse esperando. | Se usa un servicio "de mentira" (mock) que responde datos de prueba desde el inicio, así Track A no depende de que Track B termine. |
| El contrato JSON cambia a mitad de camino | Ambos equipos tendrían que rehacer trabajo. | Se congela en la Fase 0B antes de que ambos tracks avancen en serio. |
| Pocos datos para probar | Cada quien prueba con información distinta o no hay suficiente para ver si algo funciona bien. | Seeders + archivo `demo_products.json` compartido por todo el equipo. |
| Tiempo limitado del semestre | No da tiempo de hacer todo lo que se planeó. | Se prioriza siempre el MVP (secciones 4-6 del roadmap) antes que cualquier función "extra". |
| Cuestiones legales de obtener datos automáticamente | Un sitio puede prohibir la extracción automática de sus datos. | El sistema nunca depende de una sola fuente de datos (ver `02-arquitectura.md`, sección 5). |

---

## 7. Lo que queda fuera del MVP (roadmap futuro)

### v1.1 (mejoras de infraestructura, no bloquean la entrega)
- Extractor automático de precios (antes llamado "Web Scraper"). **EN IMPLEMENTACIÓN desde el 2026-08-22.** Análisis técnico y veredicto legal por supermercado en `06-referencia-extractor-vtex.md` (§4–§5); alcance y aceptación de riesgo académico en **ADR-10** (`07-decision-extractor-fuentes-riesgo.md`). Se automatizan Super Selectos (HTML) y las tres tiendas VTEX de Walmart CA; PriceSmart permanece con carga manual. Plan por fases (staging+config → drivers → normalización), un commit por fase.
- Docker (para organizar mejor cómo se despliega cada servicio).
- Documentación completa en OpenAPI.
- Registro de actividad (logging) más detallado.
- Historial de precios con gráficas.

### v1.2
- IA generativa opcional (explicaciones en lenguaje natural, chat).
- APIs oficiales de supermercados (si algún día existen).

### v2 (visión a más largo plazo)
- Aplicación móvil nativa.
- Notificaciones push.
- Programa de fidelización.

**Nota sobre CI/CD** (automatizar pruebas y despliegue cada vez que se sube código nuevo): es una
buena práctica, pero se deja en la categoría de "calidad", no de "requisito del MVP" — no debe
bloquear ninguna entrega si el equipo no llega a implementarlo por falta de tiempo.

---

## 8. Estructura sugerida del repositorio

```
smartmarket/
│
├── docs/
│   ├── 01-vision-negocio.md        (o el ensayo en Word, para Emprendedurismo)
│   ├── 02-arquitectura.md
│   ├── 03-plan-implementacion.md
│   ├── 04-sistema-experto.md
│   └── api/                        (contrato JSON / OpenAPI)
│
├── backend-laravel/
├── frontend-react/
├── expert-system/                  (servicio en Python)
│
├── shared/
│   ├── openapi.yaml
│   ├── demo_products.json
│   └── seeders/
│
└── README.md
```
