<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class PrecioActual extends Model
{
    protected $table = 'precios_actuales';

    protected $fillable = [
        'producto_id',
        'sucursal_id',
        'precio_normal',
        'precio_final',
        'tiene_promocion',
        'tipo_promocion',
        'fecha_actualizacion',
        'origen_dato',
    ];

    protected $casts = [
        'tiene_promocion' => 'boolean',
        'fecha_actualizacion' => 'datetime',
    ];

    //Relacion directa con los Productos
    public function producto()
    {
        return $this->belongsTo(Producto::class);
    }

    //Relacion inversa con la sucursal
    public function sucursal()
    {
        return $this->belongsTo(Sucursal::class);
    }
}
