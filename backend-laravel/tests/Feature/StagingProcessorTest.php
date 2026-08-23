<?php

namespace Tests\Feature;

use App\Models\AliasProducto;
use App\Models\Categoria;
use App\Models\HistorialPrecio;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ProductoRaw;
use App\Models\Supermercado;
use App\Models\Sucursal;
use App\Services\NormalizadorTexto;
use App\Services\PriceProviders\StagingProcessor;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class StagingProcessorTest extends TestCase
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
            'categoria_raw' => null,
            'precio_normal' => null,
            'precio_final' => 2.35,
            'tiene_promocion' => false,
            'disponible' => true,
            'url_fuente' => 'https://listado.test/producto/1',
            'raw_payload' => ['origen' => 'prueba'],
            'estado' => 'pendiente',
        ], $sobrescribir));
    }

    private function procesar(?string $fuente = null, bool $dryRun = false): array
    {
        return app(StagingProcessor::class)->procesar($fuente, null, $dryRun);
    }

    public function test_publica_fila_nueva_creando_producto_alias_sucursal_e_historial(): void
    {
        $this->crearRaw();

        $conteos = $this->procesar();

        $this->assertSame(1, $conteos['procesados']);
        $this->assertSame(1, $conteos['publicados']);
        $this->assertSame(1, $conteos['nuevos_productos']);
        $this->assertSame(1, $conteos['alias_nuevos']);
        $this->assertSame(0, $conteos['errores']);

        // Staging marcada como publicada y con momento de procesamiento.
        $raw = ProductoRaw::sole();
        $this->assertSame('publicado', $raw->estado);
        $this->assertNotNull($raw->procesado_at);
        $this->assertNull($raw->motivo_rechazo);

        // Producto nuevo del catálogo maestro.
        $producto = Producto::sole();
        $this->assertSame('Salsa Picante Chiltepin 250 ml', $producto->nombre);
        $this->assertSame('Sin marca', $producto->marca);
        $this->assertTrue($producto->activo);
        $this->assertSame('Otros', $producto->categoria->nombre);

        // Alias canónico (normalizado) con trazabilidad de su fuente.
        $alias = AliasProducto::sole();
        $this->assertSame($producto->id, $alias->producto_id);
        $this->assertSame(NormalizadorTexto::limpiar('Salsa Picante Chiltepin 250 ml'), $alias->alias);
        $this->assertSame(self::FUENTE, $alias->origen);

        // ADR-11: sucursal virtual sin coordenadas, excluida del ranking por distancia.
        $supermercado = Supermercado::sole();
        $this->assertSame('Super Selectos', $supermercado->nombre);
        $sucursal = Sucursal::sole();
        $this->assertSame($supermercado->id, $sucursal->supermercado_id);
        $this->assertSame('Tienda en línea', $sucursal->nombre);
        $this->assertNull($sucursal->latitud);
        $this->assertNull($sucursal->longitud);

        // Sin promo: precio_normal cae al final (columna NOT NULL en catálogo).
        $precio = PrecioActual::sole();
        $this->assertSame($producto->id, $precio->producto_id);
        $this->assertSame($sucursal->id, $precio->sucursal_id);
        $this->assertSame(2.35, (float) $precio->precio_final);
        $this->assertSame(2.35, (float) $precio->precio_normal);
        $this->assertFalse($precio->tiene_promocion);
        $this->assertSame('html-' . self::FUENTE, $precio->origen_dato); // convención {modo}-{fuente}

        // Historial: la PRIMERA publicación no archiva nada (no hay precio previo
        // que pierda vigencia). El PrecioActualObserver registra el anterior en
        // cada cambio posterior — Regla fija #1 sin duplicar filas.
        $this->assertSame(0, HistorialPrecio::count());
    }

    public function test_preserva_el_precio_normal_cuando_hay_promocion(): void
    {
        $this->crearRaw([
            'nombre' => 'Café Extra Fuerte 500 g',
            'unidad' => '500 g',
            'precio_normal' => 6.50,
            'precio_final' => 4.99,
            'tiene_promocion' => true,
        ]);

        $this->procesar();

        $precio = PrecioActual::sole();
        $this->assertSame(6.50, (float) $precio->precio_normal);
        $this->assertSame(4.99, (float) $precio->precio_final);
        $this->assertTrue($precio->tiene_promocion);
    }

    public function test_alias_exacto_existente_vincula_sin_crear_producto(): void
    {
        $categoria = Categoria::firstOrCreate(['nombre' => 'Otros']);
        $existente = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'La Ideal',
            'nombre' => 'Salsa Chiltepin Roja',
            'activo' => true,
        ]);
        AliasProducto::create([
            'producto_id' => $existente->id,
            'alias' => 'Salsa Chiltepin ROJA', // formato legible: se iguala normalizado
            'origen' => 'seed_demo',
        ]);

        // Mismo texto tras limpiar(), aunque cambien mayúsculas y espacios.
        $this->crearRaw(['nombre' => 'salsa   CHILTEPIN roja']);

        $conteos = $this->procesar();

        $this->assertSame(0, $conteos['nuevos_productos']);
        $this->assertSame(0, $conteos['alias_nuevos']); // el alias ya existía
        $this->assertSame(1, Producto::count()); // nada nuevo
        $this->assertSame($existente->id, PrecioActual::sole()->producto_id);
    }

    public function test_similitud_alta_vincula_al_producto_y_agrega_alias(): void
    {
        $existenteNombre = 'Shampoo Palmolive Manzana 750 ml';
        $rawNombre = 'Shampoo Palmolive Manzanilla 750 ml';

        // Guardia del fixture: garantizamos que cruza el umbral aprobado (doc 06 §4).
        similar_text(
            NormalizadorTexto::limpiar($rawNombre),
            NormalizadorTexto::limpiar($existenteNombre),
            $porcentaje,
        );
        $this->assertGreaterThanOrEqual(85.0, $porcentaje);

        $categoria = Categoria::firstOrCreate(['nombre' => 'Otros']);
        $existente = Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Palmolive',
            'nombre' => $existenteNombre,
            'activo' => true,
        ]);

        $this->crearRaw(['nombre' => $rawNombre]);

        $conteos = $this->procesar();

        $this->assertSame(0, $conteos['nuevos_productos']); // fuzzy lo capturó
        $this->assertSame(1, $conteos['alias_nuevos']); // nombre nuevo registrado como alias
        $this->assertSame(1, Producto::count());
        $this->assertSame($existente->id, PrecioActual::sole()->producto_id);
        $this->assertSame(NormalizadorTexto::limpiar($rawNombre), AliasProducto::latest('id')->first()->alias);
    }

    public function test_similitud_baja_crea_producto_independiente(): void
    {
        $categoria = Categoria::firstOrCreate(['nombre' => 'Otros']);
        Producto::create([
            'categoria_id' => $categoria->id,
            'marca' => 'Bimbo',
            'nombre' => 'Pan Blanco Grande',
            'activo' => true,
        ]);

        $this->crearRaw(['nombre' => 'Detergente Ajax Limon 900 ml', 'unidad' => '900 ml']);

        $conteos = $this->procesar();

        $this->assertSame(1, $conteos['nuevos_productos']);
        $this->assertSame(2, Producto::count());

        $vinculado = PrecioActual::sole()->producto_id;
        $this->assertNotSame(Producto::where('marca', 'Bimbo')->sole()->id, $vinculado);
    }
}
