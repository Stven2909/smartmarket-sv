<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class FilamentAccessTest extends TestCase
{
    use RefreshDatabase;

    /*
     * Gate de /admin (User::canAccessPanel): solo admins con cuenta activa.
     * Antes de este gate, CUALQUIER usuario autenticado podia entrar al panel
     * en entornos locales — hueco corregido en commit aislado.
     */

    public function test_invitado_es_redirigido_al_login_del_panel(): void
    {
        $this->get('/admin')->assertRedirect('/admin/login');
    }

    public function test_usuario_rol_usuario_recibe_403(): void
    {
        $usuario = User::create([
            'name' => 'Usuario Demo',
            'email' => 'usuario@test.sv',
            'password' => 'password123',
            'rol' => 'usuario',
            'estado' => 'activo',
        ]);

        $this->actingAs($usuario)->get('/admin')->assertForbidden();
    }

    public function test_admin_activo_accede_al_panel(): void
    {
        $admin = User::create([
            'name' => 'Admin Demo',
            'email' => 'admin@test.sv',
            'password' => 'password123',
            'rol' => 'admin',
            'estado' => 'activo',
        ]);

        $this->actingAs($admin)->get('/admin')->assertOk();
    }

    public function test_admin_inactivo_recibe_403_kill_switch(): void
    {
        $admin = User::create([
            'name' => 'Admin Suspendido',
            'email' => 'suspendido@test.sv',
            'password' => 'password123',
            'rol' => 'admin',
            'estado' => 'inactivo',
        ]);

        $this->actingAs($admin)->get('/admin')->assertForbidden();
    }

    public function test_moderador_todavia_no_accede_hasta_definir_sus_permisos(): void
    {
        // Sin insertar en BD: el CHECK de rol en sqlite de pruebas solo permite
        // admin/usuario (la ampliacion a 'moderador' es exclusiva de pgsql).
        // El gate se evalua igual sobre la instancia en memoria.
        $moderador = new User([
            'name' => 'Mod Demo',
            'email' => 'mod@test.sv',
            'password' => 'password123',
            'rol' => 'moderador',
            'estado' => 'activo',
        ]);

        $this->assertFalse($moderador->canAccessPanel(\Filament\Facades\Filament::getPanel('admin')));
    }
}
