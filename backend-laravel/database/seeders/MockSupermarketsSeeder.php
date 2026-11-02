<?php

namespace Database\Seeders;

use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\Supermercado;
use App\Models\Sucursal;
use Illuminate\Database\Seeder;

// Datos mock para las cadenas que NO se sincronizan por webscraping (ADR-012).
// Walmart, Maxi Despensa, La Despensa de Don Juan y PriceSmart reciben precios
// deterministas derivados del precio de Super Selectos, de modo que el
// comparador siempre tenga alternativas sin depender de scraping.
//
// El seeder es idempotente: la clave (producto_id, sucursal_id) es única y los
// valores se recalculan siempre igual, así que correrlo dos veces no duplica
// filas ni altera los precios de Super Selectos.
class MockSupermarketsSeeder extends Seeder
{
    public const ORIGEN = 'mock-seeder';

    // factor = posicionamiento relativo frente a la base de Super Selectos.
    private const CADENAS = [
        'Walmart' => [
            'sucursal' => 'Walmart Metrocentro',
            'direccion' => 'Metrocentro, San Salvador',
            'latitud' => 13.6996,
            'longitud' => -89.2182,
            'sitio_web' => 'https://walmart.com.sv',
            'factor' => 0.97,
        ],
        'Maxi Despensa' => [
            'sucursal' => 'Maxi Despensa San Salvador',
            'direccion' => 'San Salvador',
            'latitud' => 13.7012,
            'longitud' => -89.2245,
            'sitio_web' => 'https://www.maxidespensa.com.sv',
            'factor' => 0.93,
        ],
        'La Despensa de Don Juan' => [
            'sucursal' => 'Don Juan San Salvador',
            'direccion' => 'San Salvador',
            'latitud' => 13.6907,
            'longitud' => -89.2103,
            'sitio_web' => 'https://www.ladespensadedonjuan.com.sv',
            'factor' => 0.99,
        ],
        'PriceSmart' => [
            'sucursal' => 'PriceSmart Santa Elena',
            'direccion' => 'Santa Elena, Antiguo Cuscatlán',
            'latitud' => 13.6739,
            'longitud' => -89.2459,
            'sitio_web' => 'https://pricesmart.com/sv',
            'factor' => 1.04,
        ],
    ];

    public function run(): void
    {
        $productos = Producto::query()
            ->where('activo', true)
            ->orderBy('id')
            ->get();

        if ($productos->isEmpty()) {
            $this->command?->warn('MockSupermarketsSeeder: no hay productos activos; nada que sembrar.');

            return;
        }

        $baseSelectos = $this->baseSuperSelectos();
        $asegurados = 0;

        foreach (self::CADENAS as $nombreCadena => $cadena) {
            $supermercado = Supermercado::firstOrCreate(
                ['nombre' => $nombreCadena],
                ['sitio_web' => $cadena['sitio_web'], 'activo' => true],
            );

            $sucursal = Sucursal::firstOrCreate(
                ['supermercado_id' => $supermercado->id, 'nombre' => $cadena['sucursal']],
                [
                    'direccion' => $cadena['direccion'],
                    'latitud' => $cadena['latitud'],
                    'longitud' => $cadena['longitud'],
                ],
            );

            foreach ($productos as $producto) {
                $base = $baseSelectos[$producto->id] ?? $this->precioDerivado($producto);
                [$normal, $final, $tipoPromocion] = $this->precioMock($producto, $nombreCadena, $base, $cadena['factor']);

                PrecioActual::updateOrCreate(
                    ['producto_id' => $producto->id, 'sucursal_id' => $sucursal->id],
                    [
                        'precio_normal' => $normal,
                        'precio_final' => $final,
                        'tiene_promocion' => $tipoPromocion !== null,
                        'tipo_promocion' => $tipoPromocion,
                        'fecha_actualizacion' => now(),
                        'origen_dato' => self::ORIGEN,
                    ],
                );

                $asegurados++;
            }
        }

        $this->command?->info(
            'MockSupermarketsSeeder: ' . $asegurados . ' precios mock asegurados para '
            . count(self::CADENAS) . ' cadenas.'
        );
    }

    /**
     * Último precio conocido de Super Selectos por producto. Cuando no existe,
     * el precio se deriva del propio producto para mantener el determinismo.
     *
     * @return array<int, float> producto_id => precio_final
     */
    private function baseSuperSelectos(): array
    {
        $precios = PrecioActual::query()
            ->whereHas('sucursal.supermercado', fn ($query) => $query->where('nombre', 'Super Selectos'))
            ->orderBy('fecha_actualizacion')
            ->orderBy('id')
            ->get(['producto_id', 'precio_final']);

        $base = [];

        foreach ($precios as $precio) {
            $base[(int) $precio->producto_id] = (float) $precio->precio_final;
        }

        return $base;
    }

    private function precioDerivado(Producto $producto): float
    {
        $semilla = $this->semilla($producto->nombre . '|' . $producto->marca . '|' . $producto->contenido);

        // Rango estable de $1.25 a $9.99 para no inventar precios absurdos.
        return round(1.25 + ($semilla % 875) / 100, 2);
    }

    /**
     * @return array{0: float, 1: float, 2: ?string}
     */
    private function precioMock(Producto $producto, string $cadena, float $base, float $factor): array
    {
        // Jitter absoluto de ±$0.05 para que las cadenas no queden idénticas.
        $jitter = (($this->semilla($cadena . '|' . $producto->id) % 11) - 5) / 100;
        $normal = max(0.05, round($base * $factor + $jitter, 2));
        $final = $normal;
        $tipoPromocion = null;

        // ~12% de los productos por cadena llevan promoción determinista.
        if ($this->semilla($cadena . '|' . $producto->id . '|promo') % 100 < 12) {
            $tipos = ['descuento_directo', '2x1', '3x2'];
            $tipoPromocion = $tipos[$this->semilla($cadena . '|' . $producto->id . '|tipo') % count($tipos)];

            if ($tipoPromocion === 'descuento_directo') {
                $final = round($normal * 0.9, 2);
            }
        }

        return [$normal, $final, $tipoPromocion];
    }

    private function semilla(string $texto): int
    {
        return (int) sprintf('%u', crc32($texto));
    }
}
