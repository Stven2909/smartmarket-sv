# Sincronización segura con el repositorio del equipo

## Objetivo

Mantener `Stven2909/smartmarket-sv:expert-system-python` alineada con las mejoras probadas en `HenryBo06/Sistema-experto-fork:main`, **sin modificar** la rama `develop` donde se trabaja en Laravel/React.

El 3 de noviembre de 2026 se comprobó que el commit del equipo `03c256b4ea1df05ed6c5e1ad26ca53cc72036292` seguía siendo ancestro de nuestro `main`. Al inicio de HU-22 el fork ya llevaba 246 commits de ventaja. El script vuelve a consultar el origen antes de cada publicación: estos números **son observaciones históricas**, no una garantía de que siga siendo posible el avance rápido. La conexión GitHub de este chat puede leer el repositorio del compañero, pero `update_ref` devolvió `Resource not accessible by integration`; eso no demuestra que las credenciales Git personales del usuario carezcan de permisos.

## Rama espejo dentro de nuestro fork (automática)

`HenryBo06/Sistema-experto-fork:main` y `HenryBo06/Sistema-experto-fork:expert-system-python` pertenecen al **mismo repositorio privado**. El workflow `.github/workflows/sync-python-mirror.yml` se ejecuta al actualizar `main` y hace un avance rápido normal, solo en la rama espejo del fork. Verifica el último commit de `main` y se detiene si descubre divergencias. No utiliza `--force`, no accede a repositorios externos y no hace cambios en `develop`.

**Son dos tareas distintas:** mantener las dos ramas propias iguales es automático; publicar los commits del fork en `Stven2909/smartmarket-sv:expert-system-python` sigue necesitando un push autenticado como usuario con permisos. Esta última operación se realiza usando el script PowerShell descrito más abajo.

## Pasos desde Windows PowerShell

Necesitas un clon actualizado de nuestro fork y una cuenta con permisos `write` en `Stven2909/smartmarket-sv` para subir cambios a la rama del equipo. Git Credential Manager puede solicitar autenticación; no añadas claves o tokens al código.

```powershell
git clone https://github.com/HenryBo06/Sistema-experto-fork.git
cd Sistema-experto-fork

# Inspección sin publicar cambios:
.\scripts\sync_upstream_expert.ps1

# Publica únicamente si el script confirma que es un fast-forward:
.\scripts\sync_upstream_expert.ps1 -Apply
```

Si PowerShell bloquea la ejecución por la política del equipo, revisa las reglas de ejecución con tu administrador o ejecuta las mismas operaciones Git manualmente. No se requiere cambiar globalmente la política de seguridad.

## Salvaguardas

- Se verifica que `origin` corresponda a nuestro fork.
- Se recuperan las ramas más recientes antes de decidir.
- Se exige que `expert-system-python` sea ancestro de `origin/main`. Si la rama del compañero tiene trabajo adicional o divergente, la operación se detiene.
- El modo por defecto no hace `push`. El parámetro `-Apply` realiza un `git push` normal, nunca un `git push --force`.
- Git rechaza un `push` no fast-forward si la rama del equipo cambia durante el proceso.
- No se crean commits, ni se mezcla `develop`, ni se cambia la rama del usuario que ejecuta el script.

## Verificaciones posteriores

1. Revisa el commit final en `https://github.com/Stven2909/smartmarket-sv/tree/expert-system-python`.
2. Comprueba el pipeline de pruebas Python correspondiente al nuevo commit.
3. Revisa los endpoints `/health`, `/api/v1/recommend` y `/api/v1/chat` si esa rama se despliega en otro servicio.
4. En futuros cambios, fusiona primero el PR correspondiente en **nuestro** `main`, comprueba su CI y después repite la sincronización. Si hay divergencia, revisa los cambios ajenos antes de decidir cómo integrarlos.

## Por qué no se habilitó un push automático de GitHub Actions

Los permisos de GitHub de este entorno no permiten crear una rama en el repositorio del compañero (HTTP 403). No se almacenan credenciales ajenas ni se intenta eludir ese control. El script local permite usar permisos de Git concedidos directamente a la persona responsable, sin introducir un token compartido en GitHub Actions.
