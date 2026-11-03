<?php

namespace Tests\Unit;

use App\Models\Categoria;
use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\Sucursal;
use App\Models\Supermercado;
use App\Models\User;
use App\Services\Optimization\ComparisonService;
use Carbon\Carbon;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ComparisonServiceTest extends TestCase
{
    use RefreshDatabase;

    public function test_comparacion_incluye_procedencia_origenes_y_fecha_mas_reciente(): void
    {
        $categoria = Categoria::create(['nombre' => 'Abarrotes']);
        $productoA = $this->crearProducto($categoria, 'Arroz');
        $productoB = $this->crearProducto($categoria, 'Frijoles');
        $lista = $this->crearLista($productoA, $productoB);
        $sucursalMixta = $this->crearSucursal('Selectos', 'Selectos Centro');
        $sucursalManual = $this->crearSucursal('Mercado local', 'Puesto 1');

        $fechaAnterior = Carbon::parse('2026-10-30 10:00:00');
        $fechaReciente = Carbon::parse('2026-11-01 15:30:00');

        $this->crearPrecio($productoA, $sucursalMixta, 'html-super-selectos', $fechaAnterior);
        $this->crearPrecio($productoB, $sucursalMixta, 'mock-seeder', $fechaReciente);
        $fechaManual = Carbon::parse('2026-11-02 09:00:00');
        $this->crearPrecio($productoA, $sucursalManual, 'manual', $fechaManual);

        $resultados = app(ComparisonService::class)->comparar($lista)['resultados'];
        $porSucursal = collect($resultados)->keyBy('sucursal_id');

        $this->assertSame('mixtos', $porSucursal[$sucursalMixta->id]['procedencia_precios']);
        $this->assertEqualsCanonicalizing(
            ['html-super-selectos', 'mock-seeder'],
            $porSucursal[$sucursalMixta->id]['origenes_precio'],
        );
        $this->assertSame(
            $fechaReciente->toIso8601String(),
            $porSucursal[$sucursalMixta->id]['precios_actualizados_en'],
        );

        $this->assertSame('manuales', $porSucursal[$sucursalManual->id]['procedencia_precios']);
        $this->assertSame(['manual'], $porSucursal[$sucursalManual->id]['origenes_precio']);
        $this->assertSame($fechaManual->toIso8601String(), $porSucursal[$sucursalManual->id]['precios_actualizados_en']);
    }

    public function test_marca_procedencia_desconocida_si_el_origen_no_esta_registrado(): void
    {
        $categoria = Categoria::create(['nombre' => 'Abarrotes']);
        $producto = $this->crearProducto($categoria, 'Arroz');
        $lista = $this->crearLista($producto);
        $sucursal = $this->crearSucursal('Tienda local', 'Centro');
        $fechaActualizacion = Carbon::parse('2026-11-02 09:00:00');
        $this->crearPrecio($producto, $sucursal, 'api-super-selectos', $fechaActualizacion);

        $resultado = app(ComparisonService::class)->comparar($lista)['resultados'][0];

        $this->assertSame('desconocidos', $resultado['procedencia_precios']);
        $this->assertSame(['api-super-selectos'], $resultado['origenes_precio']);
        $this->assertSame($fechaActualizacion->toIso8601String(), $resultado['precios_actualizados_en']);
    }

    private function crearProducto(Categoria $categoria, string $nombre): Producto
    {
        return Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Sin marca',
            'nombre' => $nombre,
            'unidad_medida' => 'lb',
            'activo' => true,
        ]);
    }

    private function crearLista(Producto ...$productos): ListaCompra
    {
        $usuario = User::create([
            'name' => 'Usuario de prueba',
            'email' => uniqid('comparison-', true).'@test.sv',
            'password' => 'password-secreto',
        ]);

        $lista = ListaCompra::create([
            'usuario_id' => $usuario->id,
            'nombre' => 'Canasta de prueba',
            'presupuesto' => 50,
            'estado' => 'activa',
            'fecha' => now(),
        ]);

        foreach ($productos as $producto) {
            ListaCompraDetalles::create([
                'lista_id' => $lista->id,
                'producto_id' => $producto->id,
                'cantidad' => 1,
                'esencial' => true,
            ]);
        }

        return $lista;
    }

    private function crearSucursal(string $supermercadoNombre, string $sucursalNombre): Sucursal
    {
        $supermercado = Supermercado::create(['nombre' => $supermercadoNombre]);

        return Sucursal::create([
            'supermercado_id' => $supermercado->id,
            'nombre' => $sucursalNombre,
            'direccion' => 'Dirección de prueba',
            'latitud' => 13.7,
            'longitud' => -89.2,
        ]);
    }

    private function crearPrecio(Producto $producto, Sucursal $sucursal, ?string $origen, Carbon $actualizado): void
    {
        PrecioActual::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $sucursal->id,
            'precio_normal' => 2.00,
            'precio_final' => 2.00,
            'origen_dato' => $origen,
            'fecha_actualizacion' => $actualizado,
        ]);
    }
}
