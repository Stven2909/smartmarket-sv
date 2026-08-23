<?php

namespace Tests\Unit\PriceProviders;

use App\Services\PriceProviders\Exceptions\FuenteBloqueadaException;
use App\Services\PriceProviders\Support\PoliteHttpClient;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class PoliteHttpClientTest extends TestCase
{
    private PoliteHttpClient $cliente;

    protected function setUp(): void
    {
        parent::setUp();

        // Sin esperas reales en pruebas.
        config([
            'price_providers.defaults.pausa_ms' => 0,
            'price_providers.defaults.backoff_ms' => 0,
            'price_providers.defaults.reintentos' => 3,
        ]);

        $this->cliente = new PoliteHttpClient;
    }

    public function test_envia_el_user_agent_identificable_del_acta(): void
    {
        Http::fake(['*' => Http::response('<html>ok</html>')]);

        $this->cliente->get('https://ejemplo.test/listado');

        Http::assertSent(function ($request) {
            return $request->url() === 'https://ejemplo.test/listado'
                && $request->header('User-Agent')[0] === config('price_providers.defaults.user_agent');
        });
    }

    public function test_reintenta_ante_429_y_recupera_con_la_siguiente_respuesta(): void
    {
        Http::fake([
            '*' => Http::sequence()
                ->push('', 429)
                ->push('contenido recuperado', 200),
        ]);

        $respuesta = $this->cliente->get('https://ejemplo.test/api');

        $this->assertTrue($respuesta->successful());
        $this->assertSame('contenido recuperado', $respuesta->body());
    }

    public function test_aborta_cuando_el_bloqueo_es_persistente_429(): void
    {
        Http::fake([
            '*' => Http::sequence()
                ->push('', 429)
                ->push('', 429)
                ->push('', 429)
                ->push('', 429),
        ]);

        try {
            $this->cliente->get('https://ejemplo.test/api');

            $this->fail('Se esperaba FuenteBloqueadaException por saturación persistente.');
        } catch (FuenteBloqueadaException $e) {
            $this->assertStringContainsString('429', $e->getMessage());
            $this->assertStringContainsString('ejemplo.test', $e->getMessage());
        }
    }

    public function test_detecta_captcha_en_el_cuerpo_y_aborta_sin_evasion(): void
    {
        Http::fake([
            '*' => Http::response('<html>Please verify you are human to continue</html>', 200),
        ]);

        $this->expectException(FuenteBloqueadaException::class);
        $this->expectExceptionMessage('Bloqueo detectado');

        $this->cliente->get('https://ejemplo.test/detras-del-desafio');
    }

    public function test_trata_un_403_como_bloqueo_directo(): void
    {
        Http::fake(['*' => Http::response('Forbidden', 403)]);

        try {
            $this->cliente->get('https://ejemplo.test/prohibido');

            $this->fail('Se esperaba FuenteBloqueadaException ante un 403.');
        } catch (FuenteBloqueadaException $e) {
            $this->assertStringContainsString('403', $e->getMessage());
        }
    }
}
