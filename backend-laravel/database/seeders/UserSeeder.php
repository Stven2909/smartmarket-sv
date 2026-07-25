<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class UserSeeder extends Seeder
{
    // Crea un usuario admin y un usuario normal para poder probar el login
    // y los permisos por rol sin tener que registrarse manualmente.
    public function run(): void
    {
        User::firstOrCreate(
            ['email' => 'admin@smartmarket.sv'],
            [
                'name' => 'Admin SmartMarket',
                'password' => Hash::make('password123'),
                'rol' => 'admin',
                'estado' => 'activo',
            ]
        );

        User::firstOrCreate(
            ['email' => 'usuario@smartmarket.sv'],
            [
                'name' => 'Usuario de Prueba',
                'password' => Hash::make('password123'),
                'rol' => 'usuario',
                'estado' => 'activo',
            ]
        );
    }
}
