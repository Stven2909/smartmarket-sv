<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Sucursal extends Model
{
    protected $fillable = [
        'supermercado_id',
        'nombre',
        'direccion',
        'latitud',
        'longitud',
        'telefono',
        'horario',
    ];

    //Relacion inversa con supermercado
    public function supermercado()
    {
        return $this->belongsTo(Supermercado::class);
    }

    //Relacion normal con los preciosActuales
    public function preciosActuales()
    {
        return $this->hasMany(PrecioActual::class);
    }
}
