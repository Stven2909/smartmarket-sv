<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

// Zona de Staging del Flujo 2 (02-arquitectura.md §6): todo lo que recolecta un
// Price Provider aterriza aquí crudo, nunca directo al Catálogo Maestro.
// Solo datos fácticos como columnas — imágenes/textos promocionales viven
// únicamente dentro de raw_payload como evidencia de auditoría (ADR-10).
class ProductoRaw extends Model
{
    protected $table = 'producto_raw';

    protected $fillable = [
        'fuente',
        'sku_externo',
        'nombre',
        'unidad',
        'categoria_raw',
        'precio_normal',
        'precio_final',
        'tiene_promocion',
        'disponible',
        'url_fuente',
        'raw_payload',
        'estado',
        'motivo_rechazo',
        'sync_run_id',
        'procesado_at',
    ];

    protected $casts = [
        'tiene_promocion' => 'boolean',
        'disponible' => 'boolean',
        'raw_payload' => 'array',
        'procesado_at' => 'datetime',
    ];

    //Corrida de sincronización que trajo este registro
    public function syncRun()
    {
        return $this->belongsTo(SyncRun::class);
    }
}
