# Desarrollo en monorepo (backend + frontend juntos)

> **Actualización:** el repo pasó de separación por ramas a separación por carpetas en una sola
> rama. Las ramas `backend-laravel` y `frontend-react` quedaron como *legacy* y se eliminarán
> cuando la unificación se confirme estable. Este documento describe el flujo nuevo.

## Estructura

```
smartmarket/
├── backend-laravel/   → API Laravel
├── frontend-react/    → PWA React
├── docs/              → documentación
└── shared/            → datos compartidos
```

Ambos proyectos viven **al mismo tiempo** en tu checkout. Ya no se "pasa" de un proyecto al otro
con `git switch`: simplemente abrís la carpeta que vas a editar.

## Herramientas

- **Frontend (VS Code):** carpeta `frontend-react/`.
- **Backend (PhpStorm):** carpeta `backend-laravel/`.

Puedes tener ambas herramientas abiertas a la vez, y ambos servidores corriendo en paralelo.

## Cómo levantar cada proyecto

**Backend (terminal 1):**

```bash
cd backend-laravel
php artisan optimize:clear
php artisan serve
```

**Frontend (terminal 2):**

```bash
cd frontend-react
npm run dev
```

Ambos conviven sin conflictos: el API en `http://127.0.0.1:8000` y la PWA en
`http://localhost:5173`.

## Reglas de oro

1. **Todo el trabajo se hace sobre `develop`** (o una rama de feature creada desde `develop`).
2. Cada carpeta ignora sus propias dependencias: `vendor/`, `node_modules/`, `.env`, `dist/`,
   `storage/logs/`, etc. viven en disco pero **no** se versionan.
3. Un `git switch` normal **no borra nada**: todas las ramas del repo contienen ambas carpetas.
4. Los cambios del backend y del frontend se commitan **juntos** en la misma rama. Si un cambio
   toca solo una carpeta, se commitan solo esos archivos; git lo maneja solo.

## Flujo de ramas

```
main                  → estable (pendiente de recibir el árbol unificado)
develop               → rama de trabajo actual
backend-laravel       → legacy, sin tocar (se retira después de migrar main)
frontend-react        → legacy, sin tocar (se retira después de migrar main)
expert-system-python  → placeholder del Sistema Experto
```

Crear una rama de feature:

```bash
git switch develop
git switch -c feature-mi-cambio
# trabajar en backend-laravel/ y/o frontend-react/...
git add -A
git commit -m "feat: mi cambio"
git push -u origin feature-mi-cambio
```

Cuando la unificación esté probada (1-2 días), `main` recibe el árbol unificado y las ramas
legacy se eliminan. Los tags `archive/backend-laravel` y `archive/frontend-react` conservan los
últimos commits de esas ramas como respaldo.
