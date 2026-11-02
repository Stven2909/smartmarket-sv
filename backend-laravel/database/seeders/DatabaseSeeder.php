<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        $this->call([
            UserSeeder::class,
            DemoDataSeeder::class,
            // Refuerza el catálogo con los precios mock de las cadenas que no
            // se sincronizan por webscraping (ADR-012). Idempotente.
            MockSupermarketsSeeder::class,
        ]);
    }
}
