<?php

namespace App\Services\Optimization;

use App\Models\ListaCompra;
use App\Models\PrecioActual;

class ComparisonService
{
    // Extraído de ListaCompraController::comparar() — cierra la deuda técnica de la
    // Fase 3 (02-arquitectura.md sección 3: "el cálculo... debe vivir en un archivo
    // aparte que se pueda probar y revisar de forma aislada", no en el Controller).
    //
    // Calcula el costo total de una lista en cada sucursal donde haya precios
    // disponibles, cuántos productos esenciales/opcionales encontró, y el beneficio
    // en dólares de las promociones activas ahí (para alimentar el Score después).
    public function comparar(ListaCompra $lista): array
    {
        $detalles = $lista->detalles()->with('producto')->get();

        if ($detalles->isEmpty()) {
            return [
                'lista' => $lista->nombre,
                'presupuesto' => $lista->presupuesto,
                'resultados' => [],
            ];
        }

        $productoIds = $detalles->pluck('producto_id');
        $totalEsenciales = $detalles->where('esencial', true)->count();
        $totalOpcionales = $detalles->where('esencial', false)->count();

        $preciosPorSucursal = PrecioActual::with('sucursal.supermercado')
            ->whereIn('producto_id', $productoIds)
            ->get()
            ->groupBy('sucursal_id');

        $resultados = [];

        foreach ($preciosPorSucursal as $sucursalId => $preciosSucursal) {
            $costoTotal = 0;
            $beneficioPromociones = 0;
            $productosConPromocion = 0;
            $productosDisponibles = 0;
            $esencialesDisponibles = 0;
            $opcionalesDisponibles = 0;

            foreach ($detalles as $detalle) {
                $precio = $preciosSucursal->firstWhere('producto_id', $detalle->producto_id);

                if ($precio) {
                    $productosDisponibles++;
                    $costoTotal += $precio->precio_final * $detalle->cantidad;

                    if ($precio->tiene_promocion) {
                        $beneficioPromociones += ($precio->precio_normal - $precio->precio_final) * $detalle->cantidad;
                        $productosConPromocion++;
                    }

                    if ($detalle->esencial) {
                        $esencialesDisponibles++;
                    } else {
                        $opcionalesDisponibles++;
                    }
                }
            }

            $sucursal = $preciosSucursal->first()->sucursal;
            $origenesPrecio = $preciosSucursal
                ->pluck('origen_dato')
                ->filter(fn ($origen) => is_string($origen) && trim($origen) !== '')
                ->unique()
                ->values()
                ->all();
            $procedencias = $preciosSucursal
                ->map(fn (PrecioActual $precio): string => match ($precio->origen_dato) {
                    'html-super-selectos' => 'sincronizados',
                    'mock-seeder' => 'simulados',
                    'manual' => 'manuales',
                    default => 'desconocidos',
                })
                ->unique()
                ->values();
            $procedenciaPrecios = match ($procedencias->count()) {
                0 => 'desconocidos',
                1 => $procedencias->first(),
                default => 'mixtos',
            };
            $preciosActualizadosEn = $preciosSucursal
                ->pluck('fecha_actualizacion')
                ->filter()
                ->max();

            // Completitud del subtotal. Un producto sin precio en esta sucursal
            // NO suma al costo_total; por eso la UI debe distinguir un subtotal
            // parcial de un precio realmente más bajo (Q/A: listas incompletas).
            $totalProductos = $totalEsenciales + $totalOpcionales;
            $productosFaltantes = $totalProductos - $productosDisponibles;
            $esencialesFaltantes = $totalEsenciales - $esencialesDisponibles;
            $opcionalesFaltantes = $totalOpcionales - $opcionalesDisponibles;

            $resultados[] = [
                'sucursal_id' => $sucursalId,
                'sucursal' => $sucursal->nombre,
                'supermercado_id' => $sucursal->supermercado->id,
                'supermercado' => $sucursal->supermercado->nombre,
                // ADR-11: sin coordenadas (Tienda en línea) se propaga null —
                // castear a float inventaría la ubicación (0°, 0°).
                'latitud' => $sucursal->latitud !== null ? (float) $sucursal->latitud : null,
                'longitud' => $sucursal->longitud !== null ? (float) $sucursal->longitud : null,
                'costo_total' => round($costoTotal, 2),
                'beneficio_promociones' => round($beneficioPromociones, 2),
                'productos_con_promocion' => $productosConPromocion,
                'productos_disponibles' => $productosDisponibles,
                'productos_totales' => $totalProductos,
                'productos_faltantes' => $productosFaltantes,
                'productos_esenciales_disponibles' => $esencialesDisponibles,
                'productos_esenciales_totales' => $totalEsenciales,
                'productos_esenciales_faltantes' => $esencialesFaltantes,
                'productos_opcionales_disponibles' => $opcionalesDisponibles,
                'productos_opcionales_totales' => $totalOpcionales,
                'productos_opcionales_faltantes' => $opcionalesFaltantes,
                'todos_los_esenciales_disponibles' => $esencialesDisponibles === $totalEsenciales,
                'lista_completa' => $productosFaltantes === 0,
                'cobertura_productos' => $totalProductos > 0
                    ? round(($productosDisponibles / $totalProductos) * 100, 1)
                    : 100.0,
                'dentro_del_presupuesto' => $lista->presupuesto === null
                    ? null
                    : $costoTotal <= $lista->presupuesto,
                'procedencia_precios' => $procedenciaPrecios,
                'origenes_precio' => $origenesPrecio,
                'precios_actualizados_en' => $preciosActualizadosEn?->toIso8601String(),
            ];
        }

        usort($resultados, fn ($a, $b) => $a['costo_total'] <=> $b['costo_total']);

        return [
            'lista' => $lista->nombre,
            'presupuesto' => $lista->presupuesto,
            'resultados' => array_values($resultados),
        ];
    }
}
