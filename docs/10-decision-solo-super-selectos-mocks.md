# ADR-12: Sincronización limitada a Super Selectos y datos mock para el resto

**Estado:** Aceptado — decisión del equipo, 2026-11-01
**Ajusta el alcance de:** ADR-10 (`07-decision-extractor-fuentes-riesgo.md`)
**Contexto técnico:** `06-referencia-extractor-vtex.md` §4–§5, `backend-laravel/config/price_providers.php`

---

## Contexto

ADR-10 aprobó la automatización de cuatro fuentes: Super Selectos (modo HTML) y las tres
tiendas VTEX de la familia Walmart CA (Walmart SV, Maxi Despensa y La Despensa de Don Juan).
PriceSmart quedó excluido de la automatización por la prohibición explícita de su `robots.txt`,
pero seguía dependiendo de carga manual.

Para la entrega académica el equipo decidió reducir el alcance operativo:

- El backend y el frontend se mantienen en local; solo el Sistema Experto se despliega en Render.
- No se quiere asumir el mantenimiento de cuatro extractores ni la variabilidad de sus
  catálogos durante las demostraciones y la defensa.
- Se necesita que el comparador y el Motor de Optimización tengan alternativas de precio para
  todas las cadenas, aunque no provengan de datos reales.

Mantener los cuatro extractores activos agregaba superficie de fallo (bloqueos, cambios de
maquetación, tiempos de espera) sin aportar valor proporcional al objetivo de la entrega.

## Decisión

1. **Solo Super Selectos se sincroniza por webscraping.** Es la única fuente incluida en
   `price_providers.sincronizacion.fuentes_permitidas`.
2. **`precios:sync` y `precios:procesar` rechazan cualquier otra fuente**, incluso si algún día
   se vuelve a habilitar su driver. Sin `--fuente`, ambos comandos usan `super-selectos` como
   fuente por defecto.
3. **Walmart, Maxi Despensa, La Despensa de Don Juan y PriceSmart se alimentan con datos mock**
   generados por `MockSupermarketsSeeder`. Los precios son deterministas, se derivan del último
   precio de Super Selectos cuando existe y, si no, del propio producto.
4. **Los datos mock se identifican con `origen_dato = 'mock-seeder'`** y no modifican los precios
   de Super Selectos. El seeder es idempotente.
5. **Los drivers VTEX permanecen en el código, deshabilitados.** No se eliminan para no perder el
   trabajo de ADR-10 ni impedir una reactivación futura.
6. **Súper San Francisco sigue fuera del alcance**, sin driver activo y sin datos mock, porque
   requiere un convenio comercial (doc 06 §1).

## Implementación

| Componente | Cambio |
|---|---|
| `config/price_providers.php` | Nueva sección `sincronizacion.fuentes_permitidas = ['super-selectos']` y `fuente_por_defecto = 'super-selectos'`. Las demás fuentes quedan con `enabled=false` y `mock=true`. |
| `app/Console/Commands/PreciosSync.php` | Valida la lista blanca, rechaza fuentes deshabilitadas y, sin `--fuente`, solo recorre fuentes permitidas y habilitadas. |
| `app/Console/Commands/PreciosProcesar.php` | Valida la lista blanca y procesa `super-selectos` por defecto. |
| `database/seeders/MockSupermarketsSeeder.php` | Crea/reutiliza sucursales mock y genera precios deterministas para todos los productos activos. Registrado en `DatabaseSeeder`. |
| `tests/Feature/PreciosSyncCommandTest.php` | Cubre el rechazo de fuentes fuera de la lista blanca. |
| `tests/Feature/PreciosProcesarCommandTest.php` | Cubre el procesamiento exclusivo de Super Selectos. |
| `tests/Feature/MockSupermarketsSeederTest.php` | Cubre creación, no alteración de Super Selectos e idempotencia. |

## Consecuencias

**Positivas**

- Un solo extractor que mantener y una sola superficie de fallo para las demostraciones.
- El comparador conserva cuatro cadenas adicionales con precios estables y reproducibles.
- El cambio es reversible: basta con volver a incluir una fuente en `fuentes_permitidas` y
  activarla, sin tocar el pipeline.
- La trazabilidad distingue datos reales (`html-super-selectos`) de datos simulados
  (`mock-seeder`).

**Negativas y límites**

- Los precios de Walmart, Maxi Despensa, Don Juan y PriceSmart **no son reales**; son datos de
  demostración. No deben presentarse como precios de mercado ni usarse para conclusiones
  comerciales.
- El frontend no muestra todavía el `origen_dato`; la distinción queda en la base de datos y en
  la documentación. Si el mock se expone en una demo, debe aclararse verbalmente.
- Al desactivar los drivers VTEX, la cobertura de surtido real se reduce a Super Selectos.
- Los precios mock no se actualizan solos: cambian únicamente al ejecutar el seeder.

## Condiciones para reactivar una fuente

1. Volver a incluir su clave en `sincronizacion.fuentes_permitidas`.
2. Poner `enabled = true` y `mock = false` en `config/price_providers.php`.
3. Verificar que sus pruebas de driver sigan pasando y que el contrato de staging no haya
   cambiado.
4. Registrar la reactivación como una actualización de este ADR-012 o como un ADR nuevo.

## Referencias

- `docs/07-decision-extractor-fuentes-riesgo.md` — ADR-10, alcance original y obligaciones.
- `docs/06-referencia-extractor-vtex.md` — veredicto legal por fuente.
- `docs/02-arquitectura.md` §11 — registro de ADRs.
