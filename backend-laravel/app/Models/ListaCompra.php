<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ListaCompra extends Model
{
    protected $table = 'listas_compra';

    protected $fillable = [
        'usuario_id',
        'nombre',
        'presupuesto',
        'fecha'
    ];

    //Relacion directa con usuario, y los detalles de una lista
    public function usuario()
    {
        return $this->belongsTo(User::class, 'usuario_id');
    }

    public function detalles()
    {
        return $this->hasMany(ListaCompraDetalle::class, 'lista_id');
    }
}
