<?php

namespace Tests\Feature;

use App\Models\Categoria;
use App\Models\HistorialPrecio;
use App\Models\Producto;
use App\Models\Sucursal;
use App\Models\Supermercado;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class HistorialPrecioTest extends TestCase
{
    use RefreshDatabase;

    private function setupProductoConHistorial(): array
    {
        $categoria = Categoria::create(['nombre' => 'Snacks']);
        $producto = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Gamesa',
            'nombre' => 'Galletas',
        ]);

        $super = Supermercado::create(['nombre' => 'Selectos', 'activo' => true]);
        $suc1 = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Suc 1',
            'direccion' => 'D1',
            'latitud' => 13.7,
            'longitud' => -89.2,
        ]);
        $suc2 = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Suc 5',
            'direccion' => 'D5',
            'latitud' => 13.7,
            'longitud' => -89.2,
        ]);

        // snapshot dentro de 90 días.
        HistorialPrecio::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $suc1->id,
            'precio_normal' => 2.0,
            'precio_final' => 1.85,
            'tipo_promocion' => null,
            'fecha' => now()->subDays(5),
            'origen' => 'manual',
        ]);

        // snapshot fuera de la ventana de 90 días → no debe aparecer.
        HistorialPrecio::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $suc1->id,
            'precio_normal' => 2.0,
            'precio_final' => 1.85,
            'tipo_promocion' => null,
            'fecha' => now()->subDays(120),
            'origen' => 'seed',
        ]);

        // snapshot en la segunda sucursal con promo.
        HistorialPrecio::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $suc2->id,
            'precio_normal' => 3.0,
            'precio_final' => 2.5,
            'tipo_promocion' => '2x1',
            'fecha' => now()->subDays(3),
            'origen' => 'scraper',
        ]);

        return ['producto' => $producto, 'suc1' => $suc1, 'suc2' => $suc2];
    }

    public function test_endpoint_devuelve_array_plano_de_los_ultimos_90_dias_agrupado_por_sucursal(): void
    {
        ['producto' => $producto, 'suc1' => $suc1, 'suc2' => $suc2] = $this->setupProductoConHistorial();

        $payload = $this->getJson("/api/productos/{$producto->id}/historial")->assertOk()->json();

        // Array plano (no paginador, no wrapping).
        $this->assertIsArray($payload);
        $this->assertCount(2, $payload);

        // Ambas sucursales representadas.
        $sucursales = collect($payload)->pluck('sucursal.id')->unique()->values()->all();
        $this->assertEqualsCanonicalizing([$suc1->id, $suc2->id], $sucursales);

        // Ordenado por fecha ASC (más viejo → más nuevo): Suc1 (5 días) antes que Suc2 (3 días).
        $this->assertSame($suc1->id, $payload[0]['sucursal']['id']);
        $this->assertSame($suc2->id, $payload[1]['sucursal']['id']);

        // El snapshot de hace 120 días fue filtrado por la ventana de 90 días.
        $this->assertFalse(collect($payload)->contains('origen', 'seed'));

        // tipo_promocion viaja cuando existe.
        $este = collect($payload)->first(fn ($r) => $r['sucursal']['id'] === $suc2->id);
        $this->assertSame('2x1', $este['tipo_promocion']);
    }

    public function test_parametro_dias_sobrescribe_la_ventana(): void
    {
        $categoria = Categoria::create(['nombre' => 'Pan']);
        $producto = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Bimbo',
            'nombre' => 'Pan',
        ]);

        $super = Supermercado::create(['nombre' => 'Walmart', 'activo' => true]);
        $suc = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Suc 1',
            'direccion' => 'D',
            'latitud' => 13.7,
            'longitud' => -89.2,
        ]);

        HistorialPrecio::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $suc->id,
            'precio_normal' => 1.0,
            'precio_final' => 0.9,
            'fecha' => now()->subDays(15),
            'origen' => 'manual',
        ]);

        // 15 días: estadentro de 30, fuera de 3.
        $this->getJson("/api/productos/{$producto->id}/historial?dias=3")
            ->assertOk()->assertJsonCount(0);

        $this->getJson("/api/productos/{$producto->id}/historial?dias=30")
            ->assertOk()->assertJsonCount(1);
    }
}
