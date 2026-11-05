<?php

namespace Tests\Feature;

use App\Models\Categoria;
use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\Sucursal;
use App\Models\Supermercado;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class ListaOptimizarTest extends TestCase
{
    use RefreshDatabase;

    public function test_optimizar_sin_precios_devuelve_422_sin_llamar_al_experto(): void
    {
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();
        $lista = $this->crearLista($usuario, $producto);

        Http::fake();

        $this->actingAs($usuario)
            ->getJson("/api/listas/{$lista->id}/optimizar?lat=13.70&lng=-89.20")
            ->assertStatus(422)
            ->assertJson([
                'message' => 'La lista no tiene productos todavía, o ninguno tiene precio disponible.',
            ]);

        Http::assertNothingSent();
    }

    public function test_optimizar_con_respuesta_invalida_conserva_el_ranking_y_marca_el_motivo(): void
    {
        $usuario = $this->crearUsuario();
        $producto = $this->crearProducto();
        $lista = $this->crearLista($usuario, $producto);
        $this->crearSucursalConPrecio($producto, 2.50);

        // HTTP 200 pero sin los campos exigidos por el contrato: no se debe
        // persistir como recomendación válida.
        Http::fake([
            '*' => Http::response([
                'request_id' => 'lista-'.$lista->id.'-sucursal-1',
                'nivel_recomendacion' => 'EXCELENTE',
            ], 200),
        ]);

        $respuesta = $this->actingAs($usuario)
            ->getJson("/api/listas/{$lista->id}/optimizar?lat=13.70&lng=-89.20")
            ->assertOk();

        $resultado = $respuesta->json('resultados.0');

        $this->assertFalse($resultado['expert_system_available']);
        $this->assertNull($resultado['recommendation']);
        $this->assertSame('respuesta_invalida', $resultado['expert_omission_reason']);
        $this->assertNotNull($respuesta->json('resultado_optimizacion_id'));
        $this->assertNotNull($respuesta->json('mejor_opcion'));
    }

    private function crearUsuario(): User
    {
        return User::create([
            'name' => 'Cliente Demo',
            'email' => 'demo-optimizar@test.sv',
            'password' => 'password-secreto',
        ]);
    }

    private function crearProducto(): Producto
    {
        $categoria = Categoria::create(['nombre' => 'Pruebas']);

        return Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Marca',
            'nombre' => 'Producto de prueba',
            'activo' => true,
        ]);
    }

    private function crearLista(User $usuario, Producto $producto): ListaCompra
    {
        $lista = ListaCompra::create([
            'usuario_id' => $usuario->id,
            'nombre' => 'Lista de prueba',
            'presupuesto' => 10.0,
            'estado' => 'activa',
            'fecha' => now(),
        ]);

        ListaCompraDetalles::create([
            'lista_id' => $lista->id,
            'producto_id' => $producto->id,
            'cantidad' => 1,
            'esencial' => true,
        ]);

        return $lista;
    }

    private function crearSucursalConPrecio(Producto $producto, float $precio): void
    {
        $supermercado = Supermercado::create(['nombre' => 'Super de prueba']);
        $sucursal = Sucursal::create([
            'supermercado_id' => $supermercado->id,
            'nombre' => 'Sucursal de prueba',
            'direccion' => 'Calle de prueba',
            'latitud' => 13.6990,
            'longitud' => -89.2000,
        ]);

        PrecioActual::create([
            'producto_id' => $producto->id,
            'sucursal_id' => $sucursal->id,
            'precio_normal' => $precio,
            'precio_final' => $precio,
        ]);
    }
}
