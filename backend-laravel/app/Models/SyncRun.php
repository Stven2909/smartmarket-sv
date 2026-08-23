<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

// Health check por corrida de sincronización (06-referencia-extractor-vtex.md
// §4 punto 5): cada corrida de una fuente registra sus conteos para compararlos
// contra la corrida previa de la misma fuente — caída brusca ⇒ alertar y no
// publicar esa fuente (§6.4 de 02-arquitectura.md).
class SyncRun extends Model
{
    protected $table = 'sync_runs';

    protected $fillable = [
        'fuente',
        'modo',
        'estado',
        'iniciada_en',
        'finalizada_en',
        'productos_obtenidos',
        'productos_nuevos',
        'productos_duplicados',
        'rechazados',
        'detalle',
        'mensaje_error',
    ];

    protected $casts = [
        'iniciada_en' => 'datetime',
        'finalizada_en' => 'datetime',
        'detalle' => 'array',
    ];

    //Registros de staging traídos por esta corrida
    public function productosRaw()
    {
        return $this->hasMany(ProductoRaw::class);
    }
}
