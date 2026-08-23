<?php

namespace Tests\Feature;

use App\Filament\Widgets\EstadisticasGenerales;
use App\Models\Categoria;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ProductoRaw;
use App\Models\Supermercado;
use App\Models\Sucursal;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Livewire\Livewire;
use ReflectionMethod;
use Tests\TestCase;

class PanelStatsWidgetTest extends TestCase
{
    use RefreshDatabase;

    public function test_el_widget_muestra_los_cuatro_conteos_correctos(): void
    {
        $this->sembrarEscenario();

        $stats = $this->statsDelWidget();

        $this->assertSame(7, $stats['Productos activos']);
        $this->assertSame(4, $stats['Precios actualizados hoy']);
        $this->assertSame(13, $stats['Staging pendiente']);
        $this->assertSame(8, $stats['Sucursales']);
    }

    public function test_el_widget_renderiza_en_livewire(): void
    {
        $this->sembrarEscenario();

        Livewire::test(EstadisticasGenerales::class)
            ->assertSuccessful()
            ->assertSee('Estado general')
            ->assertSee('Productos activos')
            ->assertSee('Precios actualizados hoy')
            ->assertSee('Staging pendiente')
            ->assertSee('Sucursales');
    }

    private function statsDelWidget(): array
    {
        $metodo = new ReflectionMethod(EstadisticasGenerales::class, 'getStats');
        $metodo->setAccessible(true);

        $stats = [];
        foreach ($metodo->invoke(new EstadisticasGenerales) as $stat) {
            $stats[$stat->getLabel()] = $stat->getValue();
        }

        return $stats;
    }

    private function sembrarEscenario(): void
    {
        $supermercado = Supermercado::create([
            'nombre' => 'Selectos',
            'activo' => true,
        ]);

        // 8 sucursales en total (incluida la virtual online).
        for ($i = 1; $i <= 8; $i++) {
            if ($i === 8) {
                Sucursal::create([
                    'supermercado_id' => $supermercado->id,
                    'nombre' => 'Tienda en línea',
                    'direccion' => 'Virtual',
                    'latitud' => null,
                    'longitud' => null,
                    'es_online' => true,
                ]);

                continue;
            }

            Sucursal::create([
                'supermercado_id' => $supermercado->id,
                'nombre' => "Sucursal {$i}",
                'direccion' => "Dirección {$i}",
                'latitud' => 13.7,
                'longitud' => -89.2,
            ]);
        }

        $categoria = Categoria::create(['nombre' => 'Snacks']);

        // 7 activos + 2 inactivos = 9 productos.
        for ($i = 1; $i <= 9; $i++) {
            Producto::create([
                'categoria_id' => $categoria->id,
                'marca' => 'Marca',
                'nombre' => "Producto {$i}",
                'activo' => $i <= 7,
            ]);
        }

        $producto = Producto::first();
        $fechas = [now(), now(), now(), now(), now()->subDay()];
        $sucursalesPrecio = Sucursal::take(5)->get();

        foreach ($fechas as $indice => $fecha) {
            PrecioActual::create([
                'producto_id' => $producto->id,
                'sucursal_id' => $sucursalesPrecio[$indice]->id,
                'precio_normal' => 2.0,
                'precio_final' => 1.5,
                'tiene_promocion' => false,
                'origen_dato' => 'manual',
                'fecha_actualizacion' => $fecha,
            ]);
        }

        // 13 pendientes en staging.
        for ($i = 1; $i <= 13; $i++) {
            ProductoRaw::create([
                'fuente' => 'super-selectos',
                'sku_externo' => "SKU-{$i}",
                'nombre' => "Crudo {$i}",
                'precio_final' => 1.0,
                'raw_payload' => [],
                'estado' => 'pendiente',
            ]);
        }
    }
}
