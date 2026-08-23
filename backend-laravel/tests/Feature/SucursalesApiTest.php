<?php

namespace Tests\Feature;

use App\Models\Sucursal;
use App\Models\Supermercado;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class SucursalesApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_no_expone_las_sucursales_virtuales_tienda_en_linea(): void
    {
        // ADR-11: la sucursal virtual ancla precios automáticos pero no es un
        // lugar visitable — la app jamás debe mostrarla como opción.
        $super = Supermercado::create(['nombre' => 'Super Selectos', 'activo' => true]);

        Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Tienda en línea',
            'direccion' => 'Compra en línea — sin dirección física',
            'latitud' => null,
            'longitud' => null,
        ]);

        Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Selectos San Salvador Centro',
            'direccion' => 'Centro',
            'latitud' => 13.6929,
            'longitud' => -89.2182,
        ]);

        $nombres = collect($this->getJson('/api/sucursales')->assertOk()->json())
            ->pluck('nombre');

        $this->assertContains('Selectos San Salvador Centro', $nombres);
        $this->assertNotContains('Tienda en línea', $nombres);
    }
}
