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
00-contexto-proyecto.md     → resumen ejecutivo para retomar desarrollo
01-vision-negocio.md        → el ensayo grupal (problema, impacto social, modelo de negocio)
02-arquitectura.md          → arquitectura técnica congelada (v1.0), stack, ERD, ADRs
03-plan-implementacion.md   → roadmap, fases, Track A / Track B, Definition of Done
04-sistema-experto.md       → especificación del Sistema Experto (reglas, contrato JSON)
05-decision-costo-combustible.md
06-referencia-extractor-vtex.md
07-decision-extractor-fuentes-riesgo.md
08-decision-sucursal-tienda-online.md
09-preguntas-chat-experto.md → temas que responde el chat explicativo
CONTEXTO-SISTEMA-EXPERTO.md → guía de integración Laravel ↔ Python
```

> `02-arquitectura.md` está **congelado**: no se cambian decisiones de fondo ahí sin pasar antes
> por los Principios de Arquitectura (sección 1) y sin dejarlo registrado como una ADR nueva.

---

## Requisitos

- **Git** (clonar el repo)
- **PHP 8.3** + **Composer** (backend)
- **PostgreSQL** (base de datos)
- **Node.js** + **npm** (frontend)
- **Laragon** (recomendado en Windows para el entorno PHP/PostgreSQL)

---

## Estructura del repositorio

Monorepo: todos los proyectos viven juntos en el mismo repo, cada uno en su carpeta.

```
smartmarket/
│
├── backend-laravel/        → API Laravel + Filament (auth, catálogo, listas, optimización,
│   │                         pipeline de precios, integración con el experto)
│   └── README.md           → instalación, endpoints, Motor de Optimización, Sistema Experto
│
├── frontend-react/         → PWA React + Vite + Tailwind
│   └── README.md           → instalación, scripts, estructura y PWA
│
├── docs/                   → documentación técnica y de negocio (00–09 + atlas/evidencia)
├── shared/                 → datos compartidos (demo_products.json)
│
├── .github/                → workflows de CI (`.github/workflows/ci.yml`)
├── docker/                 → contenedores (pendiente de llenar)
├── scripts/                → utilidades del repo (pendiente de llenar)
│
├── .editorconfig           → reglas de formato compartidas (LF, UTF-8)
└── README.md
```

Cada carpeta maneja sus propias dependencias y archivos ignorados (`vendor/`, `node_modules/`,
`.env`, `dist/`, etc.) a través de su propio `.gitignore`.

---

## Cómo levantar el backend

```bash
cd backend-laravel
composer install
cp .env.example .env        # configurar base de datos PostgreSQL
php artisan key:generate
php artisan migrate --seed
php artisan optimize:clear
php artisan serve
```

El API queda en `http://127.0.0.1:8000`. Detalles en `backend-laravel/README.md`.

---

## Cómo levantar el frontend

```bash
cd frontend-react
npm install
npm run dev
```

La PWA queda en `http://localhost:5173`. Verifica que el API responda en `:8000` (el frontend
apunta a esa URL por defecto; se configura en `frontend-react/src/api/client.ts`).

---

## Flujo de ramas

```
main                  → rama principal (estable)
develop               → rama de trabajo actual (backend + frontend unificados)
backend-laravel       → rama legacy (solo backend) — pendiente de retirar
frontend-react        → rama legacy (solo frontend) — pendiente de retirar
expert-system-python  → rama legacy; el servicio Python vive en un repositorio aparte
```

> **Sistema Experto:** el servicio Python/FastAPI se mantiene fuera de este monorepo.
> Laravel lo consume por HTTP mediante `EXPERT_SYSTEM_URL`; React nunca lo llama
> directamente. La guía de integración está en `docs/CONTEXTO-SISTEMA-EXPERTO.md`.

- **Trabajo normal:** se trabaja sobre `develop` y se crean ramas de feature desde ahí
  (`git switch -c feature-x`). Cada rama derivada contiene **ambos** proyectos.
- **`git switch` seguro:** al estar todo en una sola rama, cambiar de rama ya **no borra** carpetas
  ni requiere scripts de restauración.
- **Tags de respaldo:** `archive/backend-laravel` y `archive/frontend-react` apuntan a los últimos
  commits de las ramas legacy, por si hace falta recuperar algo.
- **Migración a `main`:** se realizará cuando la unificación haya sido probada (1-2 días);
  entonces `main` recibirá el árbol unificado y las ramas legacy se eliminarán.

---

## Estado actual del proyecto

```
Visión de negocio (ensayo)     ██████████  Terminado
Arquitectura                   ██████████  Terminado
ERD                             ██████████  Terminado
Plan de implementación          ██████████  Terminado
Documento Sistema Experto        ██████████  Terminado (diseño + nota de implementación)
MVP Fase A (backend + API)       ██████████  Auth, catálogo, buscador, listas, comparador,
                                                        optimización, promociones, historial y pipeline de precios
MVP Fase B (frontend React)      ██████████  PWA con home, buscador, comparador, listas, perfil,
                                                        promociones, historial y chat explicativo
Sistema Experto (Python)         ██████████  Servicio desplegado e integrado (recommend + chat)
Pruebas                          ███████░░░  Backend: 117 tests. Frontend: sin tests automatizados
Mapa de sucursales               ░░░░░░░░░░  Pendiente (la optimización ya funciona; falta la vista de mapa)
Despliegue                       ██████████  Backend/frontend en local; Sistema Experto en Render
CI/CD                            ██████████  Workflow de lint + build + tests en verde (GitHub Actions)
```

**Siguiente paso:** completar la vista de mapa y cerrar la deuda técnica documentada en
`docs/03-plan-implementacion.md`. El backend y el frontend se quedan en local; solo el Sistema
Experto se despliega en Render.

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
