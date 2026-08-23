<?php

namespace Tests\Unit\PriceProviders;

use App\Services\PriceProviders\Support\PoliteHttpClient;
use App\Services\PriceProviders\VtexProvider;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class VtexProviderTest extends TestCase
{
    private const BASE = 'https://tienda-vtex.test';

    private VtexProvider $provider;

    protected function setUp(): void
    {
        parent::setUp();

        config([
            'price_providers.defaults.pausa_ms' => 0,
            'price_providers.defaults.backoff_ms' => 0,
        ]);

        $this->provider = new VtexProvider('walmart-test', self::BASE, new PoliteHttpClient);
    }

    private function simularVtex(): void
    {
        $fixtures = __DIR__ . '/../../fixtures/';

        Http::fake([
            '*/category/tree/*' => Http::response(
                file_get_contents($fixtures . 'vtex-category-tree.json'),
                200,
                ['Content-Type' => 'application/json'],
            ),
            // Página 1 con total declarado 51 ⇒ obliga a pedir una segunda página
            // (_from=50). El whenEmpty cubre las demás hojas del árbol (vacías).
            '*/products/search*' => Http::sequence()
                ->push(json_decode(file_get_contents($fixtures . 'vtex-search-page1.json'), true), 200, ['resources' => 'total=51'])
                ->push(json_decode(file_get_contents($fixtures . 'vtex-search-page2.json'), true), 200, ['resources' => 'total=51'])
                ->whenEmpty(Http::response([], 200)),
        ]);
    }

    public function test_recorre_hojas_del_arbol_y_pagina_por_cada_una(): void
    {
        $this->simularVtex();

        $filas = iterator_to_array($this->provider->traer(), false);

        // Cereal (pág. 1) + Leche (pág. 2). "Producto Sin Oferta" se descarta.
        $this->assertCount(2, $filas);

        // Segunda página pedida con el desplazamiento correcto.
        Http::assertSent(fn ($request) => str_contains($request->url(), '_from=50'));
    }

    public function test_mapea_la_mejor_oferta_con_descuento_real(): void
    {
        $this->simularVtex();

        $cereal = iterator_to_array($this->provider->traer(), false)[0];

        // Mínimo entre sellers (5.5 vs 7.0); ListPrice 7.0 > 5.5 ⇒ promo real.
        $this->assertSame('Cereal Choco 500 g', $cereal['nombre']);
        $this->assertSame(5.50, $cereal['precio_final']);
        $this->assertSame(7.00, $cereal['precio_normal']);
        $this->assertTrue($cereal['tiene_promocion']);
        $this->assertTrue($cereal['disponible']); // AvailableQuantity del seller elegido
        $this->assertSame('6 un', $cereal['unidad']);
        $this->assertSame('Frutas', $cereal['categoria_raw']); // nombre de la hoja
        $this->assertSame(self::BASE . '/cereal-choco-500-g/p', $cereal['url_fuente']);
        $this->assertArrayHasKey('items', $cereal['raw_payload']); // evidencia intacta
    }

    public function test_oferta_sin_listprice_mayor_no_marca_promocion(): void
    {
        $this->simularVtex();

        [, $leche] = iterator_to_array($this->provider->traer(), false);

        // Seller sin stock descartado (Price=0); ListPrice == Price ⇒ sin promo.
        $this->assertSame('Leche Entera Lata 900 ml', $leche['nombre']);
        $this->assertSame(3.00, $leche['precio_final']);
        $this->assertNull($leche['precio_normal']);
        $this->assertFalse($leche['tiene_promocion']);
        $this->assertSame('ml', $leche['unidad']);
    }
}
