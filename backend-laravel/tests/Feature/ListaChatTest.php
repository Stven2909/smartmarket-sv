<?php

namespace Tests\Feature;

use App\Models\ListaCompra;
use App\Models\ResultadoOptimizacion;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

// El asistente explicativo (POST /api/listas/{lista}/chat) vuelca la pregunta
// del usuario al Sistema Experto junto con los facts y la recomendación de la
// corrida de optimización YA persistida. No conserva estado: si la alternativa
// no tuvo recomendación, o el asistente no responde, se devuelve HTTP 200 con
// fallback NO_DISPONIBLE — la recomendación principal nunca se altera.
class ListaChatTest extends TestCase
{
    use RefreshDatabase;

    public function test_chat_exitoso_devuelve_respuesta_con_chatbot_available(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true);

        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-' . $lista->id . '-sucursal-7',
                'intent' => 'EXPLICACION',
                'response' => 'Esta alternativa conviene porque cumple el presupuesto.',
                'supported' => true,
            ], 200),
        ]);

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Por qué conviene esta alternativa?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()
            ->assertJson([
                'intent' => 'EXPLICACION',
                'supported' => true,
                'chatbot_available' => true,
            ]);

        $verificado = false;
        Http::assertSent(function ($request) use ($lista, &$verificado) {
            if ($request->url() !== config('services.expert_system.url') . '/api/v1/chat'
                || $request->method() !== 'POST') {
                return false;
            }

            $data = $request->data();
            $this->assertSame('¿Por qué me recomiendas esta alternativa?', $data['message']);
            $this->assertSame('lista-' . $lista->id . '-sucursal-7', $data['facts']['request_id']);
            $this->assertSame('sucursal-7', $data['facts']['alternativa_id']);
            $this->assertSame('lista-' . $lista->id . '-sucursal-7', $data['recommendation']['request_id']);
            $verificado = true;

            return true;
        });
        $this->assertTrue($verificado, 'No se envió el payload esperado a /chat');
    }

    public function test_chat_422_responde_fallback_sin_modificar_recomendacion(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true);

        Http::fake(['*' => Http::response(['detail' => 'Validation error'], 422)]);

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Por qué?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()
            ->assertJson([
                'intent' => 'NO_DISPONIBLE',
                'supported' => false,
                'chatbot_available' => false,
            ]);
    }

    public function test_chat_500_responde_fallback(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true);

        Http::fake(['*' => Http::response(['detail' => 'Internal server error'], 500)]);

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Por qué?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()->assertJson(['intent' => 'NO_DISPONIBLE', 'supported' => false]);
    }

    public function test_chat_timeout_responde_fallback(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true);

        Http::fake(function () {
            throw new \Illuminate\Http\Client\ConnectionException('cURL error 28: Operation timed out');
        });

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Por qué?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()->assertJson(['intent' => 'NO_DISPONIBLE', 'supported' => false]);
    }

    public function test_chat_sin_recomendacion_no_llama_al_asistente(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, null, false);

        Http::fake();

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Por qué?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()->assertJson(['intent' => 'NO_DISPONIBLE', 'supported' => false]);

        // Si no hubo recomendación, jamás debe contactarse al asistente.
        Http::assertNothingSent();
    }

    public function test_chat_resultado_optimizacion_de_otra_lista_es_rechazado(): void
    {
        // Usuario A: dueño de la lista sobre la que pregunta.
        $usuarioA = $this->crearUsuario('a@test.sv');
        $listaA = $this->crearLista($usuarioA->id);

        // Usuario B: dueño de otra lista, cuya corrida NO le pertenece a A.
        $usuarioB = $this->crearUsuario('b@test.sv');
        $listaB = $this->crearLista($usuarioB->id);
        $roDeB = $this->crearRun($listaB->id, 7, $this->recommendation(), true);

        Http::fake();

        $respuesta = $this->actingAs($usuarioA)->postJson("/api/listas/{$listaA->id}/chat", [
            'message' => '¿Por qué?',
            'resultado_optimizacion_id' => $roDeB->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertNotFound();

        // Nunca se consulta al asistente con datos de la corrida de otro usuario.
        Http::assertNothingSent();
    }

    public function test_distancia_se_normaliza_antes_de_llamar_al_experto(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true);

        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-' . $lista->id . '-sucursal-7',
                'intent' => 'DISTANCIA',
                'response' => 'La distancia total es de 2.00 km.',
                'supported' => true,
            ], 200),
        ]);

        $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Qué tan lejos queda esta tienda?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ])->assertOk()->assertJson(['intent' => 'DISTANCIA', 'supported' => true]);

        Http::assertSent(function ($request) {
            return $request->data()['message'] === '¿Cuál es la distancia?';
        });
    }

    public function test_promociones_se_responden_con_los_facts_sin_llamar_al_experto(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true, 3.0);

        Http::fake();

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Hay promociones aplicables?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()->assertJson([
            'intent' => 'PROMOCIONES',
            'supported' => true,
            'chatbot_available' => true,
        ]);

        $this->assertStringContainsString('promociones aplicables', $respuesta->json('response'));
        $this->assertStringContainsString('$3.00', $respuesta->json('response'));
        $this->assertStringNotContainsString('R07', $respuesta->json('response'));

        // El tema lo resuelve Laravel con los facts persistidos: no hace falta
        // exponer al experto a una pregunta que hoy responde AYUDA.
        Http::assertNothingSent();
    }

    public function test_sin_promociones_la_respuesta_lo_indica_sin_llamar_al_experto(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true, 0.0);

        Http::fake();

        $respuesta = $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Qué promociones puedo usar?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ]);

        $respuesta->assertOk()->assertJson(['intent' => 'PROMOCIONES', 'supported' => true]);
        $this->assertStringContainsString('No se registraron promociones', $respuesta->json('response'));

        Http::assertNothingSent();
    }

    public function test_pregunta_fuera_de_alcance_se_envia_sin_reescribir(): void
    {
        $usuario = $this->crearUsuario('a@test.sv');
        $lista = $this->crearLista($usuario->id);
        $ro = $this->crearRun($lista->id, 7, $this->recommendation(), true);

        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-' . $lista->id . '-sucursal-7',
                'intent' => 'AYUDA',
                'response' => 'Solo puedo explicar la alternativa actual.',
                'supported' => false,
            ], 200),
        ]);

        $this->actingAs($usuario)->postJson("/api/listas/{$lista->id}/chat", [
            'message' => '¿Cuál es el mejor supermercado?',
            'resultado_optimizacion_id' => $ro->id,
            'sucursal_id' => 7,
        ])->assertOk()->assertJson(['intent' => 'AYUDA', 'supported' => false]);

        Http::assertSent(function ($request) {
            return $request->data()['message'] === '¿Cuál es el mejor supermercado?';
        });
    }

    private function recommendation(): array
    {
        return [
            'request_id' => 'lista-SUCURSAL',
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
        ];
    }

    private function crearRun(int $listaId, int $sucursalId, ?array $recommendation, bool $available, float $beneficioPromociones = 3.0): ResultadoOptimizacion
    {
        $resultado = [
            'sucursal_id' => $sucursalId,
            'sucursal' => 'SS Centro',
            'supermercado_id' => 5,
            'supermercado' => 'Super Selectos',
            'costo_total' => 40.0,
            'distancia_km' => 2.0,
            'tiempo_minutos' => 10.0,
            'beneficio_promociones' => $beneficioPromociones,
            'productos_esenciales_disponibles' => 2,
            'productos_esenciales_totales' => 2,
            'productos_opcionales_disponibles' => 1,
            'productos_opcionales_totales' => 1,
            'productos_disponibles' => 3,
            'productos_totales' => 3,
            'expert_system_available' => $available,
            'expert_omission_reason' => $available ? null : 'presupuesto_null',
            'recommendation' => $recommendation ? ['request_id' => 'lista-' . $listaId . '-sucursal-' . $sucursalId] + $recommendation : null,
        ];

        return ResultadoOptimizacion::create([
            'lista_compra_id' => $listaId,
            'score' => 10.0,
            'ahorro' => 5.0,
            'distancia' => 2.0,
            'tiempo' => 10,
            'supermercados' => [['supermercado' => 'Super Selectos', 'sucursal' => 'SS Centro', 'score' => 10.0]],
            'resultado_json' => [
                'lista' => 'Compra semanal',
                'presupuesto' => 50.0,
                'resultados' => [$resultado],
            ],
            'fecha' => now(),
        ]);
    }

    private function crearLista(int $usuarioId): ListaCompra
    {
        return ListaCompra::create([
            'usuario_id' => $usuarioId,
            'nombre' => 'Compra semanal',
            'presupuesto' => 50.0,
            'estado' => 'activa',
            'fecha' => now(),
        ]);
    }

    private function crearUsuario(string $email): User
    {
        return User::create([
            'name' => 'Cliente',
            'email' => $email,
            'password' => 'password-secreto',
        ]);
    }
}
