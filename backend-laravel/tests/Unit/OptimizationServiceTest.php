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
use Illuminate\Support\Facades\Http;
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
    // Tests de integración con Sistema Experto
    // ------------------------------------------------------------------

    public function test_ahorro_se_calcula_por_alternativa_contra_costo_referencia(): void
    {
        $mundo = $this->crearMundoDosSucursales();

        Http::fake(['*' => Http::response(null, 200)]);

        $salida = $this->optimizar($mundo['lista']);

        // costo_referencia = max(costo_total) entre alternativas.
        // La cercana cuesta 2.50, la lejana 2.00 → referencia = 2.50.
        // Ahorro cercana = max(0, 2.50 - 2.50) = 0.
        // Ahorro lejana = max(0, 2.50 - 2.00) = 0.50.
        // Verificamos a través del payload enviado al expert system.
        $payloads = [];
        Http::assertSent(function ($request) use (&$payloads) {
            $payloads[] = $request->data();
            return true;
        });

        $this->assertCount(2, $payloads);

        $payloadPorReqId = [];
        foreach ($payloads as $p) {
            $payloadPorReqId[$p['request_id']] = $p;
        }

        // La alternativa más cara (cercana) tiene ahorro 0.
        $payloadCercana = $payloadPorReqId['lista-' . $mundo['lista']->id . '-sucursal-' . $mundo['cercana']->id];
        $this->assertEquals(0.0, $payloadCercana['ahorro']);

        // La alternativa más barata (lejana) tiene ahorro = referencia - su costo.
        $payloadLejana = $payloadPorReqId['lista-' . $mundo['lista']->id . '-sucursal-' . $mundo['lejana']->id];
        $this->assertEquals(0.50, $payloadLejana['ahorro']);
    }

    public function test_distancia_adicional_se_calcula_contra_distancia_minima(): void
    {
        $mundo = $this->crearMundoDosSucursales();

        Http::fake(['*' => Http::response(null, 200)]);

        $salida = $this->optimizar($mundo['lista']);

        $payloads = [];
        Http::assertSent(function ($request) use (&$payloads) {
            $payloads[] = $request->data();
            return true;
        });

        $payloadPorReqId = [];
        foreach ($payloads as $p) {
            $payloadPorReqId[$p['request_id']] = $p;
        }

        // La cercana (distancia ~0) tiene distancia_adicional_km = 0.
        $payloadCercana = $payloadPorReqId['lista-' . $mundo['lista']->id . '-sucursal-' . $mundo['cercana']->id];
        $this->assertEquals(0.0, $payloadCercana['distancia_adicional_km']);

        // La lejana tiene distancia_adicional > 0.
        $payloadLejana = $payloadPorReqId['lista-' . $mundo['lista']->id . '-sucursal-' . $mundo['lejana']->id];
        $this->assertGreaterThan(0.0, $payloadLejana['distancia_adicional_km']);
    }

    public function test_presupuesto_null_omite_llamada_al_sistema_experto(): void
    {
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();

        // Crear lista SIN presupuesto.
        $lista = ListaCompra::create([
            'usuario_id' => $usuario->id,
            'nombre' => 'Sin presupuesto',
            'presupuesto' => null,
            'estado' => 'activa',
            'fecha' => now(),
        ]);

        ListaCompraDetalles::create([
            'lista_id' => $lista->id,
            'producto_id' => $producto->id,
            'cantidad' => 1,
            'esencial' => true,
        ]);

        $this->crearSucursalConPrecio('Test Super', 'Test Suc', 13.700000, -89.200000, $producto->id, 2.00);

        Http::fake();
        $salida = $this->optimizar($lista);

        // No debe enviar ninguna petición al Sistema Experto.
        Http::assertNothingSent();

        // La alternativa debe tener expert_system_available = false.
        $this->assertFalse($salida['resultados'][0]['expert_system_available']);
        $this->assertNull($salida['resultados'][0]['recommendation']);
    }

    public function test_distancia_null_omite_llamada_para_tienda_en_linea(): void
    {
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();

        $lista = $this->crearListaConDetalle($usuario, $producto);

        // Crear sucursal SIN coordenadas (tienda en línea).
        $super = Supermercado::create(['nombre' => 'Online Store']);
        $suc = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Tienda en línea',
            'direccion' => 'Online',
            'latitud' => null,
            'longitud' => null,
        ]);

        PrecioActual::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $suc->id,
            'precio_normal' => 2.00,
            'precio_final' => 2.00,
        ]);

        Http::fake();
        $salida = $this->optimizar($lista);

        // Con solo una alternativa sin coordenadas, no debe llamar al expert system.
        $this->assertFalse($salida['resultados'][0]['expert_system_available']);
    }

    public function test_fallback_no_rompe_optimizacion(): void
    {
        $mundo = $this->crearMundoDosSucursales();

        // Simular que el Sistema Experto está apagado.
        Http::fake(function () {
            throw new \Illuminate\Http\Client\ConnectionException('Connection refused');
        });

        $salida = $this->optimizar($mundo['lista']);

        // La optimización debe funcionar normalmente a pesar del fallo.
        $this->assertCount(2, $salida['resultados']);
        $this->assertNotNull($salida['mejor_opcion']);

        // Todas las alternativas deben tener expert_system_available = false.
        foreach ($salida['resultados'] as $r) {
            $this->assertFalse($r['expert_system_available']);
            $this->assertNull($r['recommendation']);
        }
    }

    public function test_numero_supermercados_se_cuenta_correctamente(): void
    {
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();

        // Un solo supermercado con dos sucursales.
        $super = Supermercado::create(['nombre' => 'Mismo Super']);

        $sucA = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Suc A',
            'direccion' => 'Calle A',
            'latitud' => 13.700000,
            'longitud' => -89.200000,
        ]);

        PrecioActual::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $sucA->id,
            'precio_normal' => 2.00,
            'precio_final' => 2.00,
        ]);

        $sucB = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Suc B',
            'direccion' => 'Calle B',
            'latitud' => 13.710000,
            'longitud' => -89.210000,
        ]);

        PrecioActual::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $sucB->id,
            'precio_normal' => 2.50,
            'precio_final' => 2.50,
        ]);

        // Lista CON presupuesto para que el expert system sea llamado.
        $lista = ListaCompra::create([
            'usuario_id' => $usuario->id,
            'nombre' => 'Compra con presupuesto',
            'presupuesto' => 50.0,
            'estado' => 'activa',
            'fecha' => now(),
        ]);

        ListaCompraDetalles::create([
            'lista_id' => $lista->id,
            'producto_id' => $producto->id,
            'cantidad' => 1,
            'esencial' => true,
        ]);

        Http::fake(['*' => Http::response(null, 200)]);
        $salida = $this->optimizar($lista);

        // Solo 1 supermercado único (ambas sucursales son del mismo).
        $payloads = [];
        Http::assertSent(function ($request) use (&$payloads) {
            $payloads[] = $request->data();
            return true;
        });

        $this->assertNotEmpty($payloads);
        $this->assertEquals(1, $payloads[0]['numero_supermercados']);
    }

    public function test_productos_disponibles_mayor_que_totales_omite_alternativa(): void
    {
        // Este caso es teórico con ComparisonService actual (no puede producir
        // disponibles > totales), pero validamos que debeOmitir lo detecta.
        $service = app(OptimizationService::class);

        $resultado = [
            'distancia_km' => 2.0,
            'tiempo_minutos' => 10.0,
            'costo_total' => 30.0,
            'productos_disponibles' => 12,
            'productos_totales' => 10,
            'productos_esenciales_disponibles' => 5,
            'productos_esenciales_totales' => 6,
        ];

        $motivo = $service->debeOmitir($resultado, 50.0, 40.0, 1.0);

        $this->assertIsString($motivo);
        $this->assertStringContainsString('productos_disponibles', $motivo);
    }

    public function test_costo_total_null_omite_alternativa(): void
    {
        $service = app(OptimizationService::class);

        $resultado = [
            'distancia_km' => 2.0,
            'tiempo_minutos' => 10.0,
            'costo_total' => null,
            'productos_disponibles' => 10,
            'productos_totales' => 10,
            'productos_esenciales_disponibles' => 6,
            'productos_esenciales_totales' => 6,
        ];

        $motivo = $service->debeOmitir($resultado, 50.0, 40.0, 1.0);

        $this->assertIsString($motivo);
        $this->assertEquals('costo_total_null', $motivo);
    }

    public function test_esenciales_disponibles_mayor_que_totales_omite(): void
    {
        $service = app(OptimizationService::class);

        $resultado = [
            'distancia_km' => 2.0,
            'tiempo_minutos' => 10.0,
            'costo_total' => 30.0,
            'productos_disponibles' => 10,
            'productos_totales' => 10,
            'productos_esenciales_disponibles' => 7,
            'productos_esenciales_totales' => 6,
        ];

        $motivo = $service->debeOmitir($resultado, 50.0, 40.0, 1.0);

        $this->assertIsString($motivo);
        $this->assertEquals('esenciales_disponibles_mayor_que_totales', $motivo);
    }

    public function test_alternativa_valida_no_se_omite(): void
    {
        $service = app(OptimizationService::class);

        $resultado = [
            'distancia_km' => 2.0,
            'tiempo_minutos' => 10.0,
            'costo_total' => 30.0,
            'productos_disponibles' => 10,
            'productos_totales' => 10,
            'productos_esenciales_disponibles' => 6,
            'productos_esenciales_totales' => 6,
        ];

        $motivo = $service->debeOmitir($resultado, 50.0, 40.0, 1.0);

        $this->assertFalse($motivo);
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

        $lista = $this->crearListaConDetalle($usuario, $producto, 50.0);

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

    private function crearListaConDetalle(User $usuario, Producto $producto, ?float $presupuesto = null): ListaCompra
    {
        $lista = ListaCompra::create([
            'usuario_id' => $usuario->id,
            'nombre' => 'Compra semanal',
            'presupuesto' => $presupuesto,
            'estado' => 'activa',
            'fecha' => now(),
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
