<?php

namespace Database\Factories;

use App\Models\HistorialPrecio;
use App\Models\Producto;
use App\Models\Sucursal;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * @extends Factory<HistorialPrecio>
 */
class HistorialPrecioFactory extends Factory
{
    protected static ?string $password;

    protected function definition(): array
    {
        return [
            'producto_id' => Producto::factory(),
            'sucursal_id' => Sucursal::factory(),
            'precio_normal' => fake()->randomFloat(2, 1, 100),
            'precio_final' => fake()->randomFloat(2, 0.5, 99.99),
            'tipo_promocion' => fake()->randomElement(['2x1', 'Descuento', null]),
            'fecha' => fake()->dateTimeBetween('-90 days', 'now'),
            'origen' => fake()->randomElement(['manual', 'scraper', 'api', null]),
        ];
    }
}