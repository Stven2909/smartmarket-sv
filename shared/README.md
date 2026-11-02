# shared/ — Datos compartidos del equipo

## `demo_products.json`

Dataset de ejemplo usado por los seeders (`DemoDataSeeder.php`) para poblar la base de datos
con los mismos datos de prueba en todo el equipo (ver `03-plan-implementacion.md`, Fase 1).

### Nota sobre `sku`, `id` y `promocion`

Este archivo **no es el modelo de datos** — el modelo de datos es el ERD congelado en
`docs/02-arquitectura.md` (v1.0). `demo_products.json` es solo un **formato de intercambio /
carga de datos**, y puede tener campos que el ERD no tiene, siempre que el seeder los traduzca
correctamente al modelo real antes de persistir.

En concreto:

- **`sku`** (ej. `"FOREMOST-LECHE-ENTERA-1L"`) es un identificador lógico del dataset. Se usa
  únicamente durante el seeder para evitar duplicados, relacionar aliases, cargar precios y
  generar referencias internas. **No forma parte del modelo de datos v1.0 ni se persiste en la
  base de datos.** `Producto.id` (autogenerado por PostgreSQL) sigue siendo la única clave
  primaria real.

- **`id`** en `categorias`, `supermercados` y `sucursales` (ej. `"walmart-metrocentro"`) cumple
  el mismo rol: es una clave lógica *dentro del JSON* para que los precios y sucursales se
  relacionen entre sí sin depender de coincidencias de texto en el nombre. Tampoco se persiste
  tal cual — el seeder los usa para resolver las relaciones y luego se apoya en los IDs reales
  que genera la base de datos.

- **`promocion`** (objeto con `tipo` y `descripcion`) es un formato enriquecido pensado para que
  el dataset ya esté preparado para el día que exista una entidad `Promocion` propia. Por ahora,
  el seeder solo extrae `promocion.tipo` y lo guarda en la columna `tipo_promocion` de
  `precios_actuales`, tal como lo define el ERD. El campo `descripcion` se ignora — no se pierde
  información real porque el dataset original vive aquí, en este archivo versionado.

### ¿Cuándo reconsiderar esto?

Si en algún momento aparece una necesidad arquitectónica real — integración con APIs oficiales,
sincronización entre varias fuentes de datos, importaciones masivas, códigos de barra reales,
identificadores externos — ahí sí correspondería evaluar una ADR nueva (por ejemplo, un futuro
ADR-010) para introducir un identificador de negocio estable en el modelo de datos real. Hoy esa
necesidad no existe: el sistema funciona bien con `Producto.id` como PK interna y `sku` solo como
identificador del dataset de prueba.
