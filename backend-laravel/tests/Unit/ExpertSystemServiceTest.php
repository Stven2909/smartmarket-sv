<?php

namespace Tests\Unit;

use App\Services\ExpertResponseValidator;
use App\Services\ExpertSystemService;
use Illuminate\Http\Client\ConnectionException;
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
            'services.expert_system.api_key' => null,
            'services.expert_system.timeout' => 3,
            'services.expert_system.connect_timeout' => 2,
            'services.expert_system.retry_times' => 2,
            'services.expert_system.retry_sleep_ms' => 10,
            'services.expert_system.total_budget_ms' => 5000,
        ]);

        $this->service = new ExpertSystemService(new ExpertResponseValidator);
    }

    public function test_recommend_exitoso_devuelve_respuesta_por_request_id(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response($this->respuestaValida('lista-1-sucursal-1'), 200),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertArrayHasKey('lista-1-sucursal-1', $resultado['respuestas']);
        $this->assertEquals('EXCELENTE', $resultado['respuestas']['lista-1-sucursal-1']['nivel_recomendacion']);
        $this->assertNull($resultado['motivos']['lista-1-sucursal-1']);
        $this->assertIsInt($resultado['duracion_ms']);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/recommend'
                && $request->method() === 'POST';
        });
    }

    public function test_recommend_422_no_reintenta_y_devuelve_null(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response(['detail' => 'Validation error'], 422),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('sin_respuesta', $resultado['motivos']['lista-1-sucursal-1']);

        // Un 4xx es un error del contrato, no una caída transitoria: no se repite.
        Http::assertSentCount(1);
    }

    public function test_recommend_500_reintenta_y_devuelve_null(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response(['detail' => 'Internal server error'], 500),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('sin_respuesta', $resultado['motivos']['lista-1-sucursal-1']);

        Http::assertSentCount(2);
    }

    public function test_recommend_timeout_devuelve_null(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake(function () {
            throw new ConnectionException('cURL error 28: Operation timed out');
        });

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('sin_respuesta', $resultado['motivos']['lista-1-sucursal-1']);
    }

    public function test_recommend_vacio_devuelve_estructura_vacia(): void
    {
        $resultado = $this->service->recommend([]);

        $this->assertSame([], $resultado['respuestas']);
        $this->assertSame([], $resultado['motivos']);
        $this->assertSame(0, $resultado['duracion_ms']);
    }

    public function test_recommend_con_forma_invalida_marca_respuesta_invalida(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-1-sucursal-1',
                'nivel_recomendacion' => 'EXCELENTE',
                // Falta explicacion, reglas_activadas, trace, etc.
            ], 200),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('respuesta_invalida', $resultado['motivos']['lista-1-sucursal-1']);
    }

    public function test_recommend_con_request_id_distinto_es_invalida(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response($this->respuestaValida('lista-1-sucursal-2'), 200),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('respuesta_invalida', $resultado['motivos']['lista-1-sucursal-1']);
    }

    public function test_recommend_rechaza_traza_que_no_es_lista_de_objetos(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');
        $respuesta = $this->respuestaValida('lista-1-sucursal-1');
        $respuesta['trace'] = ['paso inválido'];

        Http::fake(['*' => Http::response($respuesta, 200)]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('respuesta_invalida', $resultado['motivos']['lista-1-sucursal-1']);
    }

    public function test_recommend_rechaza_indice_de_conveniencia_fuera_de_rango(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');
        $respuesta = $this->respuestaValida('lista-1-sucursal-1');
        $respuesta['indice_conveniencia'] = 101;

        Http::fake(['*' => Http::response($respuesta, 200)]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertSame('respuesta_invalida', $resultado['motivos']['lista-1-sucursal-1']);
    }

    public function test_recommend_acepta_respuesta_real_con_reglas_nuevas_y_campos_extra(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');
        $respuesta = $this->respuestaValida('lista-1-sucursal-1', 'BUENA', 'R16');
        $respuesta['prioridad_aplicada'] = 'CONVENIENCIA_PONDERADA';
        $respuesta['version_reglas'] = '1.3.2';
        $respuesta['version_contrato'] = '1.0.0';
        $respuesta['hechos_derivados'] = [
            'cobertura_parcial_relevante' => false,
            'faltan_productos' => true,
            'todos_esenciales_disponibles' => true,
            'conveniencia_solida' => true,
            'porcentaje_productos_disponibles' => 90.0,
        ];
        $respuesta['indice_conveniencia'] = 60.13;
        $respuesta['clasificacion_conveniencia'] = 'CONVENIENCIA_MEDIA';
        $respuesta['componentes_conveniencia'] = ['disponibilidad' => 90.0, 'distancia' => 60.0];
        $respuesta['pesos_conveniencia'] = ['disponibilidad' => 0.4, 'distancia' => 0.2];
        $respuesta['trace'] = [
            [
                'rule_id' => 'R16',
                'evaluated' => true,
                'activated' => true,
                'reason' => 'Condiciones cumplidas.',
                'conditions' => [
                    'faltan_productos' => ['expected' => true, 'actual' => true, 'matched' => true],
                ],
            ],
        ];

        Http::fake(['*' => Http::response($respuesta, 200)]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertNotNull($resultado['respuestas']['lista-1-sucursal-1']);
        $this->assertNull($resultado['motivos']['lista-1-sucursal-1']);
        $this->assertSame('R16', $resultado['respuestas']['lista-1-sucursal-1']['winning_rule']);
        $this->assertSame('CONVENIENCIA_PONDERADA', $resultado['respuestas']['lista-1-sucursal-1']['prioridad_aplicada']);
        $this->assertSame(60.13, $resultado['respuestas']['lista-1-sucursal-1']['indice_conveniencia']);
    }

    public function test_recommend_multiples_alternativas_devuelve_todas(): void
    {
        $payload1 = $this->crearPayload('lista-1-sucursal-1');
        $payload2 = $this->crearPayload('lista-1-sucursal-2');

        Http::fake([
            '*' => Http::sequence()
                ->push($this->respuestaValida('lista-1-sucursal-1', 'EXCELENTE', 'R06'), 200)
                ->push($this->respuestaValida('lista-1-sucursal-2', 'BUENA', 'R07'), 200),
        ]);

        $resultado = $this->service->recommend([$payload1, $payload2]);

        $this->assertEquals('EXCELENTE', $resultado['respuestas']['lista-1-sucursal-1']['nivel_recomendacion']);
        $this->assertEquals('BUENA', $resultado['respuestas']['lista-1-sucursal-2']['nivel_recomendacion']);
    }

    public function test_chat_exitoso_devuelve_respuesta(): void
    {
        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-1-sucursal-1',
                'intent' => 'EXPLICACION',
                'response' => 'Esta alternativa conviene porque cumple el presupuesto y los esenciales.',
                'supported' => true,
            ], 200),
        ]);

        $resultado = $this->service->chat($this->crearPayloadChat());

        $this->assertIsArray($resultado);
        $this->assertTrue($resultado['supported']);
        $this->assertEquals('EXPLICACION', $resultado['intent']);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/chat'
                && $request->method() === 'POST';
        });
    }

    public function test_chat_con_forma_invalida_devuelve_null(): void
    {
        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-1-sucursal-1',
                'intent' => 'EXPLICACION',
                // Falta response y supported.
            ], 200),
        ]);

        $this->assertNull($this->service->chat($this->crearPayloadChat()));
    }

    public function test_chat_422_devuelve_null(): void
    {
        Http::fake([
            '*' => Http::response(['detail' => 'Validation error'], 422),
        ]);

        $this->assertNull($this->service->chat($this->crearPayloadChat()));
    }

    public function test_chat_500_devuelve_null(): void
    {
        Http::fake([
            '*' => Http::response(['detail' => 'Internal server error'], 500),
        ]);

        $this->assertNull($this->service->chat($this->crearPayloadChat()));
    }

    public function test_chat_timeout_devuelve_null(): void
    {
        Http::fake(function () {
            throw new ConnectionException('cURL error 28: Operation timed out');
        });

        $this->assertNull($this->service->chat($this->crearPayloadChat()));
    }

    public function test_recommend_sin_api_key_no_envia_header(): void
    {
        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response($this->respuestaValida('lista-1-sucursal-1'), 200),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertArrayHasKey('lista-1-sucursal-1', $resultado['respuestas']);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/recommend'
                && ! $request->hasHeader('X-API-Key');
        });
    }

    public function test_chat_sin_api_key_no_envia_header(): void
    {
        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-1-sucursal-1',
                'intent' => 'EXPLICACION',
                'response' => 'Esta alternativa conviene porque cumple el presupuesto y los esenciales.',
                'supported' => true,
            ], 200),
        ]);

        $resultado = $this->service->chat($this->crearPayloadChat());

        $this->assertIsArray($resultado);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/chat'
                && ! $request->hasHeader('X-API-Key');
        });
    }

    public function test_recommend_con_api_key_envia_header(): void
    {
        config(['services.expert_system.api_key' => 'test-key']);

        $payload = $this->crearPayload('lista-1-sucursal-1');

        Http::fake([
            '*' => Http::response($this->respuestaValida('lista-1-sucursal-1'), 200),
        ]);

        $resultado = $this->service->recommend([$payload]);

        $this->assertArrayHasKey('lista-1-sucursal-1', $resultado['respuestas']);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/recommend'
                && $request->hasHeader('X-API-Key', 'test-key');
        });
    }

    public function test_chat_con_api_key_envia_header(): void
    {
        config(['services.expert_system.api_key' => 'test-key']);

        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-1-sucursal-1',
                'intent' => 'EXPLICACION',
                'response' => 'Esta alternativa conviene porque cumple el presupuesto y los esenciales.',
                'supported' => true,
            ], 200),
        ]);

        $resultado = $this->service->chat($this->crearPayloadChat());

        $this->assertIsArray($resultado);

        Http::assertSent(function ($request) {
            return $request->url() === 'https://sistema-experto-fork.onrender.com/api/v1/chat'
                && $request->hasHeader('X-API-Key', 'test-key');
        });
    }

    private function respuestaValida(string $requestId, string $nivel = 'EXCELENTE', string $regla = 'R06'): array
    {
        return [
            'request_id' => $requestId,
            'nivel_recomendacion' => $nivel,
            'accion_sugerida' => 'Comprar todo en esta alternativa.',
            'explicacion' => 'Cumple el presupuesto y los esenciales.',
            'reglas_activadas' => [$regla],
            'prioridad_aplicada' => 'CONVENIENCIA',
            'hechos_derivados' => ['dentro_presupuesto' => true, 'porcentaje_productos_disponibles' => 100.0],
            'version_reglas' => '1.0.0',
            'winning_rule' => $regla,
            'losing_rules' => [],
            'trace' => [],
        ];
    }

    private function crearPayloadChat(): array
    {
        return [
            'message' => '¿Por qué conviene esta alternativa?',
            'facts' => $this->crearPayload('lista-1-sucursal-1'),
            'recommendation' => $this->respuestaValida('lista-1-sucursal-1'),
        ];
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
