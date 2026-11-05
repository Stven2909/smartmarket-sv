# Preparación y guion de la demo final

## Datos locales

En el backend, con PostgreSQL local disponible:

```powershell
php artisan db:seed --class="Database\Seeders\DemoPresentationSeeder"
php artisan catalogo:auditoria
```

El seeder está limitado a `local` y `testing`. Es idempotente y crea o actualiza
la lista **DEMO · Lista mixta y subtotal parcial** para `usuario@smartmarket.sv`.
Contiene siete productos, mezcla esenciales y opcionales, y fija un presupuesto
de $18.50. Completa las marcas y categorías de Club Social y Snickers. Los
precios de cadenas sin sincronización real quedan marcados como simulados.

En la base de datos local revisada el 3 de noviembre de 2026 había 154 productos;
145 carecían de marca útil y categoría específica tras curar los dos productos
de marca reconocible incluidos en la lista de demo. No se asignan marcas ni
categorías por heurísticas al catálogo completo: para la demo se curan los siete
productos concretos y el resto queda como deuda documentada por la auditoría.
El inventario varía según las sincronizaciones locales.

## Integración del Sistema Experto

Laravel lee `EXPERT_SYSTEM_API_KEY` del `.env` local y lo envía en `X-API-Key`.
El servicio Python lee el mismo secreto en `SMARTMARKET_API_KEY`; ambas variables
deben tener el mismo valor. En Render el servicio exige la variable para iniciar
y mantiene `/health` público. La API Key no se guarda en Git.

Precalienta el servicio unos minutos antes de la presentación abriendo:

```text
https://sistema-experto-fork.onrender.com/health
```

El código del servicio Python valida `X-API-Key` y en Render falla al iniciar
si falta `SMARTMARKET_API_KEY`. Antes de la demo, confirma en el panel de Render
que esa variable tenga el mismo valor que `EXPERT_SYSTEM_API_KEY` en el backend
y que la última revisión esté desplegada. La comprobación remota ya se hizo:
sin clave responde HTTP 401 y con la clave local responde HTTP 200 con
`version_reglas` 1.3.2.

## Guion de 10–12 minutos

1. Inicia Laravel, PostgreSQL y React; entra con la cuenta local de demostración.
2. Abre **Mis Listas** y carga la lista de demo preparada.
3. En **Comparar**, distingue precio más bajo, mejor Score y subtotal parcial.
   Los datos mock aparecen identificados como simulados.
4. En **Mis Listas**, optimiza usando las coordenadas de la sucursal Selectos
   Centro (`13.6989`, `-89.1914`). Abre la explicación del experto y el chat.
   Si el experto clasifica como **Buena** una alternativa con faltantes
   (reglas R13/R16), aclara que el aviso de subtotal parcial se mantiene y que
   el ranking local no cambió.
5. Muestra la resiliencia: el ranking local permanece si Python no responde o
   devuelve un cuerpo que incumple el contrato.
6. Cierra con `php artisan test`, `npm run build`, `npm run lint`,
   `php artisan catalogo:auditoria`, la arquitectura y los límites conocidos.

## Límites que conviene declarar

- Los precios mock no son cotizaciones reales; Super Selectos es la única
  fuente sincronizada por extracción web en el alcance actual.
- La auditoría sigue reportando productos sin marca o categoría específica.
- Las alternativas se consultan secuencialmente al Sistema Experto; no se
  promete paralelismo ni una latencia fija, especialmente con cold start.
- El frontend no cifra secretos; la API Key solo vive en los `.env` de servidor.
