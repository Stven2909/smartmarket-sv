<?php

namespace Database\Seeders;

use App\Models\Categoria;
use App\Models\HistorialPrecio;
use App\Models\Producto;
use App\Models\Sucursal;
use Illuminate\Database\Seeder;
use Illuminate\Support\Carbon;

class HistoricoPrecioDemoSeeder extends Seeder
{
    public function run(): void
    {
        // 1. Asegurar categorías existen (tabla categorias: id, nombre, timestamps - sin activo)
        $categoriaGalletas = Categoria::firstOrCreate(
            ['nombre' => 'Snacks']
        );

        $categoriaPan = Categoria::firstOrCreate(
            ['nombre' => 'Pan']
        );

        // 2. 1 supermercado + 2 sucursales
        $super = \App\Models\Supermercado::firstOrCreate(
            ['nombre' => 'Selectos'],
            ['activo' => true, 'sitio_web' => null]
        );

        $suc1 = \App\Models\Sucursal::firstOrCreate(
            ['nombre' => 'Suc 1', 'supermercado_id' => $super->id],
            ['direccion' => 'Av. Principal', 'latitud' => 13.7, 'longitud' => -89.2]
        );

        $suc2 = \App\Models\Sucursal::firstOrCreate(
            ['nombre' => 'Suc 2', 'supermercado_id' => $super->id],
            ['direccion' => 'Av. Secundaria', 'latitud' => 13.71, 'longitud' => -89.19]
        );

        $ahora = Carbon::now();

        // 3. Producto: Galletas - con categoría Snacks
        $productoGalletas = Producto::firstOrCreate(
            ['nombre' => 'Galletas', 'marca' => 'Gamesa'],
            ['categoria_id' => $categoriaGalletas->id, 'activo' => true]
        );

        // 4. Producto: Pan - con categoría Pan
        $productoPan = Producto::firstOrCreate(
            ['nombre' => 'Pan', 'marca' => 'Bimbo'],
            ['categoria_id' => $categoriaPan->id, 'activo' => true]
        );

        // 5. Historial de precios para Galletas (4 snapshots)
        HistorialPrecio::create([
            'producto_id' => $productoGalletas->id,
            'sucursal_id' => $suc1->id,
            'precio_normal' => 2.00,
            'precio_final' => 1.75,
            'tipo_promocion' => '2x1',
            'fecha' => $ahora->copy()->subDays(5),
            'origen' => 'scraper',
        ]);

        HistorialPrecio::create([
            'producto_id' => $productoGalletas->id,
            'sucursal_id' => $suc1->id,
            'precio_normal' => 2.00,
            'precio_final' => 1.80,
            'tipo_promocion' => null,
            'fecha' => $ahora->copy()->subDays(15),
            'origen' => 'manual',
        ]);

        HistorialPrecio::create([
            'producto_id' => $productoGalletas->id,
            'sucursal_id' => $suc2->id,
            'precio_normal' => 3.00,
            'precio_final' => 2.50,
            'tipo_promocion' => 'Descuento',
            'fecha' => $ahora->copy()->subDays(30),
            'origen' => 'api',
        ]);

        HistorialPrecio::create([
            'producto_id' => $productoGalletas->id,
            'sucursal_id' => $suc2->id,
            'precio_normal' => 3.00,
            'precio_final' => 2.80,
            'tipo_promocion' => null,
            'fecha' => $ahora->copy()->subDays(45),
            'origen' => 'manual',
        ]);

        // 6. Historial de precios para Pan (4 snapshots)
        HistorialPrecio::create([
            'producto_id' => $productoPan->id,
            'sucursal_id' => $suc1->id,
            'precio_normal' => 1.50,
            'precio_final' => 1.20,
            'tipo_promocion' => '2x1',
            'fecha' => $ahora->copy()->subDays(3),
            'origen' => 'scraper',
        ]);

        HistorialPrecio::create([
            'producto_id' => $productoPan->id,
            'sucursal_id' => $suc1->id,
            'precio_normal' => 1.50,
            'precio_final' => 1.35,
            'tipo_promocion' => null,
            'fecha' => $ahora->copy()->subDays(20),
            'origen' => 'manual',
        ]);

        HistorialPrecio::create([
            'producto_id' => $productoPan->id,
            'sucursal_id' => $suc2->id,
            'precio_normal' => 1.75,
            'precio_final' => 1.40,
            'tipo_promocion' => 'Descuento',
            'fecha' => $ahora->copy()->subDays(50),
            'origen' => 'api',
        ]);

        HistorialPrecio::create([
            'producto_id' => $productoPan->id,
            'sucursal_id' => $suc2->id,
            'precio_normal' => 1.75,
            'precio_final' => 1.60,
            'tipo_promocion' => null,
            'fecha' => $ahora->copy()->subDays(75),
            'origen' => 'manual',
        ]);

        $this->command->info('Datos de historial de precios de demo cargados correctamente.');
    }
}