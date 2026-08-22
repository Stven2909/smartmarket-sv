<?php

namespace Tests\Unit;

use App\Models\Categoria;
use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ResultadoOptimizacion;
use App\Models\Supermercado;
use App\Models\Sucursal;
use App\Models\User;
use App\Services\Optimization\OptimizationService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

// Pruebas de regresion del Motor de Optimizacion tras ADR-05:
// CostoCombustible ($) fue reemplazado por PenalizacionDistancia
// (normalizada 0-1 contra el set de alternativas evaluadas).
// Formula congelada en 02-arquitectura.md seccion 5.1.
class OptimizationServiceTest extends TestCase
{
    use RefreshDatabase;

    // El usuario esta parado exactamente sobre la sucursal cercana: su
    // distancia Haversine es 0 km y la penalizacion esperada es 0 sin ambiguedad.
    private const LAT_USUARIO = 13.698900;
    private const LNG_USUARIO = -89.191400;

    public function test_penalizacion_distancia_se_mantiene_entre_0_y_1(): void
    {
        $mundo = $this->crearMundoDosSucursales();
        $salida = $this->optimizar($mundo['lista']);

        $this->assertCount(2, $salida['resultados']);

        foreach ($salida['resultados'] as $resultado) {
            $this->assertArrayHasKey('distancia_km', $resultado);
            $this->assertArrayHasKey('penalizacion_distancia', $resultado);

            // Nucleo de ADR-05: la distancia ya no se dolariza ni emite el campo viejo.
            $this->assertArrayNotHasKey('costo_combustible', $resultado);
            $this->assertGreaterThanOrEqual(0.0, $resultado['penalizacion_distancia']);
            $this->assertLessThanOrEqual(1.0, $resultado['penalizacion_distancia']);
        }

        $this->assertArrayNotHasKey('costo_combustible', $salida['mejor_opcion']);
    }

    public function test_sucursal_mas_cercana_recibe_cero_y_la_mas_lejana_uno(): void
    {
        $mundo = $this->crearMundoDosSucursales();
        $salida = $this->optimizar($mundo['lista']);

        $porSucursal = [];
        foreach ($salida['resultados'] as $resultado) {
            $porSucursal[$resultado['sucursal_id']] = $resultado;
        }

        $this->assertEqualsWithDelta(0.0, $porSucursal[$mundo['cercana']->id]['distancia_km'], 0.0001);
        $this->assertEqualsWithDelta(0.0, $porSucursal[$mundo['cercana']->id]['penalizacion_distancia'], 0.0001);

        $this->assertGreaterThan(0.0, $porSucursal[$mundo['lejana']->id]['distancia_km']);
        $this->assertEqualsWithDelta(1.0, $porSucursal[$mundo['lejana']->id]['penalizacion_distancia'], 0.0001);
    }

    public function test_la_sucursal_mas_cercana_no_recibe_penalizacion_aunque_sea_la_mas_cara(): void
    {
        // En este mundo la sucursal cercana es la MAS CARA (2.50 vs 2.00):
        // aunque pierda en el Score frente a la barata-lejana, su penalizacion
        // por distancia debe seguir siendo 0.
        $mundo = $this->crearMundoDosSucursales();
        $salida = $this->optimizar($mundo['lista']);

        $porSucursal = [];
        foreach ($salida['resultados'] as $resultado) {
            $porSucursal[$resultado['sucursal_id']] = $resultado;
        }

        $cercana = $porSucursal[$mundo['cercana']->id];
        $this->assertEqualsWithDelta(0.0, $cercana['penalizacion_distancia'], 0.0001);

        // Con distancia 0 los demas terminos se anulan (β·0, γ·tiempo(0)=0,
        // −δ·promos(0)=0): el Score se reduce al peso alpha por el costo.
        $alpha = config('optimization.pesos')['alpha'];
        $this->assertEqualsWithDelta($alpha * $cercana['costo_total'], $cercana['score'], 0.001);
    }

    public function test_resultados_quedan_ordenados_por_score_ascendente_con_mejor_opcion_primera(): void
    {
        $mundo = $this->crearMundoDosSucursales();
        $salida = $this->optimizar($mundo['lista']);

        $scores = array_column($salida['resultados'], 'score');
        $ordenados = $scores;
        sort($ordenados);
        $this->assertSame($ordenados, $scores);

        // Menor Score = mejor alternativa, y mejor_opcion apunta a la primera.
        $this->assertEquals($salida['resultados'][0], $salida['mejor_opcion']);

        // Nivel de optimizacion derivado del set: mejor=100, peor=0, monotono decreciente.
        $niveles = array_column($salida['resultados'], 'nivel_optimizacion');
        $this->assertEqualsWithDelta(100.0, $niveles[0], 0.01);
        $this->assertEqualsWithDelta(0.0, end($niveles), 0.01);
        for ($i = 1; $i < count($niveles); $i++) {
            $this->assertLessThanOrEqual($niveles[$i - 1], $niveles[$i]);
        }

        // Persistencia del historial: la corrida queda en resultados_optimizacion
        // con el nuevo esquema dentro de resultado_json (sin rastro del campo viejo).
        $this->assertNotNull($salida['resultado_optimizacion_id']);
        $fila = ResultadoOptimizacion::find($salida['resultado_optimizacion_id']);
        $this->assertNotNull($fila);

        $json = json_encode($fila->resultado_json);
        $this->assertIsString($json);
        $this->assertStringNotContainsString('costo_combustible', $json);
        $this->assertStringContainsString('penalizacion_distancia', $json);
    }

    public function test_con_una_sola_sucursal_la_penalizacion_es_cero_sin_division_por_cero(): void
    {
        // Caso borde del pase de normalizacion: rango = max-min = 0, la division
        // debe evitarse y todo queda con penalizacion 0.
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();
        $this->crearSucursalConPrecio('Unico Super', 'Unica Sucursal', 13.700000, -89.200000, $producto->id, 3.00);
        $lista = $this->crearListaConDetalle($usuario, $producto);

        $salida = app(OptimizationService::class)->optimizar($lista, self::LAT_USUARIO, self::LNG_USUARIO);

        $this->assertCount(1, $salida['resultados']);

        $unica = $salida['resultados'][0];
        $this->assertGreaterThan(0.0, $unica['distancia_km']);
        $this->assertEqualsWithDelta(0.0, $unica['penalizacion_distancia'], 0.0001);
        $this->assertEqualsWithDelta(100.0, $unica['nivel_optimizacion'], 0.01);
        $this->assertEqualsWithDelta(100.0, $salida['mejor_opcion']['nivel_optimizacion'], 0.01);
        $this->assertArrayNotHasKey('costo_combustible', $unica);
    }

    // ------------------------------------------------------------------
    // Datos de apoyo: dos supermercados con una sucursal cada uno. La
    // cercana esta sobre las coordenadas del usuario pero es la mas CARA,
    // para que distancia y precio no queden correlacionadas en las pruebas.
    // ------------------------------------------------------------------
    private function crearMundoDosSucursales(): array
    {
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();

        $cercana = $this->crearSucursalConPrecio(
            'Despensa Familiar', 'DF Centro',
            self::LAT_USUARIO, self::LNG_USUARIO,
            $producto->id, 2.50,
        );

        $lejana = $this->crearSucursalConPrecio(
            'Super Selectos', 'SS Santa Elena',
            13.730000, -89.300000,
            $producto->id, 2.00,
        );

        $lista = $this->crearListaConDetalle($usuario, $producto);

        return ['cercana' => $cercana, 'lejana' => $lejana, 'lista' => $lista];
    }

    private function crearUsuario(): User
    {
        return User::create([
            'name' => 'Cliente de Prueba',
            'email' => 'cliente@test.sv',
            'password' => 'password-secreto',
        ]);
    }

    private function crearProducto(): Producto
    {
        $categoria = Categoria::create(['nombre' => 'Lacteos']);

        return Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Alpura',
            'nombre' => 'Leche Entera',
            'presentacion' => 'Botella',
            'unidad_medida' => 'L',
            'contenido' => 1,
        ]);
    }

    private function crearSucursalConPrecio(
        string $supermercado,
        string $sucursal,
        float $latitud,
        float $longitud,
        int $productoId,
        float $precio,
    ): Sucursal {
        $super = Supermercado::create(['nombre' => $supermercado]);

        $suc = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => $sucursal,
            'direccion' => 'Calle Falsa 123',
            'latitud' => $latitud,
            'longitud' => $longitud,
        ]);

        PrecioActual::create([
            'producto_id' => $productoId,
            'sucursal_id' => $suc->id,
            'precio_normal' => $precio,
            'precio_final' => $precio,
        ]);

        return $suc;
    }

    private function crearListaConDetalle(User $usuario, Producto $producto): ListaCompra
    {
        $lista = ListaCompra::create([
            'usuario_id' => $usuario->id,
            'nombre' => 'Compra semanal',
        ]);

        ListaCompraDetalles::create([
            'lista_id' => $lista->id,
            'producto_id' => $producto->id,
            'cantidad' => 1,
            'esencial' => true,
        ]);

        return $lista;
    }

    private function optimizar(ListaCompra $lista): array
    {
        return app(OptimizationService::class)
            ->optimizar($lista, self::LAT_USUARIO, self::LNG_USUARIO);
    }
}
