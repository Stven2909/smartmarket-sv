# SmartMarket SV

Plataforma web (PWA) para comparar precios, promociones, disponibilidad y ubicación de
supermercados en El Salvador, con un Motor de Optimización y un Sistema Experto (Python) que
recomiendan la mejor alternativa de compra según costo, distancia y tiempo.

Proyecto de emprendimiento social desarrollado para las materias de **Emprendedurismo** y
**Sistemas Expertos**.

---

## Documentación

Toda la documentación técnica y de negocio vive en `docs/`. Orden recomendado de lectura:

```
01-vision-negocio.md        → el ensayo grupal (problema, impacto social, modelo de negocio)
02-arquitectura.md          → arquitectura técnica congelada (v1.0), stack, ERD, ADRs
03-plan-implementacion.md   → roadmap, fases, Track A / Track B, Definition of Done
04-sistema-experto.md       → especificación del Sistema Experto (reglas, contrato JSON)
```

> `02-arquitectura.md` está **congelado**: no se cambian decisiones de fondo ahí sin pasar antes
> por los Principios de Arquitectura (sección 1) y sin dejarlo registrado como una ADR nueva.

---

## Stack

| Parte | Tecnología |
|---|---|
| Frontend | React + Tailwind CSS (PWA) |
| Backend | Laravel 12 (PHP) |
| Panel admin | Filament |
| Base de datos | PostgreSQL |
| Mapas | Leaflet + OpenStreetMap |
| Autenticación | Laravel Sanctum |
| Sistema Experto | Python (motor de reglas — tecnología exacta pendiente de confirmar) |

---

## Estructura del repositorio

```
smartmarket/
│
├── docs/
│   ├── 01-vision-negocio.md
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

---

## Organización del equipo

El proyecto se trabaja como **dos tracks que colaboran**, no como uno solo:

- **Track A** — Laravel + React: catálogo, comparador, motor de optimización, mapa, presupuesto,
  panel admin, frontend.
- **Track B** — Sistema Experto (Python): aislado al inicio, con datos de prueba, se integra en
  la Fase 7 (ver `docs/03-plan-implementacion.md`).

Ambos tracks comparten desde el día 0 el **contrato JSON** (cómo se hablan Laravel y Python).

### Integrantes

1. Henry Barrientos
2. Fernando Herrera
3. Isaac Renderos
4. Cristhofer Rivas
5. Steven Rivera
6. José Vigil (representante)

---

## Ramas (branches)

```
main                    → siempre desplegable / estable, solo se llega por PR desde develop
develop                 → rama de integración diaria de ambos tracks
├─ feature/track-a-...  → tareas de Laravel + React (ej. feature/track-a-auth-sanctum)
└─ feature/track-b-...  → tareas del Sistema Experto (ej. feature/track-b-motor-reglas)
```

**Reglas:**
- Nombres de rama en minúsculas y con guiones: `feature/track-a-nombre-corto` o
  `feature/track-b-nombre-corto`.
- Nunca se hace commit directo a `main` ni a `develop` — todo entra por Pull Request.
- Merge a `main` solo cuando haya una demo estable o se llegue a la fase de despliegue.

---

## Definition of Done

Una tarea no se marca como terminada solo porque "ya funciona". Debe cumplir:

- [ ] Código implementado
- [ ] Sin errores conocidos importantes
- [ ] Probado (al menos manualmente)
- [ ] Documentado
- [ ] Revisado por otro integrante del equipo
- [ ] Integrado con el resto del sistema (si aplica)

Ver `docs/03-plan-implementacion.md`, sección 5, para el detalle completo.

---

## Estado actual del proyecto

```
Visión de negocio (ensayo)     ██████████  Terminado
Arquitectura                   ██████████  Terminado
ERD                             ██████████  Terminado
Plan de implementación          ██████████  Terminado
Documento Sistema Experto        █████████░  Falta reflejar la nota del campo `esencial`
Diseño detallado (wireframes)     ░░░░░░░░░░  Pendiente
Construcción del MVP               ░░░░░░░░░░  Pendiente
Pruebas                            ░░░░░░░░░░  Pendiente
Despliegue                          ░░░░░░░░░░  Pendiente
```

**Siguiente paso:** Fase 0B — casos de uso, contrato JSON congelado (Laravel ↔ Python),
documentación OpenAPI y wireframes, antes de arrancar la Fase 1 (base de datos y autenticación).
