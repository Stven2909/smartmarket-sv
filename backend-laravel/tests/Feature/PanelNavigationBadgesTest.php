<?php

namespace Tests\Feature;

use App\Filament\Resources\ProductoRaws\ProductoRawResource;
use App\Filament\Resources\SyncRuns\SyncRunResource;
use App\Models\ProductoRaw;
use App\Models\SyncRun;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class PanelNavigationBadgesTest extends TestCase
{
    use RefreshDatabase;

    public function test_staging_muestra_conteo_de_pendientes_en_ambar(): void
    {
        ProductoRaw::create($this->fila('A'));
        ProductoRaw::create($this->fila('B'));

        $this->assertSame('2', ProductoRawResource::getNavigationBadge());
        $this->assertSame('warning', ProductoRawResource::getNavigationBadgeColor());
    }

    public function test_staging_oculta_el_badge_sin_pendientes(): void
    {
        ProductoRaw::create($this->fila('A', ['estado' => 'publicado']));

        $this->assertNull(ProductoRawResource::getNavigationBadge());
    }

    public function test_syncruns_refleja_el_estado_de_la_ultima_corrida(): void
    {
        // Sin corridas: sin badge.
        $this->assertNull(SyncRunResource::getNavigationBadge());
        $this->assertNull(SyncRunResource::getNavigationBadgeColor());

        SyncRun::create($this->corrida('exitosa', now()->subDay()));
        SyncRun::create($this->corrida('fallida', now()));

        // La mas reciente manda, no la primera.
        $this->assertSame('Falló', SyncRunResource::getNavigationBadge());
        $this->assertSame('danger', SyncRunResource::getNavigationBadgeColor());
    }

    public function test_syncruns_marca_verde_si_la_mas_reciente_fue_exitosa(): void
    {
        SyncRun::create($this->corrida('fallida', now()->subDay()));
        SyncRun::create($this->corrida('exitosa', now()));

        $this->assertSame('OK', SyncRunResource::getNavigationBadge());
        $this->assertSame('success', SyncRunResource::getNavigationBadgeColor());
    }

    private function fila(string $sku, array $overrides = []): array
    {
        return [
            'fuente' => 'super-selectos',
            'sku_externo' => "SKU-{$sku}",
            'nombre' => "Producto {$sku}",
            'precio_final' => 1.5,
            'raw_payload' => [],
            'estado' => 'pendiente',
            ...$overrides,
        ];
    }

    private function corrida(string $estado, $iniciada): array
    {
        return [
            'fuente' => 'super-selectos',
            'modo' => 'html',
            'estado' => $estado,
            'iniciada_en' => $iniciada,
            'finalizada_en' => (clone $iniciada)->addMinutes(2),
            'productos_obtenidos' => 1,
            'productos_nuevos' => 1,
            'productos_duplicados' => 0,
            'rechazados' => 0,
            'mensaje_error' => $estado === 'fallida' ? 'timeout' : null,
        ];
    }
}
