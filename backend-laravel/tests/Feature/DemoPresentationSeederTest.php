<?php

namespace Tests\Feature;

use App\Models\Categoria;
use App\Models\ListaCompra;
use App\Models\Producto;
use Database\Seeders\DemoPresentationSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class DemoPresentationSeederTest extends TestCase
{
    use RefreshDatabase;

    public function test_prepara_catalogo_curado_y_lista_de_siete_productos_repetible(): void
    {
        $this->seed(DemoPresentationSeeder::class);
        $this->seed(DemoPresentationSeeder::class);

        $lista = ListaCompra::query()
            ->where('nombre', DemoPresentationSeeder::LIST_NAME)
            ->with('detalles.producto.categoria')
            ->firstOrFail();

        $this->assertCount(7, $lista->detalles);
        $this->assertSame(18.5, (float) $lista->presupuesto);

        $clubSocial = Producto::query()->where('nombre', 'Club Social Mantequilla 216 g')->firstOrFail();
        $this->assertSame('Club Social', $clubSocial->marca);
        $this->assertSame('Galletas y snacks', $clubSocial->categoria->nombre);

        $snickers = Producto::query()->where('nombre', 'Chocolate Snickers Almendra 49.9 g Barra')->firstOrFail();
        $this->assertSame('Snickers', $snickers->marca);
        $this->assertSame('Chocolates', $snickers->categoria->nombre);

        $this->assertSame(7, $lista->detalles->pluck('producto_id')->unique()->count());
        $this->assertSame(4, Categoria::query()->whereIn('nombre', ['Lácteos', 'Granos básicos', 'Galletas y snacks', 'Chocolates'])->count());
    }
}
