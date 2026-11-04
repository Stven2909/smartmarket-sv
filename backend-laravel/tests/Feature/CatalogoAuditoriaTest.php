<?php

namespace Tests\Feature;

use App\Models\AliasProducto;
use App\Models\Categoria;
use App\Models\Producto;
use App\Models\ProductoRaw;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Artisan;
use Tests\TestCase;

class CatalogoAuditoriaTest extends TestCase
{
    use RefreshDatabase;

    public function test_reporta_duplicados_alias_en_conflicto_y_revision_manual(): void
    {
        $categoria = Categoria::create(['nombre' => 'Otros']);

        $duplicadoA = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Sin marca',
            'nombre' => 'Arroz Blanco 1 lb',
            'activo' => true,
        ]);
        $duplicadoB = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Sin marca',
            'nombre' => 'ARROZ  blanco 1 LB',
            'activo' => true,
        ]);

        AliasProducto::create(['producto_id' => $duplicadoA->id, 'alias' => 'arroz comun', 'origen' => 'test']);
        AliasProducto::create(['producto_id' => $duplicadoB->id, 'alias' => 'Arroz Común', 'origen' => 'test']);

        ProductoRaw::create([
            'fuente' => 'prueba',
            'sku_externo' => 'sku-revision',
            'nombre' => 'Arroz blanco 1 lb',
            'precio_final' => 1.25,
            'disponible' => true,
            'raw_payload' => ['origen' => 'test'],
            'estado' => 'revision_manual',
            'motivo_rechazo' => 'match_ambiguo: "arroz blanco 1 lb" (95.0%) vs "arroz  blanco 1 lb" (93.0%)',
        ]);

        ProductoRaw::create([
            'fuente' => 'prueba',
            'sku_externo' => 'sku-pendiente',
            'nombre' => 'Arroz Blanco 1 lb',
            'precio_final' => 1.20,
            'disponible' => true,
            'raw_payload' => ['origen' => 'test'],
            'estado' => 'pendiente',
        ]);

        Artisan::call('catalogo:auditoria', ['--limite' => 10]);
        $salida = Artisan::output();

        $this->assertStringContainsString('Nombres normalizados duplicados: 1', $salida);
        $this->assertStringContainsString('Alias normalizados que apuntan a más de un producto: 1', $salida);
        $this->assertStringContainsString('Cola de revisión manual', $salida);
        $this->assertStringContainsString('match_ambiguo', $salida);
        $this->assertStringContainsString('Distribución de similitud', $salida);
    }
}
