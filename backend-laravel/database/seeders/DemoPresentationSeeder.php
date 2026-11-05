<?php

namespace Database\Seeders;

use App\Models\Categoria;
use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Models\Producto;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use RuntimeException;

/**
 * Prepara una lista reproducible para la presentación local.
 * No se incluye en DatabaseSeeder porque crea datos destinados a la demo.
 */
class DemoPresentationSeeder extends Seeder
{
    public const LIST_NAME = 'DEMO · Lista mixta y subtotal parcial';

    /** @var array<int, array{name: string, brand: string, category: string, essential: bool, unit?: string, amount?: float}> */
    private const PRODUCTS = [
        ['name' => 'Leche entera', 'brand' => 'Foremost', 'category' => 'Lácteos', 'essential' => true],
        ['name' => 'Frijol rojo', 'brand' => 'Genérico', 'category' => 'Granos básicos', 'essential' => true],
        ['name' => 'Gaseosa', 'brand' => 'Coca-Cola', 'category' => 'Bebidas', 'essential' => false],
        ['name' => 'Detergente en polvo', 'brand' => 'Ariel', 'category' => 'Limpieza', 'essential' => true],
        ['name' => 'Pasta dental', 'brand' => 'Colgate', 'category' => 'Higiene personal', 'essential' => true],
        [
            'name' => 'Club Social Mantequilla 216 g',
            'brand' => 'Club Social',
            'category' => 'Galletas y snacks',
            'essential' => false,
            'unit' => 'g',
            'amount' => 216,
        ],
        [
            'name' => 'Chocolate Snickers Almendra 49.9 g Barra',
            'brand' => 'Snickers',
            'category' => 'Chocolates',
            'essential' => false,
            'unit' => 'g',
            'amount' => 49.9,
        ],
    ];

    public function run(): void
    {
        if (! app()->environment('local', 'testing')) {
            throw new RuntimeException('DemoPresentationSeeder solo puede ejecutarse en local o testing.');
        }

        $this->call([
            UserSeeder::class,
            DemoDataSeeder::class,
        ]);

        $usuario = User::query()->where('email', 'usuario@smartmarket.sv')->firstOrFail();

        DB::transaction(function () use ($usuario): void {
            $productos = [];

            foreach (self::PRODUCTS as $definition) {
                $categoria = Categoria::firstOrCreate(['nombre' => $definition['category']]);
                $producto = Producto::query()->where('nombre', $definition['name'])->first();
                $atributos = [
                    'categoria_id' => $categoria->id,
                    'marca' => $definition['brand'],
                    'activo' => true,
                ];

                if ($producto) {
                    $producto->update($atributos);
                } else {
                    $producto = Producto::create([
                        ...$atributos,
                        'nombre' => $definition['name'],
                        'unidad_medida' => $definition['unit'] ?? 'unidad',
                        'contenido' => $definition['amount'] ?? 1,
                    ]);
                }

                $productos[] = [$producto, $definition['essential']];
            }

            $lista = ListaCompra::updateOrCreate(
                ['usuario_id' => $usuario->id, 'nombre' => self::LIST_NAME],
                [
                    'presupuesto' => 18.50,
                    'estado' => 'activa',
                    'fecha' => now(),
                ],
            );

            foreach ($productos as [$producto, $esencial]) {
                ListaCompraDetalles::updateOrCreate(
                    ['lista_id' => $lista->id, 'producto_id' => $producto->id],
                    ['cantidad' => 1, 'esencial' => $esencial, 'permite_sustituto' => false],
                );
            }
        });

        // Las cadenas sin extracción real reciben precios mock deterministas.
        // En la tienda física de Selectos quedan faltantes intencionalmente.
        $this->call(MockSupermarketsSeeder::class);

        $this->command?->info('Lista final de demo preparada con 7 productos y un caso de subtotal parcial.');
    }
}
