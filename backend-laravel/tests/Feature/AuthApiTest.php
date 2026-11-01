<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AuthApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_registro_crea_usuario_normal_y_devuelve_token(): void
    {
        $respuesta = $this->postJson('/api/register', [
            'name' => 'Persona Nueva',
            'email' => 'nueva@example.com',
            'password' => 'password123',
            'password_confirmation' => 'password123',
        ]);

        $respuesta->assertCreated()->assertJsonStructure(['user', 'token']);

        $this->assertDatabaseHas('users', [
            'email' => 'nueva@example.com',
            'rol' => 'usuario',
            'estado' => 'activo',
        ]);
    }

    public function test_login_con_credenciales_invalidas_devuelve_422(): void
    {
        $this->postJson('/api/login', [
            'email' => 'nadie@example.com',
            'password' => 'incorrecta',
        ])->assertStatus(422)->assertJsonValidationErrors('email');
    }

    public function test_usuario_inactivo_no_puede_iniciar_sesion(): void
    {
        User::create([
            'name' => 'Cuenta Inactiva',
            'email' => 'inactiva@example.com',
            'password' => bcrypt('password123'),
            'rol' => 'usuario',
            'estado' => 'inactivo',
        ]);

        $this->postJson('/api/login', [
            'email' => 'inactiva@example.com',
            'password' => 'password123',
        ])->assertStatus(422)->assertJsonValidationErrors('email');
    }

    public function test_me_requiere_token(): void
    {
        $this->getJson('/api/me')->assertUnauthorized();
    }

    public function test_logout_revoca_el_token_actual(): void
    {
        User::create([
            'name' => 'Persona Activa',
            'email' => 'activa@example.com',
            'password' => bcrypt('password123'),
            'rol' => 'usuario',
            'estado' => 'activo',
        ]);

        $token = $this->postJson('/api/login', [
            'email' => 'activa@example.com',
            'password' => 'password123',
        ])->assertOk()->json('token');

        $this->withToken($token)->getJson('/api/me')->assertOk();
        $this->withToken($token)->postJson('/api/logout')->assertOk();

        $this->assertDatabaseCount('personal_access_tokens', 0);

        // El guard cachea el usuario entre peticiones dentro del mismo test.
        $this->app['auth']->forgetGuards();

        $this->withToken($token)->getJson('/api/me')->assertUnauthorized();
    }
}
