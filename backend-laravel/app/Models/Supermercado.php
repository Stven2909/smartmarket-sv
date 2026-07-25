<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Supermercado extends Model
{
    protected $fillable = [
        'nombre', 'logo', 'sitio_web', 'activo'
    ];

    protected $casts = [
        'activo' => 'boolean',
    ];

    //Relacion con sus sucursales
    public function sucursales()
    {
        return $this->hasMany(Sucursal::class);
    }
}
