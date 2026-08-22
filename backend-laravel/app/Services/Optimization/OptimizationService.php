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

    // La fórmula del Score, tal cual está congelada en 02-arquitectura.md sección 5.1
    // y actualizada por ADR-05: CostoCombustible ($) se reemplazó por
    // PenalizacionDistancia (normalizada 0–1). Mientras MENOR sea el Score, mejor
    // es la alternativa — es costo ajustado, no una calificación.
    public function calcularScore(float $costoCompra, float $penalizacionDistancia, float $costoTiempo, float $beneficioPromociones): float
    {
        $pesos = config('optimization.pesos');

        return round(
            $pesos['alpha'] * $costoCompra
            + $pesos['beta'] * $penalizacionDistancia
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

            // Pase 1: señales que dependen solo de esta alternativa.
            $resultado['distancia_km'] = $distancia;
            $resultado['tiempo_minutos'] = $this->calcularTiempoMinutos($distancia);
            $resultado['costo_tiempo'] = $this->calcularCostoTiempo($distancia);
        }
        unset($resultado);

        // Normalización de la distancia contra el set (PenalizacionDistancia 0–1):
        // 0 = sucursal más cercana, 1 = la más lejana. Si todas miden lo mismo
        // (o hay una sola alternativa) la penalización es 0. No se dolariza la
        // distancia — sigue ADR-05. Ver 02-arquitectura.md §5.1.
        $distancias = array_column($comparacion['resultados'], 'distancia_km');
        $distanciaMin = min($distancias);
        $distanciaMax = max($distancias);
        $distanciaRango = $distanciaMax - $distanciaMin;

        foreach ($comparacion['resultados'] as &$resultado) {
            // Pase 2: penalización normalizada + Score.
            $penalizacionDistancia = $distanciaRango > 0
                ? round(($resultado['distancia_km'] - $distanciaMin) / $distanciaRango, 4)
                : 0.0;

            $resultado['penalizacion_distancia'] = $penalizacionDistancia;
            $resultado['score'] = $this->calcularScore(
                $resultado['costo_total'],
                $penalizacionDistancia,
                $resultado['costo_tiempo'],
                $resultado['beneficio_promociones'],
            );
        }
        unset($resultado);

        // Menor Score = mejor alternativa.
        usort($comparacion['resultados'], fn ($a, $b) => $a['score'] <=> $b['score']);
        $comparacion['resultados'] = array_values($comparacion['resultados']);

        // "Nivel de optimización" (0-100): posición relativa de cada alternativa dentro
        // del conjunto evaluado, derivada de los Scores reales de la fórmula congelada
        // (02-arquitectura.md §5.1). No es una predicción ni personalización: mide qué
        // tan destacada quedó una opción frente a las demás en esta optimización.
        // Si todas empatan (scorePeor === scoreMejor, ej. una sola sucursal), vale 100.
        $mejorScore = $comparacion['resultados'][0]['score'] ?? null;
        $peorScore = end($comparacion['resultados'])['score'] ?? null;

        foreach ($comparacion['resultados'] as &$resultado) {
            $resultado['nivel_optimizacion'] = ($peorScore !== null && $peorScore > $mejorScore)
                ? round(100 * ($peorScore - $resultado['score']) / ($peorScore - $mejorScore))
                : 100;
        }
        unset($resultado);

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
