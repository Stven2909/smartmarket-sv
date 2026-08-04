<?php

namespace App\Services\Optimization;

use App\Models\ListaCompra;
use App\Models\ResultadoOptimizacion;

class OptimizationService
{
    public function __construct(
        private ComparisonService $comparisonService,
        private DistanceService $distanceService,
    ) {}

    // Tiempo estimado de desplazamiento, en minutos. Supuesto del MVP (velocidad
    // urbana promedio constante) — ver 02-arquitectura.md sección 5.1.
    public function calcularTiempoMinutos(float $distanciaKm): float
    {
        $velocidad = config('optimization.tiempo.velocidad_promedio_kmh');

        return round(($distanciaKm / $velocidad) * 60, 1);
    }

    // Costo en dólares asociado al tiempo de desplazamiento.
    public function calcularCostoTiempo(float $distanciaKm): float
    {
        $costoPorMinuto = config('optimization.tiempo.costo_por_minuto');

        return round($this->calcularTiempoMinutos($distanciaKm) * $costoPorMinuto, 2);
    }

    // La fórmula del Score, tal cual está congelada en 02-arquitectura.md sección 5.1.
    // Mientras MENOR sea el Score, mejor es la alternativa — es costo ajustado, no
    // una calificación.
    public function calcularScore(float $costoCompra, float $costoCombustible, float $costoTiempo, float $beneficioPromociones): float
    {
        $pesos = config('optimization.pesos');

        return round(
            $pesos['alpha'] * $costoCompra
            + $pesos['beta'] * $costoCombustible
            + $pesos['gamma'] * $costoTiempo
            - $pesos['delta'] * $beneficioPromociones,
            4
        );
    }

    // Orquesta todo el flujo: ComparisonService → DistanceService → Score →
    // persistencia en ResultadoOptimizacion. Este es el método que consume el
    // controlador; el controlador no calcula nada, solo coordina la petición.
    public function optimizar(ListaCompra $lista, float $latUsuario, float $lngUsuario): array
    {
        $comparacion = $this->comparisonService->comparar($lista);

        foreach ($comparacion['resultados'] as &$resultado) {
            $distancia = $this->distanceService->calcularHaversine(
                $latUsuario,
                $lngUsuario,
                $resultado['latitud'],
                $resultado['longitud'],
            );

            $costoCombustible = $this->distanceService->calcularCostoCombustible($distancia);
            $tiempoMinutos = $this->calcularTiempoMinutos($distancia);
            $costoTiempo = $this->calcularCostoTiempo($distancia);

            $score = $this->calcularScore(
                $resultado['costo_total'],
                $costoCombustible,
                $costoTiempo,
                $resultado['beneficio_promociones'],
            );

            $resultado['distancia_km'] = $distancia;
            $resultado['costo_combustible'] = $costoCombustible;
            $resultado['tiempo_minutos'] = $tiempoMinutos;
            $resultado['costo_tiempo'] = $costoTiempo;
            $resultado['score'] = $score;
        }
        unset($resultado);

        // Menor Score = mejor alternativa.
        usort($comparacion['resultados'], fn ($a, $b) => $a['score'] <=> $b['score']);
        $comparacion['resultados'] = array_values($comparacion['resultados']);

        $mejorOpcion = $comparacion['resultados'][0] ?? null;
        $peorOpcion = end($comparacion['resultados']) ?: null;

        $resultadoGuardado = null;

        if ($mejorOpcion) {
            $ahorro = $peorOpcion ? round($peorOpcion['costo_total'] - $mejorOpcion['costo_total'], 2) : 0;

            $resultadoGuardado = ResultadoOptimizacion::create([
                'lista_compra_id' => $lista->id,
                'score' => $mejorOpcion['score'],
                'ahorro' => $ahorro,
                'distancia' => $mejorOpcion['distancia_km'],
                'tiempo' => (int) round($mejorOpcion['tiempo_minutos']),
                'supermercados' => array_map(
                    fn ($r) => ['supermercado' => $r['supermercado'], 'sucursal' => $r['sucursal'], 'score' => $r['score']],
                    $comparacion['resultados']
                ),
                'resultado_json' => $comparacion,
                'fecha' => now(),
            ]);
        }

        return [
            'lista' => $comparacion['lista'],
            'presupuesto' => $comparacion['presupuesto'],
            'mejor_opcion' => $mejorOpcion,
            'resultados' => $comparacion['resultados'],
            'resultado_optimizacion_id' => $resultadoGuardado?->id,
        ];
    }
}
