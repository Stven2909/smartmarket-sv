<?php

namespace Database\Seeders;

use App\Models\AliasProducto;
use App\Models\Categoria;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\Sucursal;
use App\Models\Supermercado;
use Illuminate\Database\Seeder;

class DemoDataSeeder extends Seeder
{
    // Lee shared/demo_products.json y crea categorías, supermercados, sucursales,
    // productos, aliases y precios actuales. Los IDs lógicos del JSON (ej. "walmart",
    // "walmart-metrocentro", "FOREMOST-LECHE-1L") solo existen aquí en el seeder para
    // enlazar los datos entre sí de forma estable — no son columnas en la base de datos
    // todavía (ver nota sobre SKU al final de este archivo).
    public function run(): void
    {
        $path = base_path('../shared/demo_products.json');

        if (! file_exists($path)) {
            $this->command->warn("No se encontró demo_products.json en: {$path}");
            return;
        }

        $data = json_decode(file_get_contents($path), true);

        // 1. Categorías, indexadas por su id lógico ("lacteos", "bebidas", ...)
        $categoriasPorId = [];
        foreach ($data['categorias'] as $cat) {
            $categoriasPorId[$cat['id']] = Categoria::firstOrCreate(['nombre' => $cat['nombre']]);
        }

        // 2. Supermercados, indexados por su id lógico ("walmart", "selectos", ...)
        $supermercadosPorId = [];
        foreach ($data['supermercados'] as $super) {
            $supermercadosPorId[$super['id']] = Supermercado::firstOrCreate(
                ['nombre' => $super['nombre']],
                ['sitio_web' => $super['sitio_web'] ?? null, 'activo' => true]
            );
        }

        // 3. Sucursales, indexadas por su id lógico ("walmart-metrocentro", ...)
        //    Nunca dependen del texto del nombre para relacionarse con su supermercado.
        $sucursalesPorId = [];
        foreach ($data['sucursales'] as $suc) {
            $supermercado = $supermercadosPorId[$suc['supermercado']];

            $sucursalesPorId[$suc['id']] = Sucursal::firstOrCreate(
                ['nombre' => $suc['nombre']],
                [
                    'supermercado_id' => $supermercado->id,
                    'direccion' => $suc['direccion'] ?? null,
                    'latitud' => $suc['latitud'],
                    'longitud' => $suc['longitud'],
                ]
            );
        }

        // 4. Productos + aliases + precios
        foreach ($data['productos'] as $prod) {
            $categoria = $categoriasPorId[$prod['categoria']];

            $producto = Producto::firstOrCreate(
                ['nombre' => $prod['nombre'], 'marca' => $prod['marca']],
                [
                    'categoria_id' => $categoria->id,
                    'presentacion' => $prod['presentacion'] ?? null,
                    'unidad_medida' => $prod['unidad_medida'] ?? null,
                    'contenido' => $prod['contenido'] ?? null,
                    'activo' => true,
                ]
            );

            // El SKU (ej. "FOREMOST-LECHE-1L") todavía no es una columna en `productos`
            // (ver nota al final). Por ahora solo se usa como clave interna del seeder
            // y como semilla del primer alias, para no perder la trazabilidad del dato.
            foreach ($prod['aliases'] ?? [] as $alias) {
                AliasProducto::firstOrCreate([
                    'producto_id' => $producto->id,
                    'alias' => $alias,
                ], [
                    'origen' => 'seed_demo',
                ]);
            }

            foreach ($prod['precios'] as $precio) {
                $sucursal = $sucursalesPorId[$precio['sucursal']] ?? null;
                if (! $sucursal) {
                    continue;
                }

                $promocion = $precio['promocion'] ?? null;

                PrecioActual::updateOrCreate(
                    ['producto_id' => $producto->id, 'sucursal_id' => $sucursal->id],
                    [
                        'precio_normal' => $precio['precio_normal'],
                        'precio_final' => $precio['precio_final'],
                        // tiene_promocion es true solo si existe un objeto "promocion" real,
                        // no solo porque precio_final < precio_normal (ese caso ya se llama
                        // "descuento_directo" y también viaja como objeto de promoción).
                        'tiene_promocion' => $promocion !== null,
                        'tipo_promocion' => $promocion['tipo'] ?? null,
                        'fecha_actualizacion' => $precio['fecha_actualizacion'] ?? now(),
                        'origen_dato' => $precio['origen_dato'] ?? 'manual',
                    ]
                );
            }
        }

        $this->command->info('Datos de demo cargados correctamente.');
    }
}

// Nota sobre el SKU y la descripción de la promoción:
// -----------------------------------------------------
// El feedback del equipo sugiere agregar un SKU interno (ej. "FOREMOST-LECHE-1L") y una
// descripción de la promoción (ej. "Compra 2 y paga 1"). Ambos son útiles, pero implican
// agregar columnas nuevas a `productos` y `precios_actuales`, que hoy no existen en el ERD
// congelado (02-arquitectura.md v1.0). Por ahora este seeder los usa solo como datos internos
// del JSON para enlazar información de forma estable, sin tocar el esquema.
// Si el equipo decide que el SKU debe persistirse (por ejemplo, para que el scraper lo use
// como clave de emparejamiento contra ProductoRaw), lo correcto es documentarlo como una ADR
// nueva (ADR-010) antes de agregar la migración correspondiente.
