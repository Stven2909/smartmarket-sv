<?php

namespace Tests\Feature;

use App\Filament\Resources\ProductoRaws\Pages\ListProductoRaws;
use App\Filament\Resources\SyncRuns\Pages\ListSyncRuns;
use App\Models\AliasProducto;
use App\Models\Categoria;
use App\Models\HistorialPrecio;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ProductoRaw;
use App\Models\SyncRun;
use App\Models\User;
use App\Services\PriceProviders\StagingProcessor;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Livewire\Livewire;
use Tests\TestCase;

class StagingCuracionTest extends TestCase
{
    use RefreshDatabase;

    private User $admin;

    protected function setUp(): void
    {
        parent::setUp();

        $this->admin = User::create([
            'name' => 'Admin Curacion',
            'email' => 'curador@test.sv',
            'password' => 'password123',
            'rol' => 'admin',
            'estado' => 'activo',
        ]);
    }

    private function filaRaw(array $overrides = []): ProductoRaw
    {
        return ProductoRaw::create([
            'fuente' => 'super-selectos',
            'sku_externo' => 'SKU-' . uniqid(),
            'nombre' => 'Galletas Club Social Mantequilla 216 g',
            'unidad' => 'g',
            'precio_normal' => 1.85,
            'precio_final' => 1.60,
            'tiene_promocion' => true,
            'disponible' => true,
            'raw_payload' => ['nombre' => 'Club Social', 'url' => 'https://example.com/p'],
            'estado' => 'pendiente',
            ...$overrides,
        ]);
    }

    public function test_procesar_filas_publica_un_lote_especifico_reutilizando_la_escalera(): void
    {
        // Catalogo previo: un producto cuyo nombre matcheara por similitud >= 85%
        Categoria::create(['nombre' => 'Snacks']);
        Producto::create([
            'categoria_id' => 1,
            'marca' => 'Gamesa',
            'nombre' => 'Galletas Club Social Mantequilla 216g',
            'activo' => true,
        ]);

        $existente = $this->filaRaw(['nombre' => 'Galletas Club Social Mantequilla 216 g']);
        $nuevo = $this->filaRaw([
            'nombre' => 'Cerveza Regia Lata 355 mL',
            'sku_externo' => 'SKU-REGIA',
            'tiene_promocion' => false,
            'precio_final' => 1.10,
        ]);

        $conteos = app(StagingProcessor::class)->procesarFilas(collect([$existente, $nuevo]));

        $this->assertSame(2, $conteos['procesados']);
        $this->assertSame(2, $conteos['publicados']);
        $this->assertSame(1, $conteos['nuevos_productos']);
        $this->assertSame(2, $conteos['alias_nuevos']);
        $this->assertSame(0, $conteos['errores']);

        // Ambas filas quedaron publicadas con trazabilidad.
        $this->assertEquals('publicado', $existente->refresh()->estado);
        $this->assertEquals('publicado', $nuevo->refresh()->estado);
        $this->assertNotNull($existente->procesado_at);

        // La sucursal virtual online (ADR-11) recibio los precios.
        $this->assertSame(2, PrecioActual::whereHas('sucursal', fn ($q) => $q->whereNull('latitud'))->count());
        $this->assertSame(2, AliasProducto::count());

        // Sin historial: primera publicacion, no habia precio anterior que archivar.
        $this->assertSame(0, HistorialPrecio::count());
    }

    public function test_fila_invalida_dentro_del_lote_queda_en_error_sin_tirar_el_resto(): void
    {
        $valida = $this->filaRaw();
        $invalida = $this->filaRaw([
            'nombre' => 'Producto Roto',
            'precio_final' => 0,
        ]);

        $conteos = app(StagingProcessor::class)->procesarFilas(collect([$invalida, $valida]));

        $this->assertSame(2, $conteos['procesados']);
        $this->assertSame(1, $conteos['publicados']);
        $this->assertSame(1, $conteos['errores']);

        $this->assertEquals('error', $invalida->refresh()->estado);
        $this->assertStringContainsString('precio_invalido', (string) $invalida->motivo_rechazo);
        $this->assertEquals('publicado', $valida->refresh()->estado);
    }

    public function test_procesar_por_fuente_delega_y_respeta_el_limite(): void
    {
        $this->filaRaw(['sku_externo' => 'A']);
        $this->filaRaw(['sku_externo' => 'B']);

        $conteos = app(StagingProcessor::class)->procesar(fuente: 'super-selectos', limite: 1);

        $this->assertSame(1, $conteos['procesados']);
        $this->assertSame(1, ProductoRaw::where('estado', 'publicado')->count());
        $this->assertSame(1, ProductoRaw::where('estado', 'pendiente')->count());
    }

    public function test_listado_de_staging_renderiza_para_admin(): void
    {
        $this->filaRaw();

        $this->actingAs($this->admin);

        Livewire::test(ListProductoRaws::class)->assertSuccessful();
    }

    public function test_listado_de_corridas_renderiza_para_admin(): void
    {
        SyncRun::create([
            'fuente' => 'super-selectos',
            'modo' => 'html',
            'estado' => 'exitosa',
            'iniciada_en' => now(),
            'finalizada_en' => now(),
            'productos_obtenidos' => 20,
            'productos_nuevos' => 20,
            'productos_duplicados' => 0,
            'rechazados' => 0,
            'detalle' => ['paginas' => 1],
        ]);

        $this->actingAs($this->admin);

        Livewire::test(ListSyncRuns::class)->assertSuccessful();
    }
}
