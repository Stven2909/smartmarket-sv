<?php

namespace Tests\Feature;

use App\Models\PrecioActual;
use App\Models\ProductoRaw;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

// ADR-012: precios:procesar solo publica filas de Super Selectos. Las demás
// cadenas se alimentan con MockSupermarketsSeeder y nunca pasan por staging.
class PreciosProcesarCommandTest extends TestCase
{
    use RefreshDatabase;

    private function crearRaw(string $fuente, string $nombre, float $precio): ProductoRaw
    {
        return ProductoRaw::create([
            'fuente' => $fuente,
            'sku_externo' => hash('sha256', $fuente . '|' . $nombre),
            'nombre' => $nombre,
            'unidad' => 'unidad',
            'precio_normal' => null,
            'precio_final' => $precio,
            'tiene_promocion' => false,
            'disponible' => true,
            'url_fuente' => 'https://listado.test/producto/1',
            'raw_payload' => ['origen' => 'prueba'],
            'estado' => 'pendiente',
        ]);
    }

    public function test_sin_fuente_procesa_solo_super_selectos(): void
    {
        $selectos = $this->crearRaw('super-selectos', 'Salsa Picante Chiltepin 250 ml', 2.35);
        $walmart = $this->crearRaw('walmart', 'Salsa Picante Chiltepin 250 ml', 2.10);

        $this->artisan('precios:procesar')->assertSuccessful();

        $this->assertSame('publicado', $selectos->fresh()->estado);
        $this->assertSame('pendiente', $walmart->fresh()->estado);
        $this->assertSame(1, PrecioActual::count());
    }

    public function test_fuente_fuera_de_lista_blanca_falla_sin_procesar(): void
    {
        $walmart = $this->crearRaw('walmart', 'Salsa Picante Chiltepin 250 ml', 2.10);

        $this->artisan('precios:procesar', ['--fuente' => 'walmart'])
            ->assertExitCode(1);

        $this->assertSame('pendiente', $walmart->fresh()->estado);
        $this->assertSame(0, PrecioActual::count());
    }

    public function test_fuente_desconocida_falla_con_codigo_de_error(): void
    {
        $this->artisan('precios:procesar', ['--fuente' => 'no-existe'])
            ->assertExitCode(1);

        $this->assertSame(0, PrecioActual::count());
    }
}
