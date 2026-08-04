<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ResultadoOptimizacion extends Model
{
    protected $table = 'resultados_optimizacion';

    protected $fillable = [
        'lista_compra_id',
        'score',
        'ahorro',
        'distancia',
        'tiempo',
        'supermercados',
        'resultado_json',
        'fecha',
    ];

    protected $casts = [
        'supermercados' => 'array',
        'resultado_json' => 'array',
        'fecha' => 'datetime',
    ];

    public function listaCompra(): \Illuminate\Database\Eloquent\Relations\BelongsTo
    {
        return $this->belongsTo(ListaCompra::class, 'lista_compra_id');
    }
}
