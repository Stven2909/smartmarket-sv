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
| Backend | Laravel 13 (PHP 8.3) |
| Panel admin | Filament 5.7 |
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
│   └── 04-sistema-experto.md
│
├── backend-laravel/
│   └── README.md              → API Laravel: instalación, endpoints, Motor de Optimización
├── frontend-react/
│
├── shared/
│   └── demo_products.json     → datos de demo que consume DemoDataSeeder
│
└── README.md
```

---

## Ramas (branches)

El repo está separado por tecnología para que cada rama solo contenga su árbol:

```
main                    → estado estable
backend-laravel         → solo backend-laravel/, docs/, shared/ (sin frontend-react/)
frontend-react          → solo frontend-react/, docs/, shared/ (sin backend-laravel/)
```

La separación se hace con `.gitignore` por rama, no borrando archivos del disco: los servidores
de desarrollo (Laragon + Vite) siguen corriendo desde el mismo checkout.

---

## Estado actual del proyecto

```
Visión de negocio (ensayo)     ██████████  Terminado
Arquitectura                   ██████████  Terminado
ERD                             ██████████  Terminado
Plan de implementación          ██████████  Terminado
Documento Sistema Experto        █████████░  Falta reflejar la nota del campo `esencial`
MVP Fase A (backend + API)       ██████████  Hecho: auth, catálogo, buscador, listas, comparador,
                                                       optimización, promociones, datos demo
MVP Fase B (frontend React)      ██████████  Hecho: PWA con home, buscador, comparador, listas, perfil
Mapa + Motor de Optimización UI  ████████░░  Motor listo en API; integración visual pendiente
Sistema Experto (Python)         ░░░░░░░░░░  Pendiente (Track B)
Pruebas                          ░░░░░░░░░░  Pendiente
Despliegue                        ░░░░░░░░░░  Pendiente
```

**Backend:** `php artisan serve` en `http://127.0.0.1:8000` — ver `backend-laravel/README.md`.
**Frontend:** Vite en `http://localhost:5173`.

**Siguiente paso:** conectar el frontend al Motor de Optimización (mapa + resultados por sucursal)
y arrancar el Track B del Sistema Experto.

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

## Definition of Done

Una tarea no se marca como terminada solo porque "ya funciona". Debe cumplir:

- [ ] Código implementado
- [ ] Sin errores conocidos importantes
- [ ] Probado (al menos manualmente)
- [ ] Documentado
- [ ] Revisado por otro integrante del equipo
- [ ] Integrado con el resto del sistema (si aplica)

Ver `docs/03-plan-implementacion.md`, sección 5, para el detalle completo.
