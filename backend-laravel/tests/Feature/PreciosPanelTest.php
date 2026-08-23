<?php

namespace Tests\Feature;

use App\Filament\Resources\PrecioActuals\Pages\CreatePrecioActual;
use App\Filament\Resources\PrecioActuals\Pages\EditPrecioActual;
use App\Models\Categoria;
use App\Models\HistorialPrecio;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\Sucursal;
use App\Models\Supermercado;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Livewire\Livewire;
use Tests\TestCase;

class PreciosPanelTest extends TestCase
{
    use RefreshDatabase;

    private User $admin;

    private Producto $producto;

    private Sucursal $sucursal;

    protected function setUp(): void
    {
        parent::setUp();

        $this->admin = User::create([
            'name' => 'Admin Panel',
            'email' => 'panel-admin@test.sv',
            'password' => 'password123',
            'rol' => 'admin',
            'estado' => 'activo',
        ]);

        $categoria = Categoria::create(['nombre' => 'Snacks']);
        $this->producto = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Club Social',
            'nombre' => 'Galletas Club Social Mantequilla 216 g',
            'activo' => true,
        ]);
        $super = Supermercado::create(['nombre' => 'Super Selectos', 'activo' => true]);
        $this->sucursal = Sucursal::create([
            'supermercado_id' => $super->id,
            'nombre' => 'Selectos Santa Elena',
            'direccion' => 'Santa Elena',
            'latitud' => 13.67,
            'longitud' => -89.19,
        ]);
    }

    public function test_editar_precio_desde_el_panel_archiva_el_valor_anterior_en_historial(): void
    {
        $precio = PrecioActual::create([
            'producto_id' => $this->producto->id,
            'sucursal_id' => $this->sucursal->id,
            'precio_normal' => 1.85,
            'precio_final' => 1.85,
            'tiene_promocion' => false,
            'origen_dato' => 'manual',
            'fecha_actualizacion' => now(),
        ]);

        $this->actingAs($this->admin);

        Livewire::test(EditPrecioActual::class, ['record' => $precio->getKey()])
            ->fillForm([
                'precio_final' => 1.50,
                'tiene_promocion' => true,
                'tipo_promocion' => 'rebaja',
            ])
            ->call('save');

        // El observer (no el panel) es quien archiva: un solo escritor de historial.
        $archivado = HistorialPrecio::where('producto_id', $this->producto->id)
            ->where('sucursal_id', $this->sucursal->id)
            ->first();

        $this->assertNotNull($archivado);
        $this->assertEquals(1.85, (float) $archivado->precio_final);
        $this->assertEquals('manual', $archivado->origen);
        $this->assertEquals(1.50, (float) $precio->refresh()->precio_final);
    }

    public function test_crear_precio_desde_el_panel_sella_origen_manual_y_fecha(): void
    {
        $this->actingAs($this->admin);

        Livewire::test(CreatePrecioActual::class)
            ->fillForm([
                'producto_id' => $this->producto->getKey(),
                'sucursal_id' => $this->sucursal->getKey(),
                'precio_normal' => '2.25',
                'precio_final' => '2.10',
            ])
            ->call('create');

        $precio = PrecioActual::query()
            ->where('producto_id', $this->producto->id)
            ->where('sucursal_id', $this->sucursal->id)
            ->first();

        $this->assertNotNull($precio);
        $this->assertSame('manual', $precio->origen_dato);
        $this->assertNotNull($precio->fecha_actualizacion);
        $this->assertFalse($precio->tiene_promocion);
    }

    public function test_listado_de_precios_renderiza_para_admin(): void
    {
        PrecioActual::create([
            'producto_id' => $this->producto->id,
            'sucursal_id' => $this->sucursal->id,
            'precio_normal' => 1.85,
            'precio_final' => 1.60,
            'tiene_promocion' => true,
            'tipo_promocion' => 'rebaja',
            'origen_dato' => 'html-super-selectos',
            'fecha_actualizacion' => now(),
        ]);

        $this->actingAs($this->admin);

        Livewire::test(\App\Filament\Resources\PrecioActuals\Pages\ListPrecioActuals::class)
            ->assertSuccessful();
    }
}
