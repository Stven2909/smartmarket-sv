<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ListaCompraDetalles extends Model
{
    protected $table = 'lista_compra_detalles';

    protected $fillable = [
        'lista_id',
        'producto_id',
        'cantidad',
        'esencial',
        'permite_sustituto',
    ];

    protected $casts = [
        'esencial' => 'boolean',
        'permite_sustituto' => 'boolean',
    ];

    //Relacion directa con la lista y sus productos
    public function lista()
    {
        return $this->belongsTo(ListaCompra::class, 'lista_id');
    }

    public function producto()
    {
        return $this->belongsTo(Producto::class);
    }
}
