<?php

namespace App\Services\Optimization;

class DistanceService
{
    /*
     * Distancia en linea recta entre 2 coordenadas, en kilometros.
     * No es la distancia real de manejo (eso requiere un servicio de rutas como las de google)
     * Para esta primera version del MVP es una aproximacion suficiente
     */

    public function calcularHaversine(float $lat1, float $lon1, float $lat2, float $lon2): float
    {
        $radioTierraKm = 6371;

        $dLat = deg2rad($lat2 - $lat1);
        $dLon = deg2rad($lon2 - $lon1);

        $a = sin($dLat / 2) ** 2
            + cos(deg2rad($lat1)) * cos(deg2rad($lat2)) * sin($dLon / 2) ** 2;

        $c = 2 * atan2(sqrt($a), sqrt(1 - $a));

        return round($radioTierraKm * $c, 2);
    }
}
