<?php

namespace App\Models;

use Filament\Models\Contracts\FilamentUser;
use Filament\Panel;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable implements FilamentUser
{
    use HasApiTokens, Notifiable;

    protected $fillable = [
        'name',
        'email',
        'password',
        'rol',
        'estado',
    ];

    protected $hidden = [
        'password',
        'remember_token',
    ];

    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
        ];
    }

    /*
     * Gate del panel /admin (Filament): solo administradores con cuenta activa.
     * Sin este metodo, Filament permite entrar a CUALQUIER usuario autenticado
     * en entornos locales (vendor/filament .../Middleware/Authenticate.php).
     * 'inactivo' funciona como kill-switch: se corta el acceso sin borrar la cuenta.
     */
    public function canAccessPanel(Panel $panel): bool
    {
        return $this->rol === 'admin' && $this->estado === 'activo';
    }

    //Relaciones con los demas modelos
    public function listasCompra()
    {
        return $this->hasMany(ListaCompra::class, 'usuario_id');
    }

    public function esAdmin(): bool
    {
        return $this->rol === 'admin';
    }
}
