<?php

namespace Tests\Feature;

use App\Models\ProductoRaw;
use App\Models\SyncRun;
use App\Services\NormalizadorTexto;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class PreciosSyncCommandTest extends TestCase
{
    use RefreshDatabase;

    // Producto VTEX mínimo, inline para no depender de fixtures compartidos.
    private function simularFuenteVtex(array $producto = []): void
    {
        $producto = $producto ?: [
            'productName' => 'Jabon Zote 400 g',
            'linkText' => 'jabon-zote-400-g',
            'categoryName' => 'Limpieza/Jabones',
            'measurementUnit' => 'g',
            'unitMultiplier' => 1,
            'items' => [[
                'sellers' => [[
                    'commertialOffer' => ['Price' => 1.25, 'ListPrice' => 1.25, 'AvailableQuantity' => 7],
                ]],
            ]],
        ];

        config(['price_providers.fuentes.prueba-vtex' => [
            'modo' => 'vtex',
            'base_url' => 'https://prueba-vtex.test',
            'enabled' => true,
        ]]);

        Http::fake([
            '*/category/tree/*' => Http::response([['id' => 9, 'name' => 'Raiz', 'hasChildren' => false]]),
            '*/products/search*' => Http::response([$producto], 200, ['resources' => 'total=1']),
        ]);
    }

    public function test_sincroniza_hacia_staging_y_registra_la_corrida(): void
    {
        $this->simularFuenteVtex();

        $this->artisan('precios:sync', ['--fuente' => 'prueba-vtex'])
            ->assertSuccessful();

        $this->assertSame(1, ProductoRaw::count());

        $fila = ProductoRaw::first();
        $skuEsperado = hash(
            'sha256',
            NormalizadorTexto::limpiar('Jabon Zote 400 g') . '|' . NormalizadorTexto::limpiar('g'),
        );

        $this->assertSame('prueba-vtex', $fila->fuente);
        $this->assertSame($skuEsperado, $fila->sku_externo);
        $this->assertSame(1.25, (float) $fila->precio_final);
        $this->assertFalse($fila->tiene_promocion);
        $this->assertTrue($fila->disponible);
        $this->assertSame('pendiente', $fila->estado); // jamás publicado directo (ADR-10)
        $this->assertNotNull($fila->sync_run_id);

        $run = SyncRun::find($fila->sync_run_id);
        $this->assertSame('exitosa', $run->estado);
        $this->assertSame('vtex', $run->modo);
        $this->assertSame(1, $run->productos_obtenidos);
        $this->assertSame(1, $run->productos_nuevos);
        $this->assertSame(0, $run->productos_duplicados);
        $this->assertNotNull($run->iniciada_en);
        $this->assertNotNull($run->finalizada_en);
    }

    public function test_segunda_corrida_de_la_misma_fuente_cuenta_duplicados(): void
    {
        $this->simularFuenteVtex();

        $this->artisan('precios:sync', ['--fuente' => 'prueba-vtex'])->assertSuccessful();
        $this->artisan('precios:sync', ['--fuente' => 'prueba-vtex'])->assertSuccessful();

        $this->assertSame(1, ProductoRaw::count()); // upsert, no duplica fila

        $segunda = SyncRun::orderByDesc('id')->first();
        $this->assertSame(0, $segunda->productos_nuevos);
        $this->assertSame(1, $segunda->productos_duplicados);
    }

    public function test_dry_run_reporta_sin_escribir_en_staging(): void
    {
        $this->simularFuenteVtex();

        $this->artisan('precios:sync', ['--fuente' => 'prueba-vtex', '--dry-run' => true])
            ->assertSuccessful();

        $this->assertSame(0, ProductoRaw::count());

        $run = SyncRun::sole();
        $this->assertSame('exitosa', $run->estado);
        $this->assertSame(1, $run->productos_obtenidos);
    }

    public function test_fuente_manual_no_tiene_driver_y_se_avisa_sin_fallar(): void
    {
        $this->artisan('precios:sync', ['--fuente' => 'pricesmart'])
            ->assertSuccessful(); // pricesmart es carga manual según ADR-10/doc 06 §5.5

        $this->assertSame(0, SyncRun::count());
    }

    public function test_fuente_desconocida_falla_con_codigo_de_error(): void
    {
        $this->artisan('precios:sync', ['--fuente' => 'no-existe'])
            ->assertExitCode(1);

        $this->assertSame(0, SyncRun::count());
    }

    public function test_bloqueo_del_supermercado_marca_corrida_abortada_y_comando_falla(): void
    {
        config(['price_providers.fuentes.prueba-vtex' => [
            'modo' => 'vtex',
            'base_url' => 'https://prueba-vtex.test',
            'enabled' => true,
        ]]);

        Http::fake(['*' => Http::response('Access Denied', 403)]);

        $this->artisan('precios:sync', ['--fuente' => 'prueba-vtex'])
            ->assertExitCode(1);

        $run = SyncRun::sole();
        $this->assertSame('abortada', $run->estado);
        $this->assertStringContainsString('403', $run->mensaje_error);
        $this->assertNotNull($run->finalizada_en);
    }
}
