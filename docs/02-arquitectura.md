# SmartMarket SV — Arquitectura Técnica (v1.0, congelada)

> Este documento es para el equipo de desarrollo, no para el ensayo académico de Emprendedurismo.
> Está escrito para que cualquier persona del equipo lo entienda, tenga o no experiencia previa
> en arquitectura de software. Cada vez que aparece un término técnico nuevo, se explica en el
> momento en que se usa por primera vez.
>
> **Estado: congelado (v1.0).** Esto significa que ya no deberíamos seguir cambiando decisiones de
> fondo aquí — solo construir sobre esta base. Si alguien propone algo nuevo, primero se revisa
> contra los Principios de Arquitectura (sección 1) antes de aceptarlo.

**Orden recomendado de lectura de la documentación del proyecto:**

```
01-vision-negocio.md          (el ensayo — problema, impacto social, modelo de negocio)
        ↓
02-arquitectura.md             (este documento — cómo está construido el sistema)
        ↓
03-plan-implementacion.md      (en qué orden se construye, quién hace qué)
        ↓
04-sistema-experto.md          (detalle del Sistema Experto, para la materia correspondiente)
```

---

## 1. Principios de Arquitectura

Estas son las "reglas de oro" del proyecto. Cualquier decisión técnica nueva debe respetarlas.

1. **El núcleo del negocio no dependerá de una tecnología específica.** Es decir, si mañana
   cambiamos de proveedor de mapas, de base de datos o quitamos algún servicio, el resto del
   sistema debe seguir funcionando.
2. **Cada módulo tendrá una única responsabilidad.** Por ejemplo, el módulo que calcula precios
   no debería también encargarse de mandar correos o de dibujar el mapa.
3. **Las integraciones externas (APIs, scraping, carga manual) serán intercambiables** sin
   afectar el funcionamiento del sistema. (Esto se explica a fondo en la sección 6).
4. **El sistema deberá seguir funcionando aun cuando falle un servicio opcional.** Por ejemplo, si
   el Sistema Experto se cae, el usuario debe poder seguir comparando precios normalmente.
5. **El MVP** (*Minimum Viable Product* — la primera versión funcional y suficiente del producto)
   **priorizará simplicidad y mantenibilidad sobre complejidad técnica.**
6. **La inteligencia artificial generativa (tipo ChatGPT) será un componente complementario y
   nunca un requisito para el funcionamiento del sistema.** Explica cosas, no decide nada.
7. **Ninguna fuente externa de datos podrá modificar directamente el Catálogo Maestro** (la lista
   "oficial" de productos del sistema, explicada en la sección 6). Toda información nueva debe
   pasar primero por un proceso de revisión antes de usarse.
8. **Las reglas de negocio serán configurables, no fijas en el código**, siempre que sea posible.
   Por ejemplo, si mañana queremos cambiar qué tanto peso le damos al ahorro de tiempo frente al
   ahorro de dinero, eso debe poder ajustarse sin reescribir el programa.

---

## 2. El stack (qué tecnología usamos en cada parte)

| Parte del sistema | Qué usamos | Por qué |
|---|---|---|
| Lo que ve el usuario (frontend) | React + Tailwind CSS | Es lo más usado hoy en día para construir páginas web modernas e interactivas. |
| El "cerebro" del negocio (backend) | Laravel 12 (PHP) | El equipo ya sabe usarlo, así que no se pierde tiempo aprendiendo algo nuevo desde cero. |
| Panel para el equipo (administración) | Filament (viene con Laravel) | Ya trae listas para editar/agregar productos, supermercados, etc., sin tener que programarlo desde cero. |
| Donde se guardan los datos (base de datos) | PostgreSQL | Es robusta, gratuita, y permite calcular distancias entre ubicaciones fácilmente. |
| Mapas | Leaflet + OpenStreetMap | Es gratis (a diferencia de Google Maps, que cobra si se usa mucho). |
| Iniciar sesión (autenticación) | Laravel Sanctum | La forma más simple de manejar login dentro de Laravel, sin complicaciones extra. |
| El Sistema Experto (el que razona y explica recomendaciones) | Python, con un motor de reglas *(la tecnología exacta se confirmará antes de empezar esa parte, ver sección 7)* | Es un requisito de la materia de Sistemas Expertos: debe hacerse en Python. |
| Obtención automática de precios (si se implementa) | Python | Python tiene las mejores herramientas para "leer" páginas web automáticamente. |
| App para el celular | PWA (*Progressive Web App*: una página web que se puede "instalar" como si fuera una app) | Funciona en Android, iPhone y computadora sin tener que programar 3 apps distintas. |

---

## 3. Cómo se conectan las piezas (arquitectura general)

Imaginen el sistema como una fábrica con distintas estaciones de trabajo, donde cada una hace
solo su parte y le pasa el resultado a la siguiente:

```
                       React (lo que ve el usuario)
                              │
                       Laravel (el "cerebro" del negocio)
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                      │
   PostgreSQL             (opcional: Redis,       Filament
   (base de datos)         para ir más rápido)   (panel admin)
        │
        │  Laravel le "pregunta" a Python por HTTP (una simple petición
        │  como cuando tu navegador pide cargar una página)
        │
   ┌────┴─────────────────────────┐
   │                              │
Sistema Experto                Proveedores de datos
(Python)                       (sección 6)
   │
   │  (opcional, solo explica en palabras — nunca decide)
   ▼
IA Generativa (opcional)
```

**Regla importante:** Laravel actúa como **orquestador central** del sistema. Todas las
solicitudes del frontend y todas las integraciones con servicios externos pasan a través del
backend, lo que garantiza desacoplamiento, seguridad y una única fuente de coordinación para la
lógica de negocio. Ni el frontend (React) le habla directamente a Python, ni Laravel le pregunta
directamente a la página de un supermercado — todo pasa por Laravel. Así, si algo falla (el
Sistema Experto, la obtención de datos, la IA), el resto sigue funcionando.

### Organización interna de Laravel

Para que el código no se vuelva un enredo a medida que el proyecto crece, dentro de Laravel
organizamos el trabajo en tres capas:

```
Controller  →  Service  →  Model
(recibe la    (aquí vive     (representa
petición)      la lógica       una tabla de
                real, los       la base de
                cálculos)       datos)
```

Por ejemplo, el cálculo de qué supermercado conviene más no debe estar mezclado directamente en
el archivo que recibe la petición web (`Controller`); debe vivir en un archivo aparte
(`OptimizationService`) que se pueda probar y revisar de forma aislada.

---

## 4. Flujo completo del sistema (de principio a fin)

Todas las piezas anteriores cobran sentido cuando se ven en conjunto. Estos son los dos recorridos
más importantes de todo SmartMarket SV.

### 4.1 Flujo 1 — Un usuario pide una recomendación

```
Usuario
   │
   ▼
React (PWA)
   │
   ▼
Laravel API
   │
   ├──► consulta PrecioActual (¿cuánto cuesta cada producto en cada sucursal?)
   ├──► consulta ListaCompra (¿qué agregó el usuario a su lista?)
   │
   ▼
OptimizationService calcula el Score (ver sección 5.1)
   │
   ▼
Se guarda en ResultadoOptimizacion
   │
   ▼
Laravel arma un JSON con los hechos y hace  POST /expert/recommend
   │
   ▼
Sistema Experto (Python) razona con sus reglas
   │
   ▼
Responde con nivel + explicación
   │
   ▼
Laravel guarda la respuesta en Recomendacion
   │
   ▼
React se lo muestra al usuario (🟢🟡🔴 + explicación en palabras simples)
```

### 4.2 Flujo 2 — Actualización de precios

```
Price Provider (carga manual, extractor automático, API o CSV — ver sección 6.1)
   │
   ▼
ProductoRaw (zona temporal / staging)
   │
   ▼
Motor de Normalización (ver sección 6.2)
   │
   ▼
Motor de Validación
   │
   ├──► inválido ──► Revisión Manual (alguien del equipo lo revisa)
   │
   ▼ válido
Catálogo Maestro (Producto)
   │
   ▼
PrecioActual  (se actualiza el precio vigente)
   │
   ▼
HistorialPrecio  (se agrega un registro nuevo, nunca se sobrescribe)
```

Con estos dos flujos, cualquier persona nueva en el equipo puede entender de principio a fin cómo
funciona el sistema completo, sin tener que leer todas las secciones sueltas.

---

## 5. Los módulos del sistema

Para que quede claro qué tan crítico es cada módulo, los agrupamos en tres categorías:

### 5.1 Módulos Core (el corazón del MVP — sin esto, no hay producto)

| Módulo | Qué hace, en palabras simples |
|---|---|
| Buscador de productos | El usuario busca "leche" y ve precio, supermercado, disponibilidad y promociones. |
| Comparador de listas | El usuario arma una lista completa y el sistema suma cuánto costaría en cada supermercado. |
| Catálogo Maestro | La "lista oficial" de productos del sistema — evita tratar como distintos dos productos que en realidad son el mismo. |
| Motor de Optimización | Decide qué supermercado conviene más, calculando un puntaje (Score). |

**El Score, formalmente:**

```
Score = α·(CostoCompra) + β·(CostoCombustible) + γ·(CostoTiempo) − δ·(BeneficioPromociones)
```

Donde `α`, `β`, `γ` y `δ` son los "pesos" de cada factor — configurables, no fijos en el código
(Principio de Arquitectura #8). Por ejemplo, una familia que prefiere ahorrar dinero puede subir
`α`, mientras que otra que prefiere ahorrar tiempo puede subir `γ`.

**Importante:** **mientras menor sea el Score, mejor es la alternativa** — es un puntaje de
"costo total ajustado", no de calificación. Esto evita que alguien interprete, por error, que un
Score alto es preferible.

### 5.2 Módulos de apoyo (mejoran la experiencia, no son indispensables para el valor central)

| Módulo | Qué hace |
|---|---|
| Planificador de presupuesto | Muestra en tiempo real cuánto se lleva gastado frente al presupuesto. |
| Promociones inteligentes | Muestra solo las ofertas relevantes a la lista activa del usuario. |
| Mapa de supermercados | Ubicación, distancia y tiempo estimado. |
| Historial | Consulta de compras y precios anteriores. |
| Panel administrativo (Filament) | Donde el equipo carga y mantiene productos, supermercados y precios. |

### 5.3 Servicios externos (opcionales — el sistema sigue funcionando si fallan)

| Servicio | Qué hace |
|---|---|
| Sistema Experto | Razona sobre el resultado del Motor de Optimización y genera una recomendación explicable (ver sección 7). |
| Price Providers | Cualquier fuente de datos de precios (manual, automatizada, API) — ver sección 6.1. |
| IA generativa | Explica en lenguaje natural — nunca decide nada (ver `02-arquitectura.md` Principio 6). |

---

## 6. De dónde vienen los datos (y por qué esto es tan importante)

Todo el sistema depende de una pregunta central: **¿de dónde sacamos los precios?** Sin datos,
SmartMarket SV no tiene nada que comparar. Por eso esta parte se diseñó con mucho cuidado.

### 6.1 "Proveedores de datos" (Price Providers)

En vez de pensar en una sola forma de obtener precios, diseñamos el sistema para aceptar
**varias fuentes distintas**, todas tratadas de la misma manera por el resto del sistema:

```
Proveedores de datos (Price Providers)
 ├─ Carga manual         (alguien del equipo escribe los precios a mano en el panel administrativo)
 ├─ Extractor automático (esto es lo que antes llamábamos "Web Scraper": un programa que entra
 │                        a la página de un supermercado y copia los precios automáticamente)
 ├─ API oficial          (si algún día un supermercado nos da acceso directo a sus datos)
 └─ Archivo CSV/Excel    (importar precios desde una hoja de cálculo)
```

**¿Por qué importa esto?** Porque el resto del sistema (el comparador, el motor de optimización,
el sistema experto) **nunca necesita saber de dónde vino un precio**. Si mañana dejamos de usar
el extractor automático y conseguimos una API oficial, no hay que tocar nada más del sistema —
solo se agrega un proveedor nuevo.

### 6.2 Motor de Normalización (módulo propio)

Es uno de los módulos más importantes de todo el sistema, aunque pase desapercibido: es el que
decide si "Coca Cola 2L", "Coca-Cola 2 Litros" y "Coca-Cola PET 2L" son en realidad el mismo
producto.

**Responsabilidades:**
- Limpiar el texto (quitar caracteres especiales, unificar mayúsculas/minúsculas).
- Reconocer la marca dentro del nombre.
- Reconocer la presentación (ej. "2L", "600ml").
- Reconocer la unidad de medida.
- Buscar si ya existe un alias parecido registrado.
- Decidir a qué Producto Maestro corresponde (o marcarlo para revisión manual si no está claro).
- Devolver el producto ya normalizado, listo para pasar a Validación.

**Fase MVP:** reglas simples de texto y alias cargados manualmente por el equipo.
**Evolución futura (v1.1+):** coincidencia difusa (*fuzzy matching*) para detectar alias parecidos
automáticamente.

### 6.3 Por qué los datos no entran directo al sistema

Aquí está una de las decisiones más importantes de todo el proyecto: **ningún proveedor de datos
puede escribir directamente en la información que usa la aplicación**. Todo pasa primero por una
"zona de revisión" (ver el Flujo 2 completo en la sección 4.2):

```
   Proveedores de datos
              │
              ▼
   ┌─────────────────────────┐
   │  Zona temporal (Staging) │   ← aquí llega el dato "en crudo", tal cual vino
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │  Motor de Normalización  │   ← ver sección 6.2
   └───────────┬─────────────┘
               │
               ▼
   ┌─────────────────────────┐
   │  Validación              │   ← ¿el precio tiene sentido? ¿no está duplicado?
   └───────────┬─────────────┘
      válido   │    inválido
        │      │        │
        ▼      │        ▼
  Catálogo     │   Revisión manual
  Maestro      │
    │
    ▼
  Historial de precios
```

**Reglas fijas de este proceso (nunca se rompen):**
1. Nunca se sobrescribe un precio anterior — siempre se agrega uno nuevo con su fecha.
2. Nunca se publica un dato sin pasar por Normalización.
3. Nunca se eliminan productos automáticamente — se manda a revisión manual, nunca se borra solo.
4. Siempre se guarda la fecha de cada actualización.
5. Todo cambio queda registrado (auditado).

### 6.4 El "Vigilante de Salud" (Health Monitor)

Revisa que el proceso de obtención de datos esté funcionando bien, y avisa si algo se ve raro:

```
Ayer se encontraron 1,250 productos.
Hoy solo se encontraron 31.
   → ¡Algo anda mal! (probablemente el supermercado cambió su página)
   → No publicar estos datos.
   → Avisar al equipo.
```

Sin este módulo, nos enteraríamos de un problema solo cuando un usuario reportara "esto no tiene
sentido" — con el Health Monitor, nos enteramos antes, apenas ocurre.

### 6.5 Nota sobre el aspecto legal

Extraer datos automáticamente de un sitio web puede estar restringido por los términos de uso de
ese sitio. Por eso, la arquitectura completa está diseñada para **no depender de una sola forma
de obtener datos**: si en algún momento no es posible o conveniente automatizar la obtención de
precios de cierto supermercado, el sistema sigue funcionando perfectamente con carga manual, sin
ningún cambio al resto de los módulos.

---

## 7. Sistema Experto (resumen — ver documento aparte para el detalle completo)

El Sistema Experto es el componente que **razona sobre las recomendaciones** — no calcula
números (eso lo hace el Motor de Optimización), sino que interpreta esos números y decide qué tan
buena es una opción, explicándole al usuario por qué.

```
Laravel  ──  POST /expert/recommend (hechos: score, ahorro, distancia, disponibilidad...)  ──►  Sistema Experto (Python)
Laravel  ◄──  { nivel, mensaje, reglas_activadas }  ────────────────────────────────────────────  Sistema Experto (Python)
```

**Importante:** Laravel nunca envía consultas SQL, nunca envía IDs internos de la base de datos, y
nunca comparte su lógica de negocio con Python — únicamente envía **hechos del problema** (los
valores ya calculados). Esto es lo que formalizamos como **ADR-009** (ver sección 9): el Sistema
Experto es *stateless* (no guarda información propia ni se conecta directamente a PostgreSQL).

- Vive en un servicio aparte, escrito en Python (requisito de la materia de Sistemas Expertos).
- La tecnología exacta del motor de reglas se confirmará antes de empezar a construirlo — mientras
  tanto, el resto de la arquitectura no depende de ese detalle.
- El detalle completo (hechos, reglas, estrategia de inferencia, contrato de API con ejemplos)
  vive en el documento `04-sistema-experto.md`.

---

## 8. Seguridad y pruebas

### 8.1 Seguridad (lo básico que sí vamos a implementar)
- **Roles de usuario**: Administrador, Moderador, Usuario normal.
- **Permisos por recurso**: solo el dueño de una lista de compras puede editarla.
- **Límite de peticiones** (*rate limiting*): evita que alguien sature el sistema.

### 8.2 Pruebas (testing) — lo mínimo necesario
- Que el cálculo del Motor de Optimización dé el resultado correcto.
- Que la Normalización agrupe bien los productos parecidos.
- Que los endpoints principales de la API respondan lo esperado.
- Una prueba de principio a fin: crear una lista → calcular el Score → obtener una recomendación.

---

## 9. No-objetivos (qué NO hará el sistema)

Tan importante como definir qué hace el sistema es dejar explícito qué **no** hace, para evitar
que el alcance del proyecto crezca sin control (*scope creep*):

- No reemplazar los sistemas propios de los supermercados.
- No realizar ventas ni procesar pagos.
- No modificar precios automáticamente sin pasar por el pipeline de validación (sección 6.3).
- No depender del Sistema Experto para funcionar — el Motor de Optimización por sí solo ya da una
  recomendación básica.
- No depender de inteligencia artificial generativa para ninguna función central.
- El Sistema Experto (Python) nunca se conecta directamente a PostgreSQL.

---

## 10. Riesgos arquitectónicos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Un supermercado cambia el HTML de su sitio | Pipeline de datos + Health Monitor (secciones 6.3–6.4) |
| El Sistema Experto se cae o no responde | Laravel continúa funcionando solo con el Motor de Optimización (Principio 4) |
| Llegan datos incompletos o corruptos | Staging + Motor de Validación antes de publicar (sección 6.3) |
| Se registra una promoción inválida o duplicada | Historial de precios append-only, nunca se sobrescribe (sección 6.3) |
| Cambia la prioridad de qué optimizar (dinero vs. tiempo) | Pesos del Score configurables, no fijos en código (sección 5.1) |

---

## 11. Decisiones ya tomadas (ADR)

*ADR = Architectural Decision Record: un registro de "por qué elegimos esto", para no tener que
volver a discutirlo cada vez que a alguien se le ocurra una idea nueva. Se numeran para poder
referenciarlas fácilmente desde otros documentos.*

| ADR | Decisión | Por qué |
|---|---|---|
| ADR-001 | Laravel como backend | El equipo ya lo conoce; se avanza más rápido. |
| ADR-002 | React como frontend (PWA) | Estándar actual para interfaces modernas; PWA cubre Android/iOS/escritorio sin apps nativas. |
| ADR-003 | PostgreSQL como base de datos | Robusto, gratuito, bueno para cálculos de distancia. |
| ADR-004 | Laravel Sanctum para autenticación | Opción más simple que ya viene con Laravel, suficiente para una SPA. |
| ADR-005 | Arquitectura por capas (Controller → Service → Model) | Mantiene la lógica de negocio aislada y fácil de probar. |
| ADR-006 | Pipeline de datos desacoplado (Price Providers → Staging → Normalización → Validación) | Permite cambiar de dónde vienen los datos sin tocar el resto del sistema. |
| ADR-007 | Motor de Normalización como módulo propio | Sin esto, comparar precios entre supermercados no sería confiable. |
| ADR-008 | Score configurable (α, β, γ, δ) | Permite adaptar la recomendación a lo que cada familia prioriza. |
| ADR-009 | Sistema Experto *stateless* | El Sistema Experto no accede directamente a PostgreSQL; solo recibe hechos en JSON y responde una recomendación. Laravel es el único responsable de consultar datos, preparar hechos, invocar el servicio Python y persistir la recomendación final. |

---

## 12. Modelo de datos (ERD v1.0)

*ERD = Diagrama Entidad-Relación: muestra qué "tablas" existen en la base de datos y cómo se
relacionan entre sí. Este modelo ya incorpora las correcciones discutidas por el equipo y sigue
el mismo criterio de todo este documento: solo entran las tablas que el MVP realmente necesita.*

### 12.1 Nivel 1 — Core (agrupado por dominio)

![ERD Nivel 1 - Core](erd_nivel1_core.png)

El diagrama agrupa las tablas en tres dominios (bandas de color) para facilitar la lectura:
**Catálogo** (azul), **Comercio** (verde) y **Usuario/Compras** (ámbar) — aunque, como se ve en
el diagrama, varias tablas se relacionan entre dominios (ej. `Producto` conecta tanto con
`PrecioActual` como con `ListaCompraDetalle`).

| Tabla | Dominio | Campos | Notas |
|---|---|---|---|
| **Usuario** | Usuario/Compras | `id` (PK), `nombre`, `email`, `password`, `rol` (enum), `estado` | El rol es un simple enum — no se necesita RBAC completo todavía. |
| **Categoria** | Catálogo | `id` (PK), `nombre` | Ej. Lácteos, Bebidas, Limpieza. |
| **Producto** | Catálogo | `id` (PK), `categoria_id` (FK), `marca`, `nombre`, `presentacion`, `unidad_medida`, `contenido`, `activo` | El "Producto Maestro" — presentaciones distintas son productos distintos. |
| **AliasProducto** | Catálogo | `id` (PK), `producto_id` (FK), `alias`, `origen` | Sin campo de "confianza" todavía (eso llega en v2 con fuzzy matching). |
| **Supermercado** | Comercio | `id` (PK), `nombre`, `logo`, `sitio_web`, `activo` | Sin coordenadas — la ubicación vive en `Sucursal`. |
| **Sucursal** | Comercio | `id` (PK), `supermercado_id` (FK), `nombre`, `direccion`, `latitud`, `longitud`, `telefono`, `horario` | El Mapa y el Motor de Optimización calculan distancia hacia aquí. |
| **PrecioActual** | Comercio | `id` (PK), `producto_id` (FK), `sucursal_id` (FK), `precio_normal`, `precio_final`, `tiene_promocion`, `tipo_promocion`, `fecha_actualizacion`, `origen_dato` | El comparador siempre consulta esta tabla, nunca el historial. |
| **HistorialPrecio** | Comercio | `id` (PK), `producto_id` (FK), `sucursal_id` (FK), `precio_normal`, `precio_final`, `tipo_promocion`, `fecha`, `origen` | Append-only. |
| **ListaCompra** | Usuario/Compras | `id` (PK), `usuario_id` (FK), `nombre`, `presupuesto`, `fecha` | Una lista creada por el usuario. |
| **ListaCompraDetalle** | Usuario/Compras | `id` (PK), `lista_id` (FK), `producto_id` (FK), `cantidad`, `esencial` (bool), `permite_sustituto` (bool, reservado v2) | `esencial` alimenta directamente los hechos del Sistema Experto (ver nota en 12.3). |

### 12.2 Nivel 2 — Pipeline de datos y Sistema Experto

![ERD Nivel 2 - Pipeline y Sistema Experto](erd_nivel2_pipeline.png)

| Tabla | Campos | Notas |
|---|---|---|
| **ProductoRaw** | `id` (PK), `origen`, `nombre_original`, `precio`, `categoria_original`, `estado` (enum), `fecha` | Zona de staging — ningún dato entra al Catálogo Maestro sin pasar antes por aquí. |
| **ResultadoOptimizacion** | `id` (PK), `lista_compra_id` (FK), `score`, `ahorro`, `distancia`, `tiempo`, `supermercados`, `resultado_json`, `fecha` | El `resultado_json` guarda el detalle completo sin necesitar más tablas. |
| **Recomendacion** | `id` (PK), `resultado_optimizacion_id` (FK), `nivel` (enum), `mensaje`, `reglas_activadas` (json), `fecha` | Python nunca sabe que esta tabla existe — Laravel la llena tras recibir la respuesta. |
| **SistemaExpertoLog** | `id` (PK), `resultado_optimizacion_id` (FK), `request_json`, `response_json`, `duracion_ms`, `estado`, `fecha` | Útil para depurar por qué una regla se activó o no. |

### 12.3 Nota pendiente hacia `04-sistema-experto.md`

El campo `esencial` de `ListaCompraDetalle` es información que el Sistema Experto podría
aprovechar, pero para que realmente se use, el contrato JSON de esa API debería separar el hecho
`productos_disponibles` en `productos_esenciales_disponibles` y `productos_opcionales_disponibles`.
Mientras ese documento no se actualice, el dato existe en la base de datos sin que el razonamiento
del Sistema Experto lo use todavía.

### 12.4 Lo que queda fuera del v1.0 (a propósito)

**Aclaración importante:** las promociones **sí se evalúan en el MVP** — no están excluidas. Ya
viven como campos dentro de `PrecioActual` y `HistorialPrecio` (`tiene_promocion`,
`tipo_promocion`, `precio_normal` vs. `precio_final`), alimentan el módulo "Promociones
inteligentes" (sección 5.2) y el término `δ·(BeneficioPromociones)` del Score (sección 5.1). Lo
que **no** entra en v1.0 es tratar "Promoción" como una **entidad propia con su propia tabla** —
por ejemplo, códigos de cupón, campañas de marketing con vigencia independiente del precio, o
promociones tipo "3x2" que no se reducen a un precio final más bajo. Ese nivel de sofisticación
no hace falta todavía: el caso más común ("este producto está más barato por promoción") ya
queda cubierto con los campos actuales.

El resto de lo que sí queda fuera del v1.0 porque el MVP no lo usa: `Favoritos`,
`HistorialBusqueda`, `Notificaciones`, `Configuraciones`, `Publicidad`, `Cupones`,
`Suscripciones`. Pueden aparecer en una v1.1 si el proyecto avanza más allá del semestre.

---

## 13. Estado del proyecto y siguiente paso

```
Visión de negocio (ensayo)     ██████████  Terminado
Arquitectura                   ██████████  Terminado
ERD                             ██████████  Terminado
Plan de implementación          ██████████  Terminado
Documento Sistema Experto        █████████░  Falta reflejar la nota de la sección 12.3
Diseño detallado (wireframes)     ░░░░░░░░░░  Pendiente
Construcción del MVP               ░░░░░░░░░░  Pendiente
Pruebas                            ░░░░░░░░░░  Pendiente
Despliegue                          ░░░░░░░░░░  Pendiente
```

Esta arquitectura ya está congelada — no deberíamos seguir cambiándola sin una razón de peso
(y, si se cambia algo de fondo, debería documentarse como un ADR nuevo). El siguiente paso es
avanzar al diseño detallado: wireframes de las pantallas principales, definición formal de
endpoints (OpenAPI), y comenzar la construcción siguiendo el orden de `03-plan-implementacion.md`.
