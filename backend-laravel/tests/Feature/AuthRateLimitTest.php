<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AuthRateLimitTest extends TestCase
{
    use RefreshDatabase;

    public function test_login_bloquea_despues_de_cinco_intentos_fallidos(): void
    {
        $payload = [
            'email' => 'nadie@example.com',
            'password' => 'contrasena-incorrecta',
        ];

        for ($intento = 1; $intento <= 5; $intento++) {
            $this->postJson('/api/login', $payload)->assertStatus(422);
        }

        $this->postJson('/api/login', $payload)->assertStatus(429);
    }

    public function test_un_login_valido_no_se_ve_afectado_antes_del_limite(): void
    {
        $user = User::create([
            'name' => 'Persona de Prueba',
            'email' => 'persona@example.com',
            'password' => bcrypt('password'),
            'rol' => 'usuario',
            'estado' => 'activo',
        ]);

        $this->postJson('/api/login', [
            'email' => $user->email,
            'password' => 'password',
        ])->assertOk()->assertJsonStructure(['user', 'token']);
    }
}
