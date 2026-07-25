<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class HistorialPrecio extends Model
{
    protected $table = 'historial_precios';

    public $timestamps = false; // solo created_at, sin updated_at

    protected $fillable = [
        'producto_id',
        'sucursal_id',
        'precio_normal',
        'precio_final',
        'tipo_promocion',
        'fecha',
        'origen',
    ];

    protected $casts = [
        'fecha' => 'datetime',
    ];

    //Relacion directa con Producto y la Sucursal
    public function producto()
    {
        return $this->belongsTo(Producto::class);
    }

    public function sucursal()
    {
        return $this->belongsTo(Sucursal::class);
    }
}
