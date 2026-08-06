<?php

namespace App\Observers;

use App\Models\HistorialPrecio;
use App\Models\PrecioActual;

class PrecioActualObserver
{
    // Antes de que un precio cambie, guarda el valor ANTERIOR en HistorialPrecio
    // (tabla append-only, nunca se sobrescribe — ver 02-arquitectura.md sección 8.1
    // y la migración de historial_precios). Así queda registrado "hasta cuándo" ese
    // precio estuvo vigente, sin importar si el cambio viene del admin (Filament) o,
    // más adelante, del scraper automático (v1.1) — nadie tiene que acordarse de
    // llamar esto a mano, sucede automático en cualquier updating().
    public function updating(PrecioActual $precioActual): void
    {
        if ($precioActual->isDirty(['precio_normal', 'precio_final', 'tipo_promocion'])) {
            HistorialPrecio::create([
                'producto_id' => $precioActual->producto_id,
                'sucursal_id' => $precioActual->sucursal_id,
                'precio_normal' => $precioActual->getOriginal('precio_normal'),
                'precio_final' => $precioActual->getOriginal('precio_final'),
                'tipo_promocion' => $precioActual->getOriginal('tipo_promocion'),
                'fecha' => now(),
                'origen' => $precioActual->origen_dato,
            ]);
        }
    }
}
