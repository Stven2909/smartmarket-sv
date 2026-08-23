<?php

namespace Tests\Unit;

use App\Services\ExpertSystemService;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class ExpertSystemServiceTest extends TestCase
{
    private ExpertSystemService $service;

    protected function setUp(): void
    {
        parent::setUp();

        config([
            'services.expert_system.url' => 'https://sistema-experto-fork.onrender.com',
            'services.expert_system.timeout' => 3,
            'services.expert_system.retry_times' => 2,
            'services.expert_system.retry_sleep_ms' => 10,
        ]);

        $this->service = new ExpertSystemService;
    }

    public function test_recommend_exitoso_devuelve_respuesta_por_request_id(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-1-sucursal-1',
                'nivel_recomendacion' => 'EXCELENTE',
                'accion_sugerida' => 'Comprar todo en esta alternativa.',
                'explicacion' => 'Cumple el presupuesto y los esenciales.',
                'reglas_activadas' => ['R06'],
                'prioridad_aplicada' => 'CONVENIENCIA',
                'hechos_derivados' => ['dentro_presupuesto' => true],
                'version_reglas' => '1.0.0',
                'winning_rule' => 'R06',
                'losing_rules' => [],
                'trace' => [],
            ], 200),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertIsArray($resultado);
        $this->assertArrayHasKey('lista-1-sucursal-1', $resultado);
        $this->assertEquals('EXCELENTE', $resultado['lista-1-sucursal-1']['nivel_recomendacion']);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/recommend'
                && $request->method() === 'POST';
        });
    }

    public function test_recommend_422_devuelve_null_para_esa_alternativa(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response(['detail' => 'Validation error'], 422),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['lista-1-sucursal-1']);
    }

    public function test_recommend_500_devuelve_null(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response(['detail' => 'Internal server error'], 500),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['lista-1-sucursal-1']);
    }

    public function test_recommend_timeout_devuelve_null(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake(function () {
            throw new \Illuminate\Http\Client\ConnectionException('cURL error 28: Operation timed out');
        });

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['lista-1-sucursal-1']);
    }

    public function test_recommend_vacio_devuelve_array_vacio(): void
    {
        $resultado = $this->service->recommend([]);

        $this->assertIsArray($resultado);
        $this->assertEmpty($resultado);
    }

    public function test_recommend_multiples_alternativas_devuelve_todas(): void
    {
        $payload1 = $this->crearPayload('lista-1-sucursal-1');
        $payload2 = $this->crearPayload('lista-1-sucursal-2');

        Http::fake([
            '*' => Http::sequence()
                ->push([
                    'request_id' => 'lista-1-sucursal-1',
                    'nivel_recomendacion' => 'EXCELENTE',
                    'accion_sugerida' => 'Comprar.',
                    'explicacion' => 'Bien.',
                    'reglas_activadas' => ['R06'],
                    'prioridad_aplicada' => 'CONVENIENCIA',
                    'hechos_derivados' => [],
                    'version_reglas' => '1.0.0',
                    'winning_rule' => 'R06',
                    'losing_rules' => [],
                    'trace' => [],
                ], 200)
                ->push([
                    'request_id' => 'lista-1-sucursal-2',
                    'nivel_recomendacion' => 'BUENA',
                    'accion_sugerida' => 'Comprar con promos.',
                    'explicacion' => 'Tiene buenas promos.',
                    'reglas_activadas' => ['R07'],
                    'prioridad_aplicada' => 'PROMOCIONES',
                    'hechos_derivados' => [],
                    'version_reglas' => '1.0.0',
                    'winning_rule' => 'R07',
                    'losing_rules' => [],
                    'trace' => [],
                ], 200),
        ]);

        $resultado = $this->service->recommend([$payload1, $payload2]);

        $this->assertArrayHasKey('lista-1-sucursal-1', $resultado);
        $this->assertArrayHasKey('lista-1-sucursal-2', $resultado);
        $this->assertEquals('EXCELENTE', $resultado['lista-1-sucursal-1']['nivel_recomendacion']);
        $this->assertEquals('BUENA', $resultado['lista-1-sucursal-2']['nivel_recomendacion']);
    }

    private function crearPayload(string $requestId): array
    {
        return [
            'request_id' => $requestId,
            'alternativa_id' => str_replace('lista-1-', '', $requestId),
            'costo_total' => 42.50,
            'presupuesto' => 50.00,
            'ahorro' => 7.50,
            'distancia_km' => 2.30,
            'distancia_adicional_km' => 0.80,
            'tiempo_estimado_min' => 12,
            'productos_disponibles' => 10,
            'productos_totales' => 10,
            'productos_esenciales_disponibles' => 6,
            'productos_esenciales_totales' => 6,
            'numero_supermercados' => 1,
            'promociones_aplicables' => true,
        ];
    }
}
