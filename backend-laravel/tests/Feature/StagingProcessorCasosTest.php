<?php

namespace Tests\Feature;

use App\Models\HistorialPrecio;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ProductoRaw;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class StagingProcessorCasosTest extends TestCase
{
    use RefreshDatabase;

    private const FUENTE = 'prueba-html';

    protected function setUp(): void
    {
        parent::setUp();

        config(['price_providers.fuentes.' . self::FUENTE => [
            'modo' => 'html',
            'supermercado' => 'Super Selectos',
        ]]);
    }

    private function crearRaw(array $sobrescribir = []): ProductoRaw
    {
        return ProductoRaw::create(array_merge([
            'fuente' => self::FUENTE,
            'sku_externo' => 'sku-' . uniqid('', true),
            'nombre' => 'Salsa Picante Chiltepin 250 ml',
            'unidad' => '250 ml',
            'precio_normal' => null,
            'precio_final' => 2.35,
            'tiene_promocion' => false,
            'disponible' => true,
            'raw_payload' => [],
            'estado' => 'pendiente',
        ], $sobrescribir));
    }

    private function procesar(bool $dryRun = false): array
    {
        return app(\App\Services\PriceProviders\StagingProcessor::class)->procesar(null, null, $dryRun);
    }

    public function test_recoleccion_posterior_archiva_precio_anterior_en_historial(): void
    {
        $this->crearRaw();
        $this->procesar();

        // Re-colección: la misma fila vuelve a pendiente con precio nuevo.
        ProductoRaw::sole()->update(['estado' => 'pendiente', 'precio_final' => 2.99]);

        $this->procesar();

        // "Hoy" queda en precios_actuales; el precio que PERDIÓ vigencia (2.35)
        // fue archivado por el PrecioActualObserver en el historial append-only.
        $this->assertSame(1, PrecioActual::count());
        $this->assertSame(2.99, (float) PrecioActual::sole()->precio_final);

        $this->assertSame(1, HistorialPrecio::count());
        $archivado = HistorialPrecio::sole();
        $this->assertSame(2.35, (float) $archivado->precio_final);
        $this->assertNotNull($archivado->fecha);
    }

    public function test_recoleccion_con_precio_igual_no_genera_ruido_en_historial(): void
    {
        $this->crearRaw();
        $this->procesar();

        ProductoRaw::sole()->update(['estado' => 'pendiente']); // mismo precio
        $conteos = $this->procesar();

        $this->assertSame(1, $conteos['publicados']); // sí se re-publicó (fecha fresca)
        $this->assertSame(0, HistorialPrecio::count()); // sin cambio ⇒ sin fila nueva
    }

    public function test_dry_run_reporta_sin_escribir_absolutamente_nada(): void
    {
        $this->crearRaw();

        $conteos = $this->procesar(dryRun: true);

        $this->assertSame(1, $conteos['procesados']);
        $this->assertSame(1, $conteos['publicados']); // lo que publicaría
        $this->assertSame(1, $conteos['nuevos_productos']);

        $this->assertSame(0, Producto::count());
        $this->assertSame(0, PrecioActual::count());
        $this->assertSame(0, HistorialPrecio::count());
        $this->assertSame(0, \App\Models\Supermercado::count());

        $raw = ProductoRaw::sole();
        $this->assertSame('pendiente', $raw->estado); // intacto
        $this->assertNull($raw->procesado_at);
    }

    public function test_fila_con_precio_invalido_queda_marcada_como_error(): void
    {
        // Insert directo que se salta las validaciones de precios:sync — defensa
        // en profundidad del procesador.
        $this->crearRaw(['precio_final' => -5]);

        $conteos = $this->procesar();

        $this->assertSame(1, $conteos['errores']);
        $this->assertSame(0, $conteos['publicados']);

        $raw = ProductoRaw::sole();
        $this->assertSame('error', $raw->estado);
        $this->assertSame('precio_invalido_en_staging', $raw->motivo_rechazo);
        $this->assertNull($raw->procesado_at);
        $this->assertSame(0, PrecioActual::count());
    }

    public function test_pipeline_completo_sync_luego_procesar(): void
    {
        config(['price_providers.fuentes.prueba-vtex' => [
            'modo' => 'vtex',
            'base_url' => 'https://prueba-vtex.test',
            'supermercado' => 'Walmart',
            'enabled' => true,
        ]]);

        Http::fake([
            '*/category/tree/*' => Http::response([['id' => 9, 'name' => 'Raiz', 'hasChildren' => false]]),
            '*/products/search*' => Http::response([[
                'productName' => 'Miel Pureza 780 g',
                'linkText' => 'miel-pureza-780-g',
                'categoryName' => 'Abarrotes',
                'measurementUnit' => 'g',
                'unitMultiplier' => 1,
                'items' => [[
                    'sellers' => [[
                        'commertialOffer' => ['Price' => 4.2, 'ListPrice' => 5.0, 'AvailableQuantity' => 3],
                    ]],
                ]],
            ]], 200, ['resources' => 'total=1']),
        ]);

        $this->artisan('precios:sync', ['--fuente' => 'prueba-vtex'])->assertSuccessful();
        $this->artisan('precios:procesar')->assertSuccessful();

        $this->assertSame(1, PrecioActual::count());
        $this->assertSame(4.20, (float) PrecioActual::sole()->precio_final);
        $this->assertSame(5.00, (float) PrecioActual::sole()->precio_normal);
        $this->assertTrue((bool) PrecioActual::sole()->tiene_promocion);
        $this->assertSame('vtex-prueba-vtex', PrecioActual::sole()->origen_dato);

        // Trazabilidad punta a punta: la fila de staging nació con la URL del
        // driver y terminó publicada.
        $this->assertSame('https://prueba-vtex.test/miel-pureza-780-g/p', ProductoRaw::sole()->url_fuente);
        $this->assertSame('publicado', ProductoRaw::sole()->estado);
    }
}
