# Desarrollo en ramas separadas (backend-laravel / frontend-react)

El repo está separado por tecnología: la rama `backend-laravel` solo contiene su árbol (sin
`frontend-react/`) y la rama `frontend-react` solo contiene el suyo (sin `backend-laravel/`). La
separación se logra con `.gitignore` por rama, **no** borrando archivos del disco: los servidores
de desarrollo corren desde el mismo checkout.

## Herramientas

- **Frontend (VS Code):** carpeta `frontend-react/`, rama `frontend-react`.
- **Backend (PhpStorm):** carpeta `backend-laravel/`, rama `backend-laravel`.

## Regla de oro

> Editá el frontend solo con el checkout en `frontend-react`, y el backend solo con el checkout en
> `backend-laravel`.

Mientras estás en una rama, los archivos de la **otra** carpeta son "ignorados" para git: podés
abrirlos y editarlos (VS Code / PhpStorm), pero git **no ve esos cambios**, y un `git switch`
pelado los **pisa o borra sin avisar**.

## Forma fácil: los scripts (recomendado)

Doble clic (o ejecutar desde la terminal) según lo que vayas a trabajar:

| Cuando voy a trabajar… | Ejecuto |
|---|---|
| El **frontend** | `frontend-on.bat` |
| El **backend** | `backend-on.bat` |

Qué hacen los scripts:

1. Cancela si hay cambios sin commitear en la rama actual.
2. Hace **backup** de tu carpeta destino antes de cambiar (para no perder ediciones "invisibles").
3. `git switch` a la rama destino.
4. Restaura la otra carpeta en disco (para que el servidor siga funcionando).
5. Re-aplica el backup: si había ediciones, quedan como **modificaciones visibles** (`M`) en la rama
   destino, listas para commitear.

Si no hay nada que cambiar (ya estás en la rama), el script lo avisa y no hace nada.

## Forma manual

**Pasarse al frontend:**

```bash
git switch frontend-react
git restore --source=backend-laravel --worktree -- backend-laravel
```

**Volver al backend:**

```bash
git switch backend-laravel
git restore --source=frontend-react --worktree -- frontend-react
```

## Lo que NUNCA se borra al cambiar de rama

`vendor/`, `node_modules/`, `.env`, `.env.local` y `dist/` están ignorados en ambas ramas, así que
los servidores (Laragon + Vite) sobreviven al switch. Solo se restaura el código fuente.

## Cómo recuperar archivos si algo se pierde

Desde cualquier rama, restaurar a mano el contenido de una carpeta desde su rama:

```bash
git restore --source=backend-laravel --worktree -- backend-laravel
git restore --source=frontend-react --worktree -- frontend-react
```

## Recordatorio

Antes de un `git switch` manual, commitéa los cambios de la rama actual:

```bash
git add -A
git commit -m "WIP"
```
