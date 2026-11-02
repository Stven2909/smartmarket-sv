<?php

namespace Tests\Feature;

use App\Models\Categoria;
use App\Models\HistorialPrecio;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\Supermercado;
use App\Models\Sucursal;
use Database\Seeders\MockSupermarketsSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

// ADR-012: las cadenas que no se sincronizan reciben datos mock deterministas.
class MockSupermarketsSeederTest extends TestCase
{
    use RefreshDatabase;

    private function producto(string $nombre): Producto
    {
        $categoria = Categoria::firstOrCreate(['nombre' => 'Pruebas']);

        return Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Marca',
            'nombre' => $nombre,
            'unidad_medida' => 'unidad',
            'contenido' => 1,
            'activo' => true,
        ]);
    }

    private function precioSuperSelectos(Producto $producto, float $precio): PrecioActual
    {
        $supermercado = Supermercado::firstOrCreate(['nombre' => 'Super Selectos']);
        $sucursal = Sucursal::firstOrCreate(
            ['supermercado_id' => $supermercado->id, 'nombre' => 'Selectos Centro'],
            ['direccion' => 'San Salvador'],
        );

        return PrecioActual::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $sucursal->id,
            'precio_normal' => $precio,
            'precio_final' => $precio,
            'tiene_promocion' => false,
            'fecha_actualizacion' => now(),
            'origen_dato' => 'manual',
        ]);
    }

    public function test_crea_precios_mock_para_las_cuatro_cadenas_sin_tocar_super_selectos(): void
    {
        $conPrecio = $this->producto('Leche entera');
        $sinPrecio = $this->producto('Frijol rojo');
        $precioSelectos = $this->precioSuperSelectos($conPrecio, 2.50);

        $this->seed(MockSupermarketsSeeder::class);

        foreach (['Walmart', 'Maxi Despensa', 'La Despensa de Don Juan', 'PriceSmart'] as $cadena) {
            $supermercado = Supermercado::where('nombre', $cadena)->first();

            $this->assertNotNull($supermercado, "Falta el supermercado {$cadena}");
            $this->assertSame(1, $supermercado->sucursales()->count(), "{$cadena} debe tener una sucursal mock");

            $sucursalId = $supermercado->sucursales()->value('id');

            foreach ([$conPrecio, $sinPrecio] as $producto) {
                $mock = PrecioActual::where('producto_id', $producto->id)
                    ->where('sucursal_id', $sucursalId)
                    ->sole();

                $this->assertSame(MockSupermarketsSeeder::ORIGEN, $mock->origen_dato);
                $this->assertGreaterThan(0, (float) $mock->precio_final);
                $this->assertLessThanOrEqual((float) $mock->precio_normal, (float) $mock->precio_final);
            }
        }

        // El precio real de Super Selectos no se modifica.
        $this->assertSame(2.50, (float) $precioSelectos->fresh()->precio_final);
        $this->assertSame('manual', $precioSelectos->fresh()->origen_dato);
    }

    public function test_es_idempotente_y_mantiene_los_mismos_precios(): void
    {
        $producto = $this->producto('Leche entera');
        $this->precioSuperSelectos($producto, 2.50);

        $this->seed(MockSupermarketsSeeder::class);

        $conteoPrecios = PrecioActual::count();
        $conteoHistorial = HistorialPrecio::count();
        $huella = PrecioActual::orderBy('id')->get(['producto_id', 'sucursal_id', 'precio_normal', 'precio_final'])
            ->toArray();

        $this->seed(MockSupermarketsSeeder::class);

        $this->assertSame($conteoPrecios, PrecioActual::count());
        $this->assertSame($conteoHistorial, HistorialPrecio::count());
        $this->assertSame(
            $huella,
            PrecioActual::orderBy('id')->get(['producto_id', 'sucursal_id', 'precio_normal', 'precio_final'])->toArray(),
        );
    }
}
