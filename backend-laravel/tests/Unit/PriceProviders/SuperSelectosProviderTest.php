<?php

namespace Tests\Unit\PriceProviders;

use App\Services\PriceProviders\SuperSelectosProvider;
use App\Services\PriceProviders\Support\PoliteHttpClient;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class SuperSelectosProviderTest extends TestCase
{
    public function test_extrae_tarjetas_normales_promociones_y_descarta_sin_precio(): void
    {
        config([
            'price_providers.defaults.pausa_ms' => 0,
            'price_providers.defaults.backoff_ms' => 0,
        ]);

        Http::fake([
            // Fixture recortado de la captura real: 3 productos válidos + 1 sin precio.
            'listado.test/*' => Http::response(
                file_get_contents(__DIR__ . '/../../fixtures/super-selectos.html'),
            ),
        ]);

        $provider = new SuperSelectosProvider(
            'super-selectos',
            'https://www.superselectos.com',
            new PoliteHttpClient,
            ['https://listado.test/ofertas'],
        );

        $filas = iterator_to_array($provider->traer(), false);

        $this->assertSame('html', $provider->modo());
        $this->assertCount(3, $filas);

        [$snickers, $atun, $harina] = $filas;

        // Producto normal: precio único, sin promo, unidad desde el nombre.
        $this->assertSame('Chocolate Snickers 52.7 g Barra', $snickers['nombre']);
        $this->assertSame('52.7 g', $snickers['unidad']);
        $this->assertSame(1.80, $snickers['precio_final']);
        $this->assertNull($snickers['precio_normal']);
        $this->assertFalse($snickers['tiene_promocion']);
        $this->assertTrue($snickers['disponible']);
        $this->assertSame('https://www.superselectos.com/?productId=5630', $snickers['url_fuente']);
        $this->assertNull($snickers['categoria_raw']);

        // Promo: el span .antes expone el precio previo (mejor que heurística min/max).
        $this->assertSame('Atun Pacifico Azul Vegetales 140 g 2 Pack Lata', $atun['nombre']);
        $this->assertSame('140 g', $atun['unidad']);
        $this->assertSame(2.75, $atun['precio_final']);
        $this->assertSame(3.25, $atun['precio_normal']);
        $this->assertTrue($atun['tiene_promocion']);
        // URL relativa resuelta contra la base.
        $this->assertSame('https://www.superselectos.com/?productId=77412', $atun['url_fuente']);

        $this->assertSame('Harina De Maiz 820 g Maseca', $harina['nombre']);
        $this->assertSame('820 g', $harina['unidad']);
        $this->assertSame(1.72, $harina['precio_final']);

        // Evidencia de auditoría (ADR-10).
        $this->assertSame('$1.80', $snickers['raw_payload']['precio_actual_texto']);
        $this->assertSame('$3.25', $atun['raw_payload']['precio_anterior_texto']);
    }
}
