<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Producto extends Model
{
    protected $fillable = [
        'categoria_id',
        'marca',
        'nombre',
        'presentacion',
        'unidad_medida',
        'contenido',
        'activo',
    ];

    protected $casts = [
        'activo' => 'boolean',
    ];

    //Relaciones
    public function categoria()
    {
        return $this->belongsTo(Categoria::class);
    }

    public function alias()
    {
        return $this->hasMany(AliasProducto::class);
    }

    public function preciosActuales()
    {
        return $this->hasMany(PrecioActual::class);
    }

    public function historialPrecios()
    {
        return $this->hasMany(HistorialPrecio::class);
    }
}
